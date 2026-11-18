# Generation 15 - predicate-dispatch crossover

## Verdict
Immutable Rust Generation 14 demand caching beats Generation 13 in 7/21 prespecified grid cells on BOTH native Linux ABIs under the declared >=10% median reduction and >=4/5 paired-block wins rule. It does not justify a universal performance claim; single calls and tiny programs often regress. The main N=10000,T=1,R=64 prediction survived: 93.32% less direct solve() time on ELF64 and 92.76% less on i686 ELF32.

## Raw provenance
- [Frozen protocol](https://github.com/jesusvilela/gprolog/blob/experiment/rust-dispatch-crossover/docs/RUST_NATIVE_DISPATCH_CROSSOVER_PROTOCOL.md)
- [Actions run 44264680827](https://github.com/jesusvilela/gprolog/actions/runs/44264680827)
- [ELF64 raw artifact 14409796572](https://github.com/jesusvilela/gprolog/actions/runs/44264680827/artifacts/14409796572)
- [i686 ELF32 raw artifact 14409263716](https://github.com/jesusvilela/gprolog/actions/runs/44264680827/artifacts/14409263716)
- Baseline dd6375e3fff21026b603c7944dd617ed9b391163; candidate 10bd90602502e55f04d0eaafbe71b47de496b3e3; toolchain Rust 1.85.1, one shared external harness, 20 solve-only nanosecond samples per version per case per ABI, five AB/BA paired blocks, three warmups per launch.

## Full measured grid
Percentages here are candidate time change relative to baseline. Negative = caching faster; positive = caching slower. Gate=Y requires >=10% lower median and >=4/5 block wins on both ABIs.

| N | T | R | ELF64 change | i686 change | Gate |
|---:|---:|---:|---:|---:|:---:|
| 1 | 1 | 1 | +22.95% | +19.44% | - |
| 1 | 1 | 8 | +7.21% | +9.14% | - |
| 1 | 1 | 64 | +4.87% | +10.60% | - |
| 64 | 1 | 1 | +18.63% | +20.48% | - |
| 64 | 1 | 8 | -9.54% | +1.34% | - |
| 64 | 1 | 64 | -10.80% | +0.45% | - |
| 64 | 16 | 1 | +14.49% | +4.12% | - |
| 64 | 16 | 8 | -7.97% | -1.90% | - |
| 64 | 16 | 64 | -2.27% | -0.81% | - |
| 1,024 | 1 | 1 | +6.42% | +8.73% | - |
| 1,024 | 1 | 8 | -60.57% | -54.92% | Y |
| 1,024 | 1 | 64 | -64.39% | -60.60% | Y |
| 1,024 | 16 | 1 | +6.96% | -4.61% | - |
| 1,024 | 16 | 8 | -17.14% | -14.96% | Y |
| 1,024 | 16 | 64 | -3.75% | -2.62% | - |
| 10,000 | 1 | 1 | +2.55% | +1.17% | - |
| 10,000 | 1 | 8 | -83.69% | -82.69% | Y |
| 10,000 | 1 | 64 | -93.32% | -92.76% | Y |
| 10,000 | 16 | 1 | +1.61% | -0.20% | - |
| 10,000 | 16 | 8 | -46.94% | -52.25% | Y |
| 10,000 | 16 | 64 | -18.02% | -17.59% | Y |

## Representation and negative controls

| Control | ELF64 | i686 | Meaning |
|---|---:|---:|---|
| builtin_only_10000 | +2.88% | +0.60% | builtin-only |
| shared_functor_10000_t1_r64 | -93.36% | -92.83% | same-functor distractors |
| grouped_10000_t16_r64 | -17.36% | -17.66% | reordered target heads |

Black-box missing predicate: both binaries returned status 2 with identical stderr: unknown predicate missing/1. All 24 timed cases per ABI had equal full answer representations in every block.

## Claim and evidence ledger
| Claim | Evidence | Disposition |
|---|---|---|
| Cached dispatch beats linear scanning for sparse repeated lookups | N=10000,T=1,R=64 on two architectures, raw samples and 5/5 winning blocks | M for that fixed regime |
| Robust local improvement extends to all program sizes | N=1 and N=64 cells include regressions or fail two-ABI gate | R |
| Improving dispatch automatically improves complex nondeterministic search | T=16,R=64 greatly reduces fractional benefit, elapsed time still milliseconds | H / not established |
| Language semantics are equivalent in general | Answer parity on grid, unknown negative control and previous differential | H outside tested subset |

## Structural audit / limitation
The candidate still tries all heads for each matching functor/arity, preserving choice-point and trail semantics; the cache only removes repeated global scans after the first lookup for each signature. The T=16,R=64 case spends milliseconds executing additional choice-point and continuation bookkeeping. The benchmark alone cannot isolate the exact breakdown, so claims about O(R^2) continuation copying or WAM heap improvements remain hypotheses.

Source program layout and distractor-functor equivalence attacks agree in sign and scale with the corresponding sparse-grid results, but are not general theorems about Prolog representation independence. The built-in-only negative control is slightly slower. Peak RSS is recorded separately, and process RSS includes parsing.

## Bias, uncertainty and next gate
Five paired blocks mitigate ordering noise but are not statistically independent performance replications. Small observed effects are susceptible to timer overhead, codegen, CPU frequency, allocator and runner effects. Authors and reference implementation share code lineage. No independent external witness exists. A 10% / 4-of-5 gate is a predeclared decision heuristic, not a statistical confidence interval.

Next bounded test: profile the execution costs of 16 matching clauses and 64 repeated goals separately (clause discovery, choicepoint allocation, continuation cloning, unification, and trail rollback). Predict alternatives/continuation overhead dominates. Controls: a 1-clause case, fixed N with increasing T, and identical ordered answers. Kill any proposed isolated cause contradicted by instrumentation; stop architectural lifts until the measured bottleneck is reproducible. Do not infer WAM readiness.

Evidence tags: M = bounded runtime measurements and CLI parity; H = cause of multi-alternative cost; S = future adaptive policy; R = universal speedup and eager-index performance claim; P = no universal theorem established.