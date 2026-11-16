"""Matched GNU Prolog float-indexing microbenchmark (stdlib only).

Generate identical Prolog sources for two installed, independently built
compiler versions. Check native results AND WAM dispatch before timing.
Raw paired times/RSS and compile times are retained; no speed claim is made
by this script beyond the specified synthetic workload and host.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import statistics
import subprocess
import tempfile
import time

CASES = ("float_uniform", "float_tail", "float_miss", "mixed_float",
         "atom_control", "variable_control")
SEED = 20261116


def fkey(i):
    return f"{i}.125"


def build_case(name, loops):
    if name in ("float_uniform", "float_tail", "float_miss"):
        facts = [(fkey(i), i) for i in range(128)]
        if name == "float_uniform":
            chosen = [((i * 37) + 11) % 128 for i in range(64)]
            queries = [(fkey(i), i) for i in chosen]
        elif name == "float_tail":
            queries = [(fkey(96 + (i % 32)), 96 + (i % 32)) for i in range(64)]
        else:
            queries = [(fkey(1000 + i), "missing") for i in range(64)]
    elif name == "mixed_float":
        facts = ([(fkey(i), i) for i in range(96)] +
                 [(str(i), 1000 + i) for i in range(16)] +
                 [(f"sym{i}", 2000 + i) for i in range(16)])
        queries = ([(fkey((i * 29 + 7) % 96), (i * 29 + 7) % 96)
                    for i in range(32)] +
                   [(str(i), 1000 + i) for i in range(16)] +
                   [(f"sym{i}", 2000 + i) for i in range(16)])
    elif name == "atom_control":
        facts = [(f"a{i}", i) for i in range(128)]
        queries = [(f"a{((i * 37) + 11) % 128}", ((i * 37) + 11) % 128)
                   for i in range(64)]
    else:
        facts = [(fkey(i), i) for i in range(64)]
        queries = []
        loops = max(100, loops // 8)

    count_each = len(facts) if name == "variable_control" else len(queries)
    expected = loops * count_each
    fact_lines = "\n".join(f"route({k}, {v})." for k, v in facts)
    if name == "variable_control":
        probe = StringProbe = (
            f"probe(_, {count_each}) :-\n"
            "    findall(K, route(K,_), Keys),\n"
            f"    length(Keys, {count_each}),\n"
            f"    Keys = [{fkey(0)}|_].\n"
        )
    else:
        probe = (
            "probe(Keys, Num) :- scan(Keys, 0, Num).\n"
            "scan([], N, N).\n"
            "scan([q(K, V)|Rest], N0, N) :-\n"
            "    ( V == missing ->\n"
            "        ( \\+ route(K, _) -> true ; halt(35) )\n"
            "    ;   ( route(K, V) -> true ; halt(36) )\n"
            "    ),\n"
            "    N1 is N0 + 1,\n"
            "    scan(Rest, N1, N).\n"
        )

    query_term = ",".join(f"q({key},{value})" for key, value in queries)
    src = (
        f"% Generated case={name}; deterministic seed={SEED}\n"
        f"{fact_lines}\n"
        f"queries([{query_term}]).\n"
        f"{probe}"
        "loop(0, _, Sum, Sum) :- !.\n"
        "loop(N, Q, Sum0, Sum) :-\n"
        "    N > 0,\n"
        "    probe(Q, Step),\n"
        "    Next is Sum0 + Step,\n"
        "    N1 is N - 1,\n"
        "    loop(N1, Q, Next, Sum).\n"
        "main :-\n"
        "    queries(Q),\n"
        f"    loop({loops}, Q, 0, Total),\n"
        f"    ( Total =:= {expected} ->\n"
        "        format('RESULT ~w~n', [Total]), halt\n"
        "    ;   halt(40) ).\n"
        ":- initialization(main).\n"
    )
    return src, expected, loops, len(facts), count_each


def launch(command, cwd, env, timeout):
    rss_path = cwd / "_benchmark_maxrss.txt"
    if rss_path.exists():
        rss_path.unlink()
    wrapper = Path("/usr/bin/time")
    cmd = ([str(wrapper), "-f", "%M", "-o", str(rss_path)]
           if wrapper.is_file() else []) + list(map(str, command))
    started = time.perf_counter_ns()
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=timeout)
    elapsed = (time.perf_counter_ns() - started) / 1e9
    rss = None
    if rss_path.exists():
        raw = rss_path.read_text().strip()
        if raw.isdigit():
            rss = int(raw)
    return {"seconds": elapsed, "max_rss_kb": rss,
            "exit": p.returncode, "output": p.stdout[-2000:]}


def assert_ok(result, label, token=None):
    if result["exit"] != 0:
        raise RuntimeError(f"{label}: exit={result['exit']}: {result['output']}")
    if token is not None and token not in result["output"]:
        raise RuntimeError(f"{label}: expected {token!r}: {result['output']}")


def median(xs):
    return statistics.median(xs)


def uncertainty(ratios):
    rng = random.Random(SEED)
    medians = sorted(median([rng.choice(ratios) for _ in ratios])
                     for _ in range(2000))
    return [medians[int(0.025 * (len(medians) - 1))],
            medians[int(0.975 * (len(medians) - 1))]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-bin", type=Path, required=True)
    ap.add_argument("--candidate-bin", type=Path, required=True)
    ap.add_argument("--baseline-ref", required=True)
    ap.add_argument("--candidate-ref", required=True)
    ap.add_argument("--samples", type=int, default=7)
    ap.add_argument("--warmups", type=int, default=1)
    ap.add_argument("--loops", type=int, default=12000)
    ap.add_argument("--output", type=Path, default=Path("float-index-benchmark.json"))
    args = ap.parse_args()
    if args.samples < 5 or args.warmups < 1 or args.loops < 1000:
        ap.error("require >=5 samples, >=1 warmup, >=1000 loops")
    bins = {"baseline": args.baseline_bin.resolve(),
            "candidate": args.candidate_bin.resolve()}
    for label, directory in bins.items():
        for tool in ("gplc", "pl2wam"):
            if not (directory / tool).is_file():
                raise RuntimeError(f"missing {label}/{tool} in {directory}")

    report = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_ref": args.baseline_ref,
        "candidate_ref": args.candidate_ref,
        "environment": {"platform": platform.platform(),
                        "machine": platform.machine(),
                        "cpu_count_visible": os.cpu_count(),
                        "python": platform.python_version(),
                        "time_rss_available": Path("/usr/bin/time").is_file()},
        "protocol": {"samples": args.samples, "warmups": args.warmups,
                     "loops_default": args.loops, "generator_seed": SEED,
                     "primary": "float_uniform",
                     "metric": "median of paired baseline/candidate wall-time ratios",
                     "uncertainty": "2000 seeded paired bootstrap median resamples",
                     "control": "atom_control",
                     "baseline_advantage_gate": "primary>=1.10 and bootstrap low>1.0",
                     "parity_gate": "atom_control median ratio in [0.85,1.15]",
                     "note": "Synthetic, single GitHub runner; bootstrap does not model host variation"},
        "cases": {}
    }

    with tempfile.TemporaryDirectory(prefix="gprolog-float-bench-") as tmp:
        root = Path(tmp)
        for name in CASES:
            src, expected, actual_loops, n_facts, calls = build_case(name, args.loops)
            h = hashlib.sha256(src.encode("utf-8")).hexdigest()
            dirs = {}
            envs = {}
            data = {"source_sha256": h, "facts": n_facts,
                    "queries_per_loop": calls, "loops": actual_loops,
                    "expected_total": expected, "versions": {}, "paired_runs": []}
            for version in ("baseline", "candidate"):
                d = root / version / name
                d.mkdir(parents=True)
                srcfile = d / "bench.pl"
                srcfile.write_text(src, encoding="utf-8")
                if hashlib.sha256(srcfile.read_bytes()).hexdigest() != h:
                    raise RuntimeError("source parity failure")
                dirs[version] = d
                envs[version] = dict(os.environ,
                                    PATH=str(bins[version]) + os.pathsep + os.environ.get("PATH", ""))
                generator = launch([bins[version] / "pl2wam", "--fast-math", "bench.pl"],
                                   d, envs[version], 120)
                assert_ok(generator, f"{name}/{version}/generator")
                wamfile = d / "bench.wam"
                if not wamfile.is_file():
                    raise RuntimeError(f"missing WAM for {version}/{name}")
                wam = wamfile.read_text(encoding="utf-8")
                has_float_term = "switch_on_term_flt(" in wam
                has_float_switch = "switch_on_float(" in wam
                if version == "baseline" and (has_float_term or has_float_switch):
                    raise RuntimeError("baseline unexpectedly has candidate float instructions")
                if version == "candidate":
                    if name == "atom_control" and (has_float_term or has_float_switch):
                        raise RuntimeError("float-free control incorrectly emitted float switch")
                    if name != "atom_control" and not (has_float_term and has_float_switch):
                        raise RuntimeError(f"{name}: candidate has not emitted float switch")
                data["versions"][version] = {
                    "wam": {"float_term": has_float_term,
                            "float_switch": has_float_switch,
                            "sha256": hashlib.sha256(wam.encode("utf-8")).hexdigest()},
                    "compiles": [], "runs": []}

            # Alternate compiler order to reduce fixed ordering bias.
            exes = {}
            for i in range(3):
                order = ("baseline", "candidate") if i % 2 == 0 else ("candidate", "baseline")
                for version in order:
                    d = dirs[version]
                    binary = d / f"bench_{i}"
                    record = launch([bins[version] / "gplc", "--no-top-level",
                                     "-o", binary.name, "bench.pl"], d, envs[version], 240)
                    assert_ok(record, f"{name}/{version}/compile[{i}]")
                    if not binary.is_file():
                        raise RuntimeError(f"missing compiled executable: {binary}")
                    record["executable_size_bytes"] = binary.stat().st_size
                    data["versions"][version]["compiles"].append(record)
                    if i == 0:
                        exes[version] = binary

            for version in ("baseline", "candidate"):
                for i in range(args.warmups):
                    warm = launch([exes[version]], dirs[version], envs[version], 180)
                    assert_ok(warm, f"{name}/{version}/warmup[{i}]", f"RESULT {expected}")

            for i in range(args.samples):
                order = ("baseline", "candidate") if i % 2 == 0 else ("candidate", "baseline")
                pair = {"index": i, "order": list(order)}
                for version in order:
                    sample = launch([exes[version]], dirs[version], envs[version], 180)
                    assert_ok(sample, f"{name}/{version}/run[{i}]", f"RESULT {expected}")
                    data["versions"][version]["runs"].append(sample)
                    pair[version] = {"seconds": sample["seconds"],
                                     "max_rss_kb": sample["max_rss_kb"]}
                pair["speedup_baseline_over_candidate"] = (pair["baseline"]["seconds"] /
                                                            pair["candidate"]["seconds"])
                data["paired_runs"].append(pair)

            ratios = [p["speedup_baseline_over_candidate"] for p in data["paired_runs"]]
            data["summary"] = {
                "baseline_median_seconds": median([p["baseline"]["seconds"] for p in data["paired_runs"]]),
                "candidate_median_seconds": median([p["candidate"]["seconds"] for p in data["paired_runs"]]),
                "paired_speedup_median": median(ratios),
                "paired_speedup_min": min(ratios),
                "paired_speedup_max": max(ratios),
                "paired_bootstrap_95pct": uncertainty(ratios),
                "baseline_compile_median_seconds": median([r["seconds"] for r in data["versions"]["baseline"]["compiles"]]),
                "candidate_compile_median_seconds": median([r["seconds"] for r in data["versions"]["candidate"]["compiles"]]),
                "candidate_over_baseline_compile_ratio":
                    median([r["seconds"] for r in data["versions"]["candidate"]["compiles"]]) /
                    median([r["seconds"] for r in data["versions"]["baseline"]["compiles"]]),
                "baseline_executable_size_bytes": data["versions"]["baseline"]["compiles"][0]["executable_size_bytes"],
                "candidate_executable_size_bytes": data["versions"]["candidate"]["compiles"][0]["executable_size_bytes"],
            }
            report["cases"][name] = data
            print(f"{name}: baseline={data['summary']['baseline_median_seconds']:.6f}s, "
                  f"candidate={data['summary']['candidate_median_seconds']:.6f}s, "
                  f"paired speedup={data['summary']['paired_speedup_median']:.3f}x, "
                  f"95% paired bootstrap={data['summary']['paired_bootstrap_95pct']}", flush=True)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                   encoding="utf-8")

    primary = report["cases"]["float_uniform"]["summary"]
    control = report["cases"]["atom_control"]["summary"]
    report["decision"] = {
        "primary_pass": (primary["paired_speedup_median"] >= 1.10 and
                         primary["paired_bootstrap_95pct"][0] > 1.0),
        "control_pass": 0.85 <= control["paired_speedup_median"] <= 1.15,
        "all_answers_equal": True,
        "claim_ceiling": "Bounded synthetic CI measurement, not general benchmark evidence"
    }
    report["decision"]["narrow_evidence_gate"] = (
        report["decision"]["primary_pass"] and report["decision"]["control_pass"])
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("DECISION: " + json.dumps(report["decision"], sort_keys=True), flush=True)
    print(f"RAW JSON: {args.output.resolve()}", flush=True)


if __name__ == "__main__":
    main()
