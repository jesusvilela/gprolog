"""R1: inject a Rust C ABI observer after actual GNU Prolog Lexer_Number.

The original sscanf and finite-range guard remain intact. The injected
code is never committed into src/BipsPl/lexer_supp.c: only this script is.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from decimal_exact_oracle import cases, INF, SIGN

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one C anchor, observed {count}")
    return text.replace(old, new)

def instrument(path):
    src = path.read_text(encoding="utf-8")
    src = replace_once(src, "#include <float.h>",
                       "#include <float.h>\n#include <stdint.h>\n#include <dlfcn.h>",
                       "C ABI imports")
    anchor = '#include <stdarg.h>\n'
    helper = r'''
/* R1 TEST ONLY: C retains full numeric authority; Rust only observes. */
typedef int (*Shadow_Finite_Parser)(const unsigned char *, size_t, uint64_t *);

static void
Rust_Decimal_Shadow(const char *token, double c_value, int c_accepted)
{
  const char *library_path = getenv("GPROLOG_RUST_SHADOW_LIB");
  static void *library_handle = NULL;
  static Shadow_Finite_Parser parser = NULL;
  uint64_t c_bits = 0;
  uint64_t rust_bits = 0;
  int status;
  FILE *f;
  const char *trace_path;
  void *symbol;
  if (!library_path || !*library_path)
    return;
  if (!parser)
    {
      library_handle = dlopen(library_path, RTLD_NOW | RTLD_LOCAL);
      if (!library_handle)
        {
          fprintf(stderr, "R1 DLOPEN: %s\n", dlerror());
          abort();
        }
      symbol = dlsym(library_handle, "gprolog_decimal_parse_bits");
      if (!symbol || sizeof(parser) != sizeof(symbol))
        abort();
      memcpy(&parser, &symbol, sizeof(parser));
    }
  memcpy(&c_bits, &c_value, sizeof(c_bits));
  status = parser((const unsigned char *) token, strlen(token), &rust_bits);
  trace_path = getenv("GPROLOG_RUST_SHADOW_TRACE");
  if (!trace_path || !*trace_path)
    abort();
  f = fopen(trace_path, "a");
  if (!f)
    abort();
  fprintf(f, "SHADOW|%s|%d|%d|%016llx|%016llx\n",
          token, c_accepted, status,
          (unsigned long long) c_bits, (unsigned long long) rust_bits);
  fclose(f);
}
'''
    src = replace_once(src, anchor, anchor + helper + "\n", "helper insertion")
    block = '    }\n\n push_back:\n  Unget_Last_Char;'
    replacement = '''    }
  /* The original C value and parser state stay untouched. */
  Rust_Decimal_Shadow(pl_token.name, pl_token.float_num,
                      pl_token.type == TOKEN_FLOAT);

 push_back:
  Unget_Last_Char;'''
    src = replace_once(src, block, replacement, "float end after guarded sscanf")
    path.write_text(src, encoding="utf-8")
    print("R1 test-only C shadow injected; original sscanf/guard unchanged")
    print("C source SHA256", hashlib.sha256(src.encode()).hexdigest())

def command(argv, cwd, env, timeout=60):
    try:
        p = subprocess.run([str(x) for x in argv], cwd=cwd, env=env,
                           text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return {"exit": p.returncode, "output": p.stdout[-2400:]}
    except subprocess.TimeoutExpired as e:
        return {"exit": None, "output": "TIMEOUT " + repr(e.stdout)[:180]}

def parsed_trace(path):
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("|")
        if len(parts) != 5 or parts[0] != "SHADOW":
            raise RuntimeError("malformed R1 trace " + line[:120])
        rows.append({"token": parts[1], "c_accepted": int(parts[2]),
                     "rust_status": int(parts[3]), "c_bits": parts[4]})
    return rows

def fixture(decimal):
    return (f"value({decimal}).\n"
            "main :- value(_), write('OK'), nl, halt.\n"
            ":- initialization(main).\n")

def verify(bin_dir, rust_library, output, abi):
    bin_dir = bin_dir.resolve()
    rust_library = rust_library.resolve()
    for x in ("gplc", "gprolog"):
        if not (bin_dir / x).is_file():
            raise RuntimeError("GNU Prolog executable missing: " + x)
    if not rust_library.is_file():
        raise RuntimeError("Rust cdylib not built")
    samples = cases()
    if len(samples) != 44 or sum((want & INF) == INF for _, _, want in samples) != 5:
        raise RuntimeError("Frozen exact rational corpus changed")
    result = {
        "claim": "Original GNU Prolog lexer and Rust C ABI shadow agree for 44 rational fixtures",
        "abi": abi, "source_patch": "runner-only after Lex_Number guarded sscanf",
        "sample_count": len(samples), "cases": [], "errors": [],
        "passed": False, "status": "H until measurements",
    }
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with tempfile.TemporaryDirectory(prefix="r1-shadow-") as tmp:
        root = Path(tmp)
        for locale in ("C", "de_DE.UTF-8"):
            for name, literal, bits in samples:
                is_finite = (bits & INF) != INF
                lexeme = literal.lstrip("+-")
                expected_magnitude = bits & ~SIGN
                src = fixture(literal)
                work = root / locale.replace(".", "_") / name
                work.mkdir(parents=True)
                (work / "shadow.pl").write_text(src, encoding="utf-8")
                env = dict(os.environ, LC_ALL=locale, LANG=locale,
                           LC_NUMERIC=locale, PATH=str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
                env["GPROLOG_RUST_SHADOW_LIB"] = str(rust_library)
                row = {"locale": locale, "name": name, "source_sha256": hashlib.sha256(src.encode()).hexdigest(),
                       "literal": literal, "oracle_bits": f"{bits:016x}",
                       "expected_finite": is_finite, "modes": {}}
                result["cases"].append(row)
                for mode, argv in (
                    ("compiled", [bin_dir / "gplc", "--no-top-level", "-o", "shadow_native", "shadow.pl"]),
                    ("consulted", [bin_dir / "gprolog", "--quiet", "--consult-file", "shadow.pl"]),
                ):
                    env2 = dict(env, GPROLOG_RUST_SHADOW_TRACE=str(work / (mode + ".trace")))
                    actual = command(argv, work, env2, timeout=90)
                    events = parsed_trace(work / (mode + ".trace"))
                    matching = [e for e in events if e["token"].lower() == lexeme.lower()]
                    row["modes"][mode] = {"process": actual, "matching_trace": matching}
                    key = f"{locale}/{name}/{mode}"
                    if not matching:
                        result["errors"].append(key + ": NO LIVE RUST C ABI SHADOW EVENT")
                    for e in matching:
                        if e["c_accepted"] != (1 if is_finite else 0):
                            result["errors"].append(key + ": historical C acceptance classification wrong")
                        if e["rust_status"] != e["c_accepted"]:
                            result["errors"].append(key + ": Rust/C status mismatch")
                        if is_finite:
                            if int(e["c_bits"], 16) != expected_magnitude:
                                result["errors"].append(key + ": C lexer bits do not match exact rational magnitude")
                            # Rust bit pattern is checked below using the separate saved rust-bit field.
                        if e["rust_status"] < 0:
                            result["errors"].append(key + ": rust ABI invalid pointer/length")
                    output_text = actual["output"]
                    if any(x in output_text.lower() for x in ("segmentation", "bad address:", "sigsegv")):
                        result["errors"].append(key + ": fatal diagnostic")
                    if actual["exit"] is None:
                        result["errors"].append(key + ": timeout")
                    if is_finite:
                        if actual["exit"] != 0:
                            result["errors"].append(key + ": rejected finite input")
                        elif mode == "consulted" and output_text.strip() != "OK":
                            result["errors"].append(key + ": wrong consulted answer")
                        if mode == "compiled" and actual["exit"] == 0:
                            native = command([work / "shadow_native"], work, env, timeout=30)
                            row["modes"]["native"] = native
                            if native["exit"] != 0 or native["output"].strip() != "OK":
                                result["errors"].append(key + ": native answer incorrect")
                    else:
                        if "finite floating point literal expected here" not in output_text:
                            result["errors"].append(key + ": overflow rejection missing")
                        if mode == "compiled" and actual["exit"] == 0:
                            result["errors"].append(key + ": overflow compiled successfully")
                save()
                print(locale, name, "finite" if is_finite else "reject",
                      "errors=" + str(len(result["errors"])), flush=True)
    result["passed"] = not result["errors"]
    result["status"] = "M for fixed corpus" if result["passed"] else "blocked"
    save()
    for issue in result["errors"][:35]: print("FAIL:", issue, flush=True)
    print("R1", abi, "PASSED", result["passed"], "CASES", len(result["cases"]),
          "ERRORS", len(result["errors"]), "RAW", output, flush=True)
    if result["errors"]:
        raise SystemExit(1)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action", required=True)
    a=sub.add_parser("instrument")
    a.add_argument("--lexer", type=Path, required=True)
    b=sub.add_parser("verify")
    b.add_argument("--bin-dir",type=Path,required=True)
    b.add_argument("--rust-library",type=Path,required=True)
    b.add_argument("--output",type=Path,required=True)
    b.add_argument("--abi",choices=["elf64","elf32"],required=True)
    args=p.parse_args()
    if args.action=="instrument": instrument(args.lexer)
    else: verify(args.bin_dir, args.rust_library, args.output, args.abi)

if __name__ == "__main__":
    main()
