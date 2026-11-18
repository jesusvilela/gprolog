#!/usr/bin/env python3
"""Gen18 vs Gen19 two-clause ownership A/B with preregistered failure attacks.

Immutable Rust release builds, common external bench_continuations.rs,
5 alternating AB/BA blocks × 4 direct-solve nanosamples per variant/cell.
The checks report negatives rather than dropping them.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile

BASE = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"
DEEP = "f(g(h(a,b),k(c,d)),[a,b,c],q(r(s(t))))"
DEEP_FAIL = "f(g(h(a,b),k(c,d)),[a,b,c],q(r(s(v))))"


def fixtures():
    facts = lambda t, body="a": (f"target({body}).\n" * t)
    for r in (128, 32):
        yield (f"t2_r{r}_success", facts(2), "target(a).", r, 1)
    for r in (128, 32):
        yield (f"t2_r{r}_deep_success", facts(2, DEEP), f"target({DEEP}).", r, 1)
    for r in (128, 32):
        yield (f"t2_r{r}_first_failure", "target(b).\ntarget(a).\n",
               "target(a).", r, 1)
    yield ("t2_r64_first_failure_deep",
           f"target({DEEP_FAIL}).\ntarget({DEEP}).\n",
           f"target({DEEP}).", 64, 1)
    yield ("t2_r8_all16", facts(2), "target(a).", 8, 16)
    yield ("t2_r1_all2", facts(2), "target(a).", 1, 2)
    yield ("t3_r64_success", facts(3), "target(a).", 64, 1)
    yield ("t16_r64_success", facts(16), "target(a).", 64, 1)
    yield ("t1_r128_success", facts(1), "target(a).", 128, 1)
    yield ("builtin_r128", "", "true.", 128, 1)


def timed(binary, src_path, query, repeat, solutions, work, label):
    stats = work / (label + ".rss")
    command = ["/usr/bin/time", "-f", "%M", "-o", str(stats),
               str(binary), str(src_path), query, str(repeat), "3", "4",
               str(solutions), "200000"]
    p = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, timeout=90,
                       env=dict(os.environ, LANG="C", LC_ALL="C"))
    if p.returncode:
        raise RuntimeError(f"{label}: exit {p.returncode}: {p.stderr[:500]}")
    rows = p.stdout.splitlines()
    if len(rows) != 5 or not rows[0].startswith("ANSWERS\t"):
        raise RuntimeError(f"{label}: malformed answer data {p.stdout[:300]!r}")
    if any(not row.startswith("NS\t") for row in rows[1:]):
        raise RuntimeError(f"{label}: malformed samples")
    times = [int(row.split("\t", 1)[1]) for row in rows[1:]]
    if min(times) <= 0:
        raise RuntimeError(f"{label}: nonpositive time")
    return {"answers": rows[0].split("\t", 1)[1],
            "ns": times, "peak_rss_kib": int(stats.read_text().strip()),
            "stderr": p.stderr, "exit": p.returncode}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--abi", choices=("elf64", "elf32"), required=True)
    p.add_argument("--candidate-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    baseline, candidate = args.baseline.resolve(), args.candidate.resolve()
    for binary in (baseline, candidate):
        if not binary.is_file():
            raise SystemExit(f"missing immutable benchmark executable {binary}")
    report = {
        "protocol": "docs/RUST_NATIVE_TWO_CLAUSE_OWNERSHIP_PROTOCOL.md",
        "baseline_commit": BASE, "candidate_source_sha": args.candidate_sha,
        "abi": args.abi,
        "metric": "median direct solve nanoseconds, not parser or process launch",
        "sampling": "5 paired AB/BA blocks × 4 timed solves per variant; 3 untimed warmups/launch",
        "independent_external_oracle": False,
        "cases": {}, "errors": [], "performance_kills": [],
        "semantic_pass": False, "performance_pass": False, "passed": False,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="gen19-owned-") as folder:
            root = Path(folder)
            data = list(fixtures())
            assert len(data) == 13, len(data)
            for key, content, query, repeat, solutions in data:
                src = root / (key + ".pl")
                src.write_text(content, encoding="utf-8")
                reference = None
                ns = {"baseline": [], "candidate": []}
                blocks = []
                for i in range(5):
                    order = [("baseline", baseline), ("candidate", candidate)]
                    if i % 2: order.reverse()
                    pair = {"block": i, "order": [r for r, _ in order]}
                    for role, binary in order:
                        val = timed(binary, src, query, repeat, solutions, root,
                                    f"{key}-{i}-{role}")
                        if reference is None: reference = val["answers"]
                        elif val["answers"] != reference:
                            report["errors"].append(f"{key}: ordered answers mismatch {i} {role}")
                        pair[role] = val
                        ns[role].extend(val["ns"])
                    blocks.append(pair)
                bmedian = statistics.median(ns["baseline"])
                cmedian = statistics.median(ns["candidate"])
                wins = sum(statistics.median(b["candidate"]["ns"]) <
                           statistics.median(b["baseline"]["ns"]) for b in blocks)
                reduction = round(100.0 * (1 - cmedian / bmedian), 3)
                report["cases"][key] = {
                    "query": query, "goals": repeat, "max_solutions": solutions,
                    "source_sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "source_bytes": len(content.encode()),
                    "ordered_answers": reference,
                    "baseline_median_solve_ns": bmedian,
                    "candidate_median_solve_ns": cmedian,
                    "candidate_reduction_pct": reduction,
                    "candidate_faster_blocks_of_5": wins,
                    "baseline_median_peak_rss_kib": statistics.median(x["baseline"]["peak_rss_kib"] for x in blocks),
                    "candidate_median_peak_rss_kib": statistics.median(x["candidate"]["peak_rss_kib"] for x in blocks),
                    "blocks": blocks,
                }
                report["semantic_pass"] = not report["errors"]
                output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
                print("CASE", args.abi, key, "base_ns", bmedian,
                      "candidate_ns", cmedian, "reduction_pct", reduction,
                      "wins", wins, flush=True)
            report["semantic_pass"] = (not report["errors"] and
                                       len(report["cases"]) == 13)
            for key in ("t2_r128_success", "t2_r32_success"):
                row = report["cases"][key]
                if row["candidate_reduction_pct"] < 5.0 or row["candidate_faster_blocks_of_5"] < 4:
                    report["performance_kills"].append(f"primary {key} did not cross >=5%/4-of-5 gate")
            for key, cell in report["cases"].items():
                if key in ("t2_r128_success", "t2_r32_success"):
                    continue
                if cell["candidate_reduction_pct"] < -10.0:
                    report["performance_kills"].append(f"{key} regressed more than 10%")
    except (RuntimeError, OSError, subprocess.TimeoutExpired, AssertionError) as exc:
        report["errors"].append(str(exc))
    report["performance_pass"] = (not report["performance_kills"] and
                                  len(report["cases"]) == 13)
    report["passed"] = report["semantic_pass"] and report["performance_pass"]
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("RESULT", args.abi, "cases", len(report["cases"]),
          "semantic", report["semantic_pass"], "performance", report["performance_pass"],
          "kills", report["performance_kills"], "errors", report["errors"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
