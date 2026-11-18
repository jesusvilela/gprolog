# Generation 20 — continuation allocator request audit

**Date:** 18 November 2026 · **Decision:** diagnostic evidence is suitable to merge; do not change the Rust engine.

**Frozen sources:** released Generation 18 `901c8b58c12fbe8b79f70b0118f951f3ed2fcf21`; retired Generation 19 `c09fff05d9b3dd43fb90014278e3a98d701d3640`. The latter was closed in PR #18 without merge, after preregistered performance gates failed. All measurements use the identical external Rust `GlobalAlloc`/source-counter harness, compiled against each pinned library.

## Verdict

The preregistered **source-copy and heap-request contrast passed separately on native ELF64 and i686 ELF32**. With two source-signature candidate clauses, 128 successive calls and the *first clause failing*, released Gen18 clones zero pending-goal elements; rejected Gen19 clones **8,128**. The rejected policy requests **6.7673× more Rust allocations** on both ABIs and **12.5544× / 11.9648× more requested allocation bytes** on ELF64/i686. The expected contrast held in **5/5 paired blocks** on both architectures. Complete ordered output is unchanged in 264/264 historical and adversarial CLI cases per ABI. No solver code was changed for this experiment.

This supports a bounded **ownership-timing** explanation of the previously observed severe slowdown. It does **not** determine what fraction of wall time is caused by allocation requests, and it is not a benchmark of physical RAM consumption or an independent Prolog conformance proof.

## Claim and evidence ledger

| Claim | Before | Evidence | Audit result | After |
|---|---|---|---|---|
| A failed first head lets the Arc-backed branch recover a unique continuation without deep copying | H | Live feature-only `ChoicepointProfile` from the frozen released engine | 0 fallback copies and 0 pending-goal elements cloned for R128 | M, bounded |
| An eager T=2 owned branch clones 8,128 pending-goal elements under the same program/query | H | Retired Gen19 live copy counters, same harness | Exactly 8,128 across both ABIs | M, bounded |
| More Rust heap requests accompany that eager-copy failure regime | H | 20 paired raw allocator-request samples per version/cell/ABI | 4,228 → 28,612 successful allocations on both native ABIs | M, bounded |
| Allocation counts alone explain 8–11× prior runtime regressions | H | Correlation with an earlier, separate uninstrumented timing experiment | No causal time attribution, only consistency | H |
| Automatic owned continuations at exactly two clauses are a good general optimization | H | Generation 19 preregistered A/B failure | Strong failure-path regression and primary-gate miss | R |

## Complete matched-control view

The table deliberately keeps **request counts** and **requested layout bytes** separate. Positive ratios indicate larger requests in the rejected policy; the [13-case machine-readable summary](../tests/rust_allocation/results/generation20_allocation_summary.csv) includes both metrics for both ABIs, input hashes and paired-block decisions.

| Workload | ELF64 allocation requests: Gen18 → Gen19 | Ratio | i686 requested bytes: Gen18 → Gen19 | Ratio |
|---|---:|---:|---:|---:|
| `t2_first_success_r128` | 27,331 → 27,204 | 0.9954× | 510,896 → 508,356 | 0.995× |
| `t2_first_failure_r128` | 4,228 → 28,612 | 6.7673× | 43,504 → 520,516 | 11.9648× |
| `t2_first_failure_r32` | 1,060 → 2,548 | 2.4038× | 11,152 → 39,796 | 3.5685× |
| `t2_first_failure_deep_r64` | 41,540 → 104,036 | 2.5045× | 582,000 → 1,608,900 | 2.7644× |
| `t2_both_fail_r128` | 418 → 799 | 1.9115× | 8,170 → 15,643 | 1.9147× |
| `t2_enumerate_r8` | 657 → 646 | 0.9833× | 7,549 → 7,329 | 0.9709× |
| `t3_first_failure_r64` | 8,419 → 8,419 | 1.0× | 142,864 → 142,864 | 1.0× |
| `t1_r128` | 2,308 → 2,308 | 1.0× | 24,644 → 24,644 | 1.0× |
| `builtin_r128` | 258 → 258 | 1.0× | 4,656 → 4,656 | 1.0× |
| `t16_first_success_r64` | 10,211 → 10,211 | 1.0× | 162,576 → 162,576 | 1.0× |

## Strongest surviving finding and structural mechanism

When two identical `target(a).` facts are present and the first head succeeds, both solvers clone **8,128 pending-goal elements** over R=128 successful sequential goals. The rejected Gen19 then makes **127 fewer allocation requests** (27,204 instead of 27,331), yet in the earlier *uninstrumented* benchmark it was about 2% slower on that case. An allocator request count is therefore **not a sufficient performance metric**.

Changing only the first same-signature fact to `target(b).` while querying `target(a).` reverses the execution history. Gen18 holds an immutable `Arc<Vec<PendingGoal>>` across the first failed attempt, then can regain unique ownership at redo. Gen19 has already cloned the suffix eagerly when it queued that alternative. Both still create **128 clause choicepoints and execute 128 redos**, but the clone-element count becomes **0 vs 8,128**. The global allocation-probe counts are consistent with this live control-flow distinction.

For deep terms and R=64, rejected allocations rise from **41,540 to 104,036** and requested bytes from **1,130,700 to 3,132,084** (ELF64), or **582,000 to 1,608,900** (i686). The deeper AST makes eager cloning more costly in allocator requests, but the probe does not label individual allocations as exclusively continuation-owned.

## Specification → implementation → test

The frozen specification called for two immutable versions, an external process-wide `System` allocator wrapper active only during `solve()`, and the source-level feature-only profiler. Neither engine's executable source was modified. Parsing, query construction, warmups, answer formatting, and process launch are outside the allocation-measurement window. Each role/case/ABI had 5 AB/BA blocks, four tracked solves per block and three untracked warmups per process: **20 raw observations per version**.

All **13 allocation fixtures per ABI** passed their structural and answer-parity gates. All **264 CLI full stdout/stderr/exit comparisons per ABI** passed. Source SHA256 and feature-counter tuples were equal across ABIs for every case. Every allocation-request count was identical across the twenty repeated samples *within the same version and native ABI*, reflecting reproducible deterministic code paths in this environment—not independent replications or a statistical confidence interval.

## Direction, metric, resources and representation limits

The reported bytes are requested `Layout::size()` values for successful Rust `alloc` and `alloc_zeroed` operations during a solve. Reallocation requested-size counters and deallocations are separately preserved in raw JSON. These sums **are not actual copied bytes, memory bandwidth, allocator overhead, peak live bytes or RSS**. The counter includes all Rust heap allocations during the window, not only those issued by `Vec<PendingGoal>`.

Reordering two same-signature facts is a representation/control-flow attack. T=1, T=3, T=16 and builtin-only controls had **identical allocator-request counts and structural profiles** across the two variants. Full enumeration, first-success, both-head-failure, and deep-term controls were retained even where they weaken a simplistic “fewer Arc handles is always faster” narrative.

## Independent witness and correction history

No independent external author, allocator profiler, or full ISO/GNU Prolog semantic oracle is available. The implementation, protocol and tests share project authorship; this remains **correlated** evidence. The first CI attempt failed before taking allocator measurements because test and release compilation artifacts shared a Cargo target directory and an exactly-one-rlib selection check could not distinguish candidates. The [append-only correction](RUST_NATIVE_ALLOCATION_AUDIT_CORRECTIONS.md) records that failed run and the fix: separate build directories and report the library count. No source SHA, experiment grid or decision gate was changed.

**Primary passing run:** [44295028644](https://github.com/jesusvilela/gprolog/actions/runs/44295028644); ELF64 [artifact 14423123088](https://github.com/jesusvilela/gprolog/actions/runs/44295028644/artifacts/14423123088), i686 [artifact 14423825186](https://github.com/jesusvilela/gprolog/actions/runs/44295028644/artifacts/14423825186). Each artifact contains full 13-case allocation block records and all 264 CLI comparisons (GitHub Actions artifact retention: 30 days). The conversation's zipped evidence bundle preserves raw copies separately.

## Corrections, retirements and next bounded experiment

**M:** exact bounded source and allocation request counts; complete tested outputs; frozen source and native ABI provenance. **Conditional P/A:** `R(R−1)/2` cloned elements under the specified eager-copy algorithm, not a general Prolog complexity theorem. **H:** the portion of CPU time causally attributable to these requests, general application performance, external ISO Prolog equivalence. **R:** the Generation 19 fixed T=2 owned policy; treating allocation counts as a CPU-time oracle. **S:** future alternative continuation ownership policy requiring a *new* preregistered experiment.

A future controlled ablation would need an independent allocation/time profiler and structure-matched work, including first-head failure, deep terms and full enumeration. Kill it upon any unexplained semantic drift or >10% failure-path regression; stop before adding WAM, GC, heuristics or richer machinery to rescue an invalid effect. **No additional engine changes are warranted by the present results.**

**Round-trip:** requirement → immutable code variants → opt-in source counters and external allocator wrapper → paired raw counts and output parity → narrow interpretation → original requirement. The unresolved remainder is recorded, not silently transported into a stronger speedup claim.
