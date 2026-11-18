#!/usr/bin/env python3
"""Gen18-vs-Gen19 exact Rust-only CLI output comparison.

Loads the existing 241-case oriented differential corpus as an immutable
test fixture; adds T2 first-failure, deep-head and cut-budget attacks.
No external ISO Prolog oracle is claimed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile

PATH = Path(__file__).resolve().parents[1] / "rust_goal_stack" / "differential.py"
SPEC = importlib.util.spec_from_file_location("gen18_frozen_cases", PATH)
GEN18 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEN18)
BASE = "901c8b58c12fbe8b79f70b0118f951f3ed2fcf21"


def attacks():
    t2 = "target(b). target(a)."
    for n in (1, 2, 8, 32):
        chain = ",".join(["target(a)"] * n) + "."
        yield (f"failed_first_t2_{n}", t2, chain, 4, 20000)
        yield (f"first_success_t2_{n}",
               "target(a). target(a).", chain, 4, 20000)
    for steps in (1, 2, 3, 4, 7, 16, 32, 64):
        yield (f"failed_first_budget_{steps}", t2,
               "target(a),target(a).", 3, steps)
    yield ("compound_fail_rollback",
           "target(f(a,b)). target(f(c,c)).",
           "target(f(X,X)),X=c.", 3, 1000)
    yield ("cut_two_owned",
           "choose(a). choose(b). p(X):-choose(X),!,true.",
           "p(X).", 8, 1000)
    yield ("cut_three_shared",
           "choose(a). choose(b). choose(c). p(X):-choose(X),!,true.",
           "p(X).", 8, 1000)
    yield ("mixed_head_arity",
           "target(a). target(a,b). target(b).",
           "target(X), X \\= a.", 8, 1000)
    yield ("deep_failure",
           "target(f(g(a),h(b))). target(f(g(a),h(c))).",
           "target(f(g(a),h(c))).", 8, 1000)
    yield ("duplicate_three",
           "target(a). target(a). target(a).",
           "target(X),true.", 3, 2000)
    yield ("three_redos",
           "p(a). p(b). p(c).",
           "p(X),true.", 3, 2000)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--abi", choices=("elf64", "elf32"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base, new = args.baseline.resolve(), args.candidate.resolve()
    if not base.is_file() or not new.is_file():
        raise SystemExit("missing executable")
    frozen = list(GEN18.corpus()) + list(GEN18.generated_corpus()) + (
        list(GEN18.extended()) + list(GEN18.additional_cases()))
    assert len(frozen) == 241
    new_cases = list(attacks())
    report = {
        "baseline_commit": BASE, "abi": args.abi,
        "metric": "full stdout, stderr, exit status",
        "frozen_gen18_cases": len(frozen), "additional_attacks": len(new_cases),
        "independent_external_witness": False,
        "cases": [], "errors": [], "passed": False,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LANG="C", LC_ALL="C")
    with tempfile.TemporaryDirectory(prefix="gen19-stdout-") as root:
        work = Path(root)
        for name, source, query, solutions, steps in frozen + new_cases:
            src = work / (name + ".pl")
            src.write_text(source, encoding="utf-8")
            baseline = GEN18.run(base, src, query, solutions, steps, env)
            candidate = GEN18.run(new, src, query, solutions, steps, env)
            good = tuple(baseline[k] for k in ("exit", "stdout", "stderr")) == tuple(
                candidate[k] for k in ("exit", "stdout", "stderr"))
            report["cases"].append({
                "case": name,
                "program_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "query": query, "max_solutions": solutions, "max_steps": steps,
                "same_observables": good,
                "baseline": {k: baseline[k] for k in ("exit", "stdout", "stderr")},
                "candidate": {k: candidate[k] for k in ("exit", "stdout", "stderr")}
            })
            if not good:
                report["errors"].append(name)
                print("MISMATCH", args.abi, name, flush=True)
            output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    report["passed"] = not report["errors"] and len(report["cases"]) == 241 + len(new_cases)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("RESULT", args.abi, "cases", len(report["cases"]),
          "passed", report["passed"], "errors", report["errors"], flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
