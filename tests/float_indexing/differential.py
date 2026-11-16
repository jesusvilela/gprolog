"""Adversarial semantic oracle for GNU Prolog static float-head indexing.

Build exactly the same generated Prolog sources with both versions.
The Python reference model enumerates source-order solutions independent
of either compiler. Compare expected output byte-for-byte across:
  - baseline native, baseline consulted
  - candidate native, candidate consulted
Also assert candidate-only float dispatch in generated WAM.

No speed measurements, no NaN/infinity claims, no dynamic indexing.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile

SEEDS = (20261116, 271828, 314159)
BOUNDARY_FLOATS = [
    "0.0", "-0.0", "0.1", "0.10000000000000001",
    "0.10000000000000002", "-0.1", "-0.10000000000000002",
    "1.0", "-1.0", "1.0000000000000002",
    "2.2250738585072014e-308", "2.225073858507201e-308",
    "5.0e-324", "-5.0e-324", "1.0e-320",
    "1.0e-300", "-1.0e-300", "1.0e300", "-1.0e300",
    "1.7976931348623157e308", "-1.7976931348623157e308",
]
NON_FLOAT = [
    ("integer", "0"), ("integer", "1"), ("integer", "-1"),
    ("integer", "65536"), ("atom", "a"), ("atom", "b"),
    ("structure", "f(a)"), ("structure", "f(b)"),
    ("list", "[a]"), ("list", "[b]"),
]


def semantic_match(fact, query):
    kind, literal, _ = fact
    qkind, qliteral = query
    if kind == "wildcard":
        return True
    if kind != qkind:
        return False
    if kind == "float":
        return float(literal) == float(qliteral)  # numeric C double equality
    return literal == qliteral


def build_source(seed):
    randomizer = random.Random(seed)
    fact_values = [("float", f) for f in BOUNDARY_FLOATS]
    fact_values += [("float", f"{i}.25") for i in range(-32, 33)]
    fact_values += NON_FLOAT
    randomizer.shuffle(fact_values)
    facts = [(kind, literal, f"v{i:03d}")
             for i, (kind, literal) in enumerate(fact_values)]
    # Variable-head clauses at several positions ensure ordered fallback.
    for offset, label in ((4, "wild_a"), (len(facts) // 2, "wild_b"),
                          (len(facts) - 3, "wild_c")):
        facts.insert(offset, ("wildcard", "_", label))
    queries = [("float", f) for f in BOUNDARY_FLOATS]
    queries += [("float", f"{i}.25") for i in (-32, -1, 0, 1, 17, 32)]
    queries += [
        ("float", "17.5"), ("float", "-17.5"), ("float", "1.5e-320"),
        ("float", "1.0e200"), ("float", "-1.0e200"),
        ("float", "0.10000000000000003"),
        ("integer", "0"), ("integer", "1"), ("integer", "65536"),
        ("atom", "a"), ("atom", "b"), ("atom", "missing"),
        ("structure", "f(a)"), ("structure", "f(missing)"),
        ("list", "[a]"), ("list", "[missing]"),
    ]
    # Permutation is a metamorphic transformation: the independent
    # source-order oracle changes accordingly, not by presuming a fixed order.
    randomizer.shuffle(queries)

    def row(name, matches):
        return f"ROW {name} [{','.join(matches)}]"

    expected = []
    run = []
    for index, query in enumerate(queries):
        name = f"q{index:03d}"
        matched = [tag for fkind, token, tag in facts
                   if semantic_match((fkind, token, tag), query)]
        expected.append(row(name, matched))
        run.append(f"    report({name}, {query[1]}),")
    expected.append(row("all", [tag for _, _, tag in facts]))
    expected.extend([
        row("cut_zero", ["cut_first"]),
        row("cut_negzero", ["cut_first"]),
        row("cut_other", ["cut_fallback"]),
    ])
    clauses = []
    for kind, literal, tag in facts:
        clauses.append(f"indexed({literal}, {tag}).")
    clauses += [
        "cut_case(0.0, cut_first) :- !.",
        "cut_case(0.0, cut_second).",
        "cut_case(_, cut_fallback).",
        "cut_case(-1.0, cut_negative).",
        "report(Name, Key) :-",
        "    findall(Tag, indexed(Key, Tag), Values),",
        "    format('ROW ~w ~w~n', [Name, Values]).",
        "report_all :-",
        "    findall(Tag, indexed(_, Tag), Values),",
        "    format('ROW all ~w~n', [Values]).",
        "report_cut(Name, Key) :-",
        "    findall(Tag, cut_case(Key, Tag), Values),",
        "    format('ROW ~w ~w~n', [Name, Values]).",
        "main :-",
        *run,
        "    report_all,",
        "    report_cut(cut_zero, 0.0),",
        "    report_cut(cut_negzero, -0.0),",
        "    report_cut(cut_other, 2.0),",
        "    halt.",
        ":- initialization(main).",
    ]
    source = f"% deterministic differential seed {seed}\n" + "\n".join(clauses) + "\n"
    return source, "\n".join(expected) + "\n", {
        "seed": seed, "facts": len(facts), "queries": len(queries),
        "boundary_float_literals": list(BOUNDARY_FLOATS),
        "float_keys": len({float(value) for kind, value, _ in facts if kind == "float"}),
    }


def run(cmd, cwd, env, timeout=150):
    result = subprocess.run([str(s) for s in cmd], cwd=cwd,
                            env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=timeout)
    return {"exit": result.returncode, "stdout": result.stdout}


def validate_result(result, expected, context):
    if result["exit"] != 0 or result["stdout"] != expected:
        delta = "\n".join(list(difflib.unified_diff(
            expected.splitlines(), result["stdout"].splitlines(),
            fromfile="independent oracle", tofile=context, lineterm=""))[:55])
        raise RuntimeError(f"{context}: exit={result['exit']}\n{delta}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-bin", type=Path, required=True)
    ap.add_argument("--candidate-bin", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path("float-differential.json"))
    args = ap.parse_args()
    bins = {
        "baseline": args.baseline_bin.resolve(),
        "candidate": args.candidate_bin.resolve(),
    }
    for version, bindir in bins.items():
        for program in ("pl2wam", "gplc", "gprolog"):
            if not (bindir / program).is_file():
                raise RuntimeError(f"{version}: no {program} in {bindir}")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": "bounded static first-argument float-head native/consulted differential",
        "platform": os.uname().sysname + " " + os.uname().machine,
        "seeds": list(SEEDS),
        "oracle": "Python model: source-order facts, numeric Python/C double equality, typed keys",
        "limitations": ["No non-finite literal syntax assumed",
                        "No dynamic predicates",
                        "No cross-ABI evidence from this run",
                        "Python and GNU parser rounding compatibility is exercised but not formally proved"],
        "cases": [], "passed": False,
    }

    def persist():
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="gprolog-float-differential-") as tmp:
        root = Path(tmp)
        for seed in SEEDS:
            source, expected, info = build_source(seed)
            case = {
                **info,
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "expected_sha256": hashlib.sha256(expected.encode()).hexdigest(),
                "versions": {},
            }
            report["cases"].append(case)
            persist()
            for version, bindir in bins.items():
                work = root / str(seed) / version
                work.mkdir(parents=True)
                (work / "probe.pl").write_text(source, encoding="utf-8")
                if hashlib.sha256((work / "probe.pl").read_bytes()).hexdigest() != case["source_sha256"]:
                    raise RuntimeError("source byte mismatch")
                env = dict(os.environ, PATH=str(bindir) + os.pathsep +
                           os.environ.get("PATH", ""))
                generation = run([bindir / "pl2wam", "--fast-math", "probe.pl"],
                                 work, env)
                if generation["exit"] != 0:
                    raise RuntimeError(f"{seed}/{version} WAM generation: {generation['stdout']}")
                wam = (work / "probe.wam").read_text(encoding="utf-8")
                has_term = "switch_on_term_flt(" in wam
                has_switch = "switch_on_float(" in wam
                if version == "baseline" and (has_term or has_switch):
                    raise RuntimeError("baseline emitted candidate-only float WAM")
                if version == "candidate" and not (has_term and has_switch):
                    raise RuntimeError("candidate failed to emit float WAM")
                compiled = run([bindir / "gplc", "--no-top-level",
                                "-o", "probe_native", "probe.pl"], work, env, timeout=240)
                if compiled["exit"] != 0:
                    raise RuntimeError(f"{seed}/{version} compile: {compiled['stdout']}")
                native = run([work / "probe_native"], work, env)
                consulted = run([bindir / "gprolog", "--quiet",
                                 "--consult-file", "probe.pl"], work, env)
                case["versions"][version] = {
                    "wam_float_term": has_term,
                    "wam_float_switch": has_switch,
                    "wam_sha256": hashlib.sha256(wam.encode()).hexdigest(),
                    "native_sha256": hashlib.sha256(native["stdout"].encode()).hexdigest(),
                    "consulted_sha256": hashlib.sha256(consulted["stdout"].encode()).hexdigest(),
                    "native_exit": native["exit"], "consulted_exit": consulted["exit"],
                }
                persist()
                validate_result(native, expected, f"{seed}/{version}/native")
                validate_result(consulted, expected, f"{seed}/{version}/consulted")
            print(f"PASS seed={seed} clauses={info['facts']} queries={info['queries']}"
                  " both versions x native/consulted -> identical independent oracle",
                  flush=True)
    report["passed"] = True
    persist()
    print(f"PASS: {len(SEEDS)} adversarial source permutations, "
          f"{4*len(SEEDS)} native+consulted compiler paths", flush=True)
    print(f"RAW JSON: {output}", flush=True)


if __name__ == "__main__":
    main()
