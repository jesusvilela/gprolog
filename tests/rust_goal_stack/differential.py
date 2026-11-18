#!/usr/bin/env python3
"""Gen17 vs Gen18 full Rust CLI differential, with orientation attacks.

The frozen 165-case Gen17 corpus and new deterministic representations are
compared in FULL stdout, stderr and exit code. No independent ISO oracle.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rust_trail"))
sys.path.insert(0, str(ROOT / "rust_choicepoint"))
from differential import corpus, generated_corpus, run  # noqa: E402
from differential_shared import extended  # noqa: E402

BASE = "46b536889e1b461af9e6cddb7f50239eec5697f5"


def additional_cases():
    src = "p(a). p(b). q(k). q(l). r(X,Y):-p(X),q(Y)."
    hand = [
        ("source_order", "", "X=a,Y=b,Z=c.", 8, 10000),
        ("no_reordering", "", "X=a,X=b.", 8, 10000),
        ("nested_and", src, "(p(X),q(Y)),true.", 8, 10000),
        ("flat_and", src, "p(X),q(Y),true.", 8, 10000),
        ("semicolon_tail", src, "(p(X);q(X)),true.", 8, 10000),
        ("nested_parentheses", src, "((p(X),true);(q(X),true)),fail.", 8, 10000),
        ("cut_preserves_new", src, "p(X),!, (Y=one;Y=two).", 8, 10000),
        ("cut_at_root", src, "(p(X);q(X)),!,true.", 8, 10000),
        ("sequential_unification", "", "X=a,Y=b,Z=c,X=a.", 8, 10000),
        ("fresh_var_display", "p(Z). p(f(Y)).", "p(X),true.", 8, 10000),
        ("failed_head_then_redo", "p(f(a,b)).p(f(c,c)).",
         "p(f(X,X)),true.", 8, 10000),
        ("cut_inside_body", "p(X):-q(X),!.p(never).q(a).q(b).",
         "p(X),true.", 8, 10000),
    ]
    yield from hand
    rng = random.Random(180017)
    templates = [
        "p(X),q(Y),true.",
        "(p(X);q(X)),true.",
        "(p(X),q(Y));(p(X),Y=k).",
        "p(X),!,q(Y).",
        "(p(X);p(Y)),!,q(Z).",
        "r(X,Y),true.",
        "p(X),p(Y),q(Z).",
        "p(X),fail;(q(Y),true).",
        "p(X), X \\= b, q(Y).",
        "(p(X),q(Y)),(Z=ok;Z=again).",
    ]
    for i in range(64):
        selected = templates[rng.randrange(len(templates))]
        # Intentionally deterministic duplication: representation/variable
        # order and cut behavior must survive identical source bytes.
        yield (f"seed_orientation_{i:03d}", src, selected, 20, 15000)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--abi", choices=("elf32", "elf64"), required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    base, candidate = args.baseline.resolve(), args.candidate.resolve()
    if not base.is_file() or not candidate.is_file():
        raise SystemExit("need both exact Rust binaries")
    cases = list(corpus()) + list(generated_corpus()) + list(extended()) + list(additional_cases())
    assert len(cases) == 241, len(cases)
    report = {
        "baseline_commit": BASE, "abi": args.abi,
        "comparison": "complete ordered stdout/stderr/exit, not merely solution sets",
        "previous_cases": 165, "orientation_additional_cases": 76,
        "cases": [], "errors": [], "passed": False,
        "independent_external_witness": False
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LC_ALL="C", LANG="C")
    with tempfile.TemporaryDirectory(prefix="gprolog-reversed-stack-") as directory:
        work = Path(directory)
        for name, source_text, query, max_solutions, max_steps in cases:
            program = work / (name + ".pl")
            program.write_text(source_text, encoding="utf-8")
            first = run(base, program, query, max_solutions, max_steps, env)
            second = run(candidate, program, query, max_solutions, max_steps, env)
            equal = (first["exit"], first["stdout"], first["stderr"]) == (
                second["exit"], second["stdout"], second["stderr"])
            row = {
                "case": name, "source_sha256": hashlib.sha256(source_text.encode()).hexdigest(),
                "query": query, "solutions_limit": max_solutions, "steps_limit": max_steps,
                "same_observables": equal,
                "baseline": {k: first[k] for k in ("exit", "stdout", "stderr")},
                "candidate": {k: second[k] for k in ("exit", "stdout", "stderr")}
            }
            report["cases"].append(row)
            if not equal:
                report["errors"].append(name)
                print("DIFF", args.abi, name, "MISMATCH", flush=True)
            output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    report["passed"] = not report["errors"]
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("RESULT", args.abi, "cases", len(report["cases"]),
          "passed", report["passed"], "errors", report["errors"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
