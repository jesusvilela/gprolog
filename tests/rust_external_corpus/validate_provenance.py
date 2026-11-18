#!/usr/bin/env python3
"""Verify a FRESH Gen23 run against immutable corpus and committed claim audit.

Do not require fresh noisy timing medians to equal historical medians.
Do require every source SHA, oracle, exact case set, raw sample count,
reported median, AB/BA order, control gate, provenance and result type.
"""
import argparse
import csv
import json
from pathlib import Path
import statistics

from fixtures import cases, self_test

GEN18 = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"
GEN19 = "c09fff05d9b3dd43fb90014278e3a98d701d3640"
REQUIRED = {
    "task_id", "claim", "specification", "implementation", "metric",
    "tests", "controls", "preregistration", "evidence", "round_trip", "result",
}


def validate(abi, record_path, historical_path):
    self_test()
    data = json.loads(record_path.read_text())
    previous = json.loads(historical_path.read_text())
    snapshot = json.loads(
        Path("docs/RUST_GEN23_PUBLISHED_LIST_MANIFEST.json").read_text()
    )
    summary = list(csv.DictReader(
        Path("tests/rust_external_corpus/results/gen23_two_abi_summary.csv").open()
    ))
    ground = {case.name: case for case in cases()}
    assert len(ground) == len(summary) == 14
    assert {x["case"] for x in summary} == set(ground)
    assert REQUIRED <= snapshot.keys()
    assert snapshot["claim"]["status_before"] == "H"
    assert snapshot["result"]["status_after"] == "M"
    assert snapshot["metric"]["type"] == "typed_tuple"
    assert snapshot["metric"]["direction"] == "partial_order"
    assert snapshot["metric"]["raw_before_clipping"] is True
    assert len(snapshot["round_trip"]["edges"]) >= 6
    assert snapshot["evidence"]["independent_witnesses"] == [], (
        "Do not invent an independent Prolog benchmark author or semantic oracle"
    )
    assert previous["abi"] == abi and previous["passed"]
    assert len(previous["cases"]) == 264
    assert all(c["same_observables"] for c in previous["cases"])

    assert data["abi"] == abi and data["passed"]
    assert data["baseline_source_sha"] == GEN18
    assert data["rejected_source_sha"] == GEN19
    assert data["semantic_pass"] and data["measurement_pass"]
    assert data["case_count"] == 14 and data["external_task_case_count"] == 12
    assert set(data["cells"]) == set(ground)
    assert not data["errors"] and not data["failed_controls"]
    for row in summary:
        name = row["case"]
        case = ground[name]
        cell = data["cells"][name]
        assert cell["source_sha256"] == case.source_sha256 == row["source_sha256"]
        assert cell["reference_url"] == case.reference_url == row["source_reference"]
        assert cell["source_type"] == case.source_type
        assert cell["query"] == case.query
        assert cell["oracle_stdout"] == case.expected_stdout
        assert cell["repeats"] == case.repeat == int(row["repeat"])
        assert cell["max_solutions"] == case.max_solutions == int(row["max_solutions"])
        assert cell["oracle_passed"] is True
        for role in ("gen18", "gen19"):
            cli = cell["cli"][role]
            assert (cli["exit"], cli["stdout"], cli["stderr"]) == (
                0, case.expected_stdout, ""
            )
        blocks = cell["blocks"]
        assert len(blocks) == 5
        values = {"gen18": [], "gen19": []}
        for i, block in enumerate(blocks):
            assert block["block"] == i
            assert block["order"] == (
                ["gen18", "gen19"] if i % 2 == 0 else ["gen19", "gen18"]
            )
            for role in values:
                result = block[role]
                assert result["exit"] == 0 and not result["stderr"]
                assert result["ordered_debug_answers"] == cell["ordered_debug_answers"]
                assert len(result["raw_solve_ns"]) == 4
                assert all(x > 0 for x in result["raw_solve_ns"])
                values[role].extend(result["raw_solve_ns"])
        assert len(values["gen18"]) == len(values["gen19"]) == 20
        med = {role: statistics.median(raw) for role, raw in values.items()}
        assert med == cell["median_solve_ns"], name
        assert abs(med["gen19"] / med["gen18"] -
                   cell["gen19_over_gen18_ratio"]) <= 0.00000051, name
        wins = sum(statistics.median(b["gen19"]["raw_solve_ns"]) >
                   statistics.median(b["gen18"]["raw_solve_ns"]) for b in blocks)
        assert wins == cell["gen19_slower_blocks_of_5"], name
        if case.source_type == "author_null_control":
            assert 0.8 <= cell["gen19_over_gen18_ratio"] <= 1.2

    print(f"GEN23 PROVENANCE PASS {abi}: 14 exact reference-linked cases, "
          "14 x 20 raw samples per role, 264 historical comparisons; "
          "no independent Prolog author claimed")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--abi", choices=("elf64","elf32"), required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--historical", type=Path, required=True)
    args = p.parse_args()
    validate(args.abi, args.data, args.historical)


if __name__ == "__main__":
    main()
