#!/usr/bin/env python3
"""Gen23 native Rust list-task transfer audit, no interpreter modification.

Frozen Gen18/retired Gen19 source, author-reconstructed external list
relations, independent Python list algebra oracle, 5 matched AB/BA blocks
per case/ABI and complete ordered direct-solve representation parity.
A negative result is retained unmodified, not rescued by changing inputs.
"""
from pathlib import Path
import argparse
import json
import os
import statistics
import subprocess
import tempfile

from fixtures import cases, self_test

GEN18 = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"
GEN19 = "c09fff05d9b3dd43fb90014278e3a98d701d3640"


def run_cli(exe, source, case):
    cmd = [
        str(exe), str(source), case.query,
        "--max-solutions", str(case.max_solutions),
        "--max-steps", "100000",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60,
        env=dict(os.environ, LC_ALL="C", LANG="C"),
    )
    return {"exit": result.returncode, "stdout": result.stdout,
            "stderr": result.stderr, "argv": cmd}


def run_benchmark(exe, source, case, workdir, label):
    rss = workdir / (label + ".rss")
    cmd = [
        "/usr/bin/time", "-f", "%M", "-o", str(rss),
        str(exe), str(source), case.query, str(case.repeat),
        "3", "4", str(case.max_solutions), "100000",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=90,
        env=dict(os.environ, LC_ALL="C", LANG="C"),
    )
    if result.returncode:
        raise RuntimeError(
            f"{case.name} {label}: failed benchmark exit={result.returncode}: "
            f"{result.stderr[:600]}"
        )
    lines = result.stdout.splitlines()
    if len(lines) != 5 or not lines[0].startswith("ANSWERS\t"):
        raise RuntimeError(f"{case.name} {label}: invalid answer/sample row count {len(lines)}")
    if any(not line.startswith("NS\t") for line in lines[1:]):
        raise RuntimeError(f"{case.name} {label}: missing nanosecond sample marker")
    nanos = [int(x.split("\t",1)[1]) for x in lines[1:]]
    if min(nanos) <= 0:
        raise RuntimeError(f"{case.name} {label}: nonpositive nanosecond sample")
    return {"ordered_debug_answers": lines[0].split("\t",1)[1],
            "raw_solve_ns": nanos, "process_peak_rss_kib": int(rss.read_text()),
            "exit": result.returncode, "stderr": result.stderr}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for variant in ("gen18", "gen19"):
        parser.add_argument(f"--{variant}-cli", type=Path, required=True)
        parser.add_argument(f"--{variant}-bench", type=Path, required=True)
    parser.add_argument("--abi", choices=("elf64", "elf32"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    self_test()
    bins = {
        variant: {"cli": getattr(args, variant+"_cli").resolve(),
                  "bench": getattr(args, variant+"_bench").resolve()}
        for variant in ("gen18", "gen19")
    }
    if any(not p.is_file() for part in bins.values() for p in part.values()):
        raise SystemExit("frozen Rust feature-disabled binaries missing")
    report = {
        "protocol": "docs/RUST_GEN23_PUBLISHED_LIST_PROTOCOL.md",
        "baseline_source_sha": GEN18, "rejected_source_sha": GEN19,
        "abi": args.abi, "case_count": 14, "external_task_case_count": 12,
        "published_relation_not_third_party_benchmark_code": True,
        "metric": "native direct solve nanoseconds, not CLI or parser",
        "sampler": "5 AB/BA paired blocks x 4 timed calls each, 3 warmups",
        "cells": {}, "errors": [], "failed_controls": [],
        "semantic_pass": False, "measurement_pass": False,
        "passed": False,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="gen23-published-") as tmp:
            work = Path(tmp)
            frozen = list(cases())
            if len(frozen) != 14:
                raise RuntimeError("external task corpus changed after preregistration")
            for c in frozen:
                source = work / (c.name + ".pl")
                source.write_text(c.source, encoding="utf-8")
                expected = {"stdout": c.expected_stdout, "stderr": "", "exit": 0}
                cli = {role: run_cli(bins[role]["cli"], source, c)
                       for role in ("gen18", "gen19")}
                for role, rec in cli.items():
                    for key, value in expected.items():
                        if rec[key] != value:
                            report["errors"].append(
                                f"{c.name}/{role}/{key}: expected {value!r}, got {rec[key]!r}")
                if tuple(cli["gen18"][key] for key in expected) != tuple(
                    cli["gen19"][key] for key in expected
                ):
                    report["errors"].append(f"{c.name}: native CLI semantic differential mismatch")
                if report["errors"]:
                    report["cells"][c.name] = {
                        **c.as_metadata(), "cli": cli, "failed_before_benchmark": True
                    }
                    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
                    raise RuntimeError(f"semantic oracle failure at {c.name}; stop before timing")
                times = {"gen18": [], "gen19": []}
                blocks = []
                expected_debug = None
                for block in range(5):
                    order = ("gen18","gen19") if block%2 == 0 else ("gen19","gen18")
                    record = {"block": block, "order": list(order)}
                    for role in order:
                        raw = run_benchmark(bins[role]["bench"], source, c, work,
                                            f"{c.name}-{block}-{role}")
                        if expected_debug is None:
                            expected_debug = raw["ordered_debug_answers"]
                        elif raw["ordered_debug_answers"] != expected_debug:
                            report["errors"].append(f"{c.name}: ordered debug answers differ")
                        record[role] = raw
                        times[role].extend(raw["raw_solve_ns"])
                    blocks.append(record)
                medians = {role: statistics.median(values)
                           for role, values in times.items()}
                ratio = medians["gen19"] / medians["gen18"]
                slower_blocks = sum(
                    statistics.median(block["gen19"]["raw_solve_ns"]) >
                    statistics.median(block["gen18"]["raw_solve_ns"])
                    for block in blocks
                )
                report["cells"][c.name] = {
                    **c.as_metadata(), "cli": cli, "oracle_passed": True,
                    "ordered_debug_answers": expected_debug,
                    "median_solve_ns": medians,
                    "gen19_over_gen18_ratio": round(ratio,6),
                    "gen19_slower_blocks_of_5": slower_blocks,
                    "blocks": blocks,
                }
                output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
                print("GEN23",args.abi,c.name,"gen18_ns",medians["gen18"],
                      "gen19_ns",medians["gen19"],"ratio",round(ratio,4),
                      "gen19_slower_blocks",slower_blocks,flush=True)
            for name in ("single_fact_r8","builtin_true_r8"):
                cell = report["cells"][name]
                if not (0.8 <= cell["gen19_over_gen18_ratio"] <= 1.2):
                    report["failed_controls"].append(
                        f"{name}: outside unchanged-path [0.8,1.2] control"
                    )
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        report["errors"].append(str(error))
    report["semantic_pass"] = (
        not report["errors"] and len(report["cells"]) == 14
        and all(cell.get("oracle_passed") for cell in report["cells"].values())
    )
    report["measurement_pass"] = (
        not report["failed_controls"] and len(report["cells"]) == 14
    )
    report["passed"] = report["semantic_pass"] and report["measurement_pass"]
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("GEN23_RESULT",args.abi,"cases",len(report["cells"]),
          "oracle",report["semantic_pass"],"controls",report["measurement_pass"],
          "passed",report["passed"],"errors",report["errors"],
          "failed_controls",report["failed_controls"],flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
