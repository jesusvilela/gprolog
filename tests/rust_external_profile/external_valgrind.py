#!/usr/bin/env python3
"""Generation 21 third-party Valgrind DHAT/Callgrind witness, ELF64 only.

The binary and parser are common across frozen Rust library versions.
Metrics are PROCESS-WIDE. Valgrind-instrumented elapsed time is unusable
as native solve time. PREPARE controls bound parser and startup overhead
but do NOT make per-solve DHAT deltas exact by subtraction.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from fixtures import valgrind_fixtures

GEN18 = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"
GEN19 = "c09fff05d9b3dd43fb90014278e3a98d701d3640"
DHAT_TOTAL = re.compile(r"Total:\s*([\d,]+)\s+bytes\s+in\s+([\d,]+)\s+blocks")
PREFIX = "docs/RUST_GEN21_EXTERNAL_PROFILE_PROTOCOL.md"


def run_profile(exe, source, query, repeats, solutions, mode, tool, destination, label):
    root = destination.resolve()
    root.mkdir(parents=True, exist_ok=True)
    tool_log = root / (label + ".valgrind.log")
    out_file = root / (label + (".dhat.json" if tool == "dhat" else ".callgrind.txt"))
    if tool == "dhat":
        flags = ["--tool=dhat", f"--dhat-out-file={out_file}"]
    else:
        flags = ["--tool=callgrind", "--cache-sim=no", "--branch-sim=no",
                 f"--callgrind-out-file={out_file}"]
    cmd = [
        "valgrind", "--error-exitcode=97",
        f"--log-file={tool_log}", *flags, str(exe),
        mode, str(source), query, str(repeats), str(solutions), "200000",
    ]
    done = subprocess.run(cmd, capture_output=True, text=True, timeout=150,
                          env=dict(os.environ, LC_ALL="C", LANG="C"))
    if done.returncode:
        raise RuntimeError(f"{label}: exit={done.returncode} stderr={done.stderr[:250]} "
                           f"log_tail={tool_log.read_text()[-400:] if tool_log.exists() else 'missing'}")
    if not out_file.exists() or not tool_log.exists():
        raise RuntimeError(f"{label}: missing Valgrind output/log")
    expected = "PREPARED\t" if mode == "PREPARE" else "ANSWERS\t"
    actual = done.stdout.strip()
    if not actual.startswith(expected) or "\n" in actual:
        raise RuntimeError(f"{label}: malformed Valgrind-instrumented answer: {actual[:180]!r}")
    if tool == "dhat":
        source_text = tool_log.read_text(errors="replace")
        found = DHAT_TOTAL.search(source_text)
        if not found:
            raise RuntimeError(f"{label}: DHAT total not present in log {source_text[-900:]!r}")
        metrics = {"whole_process_allocated_bytes": int(found.group(1).replace(",", "")),
                   "whole_process_heap_blocks": int(found.group(2).replace(",", ""))}
        # Also require machine-readable external DHAT output to exist.
        raw = json.loads(out_file.read_text())
        if not isinstance(raw, dict) or not raw:
            raise RuntimeError(f"{label}: malformed DHAT JSON")
    else:
        text = out_file.read_text(errors="replace")
        events = re.findall(r"^events:\s*(.+)$", text, flags=re.M)
        summaries = re.findall(r"^summary:\s*(.+)$", text, flags=re.M)
        if not events or not summaries:
            raise RuntimeError(f"{label}: Callgrind events/summary missing")
        names = events[-1].split()
        values = [int(v) for v in summaries[-1].split()]
        if len(names) != len(values) or "Ir" not in names:
            raise RuntimeError(f"{label}: invalid Callgrind column schema")
        metrics = {"process_dynamic_instruction_refs": values[names.index("Ir")],
                   "callgrind_event_columns": names}
    if any(v < 0 for v in metrics.values() if isinstance(v, int)):
        raise RuntimeError(f"{label}: negative external counter")
    return {"command": cmd, "output": actual, "exit": done.returncode,
            "raw_profile_file": str(out_file), "valgrind_log_file": str(tool_log),
            "metrics": metrics}


def ratio(candidate, baseline):
    if baseline <= 0:
        raise ValueError("zero baseline external counter")
    return round(candidate / baseline, 6)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gen18", type=Path, required=True)
    p.add_argument("--gen19", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--raw-dir", type=Path, required=True)
    args = p.parse_args()
    binaries = {"gen18": args.gen18.resolve(), "gen19": args.gen19.resolve()}
    if not all(x.is_file() for x in binaries.values()):
        raise SystemExit("missing frozen external Rust profiler executable")
    v = subprocess.run(["valgrind", "--version"], text=True, capture_output=True,
                       check=True).stdout.strip()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "protocol": PREFIX, "abi": "elf64",
        "sources": {"gen18": GEN18, "gen19": GEN19},
        "third_party_instrument": v,
        "metric_scope": "whole-process under Valgrind; includes parser/process startup and output",
        "independent_author": False,
        "cells": {}, "errors": [], "failed_gates": [], "passed": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="gen21-external-") as temp:
            work = Path(temp)
            cases = list(valgrind_fixtures())
            assert len(cases) == 6, len(cases)
            for case, contents, query, repeats, solutions in cases:
                src = work / (case + ".pl")
                src.write_text(contents, encoding="utf-8")
                profile = {}
                answer_reference = {}
                for tool in ("dhat", "callgrind"):
                    for mode in ("PREPARE", "SOLVE"):
                        profile.setdefault(tool, {})
                        for name in ("gen18", "gen19"):
                            label = f"{case}-{name}-{mode.lower()}-{tool}"
                            rec = run_profile(binaries[name], src, query, repeats,
                                              solutions, mode, tool, args.raw_dir, label)
                            previous = answer_reference.get(mode)
                            if previous is not None and rec["output"] != previous:
                                report["errors"].append(f"{case}: output differs by build/tool in {mode}")
                            else:
                                answer_reference[mode] = rec["output"]
                            profile[tool].setdefault(mode, {})[name] = rec
                dhat_18 = profile["dhat"]["SOLVE"]["gen18"]["metrics"]
                dhat_19 = profile["dhat"]["SOLVE"]["gen19"]["metrics"]
                cg_18 = profile["callgrind"]["SOLVE"]["gen18"]["metrics"]
                cg_19 = profile["callgrind"]["SOLVE"]["gen19"]["metrics"]
                metrics = {
                    "dhat_blocks_ratio": ratio(dhat_19["whole_process_heap_blocks"],
                                               dhat_18["whole_process_heap_blocks"]),
                    "dhat_bytes_ratio": ratio(dhat_19["whole_process_allocated_bytes"],
                                              dhat_18["whole_process_allocated_bytes"]),
                    "callgrind_instruction_ratio": ratio(
                        cg_19["process_dynamic_instruction_refs"],
                        cg_18["process_dynamic_instruction_refs"]),
                }
                report["cells"][case] = {
                    "program_sha256": hashlib.sha256(contents.encode()).hexdigest(),
                    "program_bytes": len(contents.encode()),
                    "query": query, "repeats": repeats, "max_solutions": solutions,
                    "modes": profile, "candidate_over_baseline": metrics,
                }
                output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
                print("VALGRIND", case, "ratios", metrics, flush=True)

            primary = report["cells"]["first_failure_r128"]["candidate_over_baseline"]
            if primary["dhat_blocks_ratio"] < 3.0:
                report["failed_gates"].append("first-failure DHAT process-wide blocks <3x")
            if primary["dhat_bytes_ratio"] < 3.0:
                report["failed_gates"].append("first-failure DHAT process-wide bytes <3x")
            if primary["callgrind_instruction_ratio"] < 2.0:
                report["failed_gates"].append("first-failure Callgrind process-wide instructions <2x")
            control = report["cells"]["t3_first_success_r64"]["candidate_over_baseline"]
            if any(not (0.9 <= val <= 1.1) for val in control.values()):
                report["failed_gates"].append("T3 same-ownership control differs by more than 10%")
    except (OSError, RuntimeError, ValueError, AssertionError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        report["errors"].append(str(exc))
    report["passed"] = (
        not report["errors"] and not report["failed_gates"] and len(report["cells"]) == 6
    )
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("VALGRIND_RESULT", report["passed"], "cases", len(report["cells"]),
          "errors", report["errors"], "failed_gates", report["failed_gates"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
