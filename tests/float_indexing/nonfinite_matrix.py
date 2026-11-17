"""Differential matrix for boundary float literals, GNU Prolog baseline vs fork.

Do not assume that arithmetic NaNs or infinities have lexical forms. Record
observable statuses and raw diagnostics before interpreting any result.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile

CASES = [
    ("finite_control", "head", "1.25", True),
    ("max_finite", "head", "1.7976931348623157e308", True),
    ("near_overflow", "head", "1.7976931348623159e308", False),
    ("positive_overflow", "head", "1.0e309", False),
    ("negative_overflow", "head", "-1.0e309", False),
    ("extreme_exponent", "head", "1.0e9999", False),
    ("min_subnormal", "head", "5.0e-324", True),
    ("subnormal_rounds_zero", "head", "1.0e-324", True),
    ("positive_underflow", "head", "1.0e-9999", True),
    ("negative_underflow", "head", "-1.0e-9999", True),
    ("negative_zero", "head", "-0.0", True),
    ("atom_nan_control", "head", "nan", True),
    ("atom_inf_control", "head", "inf", True),
    ("atom_infinity_control", "head", "infinity", True),
    ("arithmetic_finite", "arith", "1.25 + 2.0", True),
    ("arithmetic_overflow_literal", "arith", "1.0e309 + 1.0", False),
    ("arithmetic_exp_overflow", "arith", "exp(1000.0)", False),
    ("arithmetic_division_zero", "arith", "1.0 / 0.0", False),
    ("arithmetic_zero_zero", "arith", "0.0 / 0.0", False),
    ("arithmetic_underflow_literal", "arith", "1.0e-9999 + 0.0", True),
]


def fixture(kind, literal):
    if kind == "head":
        return (
            f"target({literal}, matched).\n"
            "target(3.75, unrelated).\n"
            "target(_, wildcard).\n"
            "main :-\n"
            f"    findall(X, target({literal}, X), Answers),\n"
            "    format('OUT ~w~n', [Answers]),\n"
            "    halt.\n"
            ":- initialization(main).\n"
        )
    return (
        "main :-\n"
        f"    catch((Value is ({literal}),\n"
        "           format('VALUE ~w~n', [Value])),\n"
        "          Error, format('EXCEPTION ~w~n', [Error])),\n"
        "    halt.\n"
        ":- initialization(main).\n"
    )


def command(args, cwd, env, timeout=35):
    try:
        proc = subprocess.run([str(a) for a in args], cwd=cwd, env=env,
                              text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout)
        diagnostic = proc.stdout.lower()
        # GNU Prolog installs its own SIGSEGV handler and may exit with code 1.
        # Never let a textual fatal segmentation diagnosis become a normal error.
        signaled = any(token in diagnostic for token in (
            "segmentation violation", "segmentation fault", "sigsegv",
            "signal 11", "bad address:"))
        status = ("crash_diagnostic" if signaled else
                  "suspected_crash" if proc.returncode < 0 or proc.returncode >= 128
                  else "error" if proc.returncode else "success")
        return {"status": status, "exit": proc.returncode,
                "stdout": proc.stdout[-3000:]}
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or b""
        if isinstance(output, bytes):
            output = output.decode("utf-8", "replace")
        return {"status": "timeout", "exit": None, "stdout": output[-3000:]}


def one_version(bin_dir, case_dir, source):
    case_dir.mkdir(parents=True)
    file = case_dir / "probe.pl"
    file.write_text(source, encoding="utf-8")
    env = dict(os.environ,
               PATH=str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
    record = {"source_sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
    gen = command([bin_dir / "pl2wam", "--fast-math", "probe.pl"],
                  case_dir, env)
    record["wam_generate"] = gen
    wam_file = case_dir / "probe.wam"
    if gen["status"] == "success" and wam_file.is_file():
        text = wam_file.read_text(encoding="utf-8")
        record["wam"] = {
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "float_term_switch": "switch_on_term_flt(" in text,
            "float_value_switch": "switch_on_float(" in text,
        }
    else:
        record["wam"] = None
    comp = command([bin_dir / "gplc", "--no-top-level", "-o",
                    "probe_native", "probe.pl"], case_dir, env, 80)
    record["native_compile"] = comp
    exe = case_dir / "probe_native"
    record["native"] = (
        command([exe], case_dir, env, 25)
        if comp["status"] == "success" and exe.is_file()
        else {"status": "not_run", "exit": None, "stdout": ""}
    )
    record["consulted"] = command(
        [bin_dir / "gprolog", "--quiet", "--consult-file", "probe.pl"],
        case_dir, env, 25)
    return record


def state(record, mode):
    if mode == "native" and record["native_compile"]["status"] != "success":
        return "compile_" + record["native_compile"]["status"]
    return record[mode]["status"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-bin", type=Path, required=True)
    parser.add_argument("--candidate-bin", type=Path, required=True)
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument("--candidate-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bins = {"baseline": args.baseline_bin.resolve(),
            "candidate": args.candidate_bin.resolve()}
    for version, directory in bins.items():
        for name in ("pl2wam", "gplc", "gprolog"):
            if not (directory / name).is_file():
                raise RuntimeError(f"missing {version}/{name}")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "hypothesis": "No candidate-only semantic or runtime failure on this predeclared float boundary suite",
        "baseline_ref": args.baseline_ref, "candidate_ref": args.candidate_ref,
        "host": platform.platform(), "cases": [], "failures": [],
        "triage_cases": [], "original_first_run_status": "incorrectly green: fatal segmentation diagnostics were classified as ordinary errors",
        "severity_policy": "shared baseline+cand crashes are failures, not safe parity",
        "nonfinite_semantics": "Observed only; no conformance claimed", "passed": False,
    }
    def persist():
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="gprolog-float-boundaries-") as temp:
        for label, kind, literal, finite_control in CASES:
            src = fixture(kind, literal)
            expected_sha = hashlib.sha256(src.encode()).hexdigest()
            case = {"name": label, "kind": kind, "literal": literal,
                    "finite_control": finite_control,
                    "source_sha256": expected_sha, "versions": {}}
            report["cases"].append(case)
            persist()
            for version in ("baseline", "candidate"):
                observed = one_version(bins[version],
                                       Path(temp) / version / label, src)
                if observed["source_sha256"] != expected_sha:
                    raise RuntimeError("identical source invariant violated")
                case["versions"][version] = observed
                persist()
            b, c = case["versions"]["baseline"], case["versions"]["candidate"]
            for mode in ("native", "consulted"):
                before, after = state(b, mode), state(c, mode)
                if before != after:
                    report["failures"].append(f"{label}/{mode}: baseline={before} candidate={after}")
                if any(x in ("timeout", "suspected_crash", "crash_diagnostic",
                             "compile_timeout", "compile_suspected_crash", "compile_crash_diagnostic")
                       for x in (before, after)):
                    report["failures"].append(f"{label}/{mode}: crash or timeout")
                if before == after == "success" and b[mode]["stdout"] != c[mode]["stdout"]:
                    report["failures"].append(f"{label}/{mode}: successful outputs disagree")
                if finite_control:
                    if before != "success" or after != "success":
                        report["failures"].append(f"{label}/{mode}: expected finite/atom control did not execute")
                    elif kind == "head" and c[mode]["stdout"] != "OUT [matched,wildcard]\n":
                        report["failures"].append(f"{label}/{mode}: known-answer mismatch {c[mode]['stdout']!r}")
            if label == "finite_control":
                bt, ct = b["wam"], c["wam"]
                if bt is None or bt["float_term_switch"] or bt["float_value_switch"]:
                    report["failures"].append("finite_control: baseline WAM structural gate failed")
                if ct is None or not (ct["float_term_switch"] and ct["float_value_switch"]):
                    report["failures"].append("finite_control: candidate float WAM not emitted")
            persist()
            issues = len([x for x in report["failures"] if x.startswith(label)])
            print(f"{label:31s} native={state(b,'native')}/{state(c,'native')} "
                  f"consulted={state(b,'consulted')}/{state(c,'consulted')} "
                  f"issues={issues}", flush=True)
    # Post-observation diagnostics: intentionally separate from frozen 20 cases.
    # These are for localization, NOT an opportunity to weaken the primary gate.
    minimal = {
        "load_only_positive": "value(1.0e309).\nmain :- halt.\n:- initialization(main).\n",
        "load_only_negative": "value(-1.0e309).\nmain :- halt.\n:- initialization(main).\n",
        "load_only_finite_control": "value(1.25).\nmain :- halt.\n:- initialization(main).\n",
        "unify_positive": "main :- X = 1.0e309, (X = 1.0e309 -> halt ; halt(14)).\n:- initialization(main).\n",
        "unify_negative": "main :- X = -1.0e309, (X = -1.0e309 -> halt ; halt(14)).\n:- initialization(main).\n",
    }
    with tempfile.TemporaryDirectory(prefix="gprolog-overflow-minimization-") as tmp:
        for name, source in minimal.items():
            row = {"name": name, "status": "posthoc_diagnostic",
                   "source": source,
                   "sha256": hashlib.sha256(source.encode()).hexdigest(),
                   "versions": {}}
            report["triage_cases"].append(row)
            for version in ("baseline", "candidate"):
                d = Path(tmp) / version / name
                d.mkdir(parents=True)
                p = d / "repro.pl"
                p.write_text(source, encoding="utf-8")
                env = dict(os.environ,
                           PATH=str(bins[version]) + os.pathsep + os.environ.get("PATH", ""))
                row["versions"][version] = command(
                    [bins[version] / "gprolog", "--quiet", "--consult-file", "repro.pl"],
                    d, env, 25)
            persist()
            print("TRIAGE", name, "baseline=" + row["versions"]["baseline"]["status"],
                  "candidate=" + row["versions"]["candidate"]["status"], flush=True)
    report["passed"] = not report["failures"]
    persist()
    for issue in report["failures"]:
        print("FAIL:", issue, flush=True)
    print(f"TOTAL cases={len(CASES)} failures={len(report['failures'])}", flush=True)
    print("JSON:", output, flush=True)
    if not report["passed"]:
        raise SystemExit(1)
    print("PASS: bounded differential with exact finite controls", flush=True)


if __name__ == "__main__":
    main()
