#!/usr/bin/env python3
"""Matched Rust-native Generation 13 vs 14 direct-solve benchmark.

The one shared source-level harness is compiled independently against the two
immutable Rust libraries. It parses source/query before each timed series and
times only solve(). Same target, compiler, source bytes, query and limits.
Raw nanoseconds, answer representations and Linux /usr/bin/time peak RSS are
retained. No timing/ratio threshold gates semantic correctness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

GEN13_COMMIT = "dd6375e3fff21026b603c7944dd617ed9b391163"
GEN14_PROTOCOL = "docs/RUST_NATIVE_DISPATCH_PROTOCOL.md"

def fixtures():
    # Program size under the Rust parser's 2 MB limit. Distractors are in
    # separate functors, hence each should be irrelevant to target/1.
    noisy = "".join(f"noise{i:05d}(v).\n" for i in range(10_000))
    middle = len(noisy) // 2
    # Split at a newline; source is intentionally interleaved, not grouped.
    first, second = noisy[:middle], noisy[middle:]
    source = first + "target(a).\n" + second
    return (
        ("sparse_96", source, "target(a).", 96, "primary: 10k unrelated clauses, 96 target calls"),
        ("single_1", source, "target(a).", 1, "control: index constructed for one target call"),
        ("builtin_96", source, "true.", 96, "negative control: index constructed but never queried"),
        ("tiny_96", "target(a).\n", "target(a).", 96, "control: no unrelated predicates"),
    )

def run(exe, source, query, repeat, abi, work, label):
    timing = work / f"time-{label}.txt"
    command = ["/usr/bin/time", "-f", "%M", "-o", str(timing),
               str(exe), str(source), query, str(repeat), "3", "4"]
    started = time.perf_counter_ns()
    p = subprocess.run(command, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True,
                       env=dict(os.environ, LC_ALL="C", LANG="C"),
                       timeout=90, check=False)
    total = time.perf_counter_ns() - started
    if p.returncode != 0:
        raise RuntimeError(f"{label}: executable exit {p.returncode}: {p.stderr[:500]}")
    lines = p.stdout.splitlines()
    if len(lines) != 5 or not lines[0].startswith("ANSWERS\t"):
        raise RuntimeError(f"{label}: malformed harness output: {p.stdout[:500]!r}")
    if not all(line.startswith("NS\t") for line in lines[1:]):
        raise RuntimeError(f"{label}: missing raw time lines")
    nanos = [int(line.split("\t", 1)[1]) for line in lines[1:]]
    if min(nanos) <= 0:
        raise RuntimeError(f"{label}: nonpositive monotonic duration")
    return {"abi": abi, "answer": lines[0].split("\t", 1)[1],
            "samples_ns": nanos, "peak_rss_kib": int(timing.read_text().strip()),
            "wrapper_wall_ns": total, "exit_code": p.returncode}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--abi", choices=("elf64", "elf32"), required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    left, right = args.baseline.resolve(), args.candidate.resolve()
    if not left.is_file() or not right.is_file():
        raise SystemExit("Missing harness binary")
    report = {
        "generation13_commit": GEN13_COMMIT,
        "generation14_protocol": GEN14_PROTOCOL,
        "abi": args.abi,
        "primary_metric": "per-solve nanoseconds (parser and process startup excluded)",
        "memory_metric": "per-process peak RSS KiB (%M on Ubuntu Linux; includes parsing)",
        "sampling": "5 paired blocks, 4 timed solves per block per variant (20 raw samples each); within each block AB/BA alternation, 3 unmeasured warmups",
        "parity_gate": "full Debug answer representation equal within and across implementations",
        "performance_acceptance_gate": "none; report negative outcomes without failing semantic CI",
        "performance_prediction": "sparse_96 candidate lower median solve time, single_1/builtin_96 may regress",
        "controls": "same pinned Rust1.85.1 compiler and ISA, external shared harness, identical parser/input/query/limits, distinct Cargo target directories",
        "independent_validation": "no: shared Rust semantics are compared to frozen Gen13, which itself is author-correlated",
        "cases": {}, "errors": [], "passed": False
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gprolog-native-index-") as folder:
        work = Path(folder)
        for name, contents, query, goals, description in fixtures():
            source = work / (name + ".pl")
            source.write_text(contents, encoding="utf-8")
            samples = {"baseline": [], "candidate": []}
            rss = {"baseline": [], "candidate": []}
            blocks = []
            expected_answer = None
            for block in range(5):
                order = [("baseline", left), ("candidate", right)]
                if block % 2:
                    order.reverse()
                observation = {}
                for role, binary in order:
                    got = run(binary, source, query, goals, args.abi, work,
                              f"{name}-{block}-{role}")
                    if expected_answer is None: expected_answer = got["answer"]
                    if got["answer"] != expected_answer:
                        report["errors"].append(f"{name}: answer parity block {block} {role}")
                    samples[role].extend(got["samples_ns"])
                    rss[role].append(got["peak_rss_kib"])
                    observation[role] = got
                blocks.append({"order": [role for role, _ in order],
                               "baseline": observation["baseline"],
                               "candidate": observation["candidate"]})
            baseline_ns = statistics.median(samples["baseline"])
            candidate_ns = statistics.median(samples["candidate"])
            paired_wins = sum(
                statistics.median(block["candidate"]["samples_ns"]) <
                statistics.median(block["baseline"]["samples_ns"]) for block in blocks)
            report["cases"][name] = {
                "description": description, "goals": goals,
                "program_bytes": len(contents.encode()),
                "program_sha256": hashlib.sha256(contents.encode()).hexdigest(),
                "query": query,
                "baseline_median_solve_ns": baseline_ns,
                "candidate_median_solve_ns": candidate_ns,
                "candidate_change_pct": round(100 * (candidate_ns / baseline_ns - 1), 3),
                "candidate_faster_blocks_of_5": paired_wins,
                "baseline_median_peak_rss_kib": statistics.median(rss["baseline"]),
                "candidate_median_peak_rss_kib": statistics.median(rss["candidate"]),
                "full_answer_representation": expected_answer,
                "blocks": blocks
            }
            print(name, "baseline median ns", baseline_ns,
                  "candidate median ns", candidate_ns, "faster blocks", paired_wins,
                  flush=True)
    report["passed"] = not report["errors"]
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("FINISHED", args.abi, "PASS" if report["passed"] else "FAIL",
          "errors", report["errors"], flush=True)
    if report["errors"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
