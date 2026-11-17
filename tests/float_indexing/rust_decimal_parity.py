"""R0 Rust/C ABI decimal parity against prior exact integer-rational oracle.

Core reference is project-authored and correlated; it is not an
independent third-party witness. Preserve raw observations per ABI.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from decimal_exact_oracle import cases, bits, INF

INVALID = [
    "nan", "NaN", "inf", "Infinity", "-inf", "1.0junk", "1,25",
    "1.", ".5", "1", "1e3", "1.0e+", " 1.0", "1.0 ", "0x1.0p0",
]

def execute(argv, env, input_text=None):
    try:
        p = subprocess.run([str(x) for x in argv], env=env,
                           input=input_text, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, timeout=90)
        return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired:
        return {"exit": None, "stdout": "", "stderr": "TIMEOUT"}

def host_fields(output):
    fields = {}
    for line in output.splitlines():
        if "=" not in line:
            raise ValueError("non key=value C host output " + line[:120])
        key, val = line.split("=", 1)
        if key in fields:
            raise ValueError("duplicate host key " + key)
        fields[key] = val
    for name in ("STATUS", "RUST", "C", "SCANNED", "LC", "POINT"):
        if name not in fields:
            raise ValueError("host missing key " + name)
    return fields

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rust-binary", type=Path, required=True)
    p.add_argument("--rust-library", type=Path, required=True)
    p.add_argument("--c-host", type=Path, required=True)
    p.add_argument("--abi", choices=["elf32", "elf64"], required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    rust = args.rust_binary.resolve()
    library = args.rust_library.resolve()
    host = args.c_host.resolve()
    for path in (rust, library, host):
        if not path.is_file():
            raise RuntimeError("missing executable/library " + str(path))

    numeric = cases()
    assert len(numeric) == 44
    assert sum((n & INF) == INF for _, _, n in numeric) == 5
    rows = [(name, token, None if (n & INF) == INF else n) for name, token, n in numeric]
    rows += [("invalid_" + str(i), token, None) for i, token in enumerate(INVALID)]
    tokens = [token for _, token, _ in rows]
    if any("\n" in value or "\r" in value for value in tokens):
        raise RuntimeError("CLI line protocol cannot encode newline token")
    report = {
        "claim": "Independent Rust f64 token parser preserves bounded GNU Prolog finite binary64 results, unlike libc ambient-locale conversions",
        "abi": args.abi, "source": "existing exact-rational 44-case oracle, plus adversarial ASCII syntax controls",
        "case_count": len(rows), "existing_oracle_count": 44, "expected_infinite": 5,
        "results": [], "locale_results": {}, "errors": [],
        "ffi_witnesses": [], "passed": False,
        "toolchain": "Rust 1.85.1 pinned, cargo dependency-free crate",
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    def failure(message):
        report["errors"].append(message)

    for locale in ("C", "de_DE.UTF-8"):
        env = dict(os.environ, LC_ALL=locale, LC_NUMERIC=locale, LANG=locale)
        cli = execute([rust], env, "\n".join(tokens) + "\n")
        report["locale_results"][locale] = {
            "exit": cli["exit"], "output_sha256": hashlib.sha256(cli["stdout"].encode()).hexdigest(),
            "stderr": cli["stderr"][-500:],
        }
        observed = cli["stdout"].splitlines()
        if cli["exit"] != 0 or len(observed) != len(rows):
            failure(f"Rust CLI {locale}: exit={cli['exit']} rowcount={len(observed)}")
        for i, (name, token, want) in enumerate(rows):
            if i >= len(observed):
                continue
            expected_line = "REJECT" if want is None else f"OK {want:016x}"
            actual_line = observed[i]
            if actual_line != expected_line:
                failure(f"Rust CLI {locale}/{name} expected={expected_line} observed={actual_line}")
            if locale == "C":
                report["results"].append({
                    "name": name, "token": token,
                    "expected": expected_line, "observed": actual_line,
                })

        for name, token, want in rows:
            result = execute([host, library, locale, token], env)
            if result["exit"] != 0:
                failure(f"C host {locale}/{name}: exit={result['exit']} {result['stderr'][:180]}")
                continue
            try:
                fields = host_fields(result["stdout"])
            except ValueError as error:
                failure(f"C host {locale}/{name}: {error}")
                continue
            if fields["POINT"] != ("." if locale == "C" else ","):
                failure(f"C locale state {locale}/{name}: decimal separator {fields['POINT']!r}")
            expected_status = 0 if want is None else 1
            try:
                status = int(fields["STATUS"])
                observed_bits = int(fields["RUST"], 16)
                old_bits = int(fields["C"], 16)
            except ValueError:
                failure(f"C host {locale}/{name} malformed bit output")
                continue
            if status != expected_status:
                failure(f"FFI {locale}/{name}: status {status}, expected {expected_status}")
            if want is not None and observed_bits != want:
                failure(f"FFI {locale}/{name}: {observed_bits:016x}, expected {want:016x}")
            if locale == "C" and name == "half" and old_bits != bits(token):
                failure(f"C locale sscanf control is wrong at {name}")
            if locale == "de_DE.UTF-8" and name == "half" and old_bits == bits(token):
                failure("German sscanf locale negative control did not differ")
            if name in {"half", "tenth", "negative_zero", "max_exact",
                        "overflow_huge", "invalid_0", "invalid_6"}:
                report["ffi_witnesses"].append({
                    "case": name, "locale": locale, "status": status,
                    "rust_bits": fields["RUST"], "c_scan_bits": fields["C"],
                    "decimal_point": fields["POINT"], "actual_locale": fields["LC"],
                })
        save()
        print(f"LOCALE={locale} CLI={len(observed)} expected={len(rows)} "
              f"failures={len(report['errors'])}", flush=True)

    report["passed"] = not report["errors"]
    save()
    for err in report["errors"][:35]:
        print("FAIL", err, flush=True)
    print(f"R0 ABI={args.abi} PASSED={report['passed']} "
          f"cases={len(rows)} ffi_calls={len(rows) * 2} errors={len(report['errors'])}")
    print("RAW JSON:", output)
    if not report["passed"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
