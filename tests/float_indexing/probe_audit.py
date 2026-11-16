"""Instrument ONLY a throwaway CI checkout of GNU Prolog's actual C float index.
Compare live insert/lookup probe counts against a separate source-order oracle.
No modifications to the production runtime are committed.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from collision_oracle import SEEDS, KEY_COUNT, CAPACITY, LAST_SLOT, choose_keys, make_case, target_elf_abi

LOGVAR = "GPROLOG_FLOAT_PROBE_LOG"
PATTERN = re.compile(r"^FLOAT_PROBE phase=(insert|lookup) size=(\d+) home=(\d+) probes=(\d+) found=(\d+) key=(\S+)$")


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"unexpected C source anchor count ({source.count(old)}): {old[:65]}")
    return source.replace(old, new)


def instrument(path):
    original = path.read_text(encoding="utf-8")
    source = replace_once(original,
        "static FltSwtInf *Locate_Flt_Swt_Element(FltSwtTbl t, int size, double key);",
        "static FltSwtInf *Locate_Flt_Swt_Element(FltSwtTbl t, int size, double key, const char *phase);")
    source = replace_once(source,
        "swt = Locate_Flt_Swt_Element(t, size, key);\n  swt->key = key;",
        'swt = Locate_Flt_Swt_Element(t, size, key, "insert");\n  swt->key = key;')
    source = replace_once(source,
        "swt = Locate_Flt_Swt_Element(t, size, key);\n  return swt->codep",
        'swt = Locate_Flt_Swt_Element(t, size, key, "lookup");\n  return swt->codep')
    source = replace_once(source,
        "Locate_Flt_Swt_Element(FltSwtTbl t, int size, double key)\n{",
        "Locate_Flt_Swt_Element(FltSwtTbl t, int size, double key, const char *phase)\n{")
    begin = source.index("static FltSwtInf *\nLocate_Flt_Swt_Element(")
    end = source.index("/*-------------------------------------------------------------------------*", begin + 85)
    before, fn, after = source[:begin], source[begin:end], source[end:]
    fn = replace_once(fn, "  FltSwtInf *swt, *end;\n  int i;",
        "  FltSwtInf *swt, *end;\n  int i;\n  unsigned long home;\n  unsigned int probes = 1;\n  const char *trace_path;\n  FILE *trace;")
    fn = replace_once(fn, "  swt = t + (hash % (unsigned long) (size + 1));",
        "  home = hash % (unsigned long) (size + 1);\n  swt = t + home;")
    fn = replace_once(fn, "    {\n      if (++swt == end)\n        swt = t;\n    }",
        "    {\n      ++probes;\n      if (++swt == end)\n        swt = t;\n    }")
    fn = replace_once(fn, "  return swt;",
        '  trace_path = getenv("' + LOGVAR + '");\n'
        "  if (trace_path && trace_path[0])\n"
        "    {\n"
        '      trace = fopen(trace_path, "a");\n'
        "      if (!trace)\n        abort();\n"
        '      fprintf(trace, "FLOAT_PROBE phase=%s size=%d home=%lu probes=%u found=%d key=%a\\n",\n'
        "              phase, size, home, probes, swt->codep != NULL, key);\n"
        "      fclose(trace);\n    }\n"
        "  return swt;")
    source = before + fn + after
    if source.count("FLOAT_PROBE phase=") != 1:
        raise ValueError("C source trace injection failed")
    path.write_text(source, encoding="utf-8")
    print("TEST-ONLY INSTRUMENTATION:", path, "original_sha256=",
          hashlib.sha256(original.encode()).hexdigest())


def execute(command, cwd, env, timeout=150):
    p = subprocess.run([str(x) for x in command], cwd=cwd, env=env,
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=timeout)
    return p.returncode, p.stdout


def parse_trace(path, values):
    if not path.is_file():
        raise RuntimeError(f"no C trace written: {path}")
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PATTERN.fullmatch(line)
        if not m:
            raise RuntimeError("malformed C trace line: " + line[:140])
        phase, size, home, probes, matched, encoded = m.groups()
        value = float.fromhex(encoded)
        if int(size) != KEY_COUNT or value not in values:
            continue
        found.append({"phase": phase, "size": int(size), "home": int(home),
                      "probes": int(probes), "found": bool(int(matched)),
                      "value": value, "hex": encoded})
    return found


def validate(records, keys, absent, offbucket, context):
    inserted = [r for r in records if r["phase"] == "insert"]
    queries = [r for r in records if r["phase"] == "lookup"]
    if len(inserted) != KEY_COUNT:
        raise RuntimeError(f"{context}: {len(inserted)} inserts, expected {KEY_COUNT}")
    if {r["value"] for r in inserted} != {float(k) for k in keys}:
        raise RuntimeError(f"{context}: inserted keys incorrect")
    if any(r["home"] != LAST_SLOT or r["found"] for r in inserted):
        raise RuntimeError(f"{context}: incorrect insertion bucket or existing code")
    if sorted(r["probes"] for r in inserted) != list(range(1, KEY_COUNT + 1)):
        raise RuntimeError(f"{context}: C insertion probes are not 1..17")
    expected_queries = Counter(float(k) for k in keys)
    expected_queries[float(keys[0])] += 1
    expected_queries[float(absent)] += 1
    expected_queries[float(offbucket)] += 1
    actual_queries = Counter(r["value"] for r in queries)
    if actual_queries != expected_queries:
        raise RuntimeError(f"{context}: wrong float lookup multiset {actual_queries}")
    hits = [r for r in queries if r["value"] in {float(k) for k in keys}]
    if any(not r["found"] or r["home"] != LAST_SLOT for r in hits):
        raise RuntimeError(f"{context}: incorrect hit semantics")
    if sorted(set(r["probes"] for r in hits)) != list(range(1, KEY_COUNT + 1)):
        raise RuntimeError(f"{context}: C hit probes are not 1..17")
    missing = [r for r in queries if r["value"] == float(absent)]
    other = [r for r in queries if r["value"] == float(offbucket)]
    if len(missing) != 1 or missing[0]["found"] or missing[0]["home"] != LAST_SLOT or missing[0]["probes"] != CAPACITY:
        raise RuntimeError(f"{context}: colliding miss should traverse exactly {CAPACITY} slots")
    if len(other) != 1 or other[0]["found"]:
        raise RuntimeError(f"{context}: unrelated missing key was found")
    return {"actual_c_records": records, "insert_events": len(inserted),
            "lookup_events": len(queries), "insert_probe_depths": list(range(1, KEY_COUNT + 1)),
            "max_hit_probes": max(r["probes"] for r in hits),
            "same_bucket_miss_probes": missing[0]["probes"],
            "other_bucket_miss_probes": other[0]["probes"]}


def verify(bindir, output):
    bindir = bindir.resolve()
    for binary in ("gplc", "gprolog", "pl2wam"):
        if not (bindir / binary).is_file():
            raise RuntimeError(f"missing {binary} in {bindir}")
    bits = target_elf_abi(bindir / "gprolog")
    if bits != target_elf_abi(bindir / "gplc"):
        raise RuntimeError("compiler and runtime ELF class mismatch")
    keys, absent, offbucket = choose_keys()
    values = set(float(x) for x in keys + [absent, offbucket])
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"experiment": "actual C float switch probes, not modelled hash counts",
              "abi": f"ELF{bits}", "seeds": list(SEEDS), "cases": [], "passed": False,
              "production_runtime_unchanged": True}
    def persist():
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="gprolog-probe-audit-") as tmp:
        for seed in SEEDS:
            source, expected, metadata = make_case(seed, keys, absent, offbucket)
            path = Path(tmp) / str(seed)
            path.mkdir()
            (path / "collision.pl").write_text(source, encoding="utf-8")
            env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ.get("PATH", ""))
            rc, message = execute([bindir / "gplc", "--no-top-level", "-o", "collision_native", "collision.pl"], path, env, 240)
            if rc:
                raise RuntimeError(f"native compile failed {seed}: {message[-1000:]}")
            case = {**metadata, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "expected_output_sha256": hashlib.sha256(expected.encode()).hexdigest(),
                    "modes": {}}
            report["cases"].append(case)
            persist()
            for mode, command in [
                ("native", [path / "collision_native"]),
                ("consulted", [bindir / "gprolog", "--quiet", "--consult-file", "collision.pl"]),
            ]:
                trace = path / (mode + ".log")
                penv = dict(env)
                penv[LOGVAR] = str(trace)
                rc, result = execute(command, path, penv)
                if rc or result != expected:
                    raise RuntimeError(f"{seed}/{mode} oracle mismatch: exit={rc}, output={result[:700]}")
                record = validate(parse_trace(trace, values), keys, absent, offbucket, f"{seed}/{mode}")
                case["modes"][mode] = {"answer_sha256": hashlib.sha256(result.encode()).hexdigest(),
                                        **record}
                persist()
                print(f"PASS {seed}/{mode} ELF{bits} C probes: insert=1..17, "
                      "same-bucket miss=18, source-order oracle exact", flush=True)
    report["passed"] = True
    persist()
    print(f"PASS {len(SEEDS)*2} actual C probe executions on ELF{bits}")
    print("RAW JSON:", output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="action", required=True)
    a = subs.add_parser("instrument")
    a.add_argument("--source", required=True, type=Path)
    b = subs.add_parser("verify")
    b.add_argument("--bin-dir", required=True, type=Path)
    b.add_argument("--output", required=True, type=Path)
    opts = p.parse_args()
    if opts.action == "instrument":
        instrument(opts.source)
    else:
        verify(opts.bin_dir, opts.output)


if __name__ == "__main__":
    main()
