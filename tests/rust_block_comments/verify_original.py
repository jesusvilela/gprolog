#!/usr/bin/env python3
"""Gen25: exact upstream Prolog *original*, no preprocessing, live SWI oracle.

Accepting /*...*/ is a parser-only change. Gen18 intentionally rejects
the original; Gen25 must accept it while matching SWI and the Gen18
comment-only normalized derivative, with every ordered answer intact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "rust_upstream_corpus"))
from compare_swi import (  # noqa: E402
    UPSTREAM, cases, check_source_identity, external_reference, invoke,
)

GEN18 = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"
BASE = "fb9e05acd87e3fe71052e83ef38f26b9c12701d3"


def run(exe, source, query):
    return invoke([
        exe.resolve(), source, query, "--max-solutions", "32",
        "--max-steps", "100000"
    ])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--gen18", required=True, type=Path)
    p.add_argument("--swi", default="swipl")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "protocol": "docs/RUST_GEN25_BLOCK_COMMENTS_PROTOCOL.md",
        "released_baseline": GEN18, "pre_feature_master": BASE,
        "test_name": "genuine upstream original vs independent SWI executable",
        "cases": {}, "errors": [], "passed": False,
    }
    try:
        raw, normalized, notice, removed = check_source_identity()
        report["original_source_sha256"] = hashlib.sha256(raw).hexdigest()
        report["normalized_source_sha256"] = hashlib.sha256(normalized).hexdigest()
        report["removed_comment_sha256"] = hashlib.sha256(removed).hexdigest()
        report["public_domain_notice_sha256"] = hashlib.sha256(notice).hexdigest()
        version = invoke([args.swi, "--version"])
        if version["exit"]:
            raise RuntimeError("SWI oracle not available")
        report["swi_version"] = version["stdout"].strip() or version["stderr"].strip()
        if not report["swi_version"].startswith("SWI-Prolog version "):
            raise RuntimeError("SWI version missing")
        initial = run(args.gen18, UPSTREAM, "likes(sam,dahl).")
        report["gen18_original_negative_control"] = initial
        if initial["exit"] != 2 or initial["stdout"] or (
            "syntax at byte 440: unsupported token byte 0x2f" not in initial["stderr"]
        ):
            raise RuntimeError("released Gen18 parser baseline no longer rejects expected original")
        if len(list(cases())) != 12:
            raise RuntimeError("Gen24 frozen query list drifted")
        with tempfile.TemporaryDirectory(prefix="gen25-derivative-control-") as tmp:
            derivative = Path(tmp) / "normalized.pl"
            derivative.write_bytes(normalized)
            for case in cases():
                reference, atoms, expected = external_reference(args.swi, UPSTREAM, case)
                current = run(args.candidate, UPSTREAM, case.query)
                candidate_derivative = run(args.candidate, derivative, case.query)
                previous_derivative = run(args.gen18, derivative, case.query)
                records = {
                    "candidate_unmodified_original": current,
                    "candidate_comment_normalized": candidate_derivative,
                    "gen18_comment_normalized": previous_derivative
                }
                good = all(
                    (x["exit"], x["stdout"], x["stderr"]) == (0, expected, "")
                    for x in records.values()
                )
                report["cases"][case.name] = {
                    "query": case.query,
                    "reference": reference,
                    "SWI_canonical_ordered_atoms": atoms,
                    "expected_stdout": expected,
                    "results": records, "passed": good,
                }
                if not good:
                    report["errors"].append(
                        f"{case.name}: unmodified original or comment metamorphic output differs"
                    )
                target.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
                print("GEN25 CASE", case.name, "unmodified", good, flush=True)
        report["passed"] = len(report["cases"]) == 12 and not report["errors"]
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as e:
        report["errors"].append(str(e))
    target.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print("GEN25 RESULT", report["passed"], "cases", len(report["cases"]),
          "errors", report["errors"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
