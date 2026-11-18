#!/usr/bin/env python3
"""Read-only Gen22 normalized DHAT and exclusive Callgrind attribution audit.

Usage: python3 analyze_callsite.py --artifact generation21-valgrind.zip
       [--validate-heldout] --output result.json
No network, source-engine edits, fabricated allocations, or hardware cycles.
"""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import zipfile

NAMES = (
    "first_failure_r128",
    "first_success_r128",
    "first_failure_deep_r64",
    "t3_first_success_r64",
    "t1_r128",
    "builtin_r128",
)
VERSIONS = ("gen18", "gen19")
MEMORY_FUNCTIONS = (
    "_int_malloc", "_int_free", "malloc_consolidate", "malloc",
    "free", "unlink_chunk.isra.0",
)
TERM = "<gprolog_native::syntax::Term as core::clone::Clone>::clone"
ENGINE = "gprolog_native::engine::solve"
DHAT_RE = re.compile(r"Total:\s*([\d,]+)\s+bytes\s+in\s+([\d,]+)\s+blocks")
FUNC_RE = re.compile(r"(c?fn)=\((\d+)\)(?:\s+(.*))?")
COST_RE = re.compile(r"([*+-]?\d+|\*)\s+(\d+)")
SUMMARY_RE = re.compile(r"^summary:\s*(\d+)\s*$", re.M)
EVENTS_RE = re.compile(r"^events:\s*(.+)$", re.M)


def sum_signed(left, right):
    return {k: right.get(k, 0) - left.get(k, 0)
            for k in sorted(set(left) | set(right))}


def callsite_symbol(frames, table):
    for idx in frames[1:]:
        if not isinstance(idx, int) or idx < 0 or idx >= len(table):
            raise ValueError("invalid DHAT frame table index")
        raw = table[idx]
        if "gprolog_native" in raw or "alloc::vec" in raw:
            return re.sub(r"^0x[0-9a-fA-F]+:\s+", "", raw).split(" (in ")[0]
    return "unknown"


def parse_dhat(json_bytes, log_bytes):
    data = json.loads(json_bytes)
    if data.get("dhatFileVersion") != 2 or data.get("mode") != "heap":
        raise ValueError("unsupported Valgrind DHAT heap schema")
    if not isinstance(data.get("pps"), list) or not isinstance(data.get("ftbl"), list):
        raise ValueError("missing DHAT allocation sites or frame table")
    matched = DHAT_RE.search(log_bytes.decode("utf-8", errors="replace"))
    if matched is None:
        raise ValueError("DHAT human log missing independent Total bytes/blocks")
    expected_bytes, expected_blocks = (
        int(matched.group(i).replace(",", "")) for i in (1, 2)
    )
    grouped = defaultdict(lambda: {"bytes": 0, "blocks": 0, "sites": 0})
    sum_bytes = sum_blocks = 0
    for site in data["pps"]:
        count = site.get("tbk")
        size = site.get("tb")
        if not isinstance(count, int) or not isinstance(size, int) or min(count, size) < 0:
            raise ValueError("invalid DHAT un-clipped site totals")
        stack = site.get("fs")
        if not isinstance(stack, list) or not stack:
            raise ValueError("missing DHAT stack frames")
        key = callsite_symbol(stack, data["ftbl"])
        grouped[key]["bytes"] += size
        grouped[key]["blocks"] += count
        grouped[key]["sites"] += 1
        sum_bytes += size
        sum_blocks += count
    if (sum_bytes, sum_blocks) != (expected_bytes, expected_blocks):
        raise ValueError(
            f"DHAT site-sum mismatch {sum_bytes}/{sum_blocks} "
            f"versus independent log {expected_bytes}/{expected_blocks}"
        )
    return {
        "whole_process_allocated_bytes": sum_bytes,
        "whole_process_heap_blocks": sum_blocks,
        "normalized_first_rust_frame": dict(sorted(grouped.items())),
        "unknown_allocated_bytes": grouped.get("unknown", {}).get("bytes", 0),
        "unknown_blocks": grouped.get("unknown", {}).get("blocks", 0),
    }


def parse_callgrind(raw_bytes):
    src = raw_bytes.decode("utf-8", errors="replace")
    summaries = SUMMARY_RE.findall(src)
    events = EVENTS_RE.findall(src)
    if len(summaries) != 1 or not events or events[-1].split() != ["Ir"]:
        raise ValueError("expected one Callgrind summary and exclusive Ir event")
    reported = int(summaries[0])
    name_by_id = {}
    self_by_id = defaultdict(int)
    current = None
    exclude_call_arc_cost = False
    for line in src.splitlines():
        m = FUNC_RE.match(line)
        if m is not None:
            is_callee, symbol_id, symbol = m.groups()
            key = int(symbol_id)
            if symbol is not None:
                old = name_by_id.get(key)
                if old is not None and old != symbol:
                    raise ValueError("conflicting Callgrind function ID symbol")
                name_by_id[key] = symbol
            if is_callee == "fn":
                current = key
                exclude_call_arc_cost = False
            continue
        if line.startswith("calls="):
            if current is None:
                raise ValueError("Callgrind calls before function header")
            exclude_call_arc_cost = True
            continue
        m = COST_RE.fullmatch(line)
        if m:
            if current is None:
                raise ValueError("Callgrind line cost before function header")
            if not exclude_call_arc_cost:
                self_by_id[current] += int(m.group(2))
            exclude_call_arc_cost = False
    by_function = defaultdict(int)
    for key, cost in self_by_id.items():
        by_function[name_by_id.get(key, f"unresolved-function-{key}")] += cost
    if sum(by_function.values()) != reported:
        raise ValueError(
            f"Callgrind exclusive function-sum {sum(by_function.values())} "
            f"does not match summary {reported}"
        )
    return {"whole_process_dynamic_instruction_Ir": reported,
            "exclusive_Ir_by_function": dict(sorted(by_function.items()))}


def read_artifact(archive, case, version, profiler):
    suffixes = {
        "dhat_json": f"{case}-{version}-solve-dhat.dhat.json",
        "dhat_log": f"{case}-{version}-solve-dhat.valgrind.log",
        "callgrind": f"{case}-{version}-solve-callgrind.callgrind.txt",
    }
    with zipfile.ZipFile(archive) as z:
        suffix = suffixes[profiler]
        matches = [name for name in z.namelist() if
                   name.endswith("/" + suffix) and not name.startswith("__MACOSX")]
        if len(matches) != 1:
            raise ValueError(f"missing or duplicate artifact member {suffix}: {len(matches)}")
        data = z.read(matches[0])
        return data, {"path": matches[0], "sha256": sha256(data).hexdigest(), "size": len(data)}


def ratio(new, old):
    if old <= 0:
        raise ValueError("invalid baseline denominator")
    return new / old


def inspect(archive, heldout=False):
    archive = Path(archive).resolve()
    report = {
        "artifact_name": archive.name,
        "artifact_sha256": sha256(archive.read_bytes()).hexdigest(),
        "heldout_after_exploratory_protocol": bool(heldout),
        "units": {
            "dhat": "whole-process heap bytes and blocks under Valgrind",
            "callgrind": "whole-process simulated exclusive dynamic instructions Ir",
        },
        "cases": {}, "errors": [], "failed_gates": [], "passed": False,
    }
    for case in NAMES:
        versions = {}
        for version in VERSIONS:
            dhat_json, dhat_origin = read_artifact(archive, case, version, "dhat_json")
            dhat_log, dhat_log_origin = read_artifact(archive, case, version, "dhat_log")
            call_data, call_origin = read_artifact(archive, case, version, "callgrind")
            versions[version] = {
                "dhat": parse_dhat(dhat_json, dhat_log),
                "callgrind": parse_callgrind(call_data),
                "source_file_sha256": {"dhat": dhat_origin, "dhat_log": dhat_log_origin,
                                       "callgrind": call_origin},
            }
        a, b = versions["gen18"], versions["gen19"]
        ad = a["dhat"]["normalized_first_rust_frame"]
        bd = b["dhat"]["normalized_first_rust_frame"]
        def site_map(d, field):
            return {key: v[field] for key, v in d.items()}
        db = sum_signed(site_map(ad, "bytes"), site_map(bd, "bytes"))
        dk = sum_signed(site_map(ad, "blocks"), site_map(bd, "blocks"))
        ir = sum_signed(a["callgrind"]["exclusive_Ir_by_function"],
                        b["callgrind"]["exclusive_Ir_by_function"])
        dbytes = b["dhat"]["whole_process_allocated_bytes"] - a["dhat"]["whole_process_allocated_bytes"]
        dblocks = b["dhat"]["whole_process_heap_blocks"] - a["dhat"]["whole_process_heap_blocks"]
        dircount = (b["callgrind"]["whole_process_dynamic_instruction_Ir"] -
                    a["callgrind"]["whole_process_dynamic_instruction_Ir"])
        if (sum(db.values()), sum(dk.values()), sum(ir.values())) != (dbytes, dblocks, dircount):
            raise ValueError("signed symbol accounting does not close")
        ratios = {
            "heap_bytes": ratio(b["dhat"]["whole_process_allocated_bytes"],
                                a["dhat"]["whole_process_allocated_bytes"]),
            "heap_blocks": ratio(b["dhat"]["whole_process_heap_blocks"],
                                 a["dhat"]["whole_process_heap_blocks"]),
            "dynamic_Ir": ratio(b["callgrind"]["whole_process_dynamic_instruction_Ir"],
                                a["callgrind"]["whole_process_dynamic_instruction_Ir"]),
        }
        report["cases"][case] = {
            "gen18": versions["gen18"], "gen19": versions["gen19"],
            "deltas": {"heap_bytes": dbytes, "heap_blocks": dblocks, "Ir": dircount},
            "gen19_over_gen18": ratios,
            "signed_site_delta_bytes": db,
            "signed_site_delta_blocks": dk,
            "signed_exclusive_function_delta_Ir": ir,
        }
    if heldout:
        primary = report["cases"]["first_failure_r128"]
        D = primary["deltas"]
        if min(D["heap_bytes"], D["heap_blocks"], D["Ir"]) <= 0:
            report["failed_gates"].append("positive primary deltas not present")
        else:
            grouped = primary["signed_site_delta_bytes"]
            block_groups = primary["signed_site_delta_blocks"]
            instr = primary["signed_exclusive_function_delta_Ir"]
            shares = {
                "two_symbol_dhat_bytes_share_of_net_delta": (
                    grouped.get(TERM, 0) + grouped.get(ENGINE, 0)) / D["heap_bytes"],
                "term_clone_dhat_blocks_share_of_net_delta": (
                    block_groups.get(TERM, 0) / D["heap_blocks"]),
                "six_heap_function_Ir_share_of_net_delta": (
                    sum(instr.get(name, 0) for name in MEMORY_FUNCTIONS) / D["Ir"]),
            }
            primary["predeclared_attribution_shares"] = shares
            if shares["two_symbol_dhat_bytes_share_of_net_delta"] < .95:
                report["failed_gates"].append("two symbolized DHAT site groups <95%")
            if shares["term_clone_dhat_blocks_share_of_net_delta"] < .9:
                report["failed_gates"].append("Term::clone DHAT block difference <90%")
            if shares["six_heap_function_Ir_share_of_net_delta"] < .65:
                report["failed_gates"].append("six libc heap symbols Ir difference <65%")
        for case in ("first_success_r128", "t3_first_success_r64", "t1_r128", "builtin_r128"):
            for metric, r in report["cases"][case]["gen19_over_gen18"].items():
                if not (.9 <= r <= 1.1):
                    report["failed_gates"].append(f"{case} {metric} outside [0.9, 1.1]: {r}")
    report["passed"] = len(report["cases"]) == len(NAMES) and not report["failed_gates"]
    return report


def self_test():
    sample = {
        "dhatFileVersion": 2, "mode": "heap",
        "pps": [{"tb": 17, "tbk": 2, "fs": [1, 2]},
                {"tb": 3, "tbk": 1, "fs": [1, 3]}],
        "ftbl": ["[root]", "malloc", "0xaa: gprolog_native::engine::solve (in /temp)",
                 "0xbb: unknown_runtime"],
    }
    d = parse_dhat(json.dumps(sample).encode(), b"Total: 20 bytes in 3 blocks")
    assert d["whole_process_allocated_bytes"] == 20
    assert d["normalized_first_rust_frame"][ENGINE]["bytes"] == 17
    assert d["unknown_allocated_bytes"] == 3
    tiny = b"events: Ir\nsummary: 11\nfn=(1) first\n2 5\ncfn=(2) other\ncalls=1 0\n2 9\nfn=(2) other\n0 6\n"
    c = parse_callgrind(tiny)
    assert c["whole_process_dynamic_instruction_Ir"] == 11
    assert c["exclusive_Ir_by_function"] == {"first": 5, "other": 6}
    for invalid in (b"Total: 18 bytes in 3 blocks", b"bad"):
        try:
            parse_dhat(json.dumps(sample).encode(), invalid)
            raise AssertionError("DHAT negative control unexpectedly passed")
        except ValueError:
            pass
    try:
        parse_callgrind(tiny.replace(b"summary: 11", b"summary: 20"))
        raise AssertionError("Callgrind negative control unexpectedly passed")
    except ValueError:
        pass
    print("GEN22 unit self-test PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-heldout", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.artifact is None or args.output is None:
        parser.error("need --artifact and --output")
    try:
        report = inspect(args.artifact, heldout=args.validate_heldout)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        report = {"passed": False, "errors": [str(exc)],
                  "artifact_name": args.artifact.name}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("GEN22", "HELDOUT" if args.validate_heldout else "EXPLORATORY",
          "PASS" if report.get("passed") else "FAIL",
          len(report.get("cases", {})), "cases",
          report.get("errors", []), report.get("failed_gates", []))
    if not report.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
