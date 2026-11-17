"""GNU Prolog numeric locale audit: observe startup guarantee and perturb it.

The repo's Set_Locale() restores LC_NUMERIC to C at Pl_Start_Prolog.
This harness measures actual C state at sscanf, not environment variables.
A deliberately injected *post-start* setlocale is a different claim.
All C changes are applied only to a throwaway GitHub Actions checkout.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from decimal_exact_oracle import bits as exact_bits, INF, SIGN

TRACE_ENV = "GPROLOG_AUDIT_LOCALE_TRACE"
FORCE_ENV = "GPROLOG_AUDIT_POSTINIT_NUMERIC"
COMMA = "de_DE.UTF-8"

SAMPLES = (
    ("quarter", "1.25"),
    ("tenth", "0.1"),
    ("half", "0.5"),
    ("representable_one", "1.0"),
    ("large_fraction", "1234.5"),
    ("exponent", "12.5e2"),
    ("smallest_subnormal", "5.0e-324"),
    ("largest_finite", "1.7976931348623157e308"),
)
REGIMES = (
    ("c_environment", "C", False),
    ("de_environment_only", COMMA, False),
    ("de_forced_at_source_token", COMMA, True),
)


def substitute_once(source, old, replacement, what):
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{what}: C source anchor count {count}, not 1")
    return source.replace(old, replacement)


def instrument(lexer_path):
    """Inject change at the actual user numeric token, AFTER ordinary startup.

    Unlike V2's hook immediately after Set_Locale (before full engine init),
    this mutation executes just before sscanf in Lexer_Number, and only when
    the recorded source lexeme matches a per-case environment marker.
    """
    s = lexer_path.read_text(encoding="utf-8")
    s = substitute_once(s, "#include <float.h>",
                           "#include <float.h>\n#include <locale.h>\n#include <stdint.h>",
                           "lexer locale header")
    original = (
        '  if (sscanf(pl_token.name, "%lf", &pl_token.float_num) != 1 ||\n'
        '      !(pl_token.float_num <= DBL_MAX && pl_token.float_num >= -DBL_MAX))'
    )
    changed = '''  {
    const char *forced = getenv("GPROLOG_AUDIT_POSTINIT_NUMERIC");
    const char *target = getenv("GPROLOG_AUDIT_MUTATE_TOKEN");
    int converted;
    /* TEST ONLY: mutate only while reading the intended source lexeme. */
    if (forced && forced[0] && target && !strcmp(pl_token.name, target))
      {
        if (!setlocale(LC_NUMERIC, forced))
          abort();
      }
    converted = sscanf(pl_token.name, "%lf", &pl_token.float_num);
    const char *trace_name = getenv("GPROLOG_AUDIT_LOCALE_TRACE");
    if (trace_name && trace_name[0])
      {
        uint64_t raw_bits = 0;
        FILE *trace;
        memcpy(&raw_bits, &pl_token.float_num, sizeof(raw_bits));
        trace = fopen(trace_name, "a");
        if (!trace) abort();
        fprintf(trace, "NUM|%s|%s|%s|%016llx|%d\\n",
                setlocale(LC_NUMERIC, NULL), localeconv()->decimal_point,
                pl_token.name, (unsigned long long) raw_bits, converted);
        fclose(trace);
      }
    if (converted != 1 ||
        !(pl_token.float_num <= DBL_MAX && pl_token.float_num >= -DBL_MAX))'''
    s = substitute_once(s, original, changed, "lexer sscanf")
    s = substitute_once(
        s,
        '      err_msg = "finite floating point literal expected here";\n    }\n\n push_back:',
        '      err_msg = "finite floating point literal expected here";\n    }\n  }\n\n push_back:',
        "lexical guard close")
    lexer_path.write_text(s, encoding="utf-8")
    print("Instrumented test-only lexer at user float conversion, not engine startup")
    print("Lexer SHA256:", hashlib.sha256(s.encode()).hexdigest())


def target_abi(executable):
    with executable.open("rb") as file:
        head = file.read(6)
    if head[:4] != b"\x7fELF" or head[4] not in (1, 2) or head[5] != 1:
        raise RuntimeError("Expected little-endian ELF32 or ELF64: " + str(executable))
    return 32 if head[4] == 1 else 64


def execute(command, cwd, env):
    try:
        r = subprocess.run([str(x) for x in command], cwd=cwd, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=120)
        return {"exit": r.returncode, "output": r.stdout[-2500:]}
    except subprocess.TimeoutExpired as e:
        return {"exit": None, "output": "TIMEOUT: " + str(e.stdout)[-300:]}


def trace_records(path):
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = line.split("|")
        if len(cells) != 6 or cells[0] != "NUM":
            raise RuntimeError("Malformed direct C trace: " + line[:130])
        _, locale, separator, lexeme, encoded, converted = cells
        observed = int(encoded, 16)
        out.append({"locale": locale, "decimal_point": separator,
                    "lexeme": lexeme, "bits": f"{observed:016x}",
                    "converted": int(converted)})
    return out


def case_source(token):
    return (f"value({token}).\n"
            "main :- value(_), write('OK'), nl, halt.\n"
            ":- initialization(main).\n")


def verify(bindir, output):
    bindir = bindir.resolve()
    for binary in ("gplc", "gprolog"):
        if not (bindir / binary).is_file():
            raise RuntimeError(f"Missing {binary}")
    abi = target_abi(bindir / "gprolog")
    if abi != target_abi(bindir / "gplc"):
        raise RuntimeError("Compiler and consulted executable ABI mismatch")

    report = {
        "claim": "Pl_Start_Prolog forces C numeric locale on ordinary startup even under de_DE.UTF-8 environment",
        "adversarial_claim": "The same parsing remains invariant if a host changes LC_NUMERIC after initialization",
        "abi": f"ELF{abi}",
        "source_instrumentation": "test-only patches of engine.c and lexer_supp.c",
        "regimes": list(REGIMES),
        "cases": [],
        "normal_startup_failures": [],
        "postinit_invariance_failures": [],
        "harness_errors": [],
        "postinit_runtime_failures": [],
        "passed_normal_startup": False,
        "postinit_invariance": None,
    }
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="gprolog-numeric-locale-") as temporary:
        root = Path(temporary)
        for name, envlocale, forced in REGIMES:
            for title, token in SAMPLES:
                source = case_source(token)
                work = root / name / title
                work.mkdir(parents=True)
                (work / "probe.pl").write_text(source, encoding="utf-8")
                env = dict(os.environ)
                env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
                env["LC_ALL"] = envlocale
                env["LC_NUMERIC"] = envlocale
                env["LANG"] = envlocale
                if forced:
                    env[FORCE_ENV] = COMMA
                    env["GPROLOG_AUDIT_MUTATE_TOKEN"] = token
                else:
                    env.pop(FORCE_ENV, None)
                    env.pop("GPROLOG_AUDIT_MUTATE_TOKEN", None)
                row = {"regime": name, "literal": token,
                       "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                       "expected_bits": f"{exact_bits(token):016x}", "modes": {}}
                report["cases"].append(row)
                save()
                for mode, command in (
                    ("compiled", [bindir / "gplc", "--no-top-level",
                                  "-o", "probe_native", "probe.pl"]),
                    ("consulted", [bindir / "gprolog", "--quiet",
                                   "--consult-file", "probe.pl"]),
                ):
                    log = work / (mode + ".trace")
                    local = dict(env)
                    local[TRACE_ENV] = str(log)
                    actual = execute(command, work, local)
                    all_traces = trace_records(log)
                    matches = [x for x in all_traces if x["lexeme"].lower() == token.lower()]
                    row["modes"][mode] = {"process": actual, "matched_C_traces": matches}
                    context = f"{name}/{title}/{mode}"
                    if not matches:
                        (report["postinit_runtime_failures"] if forced else report["normal_startup_failures"]).append(context + ": missing C lexer witness")
                    else:
                        for x in matches:
                            expected_sep = "," if forced else "."
                            expected_locale = "de_DE" if forced else "C"
                            if x["decimal_point"] != expected_sep or expected_locale not in x["locale"]:
                                report["harness_errors"].append(
                                    context + ": unexpected effective locale/decimal point " +
                                    repr((x["locale"], x["decimal_point"])))
                            if x["converted"] != 1:
                                report["harness_errors"].append(context + ": conversion failed")
                            if x["bits"] != row["expected_bits"]:
                                if forced:
                                    report["postinit_invariance_failures"].append(
                                        context + ": decimal was parsed to " + x["bits"] +
                                        ", expected " + row["expected_bits"])
                                else:
                                    report["normal_startup_failures"].append(
                                        context + ": normal startup bit mismatch " + x["bits"])
                    stdout = actual["output"]
                    if any(s in stdout.lower() for s in ("segmentation", "bad address:", "sigsegv")):
                        (report["postinit_runtime_failures"] if forced else report["normal_startup_failures"]).append(context + ": fatal process error")
                    if actual["exit"] is None:
                        (report["postinit_runtime_failures"] if forced else report["normal_startup_failures"]).append(context + ": timed out")
                    if actual["exit"] != 0:
                        (report["postinit_runtime_failures"] if forced else report["normal_startup_failures"]).append(context + ": command failed")
                    if not forced and mode == "consulted" and stdout != "OK\n":
                        report["normal_startup_failures"].append(context + ": incorrect consulted response")
                    save()
                print(f"{name:24} {title:22} "
                      f"normal_errors={len(report['normal_startup_failures'])} "
                      f"postinit_mismatches={len(report['postinit_invariance_failures'])}",
                      flush=True)

    report["passed_normal_startup"] = (
        not report["normal_startup_failures"] and not report["harness_errors"])
    report["postinit_invariance"] = not report["postinit_invariance_failures"] and not report["postinit_runtime_failures"]
    save()
    print("NORMAL_STARTUP_PASS=", report["passed_normal_startup"],
          "POSTINIT_INVARIANCE=", report["postinit_invariance"],
          "MUTATION_MISMATCHES=", len(report["postinit_invariance_failures"]),
          "POSTINIT_RUNTIME_FAILURES=", len(report["postinit_runtime_failures"]))
    print("RAW JSON:", output)
    for message in report["normal_startup_failures"][:18]:
        print("FAIL NORMAL:", message)
    for message in report["harness_errors"][:18]:
        print("FAIL HARNESS:", message)
    for message in report["postinit_invariance_failures"][:18]:
        print("COUNTEREXAMPLE POSTINIT:", message)
    for message in report["postinit_runtime_failures"][:18]:
        print("POSTINIT RUNTIME FAILURE:", message)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        affected = [x for x in report["cases"]
                    if x["regime"] == "de_forced_at_source_token"]
        compiled_nonzero = sum(x["modes"]["compiled"]["process"]["exit"] != 0
                               for x in affected)
        consulted_fatal = sum(
            any(marker in x["modes"]["consulted"]["process"]["output"].lower()
                for marker in ("segmentation", "bad address:", "sigsegv"))
            for x in affected)
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("## Numeric locale audit: two separate conclusions\n\n")
            summary.write(f"- **Normal startup under C and German environments:** "
                          f"{'PASS' if report['passed_normal_startup'] else 'FAIL'} "
                          f"(16 source/mode checks, {report['abi']}).\n")
            summary.write(f"- **Forced comma-decimal locale at user token:** "
                          f"{'invariant' if report['postinit_invariance'] else 'FALSIFIED'}; "
                          f"{len(report['postinit_invariance_failures'])}/16 bit mismatches, "
                          f"{compiled_nonzero}/8 failed compilations, "
                          f"{consulted_fatal}/8 consulted fatal diagnostics.\n\n")
            summary.write("The forced mutation is a controlled adversarial test, "
                          "**not normal GNU Prolog startup**. A green workflow "
                          "represents only the startup claim.\n")
    if not report["passed_normal_startup"]:
        raise SystemExit(1)
    if report["postinit_invariance"]:
        print("PASS: normal startup and deliberate post-initialization perturbation")
    else:
        print("PASS NORMAL ONLY: post-initialization numeric locale invariance FALSIFIED; see JSON")
        # Explicit GitHub Actions warning; this is not a claim of robust parsing.
        print("::warning::Post-initialization locale mutation caused a numeric value mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    a = sub.add_parser("instrument")
    a.add_argument("--lexer", type=Path, required=True)
    b = sub.add_parser("verify")
    b.add_argument("--bin-dir", type=Path, required=True)
    b.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "instrument":
        instrument(args.lexer)
    else:
        verify(args.bin_dir, args.output)


if __name__ == "__main__":
    main()
