# Generation 18 — reversed Rust-native goal stack

**Evidence date:** 18 November 2026. **Reference:** immutable Generation 17 `46b536889e1b461af9e6cddb7f50239eec5697f5`. **Candidate branch head:** `a38f58e0`; the GitHub pull-request merge ref `778a48a2` had the same complete Git tree (`80293c32`), verified separately.

## Verdict

The reversed internal goal Vec removes repeated suffix reconstruction in the tested Rust-native engine. Full stdout/stderr/exit parity passed on 241 fixed/seeded/extended programs per native ABI, with 12 live-profile controls per ABI. Both 128-goal primary workloads passed the preregistered >=10% lower median, 4-of-5 paired-block gate on ELF64 and i686. This is a bounded direct-`solve()` improvement, not a universal speedup or independently established ISO Prolog conformance.

## Claim and evidence ledger

| Claim | Before | Test or artifact | Result | After |
|---|---|---|---|---|
| Reverse storage preserves execution order | H | 241 complete CLI comparisons and 7 focused Rust tests per ABI | No tested differences | M |
| In-place pop eliminates Resume suffix reconstruction | H | 12 live-profile controls per ABI | Zero suffix materializations on this execution path | M |
| Faster 128-goal direct solve | H | 11 predeclared release A/B cases, 20 raw samples/variant/case/ABI | Both primaries passed | M |
| Universal optimization or complete ISO Prolog | H | No independent language oracle / real program sample | Unestablished | H |
| Copied-element counts measure bytes or CPU time | R | Logical counts, separately timed controls | Invalid inference | R |

## Complete preregistered matched A/B summary

Positive percentages are reductions in *candidate direct-solve time*, not in end-to-end CLI latency. Each cell retains its 20 raw observations per version and per ABI in the CI artifacts. No cross-architecture pooling.

| Case | ELF64 Gen17 → Gen18 (ns) | ELF64 reduction / blocks | i686 Gen17 → Gen18 (ns) | i686 reduction / blocks |
|---|---:|---:|---:|---:|
| `builtin_r128` | 9,333.5 → 6,574.5 | +29.560% / 5/5 | 12,978.5 → 9,342.5 | +28.016% / 5/5 |
| `builtin_r64` | 4,468.5 → 3,612.0 | +19.168% / 5/5 | 6,227.5 → 5,237.5 | +15.897% / 5/5 |
| `deep_t16_r64` | 3,423,339.5 → 3,335,201.0 | +2.575% / 5/5 | 4,219,524.0 → 4,132,457.0 | +2.063% / 5/5 |
| `single_clause_r128` | 59,225.5 → 41,673.5 | +29.636% / 5/5 | 101,182.0 → 77,688.0 | +23.220% / 5/5 |
| `single_clause_r64` | 29,037.0 → 21,850.5 | +24.749% / 5/5 | 47,492.5 → 39,143.0 | +17.581% / 4/5 |
| `t16_r1` | 2,936.0 → 2,869.5 | +2.265% / 2/5 | 2,846.0 → 2,935.0 | -3.127% / 2/5 |
| `t16_r64` | 286,874.0 → 268,005.5 | +6.577% / 5/5 | 404,481.0 → 391,753.5 | +3.147% / 5/5 |
| `t16_r64_all16` | 289,889.5 → 264,372.5 | +8.802% / 5/5 | 417,757.0 → 404,733.0 | +3.118% / 4/5 |
| `t16_r8_all16` | 21,861.0 → 21,488.0 | +1.706% / 5/5 | 32,408.0 → 32,869.5 | -1.424% / 3/5 |
| `t1_r1` | 489.0 → 445.5 | +8.896% / 5/5 | 861.0 → 888.5 | -3.194% / 1/5 |
| `t2_r128` | 730,244.5 → 664,982.5 | +8.937% / 5/5 | 1,019,445.0 → 954,283.5 | +6.392% / 5/5 |

## Strongest surviving result

For 128 `true` goals, median solve-only time decreased from 9,333.5 to 6,574.5 ns on ELF64 (**29.56%**), and from 12,978.5 to 9,342.5 ns on i686 (**28.02%**). For 128 sequential single-clause calls, the reductions were **29.64%** (ELF64) and **23.22%** (i686). All four primary comparisons won five of five paired blocks.

On the old first-success straight-line scheduler, `R(R-1)/2` goal elements were moved into newly rebuilt suffix vectors. For R=128 this equals 8,128 element materializations. Under the reversed `Vec::pop()` path, the directly instrumented `resume_suffix_goals_materialized` value was zero. This is an operational count, not a wall-time attribution or an allocation-byte measurement.

## Load-bearing obstruction and negative evidence

Speedup varies by problem structure. The deep-term T16/R64 control improved only **2.58%** on ELF64 and **2.06%** on i686; T16/R8 full enumeration regressed **1.42%** on i686. The trivial T1/R1 and empty-suffix T16/R1 controls regressed approximately **3%** on i686. No predeclared >15% regression gate was crossed. Removing suffix construction does not remove unification costs, Arc materialization, choicepoint traversal or parsing.

## Specification → implementation → test

Source-order goals are now stored in reverse in each `Work::Resume` Vec. `Vec::pop()` retrieves the first logical goal. Initial query goals are reversed once. Clause-body terms are appended in reverse *above* the caller suffix. Comma pushes B then A; disjunction clones the suffix and appends the respective branch term. The existing `Work::TryClause`, source clause order, `fresh_clause`, substitution trail, cut barrier, Arc-shared clause continuations and task-counted search-step limits remain intact.

Tests include nested-vs-flat conjunction, cut before/after new alternatives, failed-head rollback, deep terms, duplicates and exact step-budget boundaries. The 241 CLI cases comprise 165 previously frozen Rust cases plus 76 deterministic orientation attacks. They are project-authored, not an independently validated Prolog language specification.

## Metric type, control parity and uncertainty

The primary metric is nanoseconds in the uninstrumented Rust `solve()` function, lower being better. Both variants used Rust 1.85.1 release with the same external harness, source/query bytes, limits, host ABI and compiler flags. There are 5 alternating AB/BA blocks, 3 warmups per invocation, and 4 timed calls per block per variant (20 raw samples). Parsing and process creation are outside the primary timer. Peak process RSS includes parsing/startup and is not attributed to one allocator. Source SHA256 hashes, per-block order and samples are in the raw JSON. These five blocks do not constitute independent external replication or a formal interval estimate.

## Source ref correction and provenance

On a GitHub pull_request event, `actions/checkout` may resolve GitHub's synthetic merge ref rather than the PR branch tip. The raw benchmark records `778a48a2e6c0e9f1411338a2739c8490b7e49601`. GitHub REST confirmed its complete tree `80293c32a7b8b52de251633700f16f6f908851e1` is identical to the actual candidate branch-head tree at `a38f58e019269d9b478da3c6598784b0970b016d`. This is explicitly preserved; the earlier result is not relabeled as a different commit. The CI workflow now asserts this tree equality on pull requests.

## Corrections and retirements

The old repeated-suffix path is retired only as an implementation choice for the tested Rust subset. Neither the conditional combinatorial count nor the measured solve-only timing proves that the same effect holds for all Prolog queries. No semantic failure or engine-specific post-test repair was required in the first Generation 18 run. A GitHub source-tree equivalence check was added to clarify the PR merge-ref identity.

## Next bounded experiment

Object: determine whether the remaining `Arc` continuation-sharing policy should depend on clause count and term shape. Prediction: deferring sharing for T=2 may help tiny alternatives but could harm deep suffixes. Metric: separately tracked native ELF64/i686 direct-solve timing, full output parity, RSS, and actual Arc/copy counters across T∈{1,2,3,16} and short/deep continuations. Kill: any output, cut, trail or step-budget change, or >15% negative-control regression. Stop: do not introduce WAM, a new heap, or GC to rescue an unstable result. Promote only the measured bounded cases after preregistration and independent controls.

## Evidence tags

**M:** 241 strict CLI comparisons, 12 profiling controls and 11 matched A/B cases per ABI. **P conditional:** R(R-1)/2 old suffix materializations for the stated straight-line scheduler, not a theorem of Prolog semantics. **H:** broad/independent conformance and speedups outside the grid. **S:** adaptive sharing and persistent suffix experiments. **R:** inferring heap bytes, CPU time or universal speedup from the logical counter.

**Original exact-source-tree measurements:** [GitHub Actions run 44280316675](https://github.com/jesusvilela/gprolog/actions/runs/44280316675), [ELF64 artifact 14416143829](https://github.com/jesusvilela/gprolog/actions/runs/44280316675/artifacts/14416143829), [i686 artifact 14416167778](https://github.com/jesusvilela/gprolog/actions/runs/44280316675/artifacts/14416167778). GitHub Actions retains these raw artifacts for 30 days; tests, protocol, CSV and report remain in Git.
