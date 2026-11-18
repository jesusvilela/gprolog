# Generation 21 — Third-party heap and instruction audit

**2026-11-18. Verdict:** A matched uninstrumented native Rust experiment independently reproduced the **rejected Generation 19** failed-first-head regression on ELF64 and i686. Third-party **Valgrind 3.22.0 DHAT and Callgrind** on ELF64 corroborated an increased *process-wide* allocation/instruction burden in that regime. The released Gen18 interpreter is unchanged. No general Prolog compatibility, causal CPU-cycle attribution, or resurrection of Gen19's owned-T2 design is claimed.

## Claim and evidence ledger

| Claim | Before | Evidence | Narrow observed conclusion | After |
|---|---|---|---|---|
| Gen19's first-failed-T2 path regresses in native solve time | M (historical) | 20 native timed solves per role/cell/ABI, 5 AB/BA blocks | 9.98568× ELF64 / 8.94034× i686 slower; 5/5 block wins each | M |
| Failed-first-head copies create external heap traffic | H | DHAT 3.22.0, full-process SOLVE and matched PREPARE controls | 4,653→29,037 blocks; 96,912→994,040 allocated bytes | M for process metrics |
| Failed-first-head raises executed instruction count | H | Callgrind dynamic instruction references, ELF64 only | 1,904,680→13,524,224 Ir (7.1005×) | M for Valgrind Ir |
| Small/unchanged ownership paths should stay comparable | H | first-success, T1, T3 and builtin controls | All external ratios approximately 1.0 | M |
| Allocations account for exactly N% of native elapsed time | H | No independent controlled allocation-only intervention | Not established | H |
| Gen19 T2-owned scheduling ought to be merged | R | Performance kill condition remains violated | Remains retired | R |

## Strongest surviving result

For two same-signature clauses, `target(b).` followed by `target(a).`, 128 consecutive ground `target(a)` calls, and first-solution limit:
- **Native ELF64 solve:** Gen18 85,858 ns → Gen19 857,350.5 ns (**9.98568×**).
- **Native i686 solve:** Gen18 125,168 ns → Gen19 1,119,044.5 ns (**8.94034×**).
- **Valgrind DHAT ELF64:** Gen18 4,653 heap blocks / 96,912 bytes → Gen19 29,037 blocks / 994,040 bytes (**6.24049× / 10.25714×**).
- **Valgrind Callgrind ELF64:** 1,904,680 → 13,524,224 process-wide dynamic instruction references (**7.100523×**).
- Both native primaries won **5/5 paired blocks** and exceeded the preregistered 3× slowdown threshold. Both external measures exceeded their preregistered 3× heap and 2× instruction thresholds.

Generation 20's separate authored source-counter path had predicted 0 cloned PendingGoal elements on released Gen18 versus 8,128 on retired Gen19. The present independent profiler *software* corroborates the operational direction, not a formal causal accounting identity.

## Complete matched-control and resource-parity view

Ratios below are **retired Gen19 / released Gen18**. Native medians are solve-only elapsed time. DHAT and Callgrind ratios are whole-process under Valgrind. They cannot be combined into one scalar.

| Workload | Native ELF64 time | Native i686 time | DHAT blocks | DHAT bytes | Callgrind Ir |
|---|---:|---:|---:|---:|---:|
| Failed-first T2 / R128 | 9.986× | 8.940× | 6.240× | 10.257× | 7.101× |
| First-success T2 / R128 | 1.008× | 1.020× | 0.995× | 0.995× | 1.002× |
| Failed-first T2 / R32 | 3.026× | 2.222× | not profiled | not profiled | not profiled |
| Deep failed-first T2 / R64 | 4.016× | 3.265× | 2.430× | 2.642× | 3.230× |
| Three same-signature heads / R64 | 0.993× | 1.016× | 1.000× | 1.000× | 1.000× |
| One head / R128 | 0.980× | 0.939× | 1.000× | 1.000× | 1.000× |
| 128 builtin true goals | 1.018× | 0.988× | 1.000× | 1.000× | 1.000× |

The two versioned CSVs in [tests/rust_external_profile/results](../tests/rust_external_profile/results) retain **all seven native workloads and all six Valgrind workloads**, including original program SHA256, native medians, block wins, PREPARE totals, SOLVE totals and ratios.

## Load-bearing obstruction and specification/implementation/test drift

The third-party profiler's **DHAT bytes and blocks cover the complete process**, including startup, program/query parsing, solution formatting, library setup and tool-influenced allocation behavior. Callgrind `Ir` is the profiler's dynamic instruction count, **not hardware retired instructions, wall time or CPU cycles**. Its output must not be converted into native CPU attribution.

To control that scope, the identical external harness runs both `PREPARE` and `SOLVE` modes. In primary R128 first-failure, PREPARE was *identical across Gen18/19* at **425 heap blocks, 19,270 bytes and 545,402 Callgrind Ir**. Subtracting PREPARE from SOLVE is not a validated solve-only heap calculation because object lifetimes and memory behavior can differ.

Native timing is a separate source-independent measurement lane: feature-disabled Rust 1.85.1 libraries, exactly the same external `bench_continuations.rs` harness, 3 warmups and 5 AB/BA blocks × 4 timed solves per role/case/ABI (20 raw observations). Parsing, launch and formatting were outside the `solve()` timer. **264/264 full stdout/stderr/exit CLI differential cases passed on each ABI** against immutable versions. Source/query bytes matched and the same tagged commit SHAs were rebuilt each time. No other interpreter files changed.

## Independent witness and representation attacks

Valgrind 3.22.0 was developed independently of this project's bespoke `GlobalAlloc` and `ChoicepointProfile` counters and thus supplies a genuinely **different instrumentation mechanism**, but the protocol, fixtures, Rust harness, analysis and promotion decision remain **project-authored and correlated**. This is **not independent experimental replication** or an independent ISO Prolog oracle.

Reordering the first of two facts from a successful head to a failing head is the key adversarial representation/control-flow attack. T1/T3/builtin controls have identical DHAT totals on both engines and nearly identical Callgrind counts; the first-success T2 case has almost identical native time and external counts. The regression therefore depends on the execution history, not merely the number of signatures.

## Corrections and retirements

The original passing three-job [GitHub Actions run 44302879486](https://github.com/jesusvilela/gprolog/actions/runs/44302879486) used the initial preregistered harness and Valgrind 3.22.0. A duplicate PR-triggered workflow was slow during Valgrind package installation; the later CI-only change bounded setup and skipped unnecessary installs where possible. **No input, engine, test metric, control or threshold changed after results.** See [the infrastructure correction ledger](RUST_GEN21_EXTERNAL_PROFILE_CORRECTIONS.md).

Machine-readable source and artifacts (GitHub Actions retention: 30 days):
[ELF64 native artifact 14427151334](https://github.com/jesusvilela/gprolog/actions/runs/44302937968/artifacts/14427151334);
[i686 native artifact 14425834205](https://github.com/jesusvilela/gprolog/actions/runs/44302879486/artifacts/14425834205);
[ELF64 Valgrind artifact 14427545662](https://github.com/jesusvilela/gprolog/actions/runs/44302879486/artifacts/14427545662).
All original per-case samples and Valgrind DHAT JSON, text callgrind profiles, logs and version strings are retained in those archives. Reproducibility drivers and normalized summaries live in Git.
Official tool specifications: [Valgrind DHAT](https://valgrind.org/docs/manual/dh-manual.html) and [Callgrind](https://valgrind.org/docs/manual/cl-manual.html).

## Round-trip coherence and next bounded experiment

Original question → fixed Gen18 and retired Gen19 trees → identical benchmark harnesses → native and third-party separate measurement domains → strict answer/negative controls → bounded conclusions → original question. No units were silently collapsed.

**Next bounded experiment:** examine raw DHAT allocation-call stacks and Callgrind function call graphs for the first-failure path on a held-out independent query set, without changing the interpreter. Prediction: continuation/term-clone callsites account for most of the added process-wide heap and Ir difference. Metric: matched callsite-attributed allocations/Ir within the profiler's own domain. Kill: unresolved inlining or attribution ambiguity, a violated source/answer invariant, or no reproducible contrast. Stop: do not introduce an adaptive ownership heuristic, WAM, GC or new term heap to rescue a negative result. Independent external reviewer/Prolog oracle remains an unresolved priority.

**Evidence map:** P (conditional algebra of R(R−1)/2 copied suffix elements under eager scheduling), A (instrument/accounting assumptions), M (two-ABI native timing and ELF64 whole-process third-party metrics), H (causal CPU-time share/general semantics), S (untested alternative ownership designs), R (Generation 19 T2-owned optimization, and conflating DHAT/Callgrind with solve-only hardware measurements).
