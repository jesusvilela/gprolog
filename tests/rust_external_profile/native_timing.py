#!/usr/bin/env python3
"""Gen21 native matched solve-only timing; separate from Valgrind instrumentation.

Source baseline Gen18 and rejected Gen19 are immutable, release and feature-off.
5 AB/BA blocks x 4 timed solves, 3 untimed warmups per invocation.
Complete ordered answer parity is checked in every process.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile

from fixtures import fixtures

BASE = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"
RETIRED = "c09fff05d9b3dd43fb90014278e3a98d701d3640"


def invoke(exe, source, query, repeat, solutions, root, name):
    rss_path = root / (name + ".rss")
    cmd = [
        "/usr/bin/time", "-f", "%M", "-o", str(rss_path),
        str(exe), str(source), query, str(repeat),
        "3", "4", str(solutions), "200000",
    ]
    result = subprocess.run(
        cmd, text=True, capture_output=True, timeout=100,
        env=dict(os.environ, LC_ALL="C", LANG="C"),
    )
    if result.returncode != 0:
        raise RuntimeError(f"{name} returned {result.returncode}: {result.stderr[:500]}")
    rows = result.stdout.splitlines()
    if len(rows) != 5 or not rows[0].startswith("ANSWERS\t"):
        raise RuntimeError(f"{name}: malformed answer/timing record")
    if not all(x.startswith("NS\t") for x in rows[1:]):
        raise RuntimeError(f"{name}: malformed nanosample prefix")
    samples = [int(x.split("\t", 1)[1]) for x in rows[1:]]
    if not all(x > 0 for x in samples):
        raise RuntimeError(f"{name}: nonpositive sample")
    return {
        "answer": rows[0].split("\t", 1)[1],
        "samples_ns": samples,
        "peak_process_rss_kib": int(rss_path.read_text().strip()),
        "exit": result.returncode, "stderr": result.stderr,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gen18", type=Path, required=True)
    p.add_argument("--gen19", type=Path, required=True)
    p.add_argument("--abi", choices=("elf64", "elf32"), required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    binary = {"gen18": args.gen18.resolve(), "gen19": args.gen19.resolve()}
    if not all(exe.is_file() for exe in binary.values()):
        raise SystemExit("missing immutable Rust external bench executable")

    report = {
        "protocol": "docs/RUST_GEN21_EXTERNAL_PROFILE_PROTOCOL.md",
        "source_commits": {"gen18": BASE, "gen19": RETIRED},
        "abi": args.abi,
        "metric": "native uninstrumented Rust solve-only elapsed nanoseconds",
        "paired_blocks": 5, "samples_per_variant_per_case": 20,
        "tool_independence": "same authored Rust Instant harness, distinct from Valgrind",
        "cells": {}, "errors": [], "failed_gates": [], "passed": False,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="gen21-native-") as folder:
            root = Path(folder)
            frozen = list(fixtures())
            assert len(frozen) == 7
            for name, source, query, repeat, solutions in frozen:
                path = root / (name + ".pl")
                path.write_text(source, encoding="utf-8")
                baseline_answer = None
                blocks = []
                vals = {"gen18": [], "gen19": []}
                for block in range(5):
                    order = ["gen18", "gen19"] if block % 2 == 0 else ["gen19", "gen18"]
                    pair = {"index": block, "order": order}
                    for variant in order:
                        result = invoke(binary[variant], path, query, repeat,
                                        solutions, root, f"{name}-{block}-{variant}")
                        if baseline_answer is None:
                            baseline_answer = result["answer"]
                        elif result["answer"] != baseline_answer:
                            report["errors"].append(f"{name}: ordered answer mismatch {block} {variant}")
                        pair[variant] = result
                        vals[variant].extend(result["samples_ns"])
                    blocks.append(pair)
                median = {k: statistics.median(vals[k]) for k in vals}
                win_count = sum(
                    statistics.median(b["gen19"]["samples_ns"]) >
                    statistics.median(b["gen18"]["samples_ns"]) for b in blocks
                )
                slowdown = median["gen19"] / median["gen18"]
                report["cells"][name] = {
                    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "source_bytes": len(source.encode("utf-8")),
                    "query": query, "repeat": repeat,
                    "max_solutions": solutions, "max_steps": 200000,
                    "ordered_answers": baseline_answer,
                    "median_solve_ns": median,
                    "gen19_over_gen18_solve_ratio": round(slowdown, 6),
                    "gen19_slower_blocks_of_5": win_count,
                    "median_peak_process_rss_kib": {
                        k: statistics.median(b[k]["peak_process_rss_kib"] for b in blocks)
                        for k in vals
                    },
                    "blocks": blocks,
                }
                output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
                print("NATIVE", args.abi, name, "gen18_ns", median["gen18"],
                      "gen19_ns", median["gen19"], "ratio", round(slowdown, 4),
                      "gen19_slower_blocks", win_count, flush=True)
            primary = report["cells"]["first_failure_r128"]
            if primary["gen19_over_gen18_solve_ratio"] < 3.0 or (
                primary["gen19_slower_blocks_of_5"] < 4
            ):
                report["failed_gates"].append("first-fail R128: Gen19 slowdown <3x or <4/5 blocks")
            for name in ("first_success_r128", "t3_first_success_r64", "t1_r128", "builtin_r128"):
                ratio = report["cells"][name]["gen19_over_gen18_solve_ratio"]
                if not (0.85 <= ratio <= 1.15):
                    report["failed_gates"].append(f"{name}: control outside +/-15%: {ratio}")
    except (RuntimeError, OSError, ValueError, AssertionError, subprocess.TimeoutExpired) as exc:
        report["errors"].append(str(exc))
    report["passed"] = (
        not report["errors"] and not report["failed_gates"] and len(report["cells"]) == 7
    )
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("NATIVE_RESULT", args.abi, "passed", report["passed"],
          "errors", report["errors"], "failed_gates", report["failed_gates"],
          flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
