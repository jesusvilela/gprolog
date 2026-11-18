#!/usr/bin/env python3
"""Independent known-answer and source-hash negative tests for Gen26 census."""
from census import (
    PROGRAMS, ROOT, README_BLOB, classify_rust, classify_swi,
    git_blob, verify_original_sources,
)


def test():
    sources = verify_original_sources()
    assert set(sources) == set(PROGRAMS) and len(sources) == 4
    assert sources["colours.pl"]["upstream_intentionally_nonexecuting"] is True
    assert all(x["no_preprocessing"] for x in sources.values())
    assert git_blob(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert (ROOT / "README.md").is_file() and len(README_BLOB) == 40
    assert classify_rust({"exit": 0, "stdout": "true.\n", "stderr": ""}) == "accepted_and_true"
    assert classify_rust({"exit": 2, "stdout": "", "stderr": "syntax at byte 12: no"}) == "syntax_rejection"
    assert classify_rust({"exit": 2, "stdout": "", "stderr": "unknown predicate"}) == "runtime_or_other_failure"
    assert classify_rust({"exit": 0, "stdout": "false.\n", "stderr": ""}) == "runtime_or_other_failure"
    assert classify_swi({"exit": 0, "stderr": ""}) == "clean_load"
    assert classify_swi({"exit": 0, "stderr": "Warning"}) == "loaded_with_diagnostics"
    assert classify_swi({"exit": 1, "stderr": "Error"}) == "failed_load"
    print("GEN26 known-answer census, original source hashes and negative classes PASS")


if __name__ == "__main__":
    test()
