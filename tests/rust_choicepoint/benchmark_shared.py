#!/usr/bin/env python3
"""Matched immutable Gen16 vs Gen17 Rust-native continuation cost experiment.

All 10 preregistered cells are reported. Compile one shared uninstrumented
Rust harness once against each immutable release library. Time only solve().
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile

BASE = "cd880bda3db495d329bdc3b6a0a0a4f654691579"
PROTOCOL = "docs/RUST_NATIVE_SHARED_CONTINUATIONS_PROTOCOL.md"


def fixtures():
    def fact_program(count, term="a"):
        return f"target({term}).\n" * count

    deep = "f(g(h(a,b),k(c,d)),[a,b,c],q(r(s(t))))"
    yield "primary_t16_r64_first", fact_program(16), "target(a).", 64, 1
    yield "deep_t16_r64_first", fact_program(16, deep), f"target({deep}).", 64, 1
    yield "t2_r64_first", fact_program(2), "target(a).", 64, 1
    yield "t16_r8_first", fact_program(16), "target(a).", 8, 1
    yield "t16_r1_first", fact_program(16), "target(a).", 1, 1
    yield "t1_r64_first", fact_program(1), "target(a).", 64, 1
    yield "builtin_r64_first", fact_program(16), "true.", 64, 1
    yield "t16_r1_all16", fact_program(16), "target(a).", 1, 16
    yield "t16_r8_all16", fact_program(16), "target(a).", 8, 16
    yield "t2_r8_all16", fact_program(2), "target(a).", 8, 16


def run(exe, source, query, repeat, solutions, work, tag):
    statsfile = work / (tag + ".stats")
    cmd = ["/usr/bin/time", "-f", "%M", "-o", str(statsfile),
           str(exe), str(source), query, str(repeat), "3", "4",
           str(solutions), "200000"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, timeout=90,
                       env=dict(os.environ, LC_ALL="C", LANG="C"))
    if p.returncode:
        raise RuntimeError(f"{tag}: exit={p.returncode}, stderr={p.stderr[:400]}")
    lines = p.stdout.splitlines()
    if len(lines) != 5 or not lines[0].startswith("ANSWERS\t"):
        raise RuntimeError(f"{tag}: malformed answer/timing record {p.stdout[:320]!r}")
    if not all(line.startswith("NS\t") for line in lines[1:]):
        raise RuntimeError(f"{tag}: missing raw nanosecond samples")
    values = [int(line.split("\t", 1)[1]) for line in lines[1:]]
    if any(x <= 0 for x in values):
        raise RuntimeError(f"{tag}: nonpositive sample")
    return {
        "answer_repr": lines[0].split("\t", 1)[1],
        "samples_ns": values,
        "process_peak_rss_kib": int(statsfile.read_text().strip()),
        "exit_code": p.returncode,
        "stderr": p.stderr,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--abi", choices=("elf64", "elf32"), required=True)
    p.add_argument("--candidate-commit", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    baseline = args.baseline.resolve()
    candidate = args.candidate.resolve()
    for exe in (baseline, candidate):
        if not exe.is_file():
            raise SystemExit(f"missing compiled Rust harness: {exe}")

    report = {
        "protocol": PROTOCOL, "baseline_commit": BASE,
        "candidate_commit": args.candidate_commit,
        "abi": args.abi,
        "metric": "per-solve nanos only (parsing/launch excluded)",
        "method": "5 AB/BA paired blocks x 4 raw nanosecond samples each; 3 unmeasured warmups per launch; Rust 1.85.1, release, same ABI",
        "independent_external_witness": False,
        "all_cases": {}, "errors": [], "performance_kills": [],
        "semantic_pass": False, "primary_gate": False,
    }
    dest = args.output.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="gprolog-continuations-") as folder:
            work = Path(folder)
            for key, program, query, repeat, solutions in fixtures():
                path = work / (key + ".pl")
                path.write_text(program, encoding="utf-8")
                blocks = []
                reference = None
                samples = {"baseline": [], "candidate": []}
                for block in range(5):
                    ordered = [("baseline", baseline), ("candidate", candidate)]
                    if block % 2: ordered.reverse()
                    pair = {"block": block, "order": [kind for kind, _ in ordered]}
                    for kind, exe in ordered:
                        result = run(exe, path, query, repeat, solutions, work, f"{key}-{block}-{kind}")
                        if reference is None:
                            reference = result["answer_repr"]
                        if result["answer_repr"] != reference:
                            report["errors"].append(f"{key}: answer parity mismatch in block {block} {kind}")
                        pair[kind] = result
                        samples[kind].extend(result["samples_ns"])
                    blocks.append(pair)
                bmed = statistics.median(samples["baseline"])
                cmed = statistics.median(samples["candidate"])
                wins = sum(statistics.median(x["candidate"]["samples_ns"]) <
                           statistics.median(x["baseline"]["samples_ns"]) for x in blocks)
                improvement = 100 * (1 - cmed / bmed)
                data = {
                    "query": query, "program_sha256": hashlib.sha256(program.encode()).hexdigest(),
                    "program_bytes": len(program.encode()), "repeat_goals": repeat,
                    "max_solutions": solutions, "max_steps": 200000,
                    "ordered_answer_repr": reference,
                    "baseline_median_solve_ns": bmed, "candidate_median_solve_ns": cmed,
                    "candidate_reduction_pct": round(improvement, 3),
                    "candidate_faster_blocks_of_5": wins,
                    "baseline_median_peak_rss_kib": statistics.median(x["baseline"]["process_peak_rss_kib"] for x in blocks),
                    "candidate_median_peak_rss_kib": statistics.median(x["candidate"]["process_peak_rss_kib"] for x in blocks),
                    "blocks": blocks
                }
                report["all_cases"][key] = data
                # Every observation is durably flushed before potential gate failure.
                dest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
                print(f"CASE {args.abi} {key} baseline={bmed:.1f}ns "
                      f"shared={cmed:.1f}ns reduction={improvement:.2f}% "
                      f"wins={wins}/5", flush=True)
            report["semantic_pass"] = not report["errors"] and len(report["all_cases"]) == 10
            primary = report["all_cases"]["primary_t16_r64_first"]
            report["primary_gate"] = (primary["candidate_reduction_pct"] >= 10
                                      and primary["candidate_faster_blocks_of_5"] >= 4)
            if not report["primary_gate"]:
                report["performance_kills"].append("preregistered primary >=10% / >=4-of-5 gate missed")
            for case in ("t16_r1_first", "t1_r64_first"):
                if report["all_cases"][case]["candidate_reduction_pct"] < -10:
                    report["performance_kills"].append(f"negative control {case} regressed over 10%")
            for case in ("t16_r1_all16", "t16_r8_all16", "t2_r8_all16"):
                if report["all_cases"][case]["candidate_reduction_pct"] < -15:
                    report["performance_kills"].append(f"enumeration {case} regressed over 15%")
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        report["errors"].append(str(exc))
    report["passed"] = report["semantic_pass"] and not report["performance_kills"]
    dest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("RESULT", args.abi, "semantic_pass", report["semantic_pass"],
          "primary_gate", report["primary_gate"],
          "performance_kills", report["performance_kills"],
          "errors", report["errors"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
