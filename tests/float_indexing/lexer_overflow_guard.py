"""Guard against non-finite decimal tokens in GNU Prolog lexer.

A successful rejected case must report a controlled finite-literal error,
not merely exit with a nonzero code after a fatal segmentation violation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile

VALID = ("1.25", "-0.0", "5.0e-324", "1.0e-9999",
         "-1.0e-9999", "1.7976931348623157e308", "nan")
INVALID = ("1.0e309", "-1.0e309", "1.0e9999", "-1.0e9999",
           "1.7976931348623159e308", "-1.7976931348623159e308")
DIAGNOSTIC = "finite floating point literal expected here"


def make_source(literal):
    return (f"value({literal}).\n"
            "main :- write('OK'), nl, halt.\n"
            ":- initialization(main).\n")


def run(command, cwd, env):
    try:
        p = subprocess.run([str(s) for s in command], cwd=cwd, env=env,
                           text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=45)
        return {"exit": p.returncode, "text": p.stdout[-3500:]}
    except subprocess.TimeoutExpired as x:
        return {"exit": None, "text": "TIMED OUT: " + repr(x.stdout)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bin-dir", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    opts = ap.parse_args()
    binary_dir = opts.bin_dir.resolve()
    for executable in ("gplc", "gprolog", "pl2wam"):
        if not (binary_dir / executable).is_file():
            raise RuntimeError(f"missing {executable}")
    artifact = opts.output.resolve()
    artifact.parent.mkdir(parents=True, exist_ok=True)
    report = {"abi": platform.machine(), "invalid_literals": list(INVALID),
              "valid_literals": list(VALID), "failures": [], "cases": [],
              "passed": False}
    def write():
        artifact.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="gprolog-finite-guard-") as tmp:
        for is_invalid, literals in ((False, VALID), (True, INVALID)):
            for i, literal in enumerate(literals):
                work = Path(tmp) / (("bad_" if is_invalid else "good_") + str(i))
                work.mkdir(parents=True, exist_ok=True)
                src = make_source(literal)
                (work / "case.pl").write_text(src, encoding="utf-8")
                env = dict(os.environ,
                           PATH=str(binary_dir) + os.pathsep + os.environ.get("PATH", ""))
                compile_result = run([binary_dir / "gplc", "--no-top-level",
                                      "-o", "case_native", "case.pl"], work, env)
                consulted_result = run([binary_dir / "gprolog", "--quiet",
                                        "--consult-file", "case.pl"], work, env)
                native = (run([work / "case_native"], work, env)
                          if compile_result["exit"] == 0 and (work / "case_native").is_file()
                          else None)
                item = {"literal": literal, "invalid": is_invalid,
                        "sha256": hashlib.sha256(src.encode()).hexdigest(),
                        "compilation": compile_result, "consulted": consulted_result,
                        "native": native}
                report["cases"].append(item)
                for mode, result in (("compile", compile_result), ("consult", consulted_result)):
                    text = result["text"].lower()
                    if "segmentation" in text or "sigsegv" in text or "bad address:" in text:
                        report["failures"].append(f"{literal}/{mode}: fatal segmentation diagnostic")
                    if result["exit"] is None:
                        report["failures"].append(f"{literal}/{mode}: timeout")
                    if is_invalid:
                        if DIAGNOSTIC not in result["text"]:
                            report["failures"].append(f"{literal}/{mode}: missing controlled rejection diagnostic")
                        if mode == "compile" and result["exit"] == 0:
                            report["failures"].append(f"{literal}/{mode}: unexpectedly compiled")
                    elif result["exit"] != 0:
                        report["failures"].append(f"{literal}/{mode}: valid input rejected")
                if not is_invalid and (native is None or native["exit"] != 0 or native["text"] != "OK\n"):
                    report["failures"].append(f"{literal}/native: missing known-answer OK")
                if not is_invalid and consulted_result["text"] != "OK\n":
                    report["failures"].append(f"{literal}/consult: missing known-answer OK")
                write()
                print(("BAD" if is_invalid else "GOOD"), literal,
                      "compile=", compile_result["exit"], "consult=", consulted_result["exit"],
                      "oracle=", "reject" if is_invalid else "OK",
                      flush=True)
    report["passed"] = not report["failures"]
    write()
    for err in report["failures"]:
        print("FAIL:", err, flush=True)
    print("SUMMARY", len(report["cases"]), "cases,", len(report["failures"]),
          "failures; JSON:", artifact, flush=True)
    if report["failures"]:
        raise SystemExit(1)
    print("PASS: finite controls preserved, overflow cleanly rejected in both modes")


if __name__ == "__main__":
    main()
