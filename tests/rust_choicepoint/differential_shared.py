#!/usr/bin/env python3
"""Exact Gen16-vs-shared Rust CLI differential; no C oracle claimed.

Uses previously frozen cases + deterministic seeded generator, adds boundary,
cut, multi-answer and search-budget stresses for clause continuation sharing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rust_trail"))
from differential import corpus, generated_corpus, run  # noqa: E402

BASE = "cd880bda3db495d329bdc3b6a0a0a4f654691579"


def extended():
    facts16 = "target(a).\n" * 16
    yield ("continue_first_16_64", facts16,
           ",".join(["target(a)"] * 64) + ".", 1, 200_000)
    yield ("continue_full_16_8", facts16,
           ",".join(["target(a)"] * 8) + ".", 16, 200_000)
    yield ("continue_deep_16_16",
           "target(f(g(h(a,b),k(c,d)),[a,b,c])).\n" * 16,
           ",".join(["target(f(g(h(a,b),k(c,d)),[a,b,c]))"] * 16) + ".",
           1, 200_000)
    yield ("many_choices_before_cut", "p(a). p(b). q(k). q(l).",
           "(p(X);p(Y)),!,q(Z).", 16, 200_000)
    yield ("cut_after_multiple_signatures",
           "p(a). p(b). q(one). q(two). r(X,Y):-p(X),!,q(Y).",
           "r(X,Y).", 16, 200_000)
    yield ("nested_fail_undo",
           "p(f(a,b)). p(f(c,c)). p(f(c,d)).",
           "p(f(X,X)), (X=c;X=z).", 16, 200_000)
    yield ("duplicated_facts",
           "p(a). p(a). p(b). p(b).",
           "p(X), p(Y).", 32, 200_000)
    yield ("known_missing_arity", "p(a). p(a,b).", "p(a,b,c).", 32, 200_000)
    for budget in (1, 2, 3, 4, 5, 10, 31, 64):
        yield (f"budget_{budget}", "p(a). p(b). p(c).",
               "p(X),p(Y).", 16, budget)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--abi", choices=("elf64", "elf32"), required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    base, cand = args.baseline.resolve(), args.candidate.resolve()
    if not base.is_file() or not cand.is_file():
        raise SystemExit("missing Rust-only executables")
    report = {
        "baseline_commit": BASE,
        "abi": args.abi,
        "claim": "Exact output/exit/stderr parity on frozen and extended Rust-only corpus",
        "prior_fixed_cases": len(corpus()), "prior_seeded_cases": 128,
        "extended_cases": 16, "seed": 17262026,
        "independent_external_prolog_oracle": False,
        "tests": [], "errors": [], "passed": False,
    }
    cases = list(corpus()) + list(generated_corpus()) + list(extended())
    assert len(cases) == 21 + 128 + 16, len(cases)
    env = dict(os.environ, LC_ALL="C", LANG="C")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gen17-parity-") as folder:
        work = Path(folder)
        for name, text, query, solutions, steps in cases:
            path = work / (name + ".pl")
            path.write_text(text, encoding="utf-8")
            a = run(base, path, query, solutions, steps, env)
            b = run(cand, path, query, solutions, steps, env)
            same = (a["exit"], a["stdout"], a["stderr"]) == (b["exit"], b["stdout"], b["stderr"])
            report["tests"].append({
                "case": name,
                "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "query": query, "max_solutions": solutions,
                "max_steps": steps, "same_observables": same,
                "baseline": {k: a[k] for k in ("exit", "stdout", "stderr")},
                "candidate": {k: b[k] for k in ("exit", "stdout", "stderr")},
            })
            if not same:
                report["errors"].append(name)
                print("PARITY", args.abi, name, "MISMATCH", flush=True)
            # Keep append-only partial data even if runner aborts later.
            output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    report["passed"] = not report["errors"]
    output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print("RESULT", args.abi, len(report["tests"]), "cases",
          "PASS" if report["passed"] else "FAIL",
          report["errors"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
