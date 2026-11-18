#!/usr/bin/env python3
"""Frozen Gen26 four-file SWI-Prolog demo-directory compatibility census.

Original upstream byte identities and their public-domain license are audited.
Capture the entire raw Rust Gen24/Gen25 and external SWI-Prolog loader
observable triple for each unmodified source. Negative outcomes are evidence.
A positive semantic oracle is confined to the unchanged upstream likes.pl
and separately executed by tests/rust_block_comments/verify_original.py.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

PIN = "111385b90852dade2b772d074cc55fefa20ee1a9"
GEN24 = "fb9e05acd87e3fe71052e83ef38f26b9c12701d3"
GEN25 = "ef2c9869d2224a4c8ee1dbba6df965c8fd286e6f"
ORIGIN = "https://github.com/SWI-Prolog/swipl-devel/tree/" + PIN + "/demo"
ROOT = Path(__file__).resolve().parent / "upstream"
PROGRAMS = {
    "likes.pl": "88f3d2edcb0fb68c99b559676e5982b3780715f6",
    "trace.pl": "5dd10ee3d9176c0792afbf874c50844679b93659",
    "unicode.pl": "c7132cc2cee914b6fc132cdd4f22e25010bd6e36",
    "colours.pl": "52391491930d72df055298b28a7d9487847de140",
}
README_BLOB = "fb3850a4dae3c29faea7907d9b3cd48d940fcfaa"
# Upstream explicitly says "This code does not run" for colours.pl.
UPSTREAM_NONEXECUTABLE = {"colours.pl": True}


def git_blob(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def verify_original_sources():
    src = ROOT / "README.md"
    readme = src.read_bytes()
    if git_blob(readme) != README_BLOB:
        raise ValueError("original public-domain README blob identity changed")
    if b"All files in this demo directory are in the public domain." not in readme:
        raise ValueError("missing original public-domain license statement")
    if b"This code does not run" not in readme:
        raise ValueError("upstream intentional non-executable program label absent")
    files = {x.name for x in ROOT.iterdir() if x.is_file()}
    if files != set(PROGRAMS) | {"README.md"}:
        raise ValueError(f"unexpected demo census file set: {sorted(files)}")
    results = {}
    for name, expected_git_blob in PROGRAMS.items():
        raw = (ROOT / name).read_bytes()
        blob = git_blob(raw)
        if blob != expected_git_blob:
            raise ValueError(f"upstream {name} Git blob mismatch {blob}")
        results[name] = {
            "original_git_blob_sha1": blob,
            "original_sha256": hashlib.sha256(raw).hexdigest(),
            "original_byte_length": len(raw),
            "upstream_url": ORIGIN + "/" + name,
            "upstream_intentionally_nonexecuting": name in UPSTREAM_NONEXECUTABLE,
            "no_preprocessing": True,
        }
    return results


def call(argv):
    try:
        p = subprocess.run([str(x) for x in argv],
                           text=True, capture_output=True, timeout=45)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"unresolved loader timeout for {argv[0]}") from e
    return {
        "command": [str(x) for x in argv],
        "exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr,
    }


def classify_rust(rec):
    if rec["exit"] == 0 and rec["stdout"] == "true.\n" and not rec["stderr"]:
        return "accepted_and_true"
    if rec["exit"] == 2 and "syntax at byte" in rec["stderr"]:
        return "syntax_rejection"
    return "runtime_or_other_failure"


def classify_swi(rec):
    if rec["exit"] != 0:
        return "failed_load"
    if rec["stderr"]:
        return "loaded_with_diagnostics"
    return "clean_load"


def run(gen24, gen25, swi, external_oracle):
    results = verify_original_sources()
    version = call([swi, "--version"])
    if version["exit"] or not (version["stdout"] or version["stderr"]).startswith(
        "SWI-Prolog version "
    ):
        raise ValueError("SWI-Prolog version not accessible")
    if not isinstance(external_oracle, dict) or not external_oracle.get("passed"):
        raise ValueError("prior independently executed 12-query oracle unavailable")
    if set(external_oracle.get("cases", {})) != {
        "likes_dahl", "likes_tandoori", "likes_chips", "likes_chop_suey",
        "likes_pizza", "likes_curry_negative", "likes_unknown_negative",
        "likes_all", "indian_all", "mild_all", "chinese_all", "italian_all",
    }:
        raise ValueError("not the frozen 12-query original-source SWI oracle")
    if external_oracle.get("errors"):
        raise ValueError("external source semantic oracle reports errors")
    for item in external_oracle["cases"].values():
        if not item["passed"]:
            raise ValueError("SWI original-source semantic oracle mismatch")
        # Explicitly require that the Gen25 Rust invocation uses the
        # untouched source rather than a comment-normalized derivative.
        cmd = item["results"]["candidate_unmodified_original"]["command"]
        if not cmd[1].endswith("/tests/rust_upstream_corpus/upstream/likes.pl"):
            raise ValueError("likes semantic oracle did not execute original source")
    raw = {}
    for name, source in results.items():
        path = ROOT / name
        probe = {}
        for role, exe in (("released_gen24", gen24), ("merged_gen25", gen25)):
            rec = call([exe.resolve(), path, "true.", "--max-solutions", "1",
                        "--max-steps", "100000"])
            probe[role] = {**rec, "outcome": classify_rust(rec)}
        witness = call([swi, "-q", "-f", "none", "-s", path,
                        "-g", "true", "-t", "halt"])
        probe["SWI_reference"] = {**witness, "outcome": classify_swi(witness)}
        raw[name] = {**source, **probe}
    if raw["likes.pl"]["merged_gen25"]["outcome"] != "accepted_and_true":
        raise RuntimeError("Gen25 no longer accepts the unmodified likes.pl positive control")
    if raw["likes.pl"]["released_gen24"]["outcome"] != "syntax_rejection":
        raise RuntimeError("Gen24 original-source parser negative control changed")
    if raw["likes.pl"]["SWI_reference"]["outcome"] != "clean_load":
        raise RuntimeError("live SWI did not cleanly load original likes.pl")
    counts = {
        "released_gen24": dict(sorted(Counter(
            row["released_gen24"]["outcome"] for row in raw.values()).items())),
        "merged_gen25": dict(sorted(Counter(
            row["merged_gen25"]["outcome"] for row in raw.values()).items())),
        "SWI_reference": dict(sorted(Counter(
            row["SWI_reference"]["outcome"] for row in raw.values()).items())),
    }
    return {
        "protocol": "docs/RUST_GEN26_UPSTREAM_DEMO_CENSUS_PROTOCOL.md",
        "upstream_repo": "SWI-Prolog/swipl-devel", "upstream_commit": PIN,
        "source_census_size": 4,
        "source_dir_license_git_blob_sha1": README_BLOB,
        "source_query": "true.",
        "source_modification": "none",
        "candidate_sha": GEN25,
        "baseline_sha": GEN24,
        "SWI_version": (version["stdout"] or version["stderr"]).strip(),
        "semantic_oracle_name": "gen25-unmodified-swi-elf64",
        "semantic_oracle_passed": True,
        "semantic_oracle_cases": 12,
        "programs": raw,
        "outcome_counts": counts,
        "passed": True,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gen24", type=Path, required=True)
    ap.add_argument("--gen25", type=Path, required=True)
    ap.add_argument("--swi", default="swipl")
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = run(args.gen24, args.gen25, args.swi,
                   json.loads(args.oracle.read_text()))
    except (ValueError, RuntimeError, OSError) as err:
        data = {"passed": False, "error": str(err)}
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print("GEN26 CENSUS", "PASS" if data.get("passed") else "FAIL",
          "counts", data.get("outcome_counts"), "error", data.get("error"),
          flush=True)
    if not data.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
