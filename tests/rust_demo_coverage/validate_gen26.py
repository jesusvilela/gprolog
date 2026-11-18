#!/usr/bin/env python3
"""Gen26 claim-level final-head provenance and source-compatibility audit.

Validate a raw four-program census without interpreting process exit=0 as
a clean SWI source load. Recompute all classification and count totals,
recheck immutable Git source blobs, complete source paths, reference version,
12 original-source SWI semantic cases and exact historical Rust parity.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from census import (PROGRAMS, PIN, GEN24, GEN25, ROOT, README_BLOB,
                    verify_original_sources, classify_rust, classify_swi)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rust_upstream_corpus"))
from compare_swi import cases, parse_swi_atom_list  # noqa: E402

REQUIRED = {
    "task_id", "claim", "specification", "implementation", "metric",
    "tests", "controls", "preregistration", "evidence", "round_trip", "result"
}
ROLES = ("released_gen24", "merged_gen25")


def check(census, oracle, historical):
    original = verify_original_sources()
    assert census["passed"] and census["source_census_size"] == 4
    assert census["upstream_repo"] == "SWI-Prolog/swipl-devel"
    assert census["upstream_commit"] == PIN
    assert census["baseline_sha"] == GEN24 and census["candidate_sha"] == GEN25
    assert census["source_dir_license_git_blob_sha1"] == README_BLOB
    assert census["source_modification"] == "none"
    assert census["source_query"] == "true."
    assert census["SWI_version"].startswith("SWI-Prolog version ")
    assert census["semantic_oracle_passed"] and census["semantic_oracle_cases"] == 12
    assert set(census["programs"]) == set(PROGRAMS) == set(original)
    counts = {role: Counter() for role in (*ROLES, "SWI_reference")}
    for name, item in census["programs"].items():
        frozen = original[name]
        for field in ("original_git_blob_sha1", "original_sha256",
                      "original_byte_length", "upstream_url",
                      "upstream_intentionally_nonexecuting", "no_preprocessing"):
            assert item[field] == frozen[field], (name,field)
        src = ROOT / name
        for role in ROLES:
            info = item[role]
            assert info["outcome"] == classify_rust(info)
            assert info["command"][1] == str(src)
            assert info["command"][2:] == [
                "true.", "--max-solutions", "1", "--max-steps", "100000"
            ]
            counts[role][info["outcome"]] += 1
        witness = item["SWI_reference"]
        assert witness["outcome"] == classify_swi(witness)
        assert witness["command"][1:] == [
            "-q", "-f", "none", "-s", str(src), "-g", "true", "-t", "halt"
        ]
        has_error = any(line.lstrip().startswith("ERROR:")
                        for line in witness["stderr"].splitlines())
        assert witness["stderr_has_error_diagnostic"] is has_error
        counts["SWI_reference"][witness["outcome"]] += 1
    assert census["outcome_counts"] == {
        role: dict(sorted(counts[role].items())) for role in counts
    }, "raw classifications and tally differ"
    assert census["programs"]["likes.pl"]["released_gen24"]["outcome"] == "syntax_rejection"
    assert census["programs"]["likes.pl"]["merged_gen25"]["outcome"] == "accepted_and_true"
    assert census["programs"]["likes.pl"]["SWI_reference"]["outcome"] == "clean_load"
    assert census["programs"]["colours.pl"]["upstream_intentionally_nonexecuting"] is True

    assert oracle["passed"] and not oracle["errors"] and len(oracle["cases"]) == 12
    expected = {case.name: case for case in cases()}
    assert set(oracle["cases"]) == set(expected)
    assert oracle["original_source_sha256"] == original["likes.pl"]["original_sha256"]
    for name, row in oracle["cases"].items():
        case = expected[name]
        assert row["passed"] and row["query"] == case.query
        assert row["reference"]["exit"] == 0 and row["reference"]["stderr"] == ""
        atoms = parse_swi_atom_list(row["reference"]["stdout"])
        assert row["SWI_canonical_ordered_atoms"] == atoms
        if case.answer_variable:
            outcome = "".join(f"{case.answer_variable} = {atom}.\n" for atom in atoms)
        else:
            assert all(atom == "ok" for atom in atoms)
            outcome = "true.\n" * len(atoms) if atoms else "false.\n"
        assert row["expected_stdout"] == outcome
        for subrole in ("candidate_unmodified_original", "candidate_comment_normalized",
                        "gen18_comment_normalized"):
            result = row["results"][subrole]
            assert (result["exit"],result["stdout"],result["stderr"]) == (
                0,outcome,""
            )
            assert result["command"][-4:] == [
                "--max-solutions","32","--max-steps","100000"
            ]
        original_program_command = row["results"]["candidate_unmodified_original"]["command"]
        assert original_program_command[1].endswith(
            "/tests/rust_upstream_corpus/upstream/likes.pl"
        ), "raw original source not actually executed"
    assert historical["passed"] and historical["abi"] == "elf64"
    assert len(historical["cases"]) == 264
    assert all(row["same_observables"] for row in historical["cases"])

    audit = json.loads(Path("docs/RUST_GEN26_UPSTREAM_DEMO_CENSUS_MANIFEST.json").read_text())
    assert REQUIRED <= audit.keys()
    assert audit["claim"]["status_before"] == "H"
    assert audit["result"]["status_after"] == "M"
    assert audit["metric"]["type"] == "typed_tuple"
    assert audit["metric"]["direction"] == "partial_order"
    assert audit["metric"]["raw_before_clipping"] is True
    assert len(audit["round_trip"]["edges"]) >= 6
    assert audit["evidence"]["independent_witnesses"]
    print("GEN26 PROVENANCE PASS: all four exact upstream sources, typed SWI "
          "error diagnostics, original-source 12 SWI semantic cases, "
          "264 full historical outputs, stable claim audit. "
          "No general Prolog compliance inferred.", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--census", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--historical", type=Path, required=True)
    args = ap.parse_args()
    check(json.loads(args.census.read_text()),
          json.loads(args.oracle.read_text()),
          json.loads(args.historical.read_text()))


if __name__ == "__main__":
    main()
