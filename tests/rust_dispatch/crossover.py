#!/usr/bin/env python3
"""Frozen Gen13-vs-Gen14 direct-solve crossover grid and negative controls.

This experiment does not change the solver or select the best-looking cases.
It uses the SAME external Rust bench_solve.rs for each immutable code version.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile

BASELINE_COMMIT = "dd6375e3fff21026b603c7944dd617ed9b391163"
CANDIDATE_COMMIT = "10bd90602502e55f04d0eaafbe71b47de496b3e3"
REPEATS = (1, 8, 64)
TOTAL_CLAUSES = (1, 64, 1024, 10000)
MATCHING_HEADS = (1, 16)


def source_program(n, target_heads, layout="interleaved", distinct_noise=True):
    if not 1 <= target_heads <= n:
        raise ValueError("invalid target count")
    if layout == "grouped":
        positions = set(range(target_heads))
    elif layout == "interleaved":
        positions = {(j + 1) * n // (target_heads + 1)
                     for j in range(target_heads)}
    else:
        raise ValueError("unsupported source layout")
    if len(positions) != target_heads:
        raise AssertionError("target placement collapsed")
    parts = []
    noise_id = 0
    for i in range(n):
        if i in positions:
            parts.append("target(a).\n")
        else:
            head = f"noise{noise_id:05d}" if distinct_noise else "noise"
            parts.append(f"{head}(a).\n")
            noise_id += 1
    return "".join(parts)


def cases():
    for n in TOTAL_CLAUSES:
        for t in MATCHING_HEADS:
            if t > n:
                continue
            content = source_program(n, t)
            for repeats in REPEATS:
                yield (f"grid_n{n}_t{t}_r{repeats}", content,
                       "target(a).", repeats, "grid", n, t)
    # Explicit negative controls and representation attacks.
    yield ("builtin_only_10000", source_program(10000, 1)
           .replace("target(a).\n", "noise99999(a).\n"),
           "true.", 64, "builtin-only", 10000, 0)
    yield ("grouped_10000_t16_r64", source_program(10000, 16, "grouped"),
           "target(a).", 64, "reordered target heads", 10000, 16)
    yield ("shared_functor_10000_t1_r64",
           source_program(10000, 1, distinct_noise=False),
           "target(a).", 64, "same-functor distractors", 10000, 1)


def run_harness(executable, src, query, repeats, label, work):
    env = dict(os.environ, LC_ALL="C", LANG="C")
    stats_file = work / (label + ".stats")
    args = ["/usr/bin/time", "-f", "%M", "-o", str(stats_file),
            str(executable), str(src), query, str(repeats), "3", "4"]
    process = subprocess.run(args, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True,
                             env=env, timeout=90)
    if process.returncode != 0:
        raise RuntimeError(f"{label}: exit {process.returncode}: "
                           + process.stderr[:400])
    lines = process.stdout.splitlines()
    if len(lines) != 5 or not lines[0].startswith("ANSWERS\t"):
        raise RuntimeError(f"{label}: unexpected benchmark output "
                           + repr(process.stdout[:350]))
    if any(not value.startswith("NS\t") for value in lines[1:]):
        raise RuntimeError(f"{label}: missing raw times")
    raw = [int(value.split("\t", 1)[1]) for value in lines[1:]]
    if not all(value > 0 for value in raw):
        raise RuntimeError(f"{label}: nonpositive time")
    return {"nanos": raw, "answers": lines[0].split("\t", 1)[1],
            "peak_rss_kib": int(stats_file.read_text().strip()),
            "stderr": process.stderr, "exit": process.returncode}


def unknown_predicate_parity(baseline_cli, candidate_cli, work):
    program = work / "unknown.pl"
    content = source_program(10000, 1)
    program.write_text(content, encoding="utf-8")
    outcomes = {}
    for role, executable in (("baseline", baseline_cli),
                             ("candidate", candidate_cli)):
        p = subprocess.run([str(executable), str(program), "missing(a).",
                            "--max-steps", "200000",
                            "--max-solutions", "1"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=90,
                           env=dict(os.environ, LC_ALL="C", LANG="C"))
        outcomes[role] = {"returncode": p.returncode,
                          "stdout": p.stdout, "stderr": p.stderr}
    equal = outcomes["baseline"] == outcomes["candidate"]
    valid_error = outcomes["baseline"]["returncode"] != 0
    return {"passed": equal and valid_error, "results": outcomes,
            "source_sha256": hashlib.sha256(content.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline-cli", type=Path, required=True)
    parser.add_argument("--candidate-cli", type=Path, required=True)
    parser.add_argument("--abi", choices=("elf32", "elf64"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.baseline, args.candidate, args.baseline_cli,
                 args.candidate_cli):
        if not path.is_file():
            raise SystemExit(f"missing executable {path}")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "protocol": "docs/RUST_NATIVE_DISPATCH_CROSSOVER_PROTOCOL.md",
        "baseline_commit": BASELINE_COMMIT, "candidate_commit": CANDIDATE_COMMIT,
        "abi": args.abi,
        "metric": "nanoseconds, Rust solve() only, parsing and process launch excluded",
        "sampling": "five alternating AB/BA blocks, 4 raw samples per role per block, 3 warmups per launch",
        "benefit_decision_rule": ">=10% lower candidate median and >=4/5 candidate-faster paired block medians",
        "cross_abi_pooled": False,
        "independent_external_witness": False,
        "cases": {}, "black_box_unknown": None, "errors": [], "passed": False
    }
    try:
        with tempfile.TemporaryDirectory(prefix="rust-dispatch-crossover-") as folder:
            work = Path(folder)
            unknown = unknown_predicate_parity(args.baseline_cli.resolve(),
                                              args.candidate_cli.resolve(), work)
            report["black_box_unknown"] = unknown
            if not unknown["passed"]:
                report["errors"].append("unknown predicate CLI parity mismatch")
            for key, content, query, repetitions, kind, n, t in cases():
                source = work / (key + ".pl")
                source.write_text(content, encoding="utf-8")
                observations = []
                all_raw = {"baseline": [], "candidate": []}
                reference = None
                for block in range(5):
                    sequence = [("baseline", args.baseline.resolve()),
                                ("candidate", args.candidate.resolve())]
                    if block % 2:
                        sequence.reverse()
                    pair = {"block": block, "run_order": [v[0] for v in sequence]}
                    for role, binary in sequence:
                        observed = run_harness(binary, source, query,
                                               repetitions,
                                               f"{key}-{block}-{role}", work)
                        pair[role] = observed
                        all_raw[role].extend(observed["nanos"])
                        if reference is None:
                            reference = observed["answers"]
                        elif observed["answers"] != reference:
                            report["errors"].append(f"{key} answer mismatch {role} {block}")
                    observations.append(pair)
                med_baseline = statistics.median(all_raw["baseline"])
                med_candidate = statistics.median(all_raw["candidate"])
                wins = sum(statistics.median(block["candidate"]["nanos"]) <
                           statistics.median(block["baseline"]["nanos"])
                           for block in observations)
                ratio = med_candidate / med_baseline
                report["cases"][key] = {
                    "class": kind, "n": n, "target_head_count": t,
                    "repeated_goals": repetitions, "program_bytes": len(content.encode()),
                    "source_sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "query": query, "full_answer_representation": reference,
                    "baseline_median_solve_ns": med_baseline,
                    "candidate_median_solve_ns": med_candidate,
                    "candidate_change_pct": round(100 * (ratio - 1), 3),
                    "candidate_faster_blocks_of_5": wins,
                    "benefit_gate": ratio <= 0.9 and wins >= 4,
                    "baseline_median_rss_kib": statistics.median(
                        pair["baseline"]["peak_rss_kib"] for pair in observations),
                    "candidate_median_rss_kib": statistics.median(
                        pair["candidate"]["peak_rss_kib"] for pair in observations),
                    "blocks": observations
                }
                report["passed"] = not report["errors"]
                output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
                print(f"CASE {args.abi} {key} N={n} T={t} R={repetitions} "
                      f"B={med_baseline:.1f}ns C={med_candidate:.1f}ns "
                      f"change={100 * (ratio - 1):.2f}% wins={wins}/5", flush=True)
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        report["errors"].append(str(exc))
    report["passed"] = not report["errors"]
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(f"SUMMARY {args.abi} {len(report['cases'])} cases "
          f"passed={report['passed']} errors={report['errors']}", flush=True)
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
