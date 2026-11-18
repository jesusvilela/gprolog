#!/usr/bin/env python3
"""Gen24: compare a genuine pinned upstream file with live SWI-Prolog.

The original likes.pl is intentionally unsupported by the Rust lexer due to
one /*...*/ documentation block. A strictly comment-only normalized
derivative is passed to frozen Gen18 / retired Gen19. Neither engine is edited.
This is a semantic experiment, not a performance benchmark.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

UPSTREAM_COMMIT = "111385b90852dade2b772d074cc55fefa20ee1a9"
UPSTREAM_FILE_GIT_SHA1 = "88f3d2edcb0fb68c99b559676e5982b3780715f6"
UPSTREAM_LICENSE_GIT_SHA1 = "fb3850a4dae3c29faea7907d9b3cd48d940fcfaa"
RELEASED_SHA = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"
REJECTED_SHA = "c09fff05d9b3dd43fb90014278e3a98d701d3640"
PREFIX = Path(__file__).resolve().parent / "upstream"
UPSTREAM = PREFIX / "likes.pl"
NOTICE = PREFIX / "README.md"
ATOM_PATTERN = re.compile(r"[a-z][a-z0-9_]*\Z")


class Case:
    def __init__(self, name, query, answer_variable=None):
        self.name = name
        self.query = query
        self.answer_variable = answer_variable


def cases():
    for name, atom, success in [
        ("likes_dahl", "dahl", True),
        ("likes_tandoori", "tandoori", True),
        ("likes_chips", "chips", True),
        ("likes_chop_suey", "chop_suey", True),
        ("likes_pizza", "pizza", True),
        ("likes_curry_negative", "curry", False),
        ("likes_unknown_negative", "unknown", False),
    ]:
        yield Case(name, f"likes(sam,{atom}).")
    for name, pred in [
        ("likes_all", "likes(sam,Food)"),
        ("indian_all", "indian(Food)"),
        ("mild_all", "mild(Food)"),
        ("chinese_all", "chinese(Food)"),
        ("italian_all", "italian(Food)"),
    ]:
        yield Case(name, pred + ".", "Food")


def git_blob_sha1(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def check_source_identity():
    raw = UPSTREAM.read_bytes()
    notice = NOTICE.read_bytes()
    if git_blob_sha1(raw) != UPSTREAM_FILE_GIT_SHA1:
        raise RuntimeError("unmodified public-domain upstream file SHA1 drift")
    if git_blob_sha1(notice) != UPSTREAM_LICENSE_GIT_SHA1:
        raise RuntimeError("upstream public-domain notice SHA1 drift")
    if b"All files in this demo directory are in the public domain." not in notice:
        raise RuntimeError("cannot establish upstream demo source licensing")
    if b"Copyright: Public domain" not in raw:
        raise RuntimeError("cannot establish individual file public-domain statement")
    if raw.count(b"/*") != 1 or raw.count(b"*/") != 1:
        raise RuntimeError("expected exactly one original /*...*/ documentation block")
    m = re.search(rb"/\*.*?\*/", raw, flags=re.DOTALL)
    if not m or not m.group().startswith(b"/** <examples>"):
        raise RuntimeError("original block does not match frozen documentation scope")
    normalized = raw[:m.start()] + raw[m.end():]
    if b"/*" in normalized or b"*/" in normalized:
        raise RuntimeError("more unsupported blocks remain")
    if normalized == raw or not normalized.count(b"likes(") >= 4:
        raise RuntimeError("unanticipated normalization result")
    return raw, normalized, notice, m.group()


def invoke(command, timeout=50):
    p = subprocess.run([str(v) for v in command],
                       text=True, capture_output=True, timeout=timeout)
    return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr,
            "command": [str(v) for v in command]}


def parse_swi_atom_list(output):
    """Parse a frozen flat atom list from ISO canonical or list notation.

    SWI write_canonical/1 may emit nested list constructor terms such as
    '[|]'(a,'[|]'(b,[])) because it ignores operator/list declarations.
    Never assume write_canonical() always emits [a,b].
    """
    source = output.strip()
    if source == "[]":
        return []
    if source.startswith("[") and source.endswith("]") and "(" not in source:
        inner = source[1:-1]
        atoms = [] if not inner else [x.strip() for x in inner.split(",")]
        if any(not ATOM_PATTERN.fullmatch(x) for x in atoms):
            raise RuntimeError(f"unsupported SWI list atom: {source!r}")
        return atoms
    for ctor in ("'[|]'(", "'.'(", "[|](", ".("):
        if source.startswith(ctor) and source.endswith(")"):
            interior = source[len(ctor):-1]
            pivot = interior.find(",")
            if pivot <= 0:
                raise RuntimeError(f"malformed SWI constructor: {source!r}")
            head = interior[:pivot].strip()
            tail = interior[pivot+1:].strip()
            if not ATOM_PATTERN.fullmatch(head):
                raise RuntimeError(f"non-plain SWI atom: {head!r}")
            return [head, *parse_swi_atom_list(tail)]
    raise RuntimeError(f"unsupported reference canonical list: {source!r}")


def reference_parser_self_test():
    expected = ["dahl", "chop_suey"]
    assert parse_swi_atom_list("[dahl,chop_suey]") == expected
    assert parse_swi_atom_list("'[|]'(dahl,'[|]'(chop_suey,[]))") == expected
    assert parse_swi_atom_list("'.'(dahl,'.'(chop_suey,[]))") == expected
    assert parse_swi_atom_list("[]") == []
    for malformed in ("[a|X]", "[a,'bad input']", "foo(a,b)", "'[|]'(a,X)"):
        try:
            parse_swi_atom_list(malformed)
            raise AssertionError(f"invalid canonical syntax accepted: {malformed}")
        except RuntimeError:
            pass


def external_reference(swi, raw_file, case):
    goal = case.query.removesuffix(".")
    if case.answer_variable:
        reference = (
            f"findall({case.answer_variable},{goal},Reference),"
            "write_canonical(Reference)"
        )
    else:
        reference = f"findall(ok,{goal},Reference),write_canonical(Reference)"
    result = invoke([swi, "-q", "-f", "none", "-s", raw_file,
                     "-g", reference, "-t", "halt"])
    if result["exit"] != 0 or result["stderr"]:
        raise RuntimeError(
            f"SWI reference failed for {case.name}: "
            f"{result['exit']} {result['stderr'][:350]}"
        )
    atoms = parse_swi_atom_list(result["stdout"])
    if case.answer_variable:
        expected = "".join(f"{case.answer_variable} = {atom}.\n" for atom in atoms)
    else:
        if any(atom != "ok" for atom in atoms):
            raise RuntimeError("unexpected independent ground-reference atom")
        expected = "true.\n" * len(atoms) if atoms else "false.\n"
    return result, atoms, expected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--swi", default="swipl")
    p.add_argument("--gen18", type=Path, required=True)
    p.add_argument("--gen19", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    reference_parser_self_test()
    report = {
        "protocol": "docs/RUST_GEN24_UPSTREAM_ORACLE_PROTOCOL.md",
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_git_blob_sha1": UPSTREAM_FILE_GIT_SHA1,
        "upstream_license_blob_sha1": UPSTREAM_LICENSE_GIT_SHA1,
        "released_sha": RELEASED_SHA, "retired_sha": REJECTED_SHA,
        "source_class": "unmodified original unsupported; comment-only normalized derivative",
        "original_parser_outcome": None,
        "swi_version": None,
        "cases": {}, "errors": [], "passed": False,
    }
    try:
        raw, normalized, notice, removed_comment = check_source_identity()
        frozen = list(cases())
        if len(frozen) != 12 or len({x.name for x in frozen}) != len(frozen):
            raise RuntimeError("frozen 12-query corpus changed")
        report["raw_source_sha256"] = hashlib.sha256(raw).hexdigest()
        report["raw_source_bytes"] = len(raw)
        report["normalized_source_sha256"] = hashlib.sha256(normalized).hexdigest()
        report["normalized_source_bytes"] = len(normalized)
        report["removed_block_sha256"] = hashlib.sha256(removed_comment).hexdigest()
        report["removed_block_bytes"] = len(removed_comment)
        report["original_source_modified"] = False
        version = invoke([args.swi, "--version"])
        if version["exit"] != 0:
            raise RuntimeError("SWI executable unavailable or version unknown")
        report["swi_version"] = version["stdout"].strip() or version["stderr"].strip()
        if not report["swi_version"]:
            raise RuntimeError("SWI version not printed")
        with tempfile.TemporaryDirectory(prefix="gen24-normalized-only-") as temp:
            derivative = Path(temp) / "likes_comment_normalized.pl"
            derivative.write_bytes(normalized)
            original_rust = {
                role: invoke([binary.resolve(), UPSTREAM, "likes(sam,dahl).",
                              "--max-solutions", "1", "--max-steps", "100000"])
                for role, binary in (
                    ("gen18", args.gen18),
                    ("gen19", args.gen19),
                )
            }
            report["original_parser_outcome"] = original_rust
            for role, rec in original_rust.items():
                if rec["exit"] != 2 or rec["stdout"] or (
                    "unsupported token byte 0x2f" not in rec["stderr"]
                ):
                    report["errors"].append(
                        f"{role}: unmodified source did not show declared lexer limitation"
                    )
            if report["errors"]:
                raise RuntimeError("original-source parse provenance mismatch; stop")
            for case in frozen:
                ref, atoms, expected = external_reference(args.swi, UPSTREAM, case)
                record = {
                    "query": case.query,
                    "answer_variable": case.answer_variable,
                    "reference_implementation": "live SWI-Prolog on full unmodified source",
                    "reference_canonical_atoms": atoms,
                    "reference": ref,
                    "translated_expected_stdout": expected,
                    "normalized_source_sha256": report["normalized_source_sha256"],
                    "engines": {},
                }
                for role, exe in (("gen18", args.gen18), ("gen19", args.gen19)):
                    rust = invoke([exe.resolve(), derivative, case.query,
                                   "--max-solutions", "32",
                                   "--max-steps", "100000"])
                    record["engines"][role] = rust
                    if (rust["exit"], rust["stdout"], rust["stderr"]) != (0, expected, ""):
                        report["errors"].append(
                            f"{case.name}/{role}: SWI-vs-Rust output/status mismatch"
                        )
                record["passed"] = all(
                    (x["exit"], x["stdout"], x["stderr"]) == (0, expected, "")
                    for x in record["engines"].values()
                )
                report["cases"][case.name] = record
                output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
                print("GEN24 CASE", case.name, "SWI", atoms, "match", record["passed"], flush=True)
            report["passed"] = not report["errors"] and len(report["cases"]) == 12
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as e:
        report["errors"].append(str(e))
    output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print("GEN24 RESULT", report["passed"], "cases", len(report["cases"]),
          "original_unmodified_rejected", bool(report["original_parser_outcome"]),
          "errors", report["errors"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
