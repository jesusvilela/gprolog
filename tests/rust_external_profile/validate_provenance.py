#!/usr/bin/env python3
"""Gen21: cross-check fresh native/Valgrind records against frozen Git summaries.

Checks typed provenance and presence, not numeric identity between noisy native
timing reruns. The separate benchmark scripts enforce preregistered thresholds.
This does not replace an independent scientific oracle.
"""
import argparse
import csv
import json
from pathlib import Path


MANIFEST = Path("docs/RUST_GEN21_EXTERNAL_PROFILE_MANIFEST.json")
REQUIRED = {
    "task_id", "claim", "specification", "implementation", "metric",
    "tests", "controls", "preregistration", "evidence", "round_trip", "result",
}
GEN18 = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"
GEN19 = "c09fff05d9b3dd43fb90014278e3a98d701d3640"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lane", choices=("native", "external"), required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--abi", choices=("elf64", "elf32"))
    args = p.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    assert REQUIRED <= manifest.keys(), "missing manifest sections"
    assert manifest["claim"]["status_before"] == "H"
    assert manifest["result"]["status_after"] == "M"
    assert manifest["metric"]["type"] == "typed_tuple"
    assert manifest["metric"]["raw_before_clipping"] is True
    assert len(manifest["round_trip"]["edges"]) >= 6
    assert manifest["evidence"]["independent_witnesses"] == [], (
        "third-party profiler software is not independent experimental authorship")

    if args.lane == "native":
        assert args.abi in ("elf64", "elf32")
        path = Path("tests/rust_external_profile/results/gen21_native_summary.csv")
    else:
        assert args.abi in (None, "elf64")
        path = Path("tests/rust_external_profile/results/gen21_valgrind_summary.csv")
    rows = list(csv.DictReader(path.open()))
    fresh = json.loads(args.data.read_text())
    assert fresh["passed"] is True, fresh.get("errors")
    expected_count = 7 if args.lane == "native" else 6
    assert len(rows) == len(fresh["cells"]) == expected_count
    assert {row["case"] for row in rows} == set(fresh["cells"])
    for row in rows:
        f = fresh["cells"][row["case"]]
        field = "source_sha256" if args.lane == "native" else "program_sha256"
        assert row["program_sha256"] == f[field], row["case"]
        assert len(row["program_sha256"]) == 64
        if args.lane == "native":
            assert fresh["source_commits"] == {"gen18": GEN18, "gen19": GEN19}
            assert fresh["abi"] == args.abi
            assert len(f["blocks"]) == 5
            assert all(
                len(b["gen18"]["samples_ns"]) == len(b["gen19"]["samples_ns"]) == 4
                for b in f["blocks"]
            )
            assert f["median_solve_ns"]["gen18"] > 0
            assert f["median_solve_ns"]["gen19"] > 0
        else:
            assert fresh["sources"] == {"gen18": GEN18, "gen19": GEN19}
            assert fresh["abi"] == "elf64"
            assert fresh["third_party_instrument"].startswith("valgrind-")
            for tool in ("dhat", "callgrind"):
                for mode in ("PREPARE", "SOLVE"):
                    assert set(f["modes"][tool][mode]) == {"gen18", "gen19"}
                    a, b = (f["modes"][tool][mode][v]["output"] for v in ("gen18", "gen19"))
                    assert a == b
    print("GEN21 PROVENANCE PASS", args.lane, args.abi or "elf64",
          expected_count, "fresh-source-linked cases; source claims bounded")


if __name__ == "__main__":
    main()
