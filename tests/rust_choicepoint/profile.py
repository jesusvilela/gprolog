#!/usr/bin/env python3
"""Rust-only feature-instrumented choicepoint profile, not a time benchmark.

Hard gate: counters are collected inside the executing engine and match
preregistered analytic predictions. Never convert element counts to bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

COUNTERS = (
    "user_predicate_dispatches", "try_clause_tasks", "work_resume_tasks",
    "clause_choices_pushed", "disjunction_choices_pushed",
    "clause_continuation_vectors_cloned", "clause_continuation_goals_cloned",
    "resume_suffix_goals_materialized", "disjunction_rest_goals_cloned",
    "choicepoints_redone", "cut_choicepoints_pruned", "binding_writes",
    "binding_undo_writes", "maximum_pending_choices", "total_search_steps",
)


def cases():
    primary = [(1, 1), (1, 64), (2, 64), (16, 1),
               (16, 8), (16, 64), (32, 64)]
    for t, r in primary:
        yield f"first_t{t}_r{r}", "target(a).\n" * t, "target(a).", r, 1, "first"
    # Goal size changes the bytes copied, not the count of pending goals.
    yield ("deep_t16_r64", "target(f(a,b,c,d,e)).\n" * 16,
           "target(f(a,b,c,d,e)).", 64, 1, "deep-terms")
    yield ("builtin_r64", "target(a).\n", "true.", 64, 1, "builtin")
    yield ("redo_two", "p(a).p(b).", "p(X).", 1, 2, "redo")
    yield ("failed_head", "p(f(a,b)).p(f(c,c)).",
           "p(f(X,X)).", 1, 1, "failed-unify")
    yield ("cut_then_new_choice",
           "choose(a). choose(b). p(X):-choose(X),!, (Z=one;Z=two). p(c).",
           "p(X).", 1, 2, "cut")


def expected_first(t, r):
    suffix = r * (r - 1) // 2
    choices = (t - 1) * r
    return {
        "user_predicate_dispatches": r,
        "try_clause_tasks": r,
        "work_resume_tasks": r + 1,
        "clause_choices_pushed": choices,
        "disjunction_choices_pushed": 0,
        "clause_continuation_vectors_cloned": choices,
        "clause_continuation_goals_cloned": (t - 1) * suffix,
        "resume_suffix_goals_materialized": suffix,
        "disjunction_rest_goals_cloned": 0,
        "choicepoints_redone": 0,
        "cut_choicepoints_pruned": 0,
        "binding_writes": 0,
        "binding_undo_writes": 0,
        "maximum_pending_choices": choices,
        "total_search_steps": 2 * r + 1,
    }


def check_expected(label, kind, t, r, counts):
    if kind == "first" or kind == "deep-terms":
        expectation = expected_first(t, r)
    elif kind == "builtin":
        suffix = r * (r - 1) // 2
        expectation = {
            "user_predicate_dispatches": 0,
            "try_clause_tasks": 0,
            "work_resume_tasks": r + 1,
            "clause_choices_pushed": 0,
            "clause_continuation_vectors_cloned": 0,
            "clause_continuation_goals_cloned": 0,
            "resume_suffix_goals_materialized": suffix,
            "choicepoints_redone": 0,
            "total_search_steps": r + 1,
        }
    elif kind == "redo":
        expectation = {"clause_choices_pushed": 1,
                       "choicepoints_redone": 1, "binding_writes": 2,
                       "binding_undo_writes": 1}
    elif kind == "failed-unify":
        expectation = {"clause_choices_pushed": 1,
                       "choicepoints_redone": 1, "binding_writes": 2,
                       "binding_undo_writes": 1}
    elif kind == "cut":
        expectation = {"cut_choicepoints_pruned": 2,
                       "disjunction_choices_pushed": 1,
                       "choicepoints_redone": 1}
    else:
        raise ValueError(kind)
    mismatches = [
        {"field": name, "expected": expected, "observed": counts[name]}
        for name, expected in expectation.items() if counts[name] != expected
    ]
    return {"matched": not mismatches, "expected_fields": expectation,
            "mismatches": mismatches}


def run_probe(binary, source, query, repeat, limit, temp, label):
    path = temp / f"{label}.pl"
    path.write_text(source, encoding="utf-8")
    cmd = [str(binary), str(path), query, str(repeat), str(limit), "200000"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=40)
    if result.returncode != 0:
        raise RuntimeError(
            f"probe failure {label} exit {result.returncode}: {result.stderr[:400]}")
    lines = result.stdout.splitlines()
    if not lines or not lines[0].startswith("ANSWERS\t"):
        raise RuntimeError(f"missing answer trace for {label}")
    counters = {}
    for row in lines[1:]:
        tag, key, value = row.split("\t")
        if tag != "COUNT" or key in counters or key not in COUNTERS:
            raise RuntimeError(f"malformed counter: {row!r}")
        counters[key] = int(value)
    if set(counters) != set(COUNTERS):
        raise RuntimeError(f"missing counter(s) for {label}: {set(COUNTERS)-set(counters)}")
    return {"counters": counters,
            "answers_debug": lines[0].split("\t", 1)[1],
            "stderr": result.stderr, "exit_code": result.returncode,
            "program_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "query": query, "repeated_goals": repeat, "max_solutions": limit,
            "source_bytes": len(source.encode())}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--probe", type=Path, required=True)
    p.add_argument("--abi", choices=("elf32", "elf64"), required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    binary = args.probe.resolve()
    if not binary.is_file():
        raise SystemExit(f"missing Rust probe {binary}")
    report = {
        "protocol": "docs/RUST_NATIVE_CHOICEPOINT_PROFILE_PROTOCOL.md",
        "source_base": "2528697368fa2d930029b6c1efa9528745e91f61",
        "abi": args.abi,
        "claim": "Operation counts from live feature-gated Rust execution",
        "warning": "Counters are not time attribution, allocation counts, or bytes copied",
        "feature": "choicepoint-profile",
        "independent_witness": False,
        "cases": {}, "errors": [], "passed": False
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="choicepoint-profile-") as folder:
        temp = Path(folder)
        for label, source, query, repeat, max_solutions, kind in cases():
            try:
                measured = run_probe(binary, source, query, repeat, max_solutions, temp, label)
                t = 16 if kind == "deep-terms" else int(label.split("_t")[1].split("_")[0]) if kind == "first" else 0
                decision = check_expected(label, kind, t, repeat, measured["counters"])
                measured["kind"] = kind
                measured["prediction_check"] = decision
                measured["total_alternatives_created"] = (
                    measured["counters"]["clause_choices_pushed"] +
                    measured["counters"]["disjunction_choices_pushed"])
                measured["unresumed_at_exit"] = (
                    measured["total_alternatives_created"] -
                    measured["counters"]["choicepoints_redone"] -
                    measured["counters"]["cut_choicepoints_pruned"])
                if not decision["matched"]:
                    report["errors"].append({"case": label, "mismatch": decision["mismatches"]})
                report["cases"][label] = measured
                c = measured["counters"]
                print("PROFILE", args.abi, label,
                      "choices", c["clause_choices_pushed"],
                      "clone-goals", c["clause_continuation_goals_cloned"],
                      "redo", c["choicepoints_redone"],
                      "prune", c["cut_choicepoints_pruned"],
                      "PASS" if decision["matched"] else "FAIL", flush=True)
            except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                report["errors"].append({"case": label, "exception": str(exc)})
                print("PROFILE", args.abi, label, "ERROR", str(exc), flush=True)
    report["passed"] = not report["errors"] and len(report["cases"]) == 12
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("RESULT", args.abi, report["passed"], len(report["cases"]),
          "cases errors", len(report["errors"]), flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
