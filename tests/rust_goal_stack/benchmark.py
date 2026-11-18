#!/usr/bin/env python3
"""Gen17 vs Gen18 reversed goal-stack A/B using one shared uninstrumented Rust harness.

All preregistered cases and raw paired measurements retained, including
negative results. Time only Rust solve(); no parser/process-startup attribution.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile

BASE = "46b536889e1b461af9e6cddb7f50239eec5697f5"


def fixtures():
    fact = lambda t, atom="a": f"target({atom}).\n" * t
    deep = "f(g(h(a,b),k(c,d)),[a,b,c],q(r(s(t))))"
    yield ("builtin_r128", "", "true.", 128, 1)
    yield ("single_clause_r128", fact(1), "target(a).", 128, 1)
    yield ("builtin_r64", "", "true.", 64, 1)
    yield ("single_clause_r64", fact(1), "target(a).", 64, 1)
    yield ("t2_r128", fact(2), "target(a).", 128, 1)
    yield ("t16_r64", fact(16), "target(a).", 64, 1)
    yield ("t16_r8_all16", fact(16), "target(a).", 8, 16)
    yield ("deep_t16_r64", fact(16, deep), f"target({deep}).", 64, 1)
    yield ("t16_r1", fact(16), "target(a).", 1, 1)
    yield ("t1_r1", fact(1), "target(a).", 1, 1)
    yield ("t16_r64_all16", fact(16), "target(a).", 64, 16)


def run(exe, source, query, repeat, solutions, work, tag):
    statfile = work / (tag + ".stats")
    cmd = ["/usr/bin/time", "-f", "%M", "-o", str(statfile), str(exe),
           str(source), query, str(repeat), "3", "4", str(solutions), "200000"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, timeout=90,
                       env=dict(os.environ, LANG="C", LC_ALL="C"))
    if p.returncode != 0:
        raise RuntimeError(f"{tag} failed {p.returncode}: {p.stderr[:400]}")
    lines = p.stdout.splitlines()
    if len(lines) != 5 or not lines[0].startswith("ANSWERS\t"):
        raise RuntimeError(f"{tag} unexpected answer lines: {p.stdout[:200]!r}")
    if any(not x.startswith("NS\t") for x in lines[1:]):
        raise RuntimeError(f"{tag} missing raw nanosecond records")
    samples = [int(x.split("\t", 1)[1]) for x in lines[1:]]
    if any(x <= 0 for x in samples):
        raise RuntimeError(f"{tag} nonpositive sample")
    return {"ordered_answers": lines[0].split("\t", 1)[1],
            "samples_ns": samples,
            "peak_process_rss_kib": int(statfile.read_text().strip()),
            "exit": p.returncode, "stderr": p.stderr}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--abi", choices=("elf32", "elf64"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base, candidate = args.baseline.resolve(), args.candidate.resolve()
    if not base.is_file() or not candidate.is_file():
        raise SystemExit("missing benchmark executables")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "protocol": "docs/RUST_NATIVE_REVERSED_GOAL_STACK_PROTOCOL.md",
        "baseline_commit": BASE, "candidate_commit": args.candidate_sha,
        "abi": args.abi,
        "metric": "median uninstrumented direct solve nanoseconds (parser/process excluded)",
        "sampling": "5 AB/BA blocks, 4 timed solves each per variant, 3 warmups per launch",
        "independent_oracle": False, "cross_abi_pooled": False,
        "cases": {}, "errors": [], "performance_kills": [],
        "semantic_pass": False, "performance_pass": False, "passed": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="gprolog-reversed-bench-") as folder:
            work = Path(folder)
            for name, text, query, repeat, solutions in fixtures():
                src = work / (name + ".pl")
                src.write_text(text, encoding="utf-8")
                blocks = []
                raw = {"baseline": [], "candidate": []}
                reference = None
                for block in range(5):
                    order = [("baseline", base), ("candidate", candidate)]
                    if block % 2:
                        order.reverse()
                    pair = {"block": block, "order": [role for role, _ in order]}
                    for role, exe in order:
                        val = run(exe, src, query, repeat, solutions, work,
                                  f"{name}-{block}-{role}")
                        if reference is None:
                            reference = val["ordered_answers"]
                        elif reference != val["ordered_answers"]:
                            report["errors"].append(f"{name}: answer mismatch {role}, block {block}")
                        pair[role] = val
                        raw[role].extend(val["samples_ns"])
                    blocks.append(pair)
                baseline_med = statistics.median(raw["baseline"])
                candidate_med = statistics.median(raw["candidate"])
                reduction = 100 * (1 - candidate_med / baseline_med)
                wins = sum(statistics.median(block["candidate"]["samples_ns"]) <
                           statistics.median(block["baseline"]["samples_ns"]) for block in blocks)
                report["cases"][name] = {
                    "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "source_bytes": len(text.encode()), "query": query, "goals": repeat,
                    "max_solutions": solutions, "max_steps": 200000,
                    "ordered_answer_representation": reference,
                    "baseline_median_solve_ns": baseline_med,
                    "candidate_median_solve_ns": candidate_med,
                    "candidate_reduction_pct": round(reduction, 3),
                    "candidate_faster_blocks_of_5": wins,
                    "baseline_median_peak_rss_kib": statistics.median(x["baseline"]["peak_process_rss_kib"] for x in blocks),
                    "candidate_median_peak_rss_kib": statistics.median(x["candidate"]["peak_process_rss_kib"] for x in blocks),
                    "blocks": blocks
                }
                output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
                print("CASE", args.abi, name, "baseline_ns", baseline_med,
                      "reversed_ns", candidate_med, "reduction_pct",
                      round(reduction, 3), "wins", wins, flush=True)
            report["semantic_pass"] = not report["errors"] and len(report["cases"]) == 11
            for key in ("builtin_r128", "single_clause_r128"):
                cell = report["cases"][key]
                if cell["candidate_reduction_pct"] < 10 or cell["candidate_faster_blocks_of_5"] < 4:
                    report["performance_kills"].append(f"primary {key}: failed >=10% and 4/5 gate")
            for key in ("t16_r1", "t1_r1", "t16_r8_all16", "t16_r64_all16",
                        "t2_r128", "t16_r64", "deep_t16_r64"):
                if report["cases"][key]["candidate_reduction_pct"] < -15:
                    report["performance_kills"].append(f"regression {key}: greater than 15%")
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        report["errors"].append(str(exc))
    report["performance_pass"] = not report["performance_kills"] and len(report["cases"]) == 11
    report["passed"] = report["semantic_pass"] and report["performance_pass"]
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("RESULT", args.abi, "semantic", report["semantic_pass"],
          "performance", report["performance_pass"], "errors", report["errors"],
          "kills", report["performance_kills"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
