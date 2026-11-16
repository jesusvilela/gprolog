"""Collision-and-wraparound differential audit for static float indexing.

Fixture construction targets the C runtime's FNV-like home bucket, but
the semantic oracle deliberately does NOT use hashing. It enumerates
the source clauses in order, testing numeric double equality.

All 17 distinct finite keys hash to the last slot of a capacity-18
table on BOTH Linux ILP32 (32-bit unsigned long) and LP64 (64-bit
unsigned long). An absent key has the same hash on both ABIs.
Seventeen insertions force probing across the array boundary; a miss
must reach the single empty slot without looping or returning a wrong key.

Scope: little-endian ELF Linux, finite exactly represented binary64 values.
No NaN, infinity, big-endian, Windows LLP64, or dynamic predicates.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import tempfile

KEY_COUNT = 17
CAPACITY = KEY_COUNT + 1
LAST_SLOT = CAPACITY - 1
SEEDS = (17, 271828, 314159)


def c_hash_for_abi(literal, bits):
    """Mirror only the C unsigned-long hash for collision CONSTRUCTION."""
    if bits not in (32, 64):
        raise ValueError("Linux ELF32/ELF64 only")
    key = float(literal)
    if key == 0.0:
        key = 0.0
    mask = (1 << bits) - 1
    h = 2166136261
    for byte in struct.pack("<d", key):
        h = ((h ^ byte) * 16777619) & mask
    return h


def choose_keys():
    """Choose integer+1/8 dyadics, precisely representable as binary64."""
    selected = []
    offbucket = None
    for i in range(1, 100000):
        for sign in ("", "-"):
            literal = f"{sign}{i}.125"
            homes = tuple(c_hash_for_abi(literal, width) % CAPACITY
                          for width in (32, 64))
            if homes == (LAST_SLOT, LAST_SLOT):
                selected.append(literal)
                if len(selected) == KEY_COUNT + 1:
                    break
            elif offbucket is None and homes[0] != LAST_SLOT and homes[1] != LAST_SLOT:
                offbucket = literal
        if len(selected) == KEY_COUNT + 1:
            break
    if len(selected) != KEY_COUNT + 1 or offbucket is None:
        raise AssertionError("deterministic generator could not construct collisions")
    if len({float(x) for x in selected}) != KEY_COUNT + 1:
        raise AssertionError("duplicate numeric collision key")
    return selected[:KEY_COUNT], selected[-1], offbucket


def target_elf_abi(path):
    """Read the actual built executable header, not the Python host bits."""
    with path.open("rb") as f:
        ident = f.read(6)
    if len(ident) < 6 or ident[:4] != b"\x7fELF":
        raise RuntimeError(f"{path}: not an ELF executable")
    if ident[5] != 1:
        raise RuntimeError(f"{path}: endianness not tested")
    if ident[4] not in (1, 2):
        raise RuntimeError(f"{path}: unknown ELF class {ident[4]}")
    return {1: 32, 2: 64}[ident[4]]


def make_case(seed, keys, miss, offbucket):
    rng = random.Random(seed)
    facts = [(v, f"key_{i:03d}") for i, v in enumerate(keys)]
    rng.shuffle(facts)
    # Repeating an existing value must not increase the table's key count.
    duplicate = (keys[0], "duplicate_000")
    facts.insert(seed % (len(facts) + 1), duplicate)

    # Oracle order is determined by the source, not the switch hash table.
    queries = [(f"hit_{i:03d}", value, "float")
               for i, value in enumerate(keys)]
    queries.extend([
        ("same_bucket_miss", miss, "float"),
        ("other_bucket_miss", offbucket, "float"),
        ("integer_miss", "1", "integer"),
        ("atom_miss", "not_a_float", "atom"),
        ("hit_repeat", keys[0], "float"),
    ])
    rng.shuffle(queries)

    expected = []
    program = ["% 17 exact-dyadic float keys, one duplicate clause",
               f"% seed={seed}, target bucket={LAST_SLOT}/{CAPACITY}"]
    program.extend(f"collision({value}, {tag})." for value, tag in facts)
    program.extend([
        "report(Name, Key) :-",
        "    findall(Tag, collision(Key, Tag), Values),",
        "    format('ROW ~w ~w~n', [Name, Values]).",
        "report_all :-",
        "    findall(Tag, collision(_, Tag), Values),",
        "    format('ROW all ~w~n', [Values]).",
        "main :-",
    ])
    for name, value, kind in queries:
        wanted = ([tag for fact, tag in facts if float(fact) == float(value)]
                  if kind == "float" else [])
        expected.append("ROW " + name + " [" + ",".join(wanted) + "]")
        program.append(f"    report({name}, {value}),")
    expected.append("ROW all [" + ",".join(tag for _, tag in facts) + "]")
    program.extend(["    report_all,",
                    "    halt.",
                    ":- initialization(main)."])
    return "\n".join(program) + "\n", "\n".join(expected) + "\n", {
        "seed": seed,
        "facts": len(facts),
        "distinct_float_keys": len({float(v) for v, _ in facts}),
        "bound_queries": len(queries),
        "has_duplicate_key": True,
        "contains_missing_key_with_same_home_bucket": True,
    }


def execute(cmd, cwd, env, timeout=150):
    p = subprocess.run([str(x) for x in cmd], cwd=cwd, env=env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=timeout)
    return p.returncode, p.stdout


def assert_output(code, actual, expected, context):
    if code == 0 and actual == expected:
        return
    diff = "\n".join(list(difflib.unified_diff(
        expected.splitlines(), actual.splitlines(), "source-order oracle",
        context, lineterm=""))[:60])
    raise RuntimeError(f"{context}: exit={code}\n{diff}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-bin", type=Path, required=True)
    parser.add_argument("--candidate-bin", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("float-collision-evidence.json"))
    args = parser.parse_args()
    bins = {
        "baseline": args.baseline_bin.resolve(),
        "candidate": args.candidate_bin.resolve(),
    }
    bits = {}
    for version, directory in bins.items():
        for name in ("gprolog", "gplc", "pl2wam"):
            if not (directory / name).is_file():
                raise RuntimeError(f"{version}: missing {name}")
        bits[version] = target_elf_abi(directory / "gprolog")
        if bits[version] != target_elf_abi(directory / "gplc"):
            raise RuntimeError(f"{version}: gplc/gprolog have mismatched ELF class")
    if bits["baseline"] != bits["candidate"]:
        raise RuntimeError("baseline and candidate have different ABI classes")
    target_bits = bits["candidate"]
    keys, miss, other = choose_keys()
    for literal in keys + [miss]:
        for word_bits in (32, 64):
            if c_hash_for_abi(literal, word_bits) % CAPACITY != LAST_SLOT:
                raise RuntimeError("incomplete dual-ABI collision fixture")

    report = {
        "claim": "Colliding float keys never change answer identity, ordering, or miss behavior",
        "scope": "Linux little-endian ELF32/ELF64 with finite exact dyadic literals",
        "hash_bits": target_bits,
        "capacity": CAPACITY,
        "expected_home_bucket": LAST_SLOT,
        "distinct_colliding_keys": KEY_COUNT,
        "keys": keys,
        "absent_same_bucket_key": miss,
        "absent_different_bucket_key": other,
        "hash_buckets_32": [c_hash_for_abi(k, 32) % CAPACITY for k in keys + [miss]],
        "hash_buckets_64": [c_hash_for_abi(k, 64) % CAPACITY for k in keys + [miss]],
        "theoretical_last_insert_probe_depth": KEY_COUNT,
        "theoretical_same_bucket_miss_probe_depth": KEY_COUNT + 1,
        "evidence_limits": [
            "Python reconstructs the C hash and is not an independent hashing implementation",
            "The semantic oracle never uses the hash function",
            "Theoretical probe depth is not an instrumented C counter",
            "These tests are not independently audited and exclude nonfinite values",
        ],
        "cases": [],
        "passed": False,
    }
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    def persist():
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="gprolog-collision-oracle-") as root_name:
        root = Path(root_name)
        for seed in SEEDS:
            source, expected, metadata = make_case(seed, keys, miss, other)
            case = {
                **metadata,
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "oracle_sha256": hashlib.sha256(expected.encode()).hexdigest(),
                "versions": {},
            }
            report["cases"].append(case)
            persist()
            for version, directory in bins.items():
                work = root / str(seed) / version
                work.mkdir(parents=True)
                src = work / "collision.pl"
                src.write_text(source, encoding="utf-8")
                if hashlib.sha256(src.read_bytes()).hexdigest() != case["source_sha256"]:
                    raise RuntimeError("same-source parity violated")
                env = dict(os.environ,
                           PATH=str(directory) + os.pathsep + os.environ.get("PATH", ""))
                rc, output = execute([directory / "pl2wam", "--fast-math",
                                      "collision.pl"], work, env)
                if rc:
                    raise RuntimeError(f"{version}/{seed}: WAM generation: {output}")
                wam = (work / "collision.wam").read_text(encoding="utf-8")
                tables = re.findall(r"switch_on_float\(\[(.*?)\]\)", wam, re.DOTALL)
                has_new = "switch_on_term_flt(" in wam and bool(tables)
                if version == "baseline" and has_new:
                    raise RuntimeError("historical compiler emitted new switch")
                if version == "candidate":
                    if not has_new or len(tables) != 1:
                        raise RuntimeError("candidate float switch missing or split")
                    pairs = re.findall(r"\(([^(),]+),([^(),]+)\)", tables[0])
                    if len(pairs) != KEY_COUNT:
                        raise RuntimeError(f"unexpected float table size {len(pairs)}")
                    parsed_values = {float(k) for k, _ in pairs}
                    if parsed_values != {float(k) for k in keys}:
                        raise RuntimeError("WAM dispatch keys not equal to planned collision keys")
                rc, compile_output = execute([directory / "gplc", "--no-top-level",
                                              "-o", "collision_native", "collision.pl"],
                                             work, env, timeout=240)
                if rc:
                    raise RuntimeError(f"{version}/{seed}: native compile: {compile_output}")
                native_rc, native_output = execute([work / "collision_native"], work, env)
                consulted_rc, consulted_output = execute(
                    [directory / "gprolog", "--quiet", "--consult-file", "collision.pl"],
                    work, env)
                case["versions"][version] = {
                    "wam_sha256": hashlib.sha256(wam.encode()).hexdigest(),
                    "native_output_sha256": hashlib.sha256(native_output.encode()).hexdigest(),
                    "consulted_output_sha256": hashlib.sha256(consulted_output.encode()).hexdigest(),
                    "native_exit": native_rc, "consulted_exit": consulted_rc,
                    "new_float_switch": has_new,
                }
                persist()
                assert_output(native_rc, native_output, expected, f"{seed}/{version}/native")
                assert_output(consulted_rc, consulted_output, expected, f"{seed}/{version}/consulted")
            print(f"PASS collision seed={seed}: 17 keys + 1 duplicate, "
                  "same-home hit/miss/wrap/ordering, baseline+candidate native+consulted",
                  flush=True)
    report["passed"] = True
    persist()
    print(f"PASS dual-ABI collision construction: actual ELF{target_bits}; "
          f"{len(SEEDS) * 4} semantic execution paths", flush=True)
    print(f"RAW JSON: {out}", flush=True)


if __name__ == "__main__":
    main()
