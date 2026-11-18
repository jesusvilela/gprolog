#!/usr/bin/env python3
"""Final-head bounded Gen27 source/provenance and live SWI-oracle validator."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import sys

from census import (
    PROGRAMS, DOCUMENTS, GEN24, GEN26, SWI, SCRYER, ROOT,
    classify_rust, classify_swi, diagnostics, verify_sources,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rust_upstream_corpus"))
from compare_swi import cases, parse_swi_atom_list  # noqa: E402

REQUIRED = {
    "task_id","claim","specification","implementation","metric","tests",
    "controls","preregistration","evidence","round_trip","result",
}
ROLES = ("rust_gen24","rust_gen26")


def validate(census, oracle, history):
    source_meta = verify_sources()
    assert census["passed"] is True, census.get("error")
    assert census["program_count"] == 7
    assert census["source_transformation"] == "none"
    assert census["license_document_sha1s"] == DOCUMENTS
    assert census["swi_commit"] == SWI and census["scryer_commit"] == SCRYER
    assert census["rust_gen24_sha"] == GEN24
    assert census["rust_candidate_sha"] == GEN26
    assert census["SWI_version"].startswith("SWI-Prolog version ")
    assert set(census["programs"]) == set(PROGRAMS) == set(source_meta)
    counts={k:Counter() for k in (*ROLES,"SWI_reference")}
    for name,item in census["programs"].items():
        expected=source_meta[name]
        for field in ("source_path","upstream_url","upstream_repo",
                      "upstream_commit","git_blob_sha1","sha256",
                      "source_bytes","license_class","unmodified"):
            assert item[field] == expected[field], (name,field)
        original=(ROOT / expected["source_path"]).resolve()
        for role in ROLES:
            outcome=item[role]
            assert outcome["outcome"] == classify_rust(outcome)
            assert Path(outcome["argv"][1]) == original
            assert outcome["argv"][2:] == [
                "true.","--max-solutions","1","--max-steps","100000"
            ]
            counts[role][outcome["outcome"]]+=1
        reference=item["SWI_reference"]
        assert reference["outcome"] == classify_swi(reference)
        assert reference["argv"][1:] == [
            "-q","-f","none","-s",str(original),"-g","true","-t","halt"
        ]
        for flag,value in diagnostics(reference["stderr"]).items():
            assert reference[flag] == value
        counts["SWI_reference"][reference["outcome"]]+=1
    assert census["outcome_counts"] == {
        k:dict(sorted(v.items())) for k,v in counts.items()
    }
    clean=[name for name in PROGRAMS
           if census["programs"][name]["SWI_reference"]["outcome"] == "clean_load"]
    overlap=[name for name in clean
             if census["programs"][name]["rust_gen26"]["outcome"] == "accepted_and_true"]
    assert clean == census["clean_under_swi"]
    assert overlap == census["clean_and_accepted_under_rust"]
    assert "swi_likes" in clean and "swi_likes" in overlap
    assert census["programs"]["swi_likes"]["rust_gen24"]["outcome"] == "syntax_rejection"

    assert oracle["passed"] is True and not oracle["errors"]
    frozen={c.name:c for c in cases()}
    assert len(frozen) == len(oracle["cases"]) == 12
    assert set(frozen) == set(oracle["cases"])
    assert oracle["original_source_sha256"] == source_meta["swi_likes"]["sha256"]
    assert oracle["swi_version"].startswith("SWI-Prolog version ")
    for name,item in oracle["cases"].items():
        case=frozen[name]
        assert item["query"] == case.query and item["passed"]
        witness=item["reference"]
        assert witness["exit"] == 0 and not witness["stderr"]
        atoms=parse_swi_atom_list(witness["stdout"])
        assert atoms == item["SWI_canonical_ordered_atoms"]
        if case.answer_variable:
            desired="".join(f"{case.answer_variable} = {x}.\n" for x in atoms)
        else:
            assert all(x == "ok" for x in atoms)
            desired=("true.\n" * len(atoms)) if atoms else "false.\n"
        assert item["expected_stdout"] == desired
        for key in ("candidate_unmodified_original","candidate_comment_normalized",
                    "gen18_comment_normalized"):
            row=item["results"][key]
            assert (row["exit"],row["stdout"],row["stderr"]) == (0,desired,"")
            assert row["command"][-4:] == [
                "--max-solutions","32","--max-steps","100000"
            ]
        assert Path(item["results"]["candidate_unmodified_original"]["command"][1]).name == "likes.pl"

    assert history["passed"] and history["abi"] == "elf64"
    assert len(history["cases"]) == 264
    assert all(row["same_observables"] for row in history["cases"])
    audit=json.loads(Path("docs/RUST_GEN27_CROSS_PROJECT_SOURCE_MANIFEST.json").read_text())
    assert REQUIRED <= audit.keys()
    assert audit["claim"]["status_before"]=="H"
    assert audit["result"]["status_after"]=="M"
    assert audit["metric"]["type"]=="typed_tuple"
    assert audit["metric"]["direction"]=="partial_order"
    assert audit["metric"]["raw_before_clipping"] is True
    assert len(audit["round_trip"]["edges"]) >= 6
    assert audit["evidence"]["independent_witnesses"]
    assert audit["result"]["observed"], "observed bounded result must be documented"
    print("GEN27 PROVENANCE PASS: 7/7 exact original sources + rights, "
          "typed per-source SWI stdout/stderr/exit, all clean-subset records, "
          "12/12 independent likes oracle and 264 strict historical cases; "
          "no broad language conformance claimed",flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--census",type=Path,required=True)
    p.add_argument("--oracle",type=Path,required=True)
    p.add_argument("--historical",type=Path,required=True)
    x=p.parse_args()
    validate(json.loads(x.census.read_text()),json.loads(x.oracle.read_text()),
             json.loads(x.historical.read_text()))


if __name__ == "__main__":
    main()
