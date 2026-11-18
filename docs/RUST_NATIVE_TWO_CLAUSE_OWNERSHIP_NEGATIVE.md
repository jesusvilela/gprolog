# Generation 19 — two-clause owned-continuation experiment: negative result

**Date:** 18 November 2026. **Production baseline:** Generation 18 `901c8b58c12fbe8b79f70b0118f951f3ed2fcf21` (merged PR #17). **Tested candidate:** experimental head `c09fff05d9b3dd43fb90014278e3a98d701d3640`, draft PR #18; **not merged**.

## Verdict

**The T=2 owned-continuation policy is retired for performance, not for semantic correctness.** Both native Linux architectures passed 264/264 strict CLI stdout/stderr/exit comparisons against the frozen Generation 18 Rust engine, including the 241-case historical corpus and adversarial cut/failure/budget cases. However, the prescribed primary performance benefit did not appear on either ABI, and first-head-failure cases were several times slower. The experiment failed the predeclared kill conditions. The Generation 18 `Arc` path stays in production.

## Preregistered 13-case matched A/B matrix

Positive reduction means the experimental candidate ran faster; negative means slower. These are **median direct `solve()` nanoseconds**, not end-to-end application timings, and no ABI values are pooled. Paired-block faster counts appear in parentheses.

| Preregistered case | ELF64 baseline → owned (ns) | Reduction | i686 baseline → owned (ns) | Reduction |
|---|---:|---:|---:|---:|
| `builtin_r128` | 6,469.5 → 6,381.5 | +1.360% (5/5) | 9,689.5 → 9,734.5 | -0.464% (3/5) |
| `t16_r64_success` | 266,239.0 → 264,399.5 | +0.691% (4/5) | 387,050.5 → 394,802.0 | -2.003% (2/5) |
| `t1_r128_success` | 41,630.0 → 41,762.5 | -0.318% (1/5) | 77,777.5 → 77,657.5 | +0.154% (3/5) |
| `t2_r128_deep_success` | 9,226,972.0 → 9,419,002.5 | -2.081% (2/5) | 11,720,077.0 → 11,772,340.5 | -0.446% (1/5) |
| `t2_r128_first_failure` | 71,264.0 → 760,160.5 | -966.682% (0/5) | 132,511.0 → 1,109,754.0 | -737.481% (0/5) |
| `t2_r128_success` | 662,408.0 → 676,265.0 | -2.092% (0/5) | 979,691.5 → 993,227.5 | -1.382% (1/5) |
| `t2_r1_all2` | 729.5 → 718.0 | +1.576% (3/5) | 1,352.5 → 1,387.0 | -2.551% (2/5) |
| `t2_r32_deep_success` | 661,051.0 → 660,743.0 | +0.047% (1/5) | 896,135.0 → 897,126.5 | -0.111% (2/5) |
| `t2_r32_first_failure` | 19,243.0 → 62,993.5 | -227.358% (0/5) | 33,606.0 → 76,907.0 | -128.849% (0/5) |
| `t2_r32_success` | 56,988.0 → 59,434.0 | -4.292% (0/5) | 84,257.5 → 82,985.5 | +1.510% (4/5) |
| `t2_r64_first_failure_deep` | 689,693.5 → 2,875,964.5 | -316.992% (0/5) | 1,211,497.5 → 3,826,483.0 | -215.847% (0/5) |
| `t2_r8_all16` | 11,861.0 → 11,577.0 | +2.394% (3/5) | 22,859.5 → 22,810.0 | +0.217% (4/5) |
| `t3_r64_success` | 192,336.5 → 193,501.0 | -0.605% (3/5) | 285,377.0 → 286,298.5 | -0.323% (2/5) |

## Claim-to-evidence ledger

| Claim | Prior | Artifact | Result | After |
|---|---:|---|---|---:|
| T=2 owned continuation improves both ordinary first-success workloads | H | Preregistered 13-cell release A/B, 5 paired blocks per cell | Failed both primary gates | R |
| T=2 owned continuation retains tested Rust CLI semantics | H | 264 strict stdout/stderr/exit cases per ABI | All cases matched | M |
| Eager T=2 suffix copying is harmless when first head fails | H | Failure-first & deep-failure controls | 2.29–10.67× candidate runtime vs Gen18 across recorded cases | R |
| Actual copying can differ despite equal first-success cloned-element totals | H | Live source path and failure-path control | Mechanistic explanation is consistent; no isolated allocation profiler | H |
| Generational code passes complete ISO/GNU Prolog semantics | H | No independent external oracle | Unestablished | H |

## Strongest result and principal obstruction

On ELF64, the **T2/R128 ground first-head-failure** case rose from **71,264 ns to 760,160.5 ns** (10.67× runtime; candidate reduction -966.682%). On i686 it rose from **132,511 ns to 1,109,754 ns** (8.38× runtime; reduction -737.481%). The **T2/R64 deep first-head-failure** control increased from **689,693.5 to 2,875,964.5 ns** on ELF64 (4.17×), and from **1,211,497.5 to 3,826,483 ns** on i686 (3.16×).

The causal hypothesis is that a shared `Arc` can avoid copying a long continuation if the first candidate fails and the second becomes the sole owner, while the owned T=2 choicepoint must copy its full suffix before attempting the first candidate. These measured differences are consistent with that mechanism, but a separate allocation/CPU attribution study has **not** been performed. Do not infer precise allocated byte totals from logical copied-element counts.

## Specification, implementation and test audit

The original frozen protocol specified exactly one intervention: use owned continuations with **two** source-signature candidate clauses while retaining `Arc` for **three or more**. The actual Rust branch changed the threshold in the live `solve()` dispatch path; it did not alter `TryClause` step counting, freshening, cut barriers, reversal of `Work::Resume`, binding trail or clause indexing. The profile tests were updated to distinguish T2 owned from T3 shared paths; default and feature-enabled Rust suites passed in the observed first runs. The exact-output differential passed **264/264 on both ABIs**, including cutoff and rollback behavior.

The benchmark was intentionally allowed to **fail CI** on the predeclared performance kill gate, and the raw evidence was retained. That is a successful research falsification, **not** a passing optimization release. The later diagnostic probe step was not reached because the benchmark step failed; do not claim a separate machine-readable live profiler JSON from this run.

## Controls and resource parity

Both versions used Rust 1.85.1 release, the same external uninstrumented Rust harness, same target ABI, source program/query bytes and limits. Five alternating AB/BA blocks × four timed solves per variant (20 nanosecond samples) and three warmups per launch. Full Debug answer representation parity was checked. The first-failure, deep-term, two-answer/16-answer, T3, T16, T1 and builtin controls were all reported. Raw per-process peak RSS was recorded but includes parsing and startup; there is no isolated heap attribution.

No confidence interval or independent runner replication was established. The experiment and tests share project authorship. Although severe first-failure regressions are unlikely to be explained by noise alone, they remain observations under synthetic workloads, not universal Prolog runtime factors.

## Representation attack and correction/retirement

Switching from `target(a). target(a).` to `target(b). target(a).` leaves the requested ground first answer valid but reverses the cost trade-off; it exposes the fact that **source-head failure order**, not merely total clause count, is a load-bearing factor. A fixed clause-count threshold erases this dependence. The threshold-3 policy and its predicted primary speedup are **retired**. The original positive Generation 17/18 performance measurements are not invalidated.

No post-measurement threshold tweaking, term-size heuristic or WAM rewrite is authorized by this failed result.

## Next bounded experiment

**Object:** independently measure continuation copy, Arc allocation, branch failure frequency, and total runtime across controlled first-head-failure probability while keeping the **released Generation 18 algorithm fixed**. **Prediction:** Arc's avoided copies increase as early failure becomes common, especially for deep suffixes. **Metric:** a typed vector of allocations, cloned AST nodes, direct-solve nanos and full answer parity, not a single score. **Controls:** first success, first fail, late fail, T=2/3/16, flat/deep terms, exact Work step counts. **Kill:** if any logging or attribution changes semantic outputs or if the claimed mechanism does not predict independently measured copy counts. **Stop:** no production optimization until evidence supports a measurable improvement without failing adversarial controls. **Promotion:** only after independent architecture/profiling evidence and a new preregistered A/B, with unmodified release baseline.

## Evidence and provenance

- [Frozen preimplementation protocol](https://github.com/jesusvilela/gprolog/blob/experiment/rust-two-clause-ownership/docs/RUST_NATIVE_TWO_CLAUSE_OWNERSHIP_PROTOCOL.md)
- [Candidate PR #18 — rejected code](https://github.com/jesusvilela/gprolog/pull/18)
- [Two-ABI GitHub Actions run 44290905287](https://github.com/jesusvilela/gprolog/actions/runs/44290905287)
- [Raw ELF64 artifact 14420133764](https://github.com/jesusvilela/gprolog/actions/runs/44290905287/artifacts/14420133764) and [raw i686 artifact 14421666092](https://github.com/jesusvilela/gprolog/actions/runs/44290905287/artifacts/14421666092), subject to 30-day artifact retention
- Complete raw paired JSON and strict CLI outputs are preserved in the conversation evidence ZIP and compact CSV; summary and audit should be committed as **documentation-only**, not the rejected engine change.

**Evidence governance:** bounded performance = **M**; failed improvement claim = **R**; mechanism without independent allocation attribution = **H**; future adaptive design = **S**; external ISO/GNU Prolog conformance = **H**.