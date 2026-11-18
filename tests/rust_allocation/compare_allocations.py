#!/usr/bin/env python3
"""Gen20: pinned Gen18 vs retired Gen19 requested-heap allocation comparison.

External, identical Rust System allocator probe + existing live counters.
All 13 fixtures, 20 raw observations/version/cell/ABI, AB/BA block pairing.
Reject wrong source counters or missing allocation contrast; never reinterpret
requested layout bytes as actual copied bytes, RSS or causal wall time.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile

GEN18 = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"
GEN19 = "c09fff05d9b3dd43fb90014278e3a98d701d3640"
FIELDS = (
    "alloc_calls", "alloc_zeroed_calls", "alloc_requested_bytes",
    "realloc_calls", "realloc_old_requested_bytes", "realloc_new_requested_bytes",
    "dealloc_calls", "dealloc_layout_bytes",
)
PROFILES = (
    "user_predicate_dispatches", "try_clause_tasks", "work_resume_tasks",
    "clause_choices_pushed", "disjunction_choices_pushed",
    "clause_continuation_vectors_cloned", "clause_continuation_goals_cloned",
    "shared_continuation_anchors", "shared_continuation_handle_clones",
    "shared_continuation_fallback_copies", "resume_suffix_goals_materialized",
    "disjunction_rest_goals_cloned", "choicepoints_redone",
    "cut_choicepoints_pruned", "binding_writes", "binding_undo_writes",
    "maximum_pending_choices", "total_search_steps",
)
DEEP = "f(g(h(a,b),k(c,d)),[a,b,c],q(r(s(t))))"
DEEP_BAD = "f(g(h(a,b),k(c,d)),[a,b,c],q(r(s(v))))"


def fixtures():
    facts = lambda number, atom="a": f"target({atom}).\n" * number
    yield ("t2_first_success_r128", facts(2), "target(a).", 128, 1)
    yield ("t2_first_failure_r128",
           "target(b).\ntarget(a).\n", "target(a).", 128, 1)
    yield ("t2_first_success_r32", facts(2), "target(a).", 32, 1)
    yield ("t2_first_failure_r32",
           "target(b).\ntarget(a).\n", "target(a).", 32, 1)
    yield ("t2_first_failure_deep_r64",
           f"target({DEEP_BAD}).\ntarget({DEEP}).\n", f"target({DEEP}).", 64, 1)
    yield ("t2_first_success_deep_r64",
           facts(2, DEEP), f"target({DEEP}).", 64, 1)
    yield ("t2_both_fail_r128",
           "target(b).\ntarget(c).\n", "target(a).", 128, 1)
    yield ("t2_enumerate_r8", facts(2), "target(a).", 8, 16)
    yield ("t3_first_failure_r64",
           "target(b).\ntarget(a).\ntarget(a).\n", "target(a).", 64, 1)
    yield ("t3_first_success_r64", facts(3), "target(a).", 64, 1)
    yield ("t1_r128", facts(1), "target(a).", 128, 1)
    yield ("builtin_r128", "", "true.", 128, 1)
    yield ("t16_first_success_r64", facts(16), "target(a).", 64, 1)


def probe(binary, program, query, repeat, solutions, directory, label):
    command = [str(binary), str(program), query, str(repeat),
               str(solutions), "200000", "3", "4"]
    process = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=90,
        env=dict(os.environ, LC_ALL="C", LANG="C"),
    )
    if process.returncode != 0:
        raise RuntimeError(f"{label} exit={process.returncode} stderr={process.stderr[:600]}")
    lines = process.stdout.splitlines()
    if len(lines) != 1 + 4 + len(PROFILES) or not lines[0].startswith("ANSWERS\t"):
        raise RuntimeError(f"{label} incomplete sample/profile rows: {len(lines)}")
    allocations = []
    for line in lines[1:5]:
        columns = line.split("\t")
        if len(columns) != len(FIELDS) + 1 or columns[0] != "ALLOC":
            raise RuntimeError(f"{label}: malformed allocator sample")
        allocation = dict(zip(FIELDS, (int(value) for value in columns[1:])))
        if min(allocation.values()) < 0:
            raise RuntimeError(f"{label}: invalid negative allocator count")
        if allocation["alloc_zeroed_calls"] > allocation["alloc_calls"]:
            raise RuntimeError(f"{label}: zeroed allocation subset larger than all allocs")
        allocations.append(allocation)
    profile = {}
    for line in lines[5:]:
        columns = line.split("\t")
        if len(columns) != 3 or columns[0] != "PROFILE":
            raise RuntimeError(f"{label}: malformed profile")
        if columns[1] in profile:
            raise RuntimeError(f"{label}: repeated profile metric")
        profile[columns[1]] = int(columns[2])
    if set(profile) != set(PROFILES):
        raise RuntimeError(f"{label}: invalid profile schema")
    return {
        "answers": lines[0].split("\t", 1)[1],
        "raw_allocator_requests": allocations,
        "source_profile": profile,
        "exit": process.returncode,
        "stderr": process.stderr,
    }


def require(path, expectation, actual, errors):
    if actual != expectation:
        errors.append({
            "path": path, "expected": expectation, "observed": actual
        })


def structural_known_answers(case, cells, errors):
    released = cells["released"]["source_profile"]
    rejected = cells["rejected"]["source_profile"]
    if case == "t2_first_failure_r128":
        for role, p, expected in (
            ("released", released, {
                "clause_choices_pushed": 128,
                "try_clause_tasks": 256,
                "clause_continuation_goals_cloned": 0,
                "clause_continuation_vectors_cloned": 1,
                "shared_continuation_anchors": 127,
                "shared_continuation_handle_clones": 127,
                "shared_continuation_fallback_copies": 0,
                "choicepoints_redone": 128,
            }),
            ("rejected", rejected, {
                "clause_choices_pushed": 128,
                "try_clause_tasks": 256,
                "clause_continuation_goals_cloned": 8128,
                "clause_continuation_vectors_cloned": 128,
                "shared_continuation_anchors": 0,
                "shared_continuation_handle_clones": 0,
                "shared_continuation_fallback_copies": 0,
                "choicepoints_redone": 128,
            }),
        ):
            for name, value in expected.items():
                require(f"{case}/{role}/{name}", value, p[name], errors)

    if case == "t2_first_success_r128":
        for role, p in (("released", released), ("rejected", rejected)):
            require(f"{case}/{role}/cloned_elements", 8128,
                    p["clause_continuation_goals_cloned"], errors)
            require(f"{case}/{role}/choices", 128, p["clause_choices_pushed"], errors)
            require(f"{case}/{role}/redone", 0, p["choicepoints_redone"], errors)
        require(f"{case}/released/anchors", 127,
                released["shared_continuation_anchors"], errors)
        require(f"{case}/rejected/anchors", 0,
                rejected["shared_continuation_anchors"], errors)

    if case in ("t3_first_success_r64", "t1_r128", "builtin_r128",
                "t16_first_success_r64", "t3_first_failure_r64"):
        require(f"{case}/profile_parity", released, rejected, errors)

    if case == "t2_first_failure_deep_r64":
        require(f"{case}/released/goal_copies", 0,
                released["clause_continuation_goals_cloned"], errors)
        require(f"{case}/rejected/goal_copies", 2016,
                rejected["clause_continuation_goals_cloned"], errors)

    if case == "t2_both_fail_r128":
        require(f"{case}/released/goal_copies", 0,
                released["clause_continuation_goals_cloned"], errors)
        require(f"{case}/rejected/goal_copies", 127,
                rejected["clause_continuation_goals_cloned"], errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--released", type=Path, required=True)
    parser.add_argument("--rejected", type=Path, required=True)
    parser.add_argument("--abi", choices=("elf64", "elf32"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    released, rejected = args.released.resolve(), args.rejected.resolve()
    for executable in (released, rejected):
        if not executable.is_file():
            raise SystemExit(f"missing compiled probe {executable}")
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "protocol": "docs/RUST_NATIVE_ALLOCATION_AUDIT_PROTOCOL.md",
        "released_commit": GEN18, "rejected_commit": GEN19, "abi": args.abi,
        "measurement": "Rust GlobalAlloc allocation requests during solve only; no timing or RSS",
        "instrumented_feature": "choicepoint-profile",
        "source_correlation": "same external authored harness and source-originated counters, not independent",
        "paired_blocks": 5, "samples_per_role_per_case": 20,
        "cases": {}, "errors": [], "kill_conditions": [], "passed": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="rust-alloc-audit-") as directory:
            folder = Path(directory)
            cases = list(fixtures())
            assert len(cases) == 13
            for name, source, query, repeat, solutions in cases:
                path = folder / (name + ".pl")
                path.write_text(source, encoding="utf-8")
                reference = None
                profile_reference = {}
                blocks = []
                raw = {"released": [], "rejected": []}
                for block_id in range(5):
                    order = [("released", released), ("rejected", rejected)]
                    if block_id % 2:
                        order.reverse()
                    pair = {"index": block_id, "order": [v[0] for v in order]}
                    for role, executable in order:
                        result = probe(executable, path, query, repeat, solutions,
                                       folder, f"{name}/{block_id}/{role}")
                        if reference is None:
                            reference = result["answers"]
                        elif result["answers"] != reference:
                            report["errors"].append(f"{name}: answer mismatch {block_id}/{role}")
                        if role in profile_reference and (
                                profile_reference[role] != result["source_profile"]):
                            report["errors"].append(f"{name}: nondeterministic source counters {role}")
                        else:
                            profile_reference[role] = result["source_profile"]
                        pair[role] = result
                        raw[role].extend(result["raw_allocator_requests"])
                    blocks.append(pair)
                structural_known_answers(name, {
                    "released": {"source_profile": profile_reference["released"]},
                    "rejected": {"source_profile": profile_reference["rejected"]},
                }, report["errors"])
                medians = {
                    role: {
                        field: statistics.median(x[field] for x in raw[role])
                        for field in FIELDS
                    }
                    for role in ("released", "rejected")
                }
                faster = {
                    field: sum(
                        statistics.median(x[field] for x in block["rejected"]["raw_allocator_requests"]) >
                        statistics.median(x[field] for x in block["released"]["raw_allocator_requests"])
                        for block in blocks
                    )
                    for field in ("alloc_calls", "alloc_requested_bytes")
                }
                report["cases"][name] = {
                    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "source_bytes": len(source.encode()),
                    "query": query, "repeats": repeat,
                    "max_solutions": solutions, "max_steps": 200000,
                    "complete_ordered_answers": reference,
                    "profile": profile_reference,
                    "median_allocator_requests": medians,
                    "rejected_exceeds_released_in_blocks_of_5": faster,
                    "blocks": blocks,
                }
                report["passed"] = False
                target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
                print("CASE", args.abi, name,
                      "released allocs", medians["released"]["alloc_calls"],
                      "rejected allocs", medians["rejected"]["alloc_calls"],
                      "released bytes", medians["released"]["alloc_requested_bytes"],
                      "rejected bytes", medians["rejected"]["alloc_requested_bytes"],
                      "wins", faster, flush=True)

            primary = report["cases"]["t2_first_failure_r128"]
            for metric in ("alloc_calls", "alloc_requested_bytes"):
                a = primary["median_allocator_requests"]["released"][metric]
                b = primary["median_allocator_requests"]["rejected"][metric]
                wins = primary["rejected_exceeds_released_in_blocks_of_5"][metric]
                if not b > a or wins < 4:
                    report["kill_conditions"].append(
                        f"failed predicted allocation contrast: {metric}: {a} vs {b}; {wins}/5"
                    )
    except (OSError, RuntimeError, subprocess.TimeoutExpired, AssertionError, KeyError) as exc:
        report["errors"].append(str(exc))
    report["passed"] = (not report["errors"] and not report["kill_conditions"]
                        and len(report["cases"]) == 13)
    target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("SUMMARY", args.abi, "passed", report["passed"],
          "cases", len(report["cases"]),
          "errors", report["errors"], "kills", report["kill_conditions"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
