#!/usr/bin/env python3
"""Frozen Generation 27: seven unmodified, licensed, cross-project .pl files.

Record source-identity, rights, three raw executable load outcomes and
a non-cherry-picked SWI-clean subset. This is a source-loading census;
only the independent 12-query likes.pl execution is a semantic oracle.
"""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent / "upstream"
SWI = "111385b90852dade2b772d074cc55fefa20ee1a9"
SCRYER = "47f2c4e7cf9232137e2d43c7190c5504eb1a0045"
GEN24 = "fb9e05acd87e3fe71052e83ef38f26b9c12701d3"
GEN26 = "dbaf3af2b417893fcb636f196507aaaab905c286"
PROGRAMS = {
    "swi_likes": ("swi/demo/likes.pl", "88f3d2edcb0fb68c99b559676e5982b3780715f6", "SWI-Prolog/swipl-devel", SWI, "public-domain"),
    "swi_test_list": ("swi/tests/core_lang/test_list.pl", "2d2c0efb0e087f7ba3efa2f327d34c0acf352f2f", "SWI-Prolog/swipl-devel", SWI, "BSD-2 per-file"),
    "swi_test_unify": ("swi/tests/core_lang/test_unify.pl", "24a3ddcbe02f8e54bedfbab6df887eed1cde170f", "SWI-Prolog/swipl-devel", SWI, "BSD-2 per-file"),
    "swi_test_bags": ("swi/tests/core_lang/test_bags.pl", "a79eaa47096310207453adf98d3c6cd0c8a93cca", "SWI-Prolog/swipl-devel", SWI, "BSD-2 per-file"),
    "scryer_least_time": ("scryer/src/examples/least_time.pl", "2b599b6028fb9712c830e1dc5a11e0e2947b2374", "mthom/scryer-prolog", SCRYER, "BSD-3 repository"),
    "scryer_plres": ("scryer/src/examples/plres.pl", "9bc2931bed606280c86e680410f7def39768e4ef", "mthom/scryer-prolog", SCRYER, "BSD-3 repository; source public-domain attribution"),
    "scryer_echo_server": ("scryer/src/examples/echo_server.pl", "4543e60dae09b0435ec5babd092cbb1df5ed5faa", "mthom/scryer-prolog", SCRYER, "BSD-3 repository"),
}
DOCUMENTS = {
    "swi/demo/README.md": "fb3850a4dae3c29faea7907d9b3cd48d940fcfaa",
    "swi/tests/COPYING": "22bde7dfaceafad0fb8c58cc629c0090cc91c161",
    "scryer/LICENSE": "c6b5e60894896b32bd9a90404fbe6bf8fc023e1f",
}


def git_blob(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def verify_sources():
    files = {x.relative_to(ROOT).as_posix() for x in ROOT.rglob("*") if x.is_file()}
    expected = {row[0] for row in PROGRAMS.values()} | set(DOCUMENTS)
    if files != expected:
        raise ValueError(f"corpus mismatch expected {sorted(expected)}, got {sorted(files)}")
    for path, sha in DOCUMENTS.items():
        if git_blob((ROOT / path).read_bytes()) != sha:
            raise ValueError(f"licence authority blob mismatch {path}")
    if b"All files in this demo directory are in the public domain." not in (ROOT / "swi/demo/README.md").read_bytes():
        raise ValueError("SWI demo public-domain note absent")
    if b"Most of the SWI-Prolog test suite" not in (ROOT / "swi/tests/COPYING").read_bytes():
        raise ValueError("SWI test-suite mixed-license warning absent")
    if b"BSD 3-Clause License" not in (ROOT / "scryer/LICENSE").read_bytes():
        raise ValueError("Scryer original BSD-3 license absent")
    identity = {}
    for name, (path, sha, origin, commit, license_class) in PROGRAMS.items():
        raw = (ROOT / path).read_bytes()
        if git_blob(raw) != sha:
            raise ValueError(f"original source Git blob drift {name}")
        if license_class == "BSD-2 per-file" and b"Redistribution and use in source and binary forms" not in raw:
            raise ValueError(f"no individually licensed BSD-2 source header {name}")
        if license_class == "public-domain" and b"Copyright: Public domain" not in raw:
            raise ValueError(f"no individual public-domain source annotation {name}")
        identity[name] = {
            "source_path": path,
            "upstream_url": f"https://github.com/{origin}/blob/{commit}/{path.split('/',1)[1]}",
            "upstream_repo": origin,
            "upstream_commit": commit,
            "git_blob_sha1": sha,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_bytes": len(raw),
            "license_class": license_class,
            "unmodified": True,
        }
    return identity


def run(argv):
    p = subprocess.run([str(x) for x in argv], capture_output=True,
                       text=True, timeout=50)
    return {"argv": [str(x) for x in argv], "exit": p.returncode,
            "stdout": p.stdout, "stderr": p.stderr}


def classify_rust(o):
    if (o["exit"], o["stdout"], o["stderr"]) == (0, "true.\n", ""):
        return "accepted_and_true"
    if o["exit"] == 2 and "syntax at byte" in o["stderr"]:
        return "syntax_rejection"
    return "other"


def classify_swi(o):
    if o["exit"] != 0:
        return "failed_load"
    if o["stdout"] or o["stderr"]:
        return "process_exit0_with_output_or_diagnostics"
    return "clean_load"


def diagnostics(s):
    lines = [x.lstrip() for x in s.splitlines()]
    return {
        "has_error_line": any(x.startswith("ERROR:") for x in lines),
        "has_warning_line": any(x.startswith("Warning:") for x in lines),
        "stderr_line_count": len(lines),
    }


def inspect(gen24, gen26, swi):
    frozen = verify_sources()
    version = run([swi, "--version"])
    if version["exit"] or not (version["stdout"] or version["stderr"]).strip().startswith("SWI-Prolog version "):
        raise RuntimeError("independent SWI-Prolog version not identified")
    records = {}
    for name, details in frozen.items():
        source = (ROOT / details["source_path"]).resolve()
        rust_runs = {}
        for label, binary in (("rust_gen24",gen24), ("rust_gen26",gen26)):
            result = run([binary.resolve(), source, "true.",
                          "--max-solutions", "1", "--max-steps", "100000"])
            rust_runs[label] = {**result, "outcome": classify_rust(result)}
        reference = run([swi, "-q", "-f", "none", "-s", source, "-g", "true", "-t", "halt"])
        reference = {**reference, "outcome": classify_swi(reference), **diagnostics(reference["stderr"])}
        records[name] = {**details, **rust_runs, "SWI_reference": reference}
        print(f"GEN27 {name}: gen24={rust_runs['rust_gen24']['outcome']} "
              f"gen26={rust_runs['rust_gen26']['outcome']} "
              f"SWI={reference['outcome']} errors={reference['has_error_line']}",
              flush=True)
    if records["swi_likes"]["rust_gen24"]["outcome"] != "syntax_rejection":
        raise RuntimeError("prior original-source parser negative control drifted")
    if records["swi_likes"]["rust_gen26"]["outcome"] != "accepted_and_true":
        raise RuntimeError("original-source likes positive Rust control drifted")
    if records["swi_likes"]["SWI_reference"]["outcome"] != "clean_load":
        raise RuntimeError("original-source likes SWI reference no longer clean")
    clean = [name for name in PROGRAMS if records[name]["SWI_reference"]["outcome"] == "clean_load"]
    accepted_clean = [name for name in clean if records[name]["rust_gen26"]["outcome"] == "accepted_and_true"]
    counts = {k: dict(sorted(Counter(records[n][k]["outcome"] for n in PROGRAMS).items()))
              for k in ("rust_gen24","rust_gen26","SWI_reference")}
    return {
        "protocol": "docs/RUST_GEN27_CROSS_PROJECT_SOURCE_PROTOCOL.md",
        "program_count": 7,
        "license_document_sha1s": DOCUMENTS,
        "swi_commit": SWI, "scryer_commit": SCRYER,
        "rust_gen24_sha": GEN24,"rust_candidate_sha": GEN26,
        "SWI_version": (version["stdout"] or version["stderr"]).strip(),
        "source_transformation": "none",
        "primary_metric": "seven separate typed original-source load outcomes; not general conformance",
        "programs": records, "clean_under_swi": clean,
        "clean_and_accepted_under_rust": accepted_clean,
        "outcome_counts": counts,
        "passed": True,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gen24",type=Path,required=True)
    p.add_argument("--gen26",type=Path,required=True)
    p.add_argument("--swi",default="swipl")
    p.add_argument("--output",type=Path,required=True)
    x=p.parse_args()
    x.output.parent.mkdir(parents=True,exist_ok=True)
    try:
        data=inspect(x.gen24,x.gen26,x.swi)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
        data={"passed":False,"error":str(e)}
    x.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print("GEN27 FINAL",data.get("passed"),"clean",data.get("clean_under_swi"),
          "clean_and_accepted",data.get("clean_and_accepted_under_rust"),
          "error",data.get("error"),flush=True)
    if not data.get("passed"):
        raise SystemExit(1)

if __name__=="__main__":
    main()
