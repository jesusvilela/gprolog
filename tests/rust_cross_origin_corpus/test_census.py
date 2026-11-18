#!/usr/bin/env python3
"""Gen27 known-answer, malformed classifier and byte-licence provenance tests."""
from census import PROGRAMS, DOCUMENTS, classify_rust, classify_swi, diagnostics
from census import git_blob, verify_sources


def test():
    src = verify_sources()
    assert set(src) == set(PROGRAMS) and len(src) == 7
    assert len(DOCUMENTS) == 3
    assert sum(k.startswith("swi_") for k in src) == 4
    assert sum(k.startswith("scryer_") for k in src) == 3
    assert all(row["unmodified"] and len(row["git_blob_sha1"]) == 40
               and len(row["sha256"]) == 64 and row["source_bytes"] > 0
               for row in src.values())
    assert git_blob(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert classify_rust({"exit":0,"stdout":"true.\n","stderr":""}) == "accepted_and_true"
    assert classify_rust({"exit":2,"stdout":"","stderr":"syntax at byte 12: unsupported"}) == "syntax_rejection"
    assert classify_rust({"exit":2,"stdout":"","stderr":"unknown predicate"}) == "other"
    assert classify_rust({"exit":0,"stdout":"false.\n","stderr":""}) == "other"
    assert classify_swi({"exit":0,"stdout":"","stderr":""}) == "clean_load"
    assert classify_swi({"exit":0,"stdout":"hello","stderr":""}) == "process_exit0_with_output_or_diagnostics"
    assert classify_swi({"exit":0,"stdout":"","stderr":"ERROR: Syntax error"}) == "process_exit0_with_output_or_diagnostics"
    assert classify_swi({"exit":0,"stdout":"","stderr":"Warning: lonely singleton"}) == "process_exit0_with_output_or_diagnostics"
    assert classify_swi({"exit":1,"stdout":"","stderr":""}) == "failed_load"
    assert diagnostics("ERROR: missing\nWarning: ignored\n") == {
        "has_error_line": True, "has_warning_line": True, "stderr_line_count": 2
    }
    assert not diagnostics("")["has_error_line"]
    print("GEN27 source & licence identities, error-bearing exit-zero and raw-negative classifier PASS")


if __name__ == "__main__":
    test()
