#!/usr/bin/env python3
"""Generation 25: verify exact upstream, live SWI, Rust original and regression.

The independently implemented Prolog reference operates on the untouched
upstream source. The new Rust parser must match SWI on the same bytes.
Gen18 on the comment-only derivative and new Rust on that derivative
serve as distinct controls. No timing or full language conformance claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "rust_upstream_corpus"))
from compare_swi import (  # noqa: E402
    check_source_identity, cases, parse_swi_atom_list
)

REQUIRED = {
    "task_id", "claim", "specification", "implementation", "metric",
    "tests", "controls", "preregistration", "evidence", "round_trip", "result",
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-oracle", type=Path)
    p.add_argument("--historical", type=Path, required=True)
    p.add_argument("--abi", choices=("elf64", "elf32"), required=True)
    args = p.parse_args()
    old = json.loads(args.historical.read_text())
    assert old["abi"] == args.abi and old["passed"]
    assert len(old["cases"]) == 264
    assert all(case["same_observables"] for case in old["cases"])
    manifest = json.loads(Path("docs/RUST_GEN25_BLOCK_COMMENTS_MANIFEST.json").read_text())
    assert REQUIRED <= manifest.keys()
    assert manifest["claim"]["status_before"] == "H"
    assert manifest["result"]["status_after"] == "M"
    assert manifest["metric"]["type"] == "typed_tuple"
    assert manifest["metric"]["direction"] == "partial_order"
    assert manifest["metric"]["raw_before_clipping"] is True
    assert len(manifest["round_trip"]["edges"]) >= 6
    assert manifest["evidence"]["independent_witnesses"], (
        "SWI reference must be named, not inferred from Rust outputs"
    )
    if args.abi == "elf32":
        assert args.original_oracle is None
        print("GEN25 provenance PASS i686: 264/264 historical output cases; "
              "no i686 SWI source witness is claimed")
        return
    assert args.original_oracle is not None
    report = json.loads(args.original_oracle.read_text())
    assert report["passed"] and not report["errors"]
    assert len(report["cases"]) == 12
    raw, normalized, _, block = check_source_identity()
    assert report["original_source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["normalized_source_sha256"] == hashlib.sha256(normalized).hexdigest()
    assert report["removed_comment_sha256"] == hashlib.sha256(block).hexdigest()
    assert report["swi_version"].startswith("SWI-Prolog version ")
    released = report["gen18_original_negative_control"]
    assert (released["exit"], released["stdout"]) == (2, "")
    assert "syntax at byte 440: unsupported token byte 0x2f" in released["stderr"]
    frozen = {c.name: c for c in cases()}
    assert set(report["cases"]) == set(frozen)
    for name, result in report["cases"].items():
        case = frozen[name]
        assert result["passed"] and result["query"] == case.query
        witness = result["reference"]
        assert witness["exit"] == 0 and witness["stderr"] == ""
        atoms = parse_swi_atom_list(witness["stdout"])
        assert atoms == result["SWI_canonical_ordered_atoms"]
        if case.answer_variable:
            expected = "".join(f"{case.answer_variable} = {atom}.\n" for atom in atoms)
        else:
            assert all(x == "ok" for x in atoms)
            expected = "true.\n" * len(atoms) if atoms else "false.\n"
        assert expected == result["expected_stdout"]
        for key in (
            "candidate_unmodified_original", "candidate_comment_normalized",
            "gen18_comment_normalized",
        ):
            row = result["results"][key]
            assert (row["exit"], row["stdout"], row["stderr"]) == (0, expected, "")
            assert row["command"][-4:] == [
                "--max-solutions", "32", "--max-steps", "100000"
            ]
    print("GEN25 provenance PASS ELF64: exact upstream original matches "
          "12 SWI queries with two comment-normalization controls; "
          "264 historical exact-output cases; fixed resource limits")


if __name__ == "__main__":
    main()
