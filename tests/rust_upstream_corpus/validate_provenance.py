#!/usr/bin/env python3
"""Gen24 exact-head independent reference provenance and bounded evidence audit.

Checks the Git blob identity, original parser negative, comment-only source
transform, SWI independent execution representation and full source-linked
ordered answers. Validates the historic 264-case Rust differential as a
separate correlated regression guard. No performance claim.
"""
import argparse
import hashlib
import json
from pathlib import Path

from compare_swi import (
    UPSTREAM_FILE_GIT_SHA1, UPSTREAM_LICENSE_GIT_SHA1,
    RELEASED_SHA, REJECTED_SHA, check_source_identity, cases,
    parse_swi_atom_list,
)

REQUIRED = {
    "task_id", "claim", "specification", "implementation", "metric",
    "tests", "controls", "preregistration", "evidence", "round_trip", "result",
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--historical", type=Path, required=True)
    args = p.parse_args()
    run = json.loads(args.data.read_text())
    hist = json.loads(args.historical.read_text())
    audit = json.loads(Path("docs/RUST_GEN24_UPSTREAM_ORACLE_MANIFEST.json").read_text())
    raw, normalized, _, block = check_source_identity()
    assert REQUIRED <= audit.keys()
    assert audit["claim"]["status_before"] == "H"
    assert audit["result"]["status_after"] == "M"
    assert audit["metric"]["type"] == "typed_tuple"
    assert audit["metric"]["direction"] == "partial_order"
    assert audit["metric"]["raw_before_clipping"] is True
    assert len(audit["round_trip"]["edges"]) >= 6
    assert audit["evidence"]["independent_witnesses"], "SWI witness must be separately named"

    assert run["passed"] is True and not run["errors"]
    assert run["upstream_git_blob_sha1"] == UPSTREAM_FILE_GIT_SHA1
    assert run["upstream_license_blob_sha1"] == UPSTREAM_LICENSE_GIT_SHA1
    assert run["released_sha"] == RELEASED_SHA
    assert run["retired_sha"] == REJECTED_SHA
    assert run["raw_source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert run["normalized_source_sha256"] == hashlib.sha256(normalized).hexdigest()
    assert run["removed_block_sha256"] == hashlib.sha256(block).hexdigest()
    assert run["removed_block_bytes"] == len(block) == 125
    assert run["original_source_modified"] is False
    assert run["swi_version"].startswith("SWI-Prolog version ")
    for role in ("gen18", "gen19"):
        error = run["original_parser_outcome"][role]
        assert error["exit"] == 2 and not error["stdout"]
        assert "syntax at byte 440: unsupported token byte 0x2f" in error["stderr"]

    frozen = {x.name: x for x in cases()}
    assert len(frozen) == len(run["cases"]) == 12
    assert set(frozen) == set(run["cases"])
    for name, value in run["cases"].items():
        case = frozen[name]
        assert value["passed"]
        assert value["query"] == case.query
        assert value["answer_variable"] == case.answer_variable
        assert value["normalized_source_sha256"] == run["normalized_source_sha256"]
        ref = value["reference"]
        assert ref["exit"] == 0 and ref["stderr"] == ""
        atoms = parse_swi_atom_list(ref["stdout"])
        assert atoms == value["reference_canonical_atoms"]
        if case.answer_variable:
            expect = "".join(f"{case.answer_variable} = {atom}.\n" for atom in atoms)
        else:
            assert all(atom == "ok" for atom in atoms)
            expect = "true.\n" * len(atoms) if atoms else "false.\n"
        assert value["translated_expected_stdout"] == expect
        for role in ("gen18", "gen19"):
            rec = value["engines"][role]
            assert (rec["exit"], rec["stdout"], rec["stderr"]) == (0, expect, "")
            cmd = rec["command"]
            assert cmd[-4:] == ["--max-solutions", "32", "--max-steps", "100000"], (
                "fixed solutions and steps cap must not depend on observed SWI solution count"
            )
    assert hist["passed"] and len(hist["cases"]) == 264
    assert all(row["same_observables"] for row in hist["cases"])
    print("GEN24 PROVENANCE PASS: original parsing unsupported as expected; "
          "12/12 live SWI cases matched by both Rust versions under a fixed "
          "32-solution/100000-step cap; historical 264/264 strict cases pass")


if __name__ == "__main__":
    main()
