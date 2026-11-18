# Generation 15 — Rust-native predicate-dispatch crossover
Frozen on 18 November 2026, before crossover measurements.

## Object
Compare *immutable* Rust Generation 13 (dd6375e3fff21026b603c7944dd617ed9b391163) with *immutable* Rust Generation 14 (10bd90602502e55f04d0eaafbe71b47de496b3e3). Both compile with Rust 1.85.1, same target architecture, same external bench_solve.rs, and no C runtime bridge. The code on master is not modified in this experiment.

Question: under which program-size, matching-clause-count and repeated-call regimes does demand-cached functor/arity dispatch beat the unindexed scanner?

## Frozen discrete grid
- Total clauses N = {1, 64, 1024, 10000}.
- Matching facts T = {1, 16}; T=16 is invalid for N=1 and omitted.
- Repeated identical ground target(a) goals R = {1, 8, 64}.
- Interleave T identical target(a). facts deterministically among N-T distractors, each with a distinct noiseXXXXX(a). functor. All goals succeed; max_solutions=1; max_steps=200000.
- Total: 21 grid cells per ABI (ELF64 and actual i686 ELF32).

Additional controls: builtin-only program with 10,000 distractors plus 64 true goals; representation layout control with 16 target facts grouped first at N=10000,R=64; repeated identical noise(a) facts rather than distinct noiseXXXXX(a) for N=10000,T=1,R=64; unknown-predicate stderr/exit equivalence as an untimed black-box negative control. Distinguish source-order representation attacks from a claim about all Prolog programs.

## Measurement
The shared external Rust bench_solve.rs parses source and query before the timed series. Time only solve(), not parse or process launch. Five AB/BA alternated paired blocks, three untimed warmups per launch, four raw timed solves per block and variant: twenty nanosecond observations each. Retain per-block medians, all raw observations, full Debug answer representations, peak process RSS from GNU time (which includes parsing), input SHA256, program byte count and error logs. No cherry picking or cross-ABI mean.

Strongly supported local benefit: candidate median at least 10% below baseline and faster in >=4 of 5 paired blocks *for the same case on each ABI*. This is a heuristic decision gate, not a p-value, nor a continuous threshold theorem.

## Predictions and preregistered decisions
Prediction: N=10000,T=1,R=64 is substantially faster in Gen14; N=1 or R=1 may regress. T=16 may incur costs from deferred alternative clause frames; same-functor noise may change cost despite semantic similarity.

Correctness kill: any unexplained full-answer mismatch, exit/stderr difference, unknown-predicate behavior, source order, generated-variable, budget, rollback, or cut change. Performance interpretation kill: N=10000,T=1,R=64 fails the >=10%/4-of-5 gate on either ABI. Stop: do not modify the live solver to rescue an unsuccessful crossover. An honest negative crossover report may be merged as a measurement, not as an engine optimization. Promote only discrete measured regimes for this fixed test harness.

## Audit map and limitations
Requirement -> fixed source generator -> parsed ground query -> separately compiled pinned Rust libraries -> same direct solve harness -> raw samples -> per-ABI effect region -> bounded claim.

The frozen implementation and the independent-from-timed-implementation harness are author-correlated; not an external independent witness. Runner scheduling, allocator, CPU cache state, compiler codegen, parse/launch costs, non-ground terms, multiple-solution enumeration and application workloads are unresolved remainder. Generation 14 synthetic sparse effect is M; new crossover predictions H; eager per-solve global index speedup R; adaptive dispatch S only until separately tested.
