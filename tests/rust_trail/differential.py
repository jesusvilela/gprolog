#!/usr/bin/env python3
"""Compare the Rust-native trail rewrite against the last Rust snapshot engine.

No GNU Prolog C bridge, no new expected outputs constructed from the
candidate. Match complete stdout, stderr and exit code for frozen cases.
Benchmark is separate, synthetic and descriptive only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import tempfile
import time

BASELINE_COMMIT = "2f4c7b9346c7bcdfcd177907049f67cfe957f4d4"

def corpus():
    ancestor = ("parent(ada,noah). parent(noah,mei). "
                "ancestor(X,Y):-parent(X,Y). "
                "ancestor(X,Y):-parent(X,Z),ancestor(Z,Y).")
    member = "member(X,[X|_]). member(X,[_|T]):-member(X,T)."
    append = "append([],Ys,Ys). append([X|Xs],Ys,[X|Zs]):-append(Xs,Ys,Zs)."
    nested = ("inner(X):-!, (X=a;X=b). inner(c). "
              "outer(Z):-(Z=one;Z=two),inner(_).")
    p200 = "".join(f"p(k{i}).\n" for i in range(250))
    return [
      ("ancestor", ancestor, "ancestor(ada,Who).", 32, 100000),
      ("member", member, "member(V,[a,b,c]).", 32, 100000),
      ("append", append, "append([a,b],[c],Out).", 32, 100000),
      ("root_cut", "p(a). p(b).", "p(X),!.", 32, 100000),
      ("clause_cut", "p(X):-(X=a;X=b),!. p(c).", "p(X).", 32, 100000),
      ("post_cut_choice", "p(X):-!, (X=a;X=b). p(c).", "p(X).", 32, 100000),
      ("child_cut", nested, "outer(Z).", 32, 100000),
      ("cut_fail", "p:-!,fail. p.", "p.", 32, 100000),
      ("or_precedence", "", "X=a,fail;X=b.", 32, 100000),
      ("group_fail", "", "(X=a;X=b),fail.", 32, 100000),
      ("partial_failure", "", "(X=f(a),X=f(b);X=g(c)).", 32, 100000),
      ("disequality_redo", "", r"(X=a,X \= a;X=b).", 32, 100000),
      ("compound_probe", "p(f(a,b)). p(f(a,a)).", "p(f(X,X)).", 32, 100000),
      ("aliases", "", "X=Y,Y=Z,Z=a.", 32, 100000),
      ("occurs", "", "X=f(Y),Y=g(X).", 32, 100000),
      ("float_zero", "f(-0.0). f(0.0).", "f(X).", 32, 100000),
      ("known_failure", "p(a).", "p(b).", 32, 100000),
      ("unknown", "", "missing(ada).", 32, 100000),
      ("budget", "loop:-loop.", "loop.", 1, 10),
      ("many_facts", p200, "p(X).", 250, 100000),
      ("nested_choice", "p(a). p(b). q(one). q(two). r(X,Y):-p(X),q(Y).",
       "r(X,Y).", 32, 100000),
    ]

def generated_corpus():
    """Reproducible representation attacks with fully ground query answers."""
    rng = random.Random(17262026)
    templates = [
        "p(X).", "q(X).", "p(X),q(Y).", "r(X,Y).",
        "p(X),!,q(Y).", "r(X,Y),!.",
        "pc(X).", "p(X);q(X).",
        "p(X),(q(Y);Y=extra).",
        "p(X),q(Y),fail;X=alternative,Y=alternative.",
        "p(X),X \\= k999.",
    ]
    for i in range(128):
        ps = rng.sample(range(18), rng.randint(1, 5))
        qs = rng.sample(range(18), rng.randint(1, 4))
        source = "".join(f"p(k{j}).\n" for j in ps)
        source += "".join(f"q(m{j}).\n" for j in qs)
        source += "r(X,Y):-p(X),q(Y).\npc(X):-p(X),!.\n"
        yield (f"generated_{i:03d}", source, templates[rng.randrange(len(templates))],
               96, 100000)

def run(executable, source, query, max_solutions, max_steps, environment):
    cmd = [str(executable), str(source), query,
           "--max-solutions", str(max_solutions),
           "--max-steps", str(max_steps)]
    began = time.perf_counter_ns()
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=environment, timeout=30)
        return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr,
                "wall_ns": time.perf_counter_ns() - began}
    except subprocess.TimeoutExpired:
        return {"exit": None, "stdout": "", "stderr": "TIMEOUT",
                "wall_ns": time.perf_counter_ns() - began}

def timed(executable, source, query, max_solutions, max_steps, environment,
          dest):
    # GNU /usr/bin/time gives per-process peak RSS kB; not Python parent's.
    cmd = ["/usr/bin/time", "-f", "%e %M", "-o", str(dest),
           str(executable), str(source), query,
           "--max-solutions", str(max_solutions),
           "--max-steps", str(max_steps)]
    began = time.perf_counter_ns()
    p = subprocess.run(cmd, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, env=environment, timeout=40)
    wall_ns = time.perf_counter_ns() - began
    elapsed, rss = dest.read_text().strip().split()
    return {"wall_ns": wall_ns, "wall_s": wall_ns / 1_000_000_000,
            "gnu_time_wall_rounded_s": float(elapsed),
            "max_rss_kb": int(rss),
            "exit": p.returncode, "output_sha256":
            hashlib.sha256(p.stdout.encode()).hexdigest(),
            "stderr": p.stderr[:200]}

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--baseline", type=Path, required=True)
    cli.add_argument("--candidate", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    baseline, candidate = args.baseline.resolve(), args.candidate.resolve()
    if not baseline.is_file() or not candidate.is_file():
        raise SystemExit("Missing executable")
    output = args.output.resolve()
    env = dict(os.environ, LC_ALL="C", LANG="C")
    report = {"baseline_commit": BASELINE_COMMIT,
       "claim": "Behavioral equivalence for a fixed Rust-only subset; candidate trail vs snapshot baseline",
       "controls": "Same runner, identical source/query bytes, Rust toolchain 1.85.1, C locale; 64-bit only",
       "tests": [], "errors": [], "benchmark": {},
       "generated_seed": 17262026, "generated_cases": 128,
       "independent_witness": False, "passed": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rust-trail-compare-") as tmp:
        root = Path(tmp)
        for name, program, query, solutions, steps in list(corpus()) + list(generated_corpus()):
            source = root / (name + ".pl")
            source.write_text(program, encoding="utf-8")
            a = run(baseline, source, query, solutions, steps, env)
            b = run(candidate, source, query, solutions, steps, env)
            match = (a["exit"], a["stdout"], a["stderr"]) == (
                b["exit"], b["stdout"], b["stderr"])
            report["tests"].append({
                "case": name, "source_sha256":
                hashlib.sha256(program.encode()).hexdigest(),
                "query": query, "same_full_observables": match,
                "baseline": a, "candidate": b})
            if not match:
                report["errors"].append(name)
            print("PARITY", name, "PASS" if match else "FAIL", flush=True)
        # Enlarged predeclared synthetic choicepoint workload after first
        # round was below GNU time precision (all samples 0.00 seconds).
        # This compares TWO ALGORITHMS, not the trail contribution alone.
        source_text = "".join(f"p(k{i}).\n" for i in range(20_000))
        query, solutions, steps = "p(X).", 256, 1_000_000
        source = root / "synthetic_choice.pl"
        source.write_text(source_text, encoding="utf-8")
        times = {"baseline": [], "candidate": []}
        # Warm up each binary; alternate AB and BA orders across five pairs.
        for key, exe in (("baseline", baseline), ("candidate", candidate)):
            for i in range(2):
                timed(exe, source, query, solutions, steps, env,
                      root / f"warmup-{key}-{i}.txt")
        for i in range(5):
            order = [("baseline", baseline), ("candidate", candidate)]
            if i % 2: order.reverse()
            for key, exe in order:
                observation = timed(exe, source, query, solutions, steps,
                    env, root / f"measured-{key}-{i}.txt")
                times[key].append(observation)
        report["benchmark"] = {
            "scope": "Synthetic 20,000-fact source, first 256 answers; not all Prolog workloads",
            "timing_resolution": "Python per-process perf_counter_ns incl. spawn and /usr/bin/time wrapper; not kernel nanosecond accuracy",
            "samples": times,
            "baseline_median_wall_s": statistics.median(x["wall_s"] for x in times["baseline"]),
            "candidate_median_wall_s": statistics.median(x["wall_s"] for x in times["candidate"]),
            "baseline_median_max_rss_kb": statistics.median(x["max_rss_kb"] for x in times["baseline"]),
            "candidate_median_max_rss_kb": statistics.median(x["max_rss_kb"] for x in times["candidate"]),
            "caveat": "Engine changes both substitution storage and eager vs lazy clause candidate evaluation; any difference cannot be causally attributed to the trail alone."
        }
        for key, observations in times.items():
            if any(s["exit"] != 0 for s in observations):
                report["errors"].append("benchmark_nonzero_" + key)
        if times["baseline"][0]["output_sha256"] != times["candidate"][0]["output_sha256"]:
            report["errors"].append("benchmark_output_sha256")
    report["passed"] = not report["errors"]
    output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print("DIFFERENTIAL", "PASS" if report["passed"] else "FAIL",
          len(report["tests"]), "fixed+seeded programs", len(report["errors"]),
          "errors", flush=True)
    print("SYNTHETIC BASELINE", report["benchmark"]["baseline_median_wall_s"],
          "s", report["benchmark"]["baseline_median_max_rss_kb"], "KB")
    print("SYNTHETIC TRAIL", report["benchmark"]["candidate_median_wall_s"],
          "s", report["benchmark"]["candidate_median_max_rss_kb"], "KB")
    if report["errors"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
