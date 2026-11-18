# Generation 22 — Call-site attribution with a same-workload held-out replay

**Date:** 18 November 2026. **Verdict:** A read-only, symbol-grouped analysis of Valgrind DHAT and Callgrind traces identifies where the extra *process-wide* heap activity and dynamic instructions accumulate when retired Gen19 eagerly clones a continuation before a failed first head. A second run of the **same** workload reproduced the decomposition. The evidence remains conditional on instrumentation, compilation, and normalized symbols; it is **not** an independent experimental study, source-line proof or native CPU-cycle attribution.

## Claim and evidence ledger

| Claim | Prior status | Observable | Result | New status |
|---|---|---|---|---|
| Two symbolized Rust groups carry most of the net DHAT byte increase | H, generated from exploratory run | Signed allocation-site totals | Exactly 897,128 / 897,128 net extra bytes in `Term::clone` and `engine::solve` | M for same-workload replay |
| A `Term::clone` site group carries most of the extra allocation blocks | H | Signed DHAT block-site totals | Exactly 24,384 / 24,384 net extra blocks | M |
| Six specified libc heap-management functions carry much of extra Callgrind `Ir` | H | Signed per-function *exclusive* Ir | 8,579,808 / 11,619,544 = 73.839% | M |
| The six fixed control cases preserve execution/measurement domain | H | Exact DHAT sums, Callgrind exclusive totals; unchanged-path ratios | All six cases parsed; T2-success, T1/T3 and builtins within [0.9,1.1] | M |
| These groups explain 100% of *native CPU time* | H | Neither DHAT nor Callgrind measures native-cycle causal decomposition | **Not established** | H |
| Gen19's eager-owned T=2 policy improves generalized execution | R | Gen19 and Gen20/21 preregistered counterexamples | Remains rejected | R |

## Original discovery and same-workload verification

**Discovery artifact:** [Gen21 #44302879486, artifact 14427545662](https://github.com/jesusvilela/gprolog/actions/runs/44302879486/artifacts/14427545662), archive SHA256 `21efbf87d2afb2c6781decb2b018dc063d2f90edbe59c5a5690c600a3e2416d0`. The exploratory decomposition was computed *before* the Generation 22 prediction was written, so it is **not preregistered evidence**.

**Frozen held-out replay:** [Gen21 #44305428250, artifact 14427846479](https://github.com/jesusvilela/gprolog/actions/runs/44305428250/artifacts/14427846479), archive SHA256 `289b36d06c827428b5f1a865d5011f7ef8e18ef33736f86217fd9dd4f744a9fd`. The protocol and analyzer were committed before this separate archive's detailed allocation/callsite data were examined. It reuses the same engine binaries, source tests and compiler family, so this is a **replication of measurement within the same distribution**, not independent workload validation.

Both had the same signed primary DHAT deltas and Callgrind `Ir` delta:

| First failing head, T2/R128 | Gen18 | Retired Gen19 | Signed increase |
|---|---:|---:|---:|
| DHAT whole-process allocated bytes | 96,912 | 994,040 | +897,128 |
| DHAT whole-process heap blocks | 4,653 | 29,037 | +24,384 |
| Callgrind dynamic `Ir`, exploration | 1,904,680 | 13,524,224 | +11,619,544 |
| Callgrind dynamic `Ir`, held-out | 1,905,347 | 13,524,891 | +11,619,544 |

### Allocation site decomposition

Using the first identifiable project Rust frame (or `alloc::vec` fallback) per DHAT allocation stack, after stripping address and process-specific executable path:

| Normalized first Rust frame | Signed net extra DHAT bytes | Signed net extra blocks |
|---|---:|---:|
| `<gprolog_native::syntax::Term as core::clone::Clone>::clone` | +447,040 | +24,384 |
| `gprolog_native::engine::solve` | +450,088 | 0 |
| **All other groups (net)** | **0** | **0** |
| **Total** | **+897,128** | **+24,384** |

This is an exact **accounting identity under the declared symbol heuristic**, not proof of unique allocation origin. A group with no *net* block increase may still request much larger allocations, as happens with `engine::solve`. The full generated results preserve every positive and negative group; the compact source JSON records the two explanatory groups and zero other-group net remainder.

### Dynamic instruction decomposition

Callgrind exclusive function instruction counts were parsed without double-counting edges after `calls=`. The sum of all function-self costs equals Callgrind's `summary` in every inspected record. Six libc heap-management names selected *before the held-out analysis* contribute:

| Exact function name | Additional exclusive `Ir` |
|---|---:|
| `_int_malloc` | +3,344,075 |
| `_int_free` | +1,809,247 |
| `malloc_consolidate` | +1,207,331 |
| `malloc` | +1,082,461 |
| `free` | +755,904 |
| `unlink_chunk.isra.0` | +380,790 |
| **Six-function subtotal** | **+8,579,808** |

The subtotal represents **73.839%** of the signed **+11,619,544 `Ir` net increase**. These are simulator-counted instruction references in named functions, not directly elapsed CPU time, hardware retired instructions, memory bandwidth or a general allocator complexity theorem.

## Controls, negative evidence and representation attacks

The primary variation is the order of same-signature facts, which changes whether a failed first head can leave the immutable continuation uniquely owned. Source code and source-goal count otherwise match the frozen Generation 21 study. The first-success R128 control's DHAT byte/blocks ratios are **0.994928/0.995425** and its `Ir` ratio approximately 1.00175; T3, T1 and builtin controls have exactly equal DHAT totals and Callgrind `Ir` within 0.04% between variants. All held-out and exploratory controls satisfied the preregistered [0.9,1.1] windows.

The deep first-failure R64 trace also has the expected increase (DHAT 1,219,157→3,220,541 bytes, 43,703→106,199 blocks, and Callgrind 14.01m→45.25m `Ir` in the held-out run). It was **not** used to tune the primary symbol-share thresholds.

The previously merged Gen21 audit supplied **264/264 strict Rust CLI differential cases per ABI** and the direct-solve time ratios; this read-only Gen22 analysis does **not rerun or upgrade** those semantic tests.

## Specification → implementation → test and metric audit

The standalone, standard-library [`analyze_callsite.py`](../tests/rust_external_profile/analyze_callsite.py) reads the exact original DHAT v2 JSON, human DHAT total logs and Callgrind text traces. It refuses missing, duplicate or malformed inputs; independently reconciles `sum(pps[].tb/tbk)` to DHAT's log; reconciles all function-exclusive Callgrind costs to `summary`; records raw per-frame/per-function signed deltas; and checks fixed held-out thresholds without clipping. Synthetic self-tests include positive known answers and deliberately malformed-total negatives.

The source algorithm is frozen at released Gen18 `901c8b58c12fbe8b79f70b0118f951f3ed2fcf21` versus rejected Gen19 `c09fff05d9b3dd43fb90014278e3a98d701d3640`. Neither engine source is edited. The separate CI replay points to exact historical artifact IDs; the artifact expires under GitHub Actions retention, so the script can also be run offline against archived copies. Do not treat CI replay success as a new independent instrument if it merely reprocesses the same bytes.

## Load-bearing obstruction and independence

Source optimizations and symbol inlining may cause a conceptual allocation site to land under different *first Rust frame* labels. The `Term::clone` and `engine::solve` labels are therefore **attribution conventions** rather than uniquely proven source lines or a causal intervention. Glibc heap-management routines being hot are consistent with the earlier Rust GlobalAlloc results, but the study has not isolated malloc cost from AST traversal, deallocations, cache effects or branch behavior.

Valgrind is independent third-party **software**, not an independent investigator, oracle or new workload. A held-out CI run of the same binary and synthetic tests is not out-of-distribution validation. The structural pattern is reproduced in the declared narrow regime only.

## Correction/retirement and next bounded step

No out-of-threshold held-out corrections were needed. The exploratory decomposition was plainly labeled retrospective; the frozen held-out thresholds, case set and grouping rule were not retuned. Prior Gen19 two-clause owned optimization remains **R**; any interpretation of these `Ir` as native CPU cycles is **R**. The genuine next question is whether a new **independently selected, non-synthetic workload corpus** produces the same sign and cost-site concentration. That requires a new protocol; do not promote the present two-run match into a general theorem.

**Next experiment (not authorized by this merge):** corpus of externally specified Prolog programs with distinct clause order, head-failure rates, term depth and cut/backtracking, measured by the same source-independent profiles. Primary metric: held-out range of normalized *typed* site-share contributions with full parity. Kill on semantic mismatches, unstable symbolization or a control regression. Stop before new ownership heuristics, WAM, GC, compiler redesign or arbitrary hypercomplex lifts are added to rescue a failed effect.

## Final P/A/M/H/S/R map

**P (conditional):** `R(R-1)/2` extra copied suffix elements under the previously inspected eager-copy path, not a general Prolog proof. **A:** first-symbol grouping, compiler/Valgrind account domains. **M:** the raw typed DHAT/Callgrind site deltas and same-workload replay. **H:** causal native-cycle share, general real-program behavior, independent ISO Prolog conformance. **S:** speculative alternative representations outside current scope. **R:** Gen19 fixed T2-owned optimization and strong causal cycle interpretations from instruction counts.
