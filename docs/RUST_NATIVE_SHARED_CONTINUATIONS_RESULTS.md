# Generation 17 - shared immutable Rust clause continuations

18 November 2026 | Exact implementation head: `11fa2975f8ca5a40e4e510dec0aea0c37b50361b`

## Verdict

The bounded replacement of eager per-alternative cloned continuation vectors with a shared immutable `Arc<Vec<PendingGoal>>` (only when multiple candidates and a nonempty suffix exist) meets the preregistered primary performance and negative-control gates on native ELF64 and i686 ELF32. All **165 exact full-output CLI cases per ABI** and all **12 structural profile cases per ABI** passed. This supports a localized implementation improvement, not a universal Prolog performance or correctness theorem.

## Claims and evidence ledger

| Claim | Prior status | Evidence | Current status |
|---|---|---|---|
| Original 16x64 first-answer code clones 30,240 pending-goal elements | M | Generation 16 live profiler, PR #15 | M |
| Immutable continuation sharing preserves the tested Rust subset | H | Full ordered stdout/stderr/exit parity, 165 cases per ABI + native tests | M (bounded) |
| Shared candidate decreases first-answer 16x64 direct solve cost | H | 20 timed samples per version, per ABI, paired A/B and controls | M (bounded) |
| The implementation allocates 960 `Arc`s | R | Only 63 anchors and 945 extra Arc handles in primary case | R |
| The improvement applies to all Prolog workloads | H | One-clause and two-clause negative controls | Not established |

## Strongest surviving result

The primary preregistered first-answer workload used 16 identical ground facts and 64 repeated goals, with one requested solution. Rust 1.85.1, two immutable releases, identical external harnesses, parser and startup outside timed region, five alternating AB/BA blocks and 20 timed `solve()` samples per version/ABI.

| ABI | Gen16 median | Gen17 median | Reduction | Candidate-faster blocks | Peak process RSS (Gen16 to Gen17) |
|---|---:|---:|---:|---:|---:|
| ELF64 | 2,951,252 ns | 323,228 ns | 89.048% | 5/5 | 7,940 to 2,812 KiB |
| i686 ELF32 | 3,978,234 ns | 442,748 ns | 88.871% | 5/5 | 5,076 to 2,560 KiB |

The deeply nested term version showed 93.32% reduction on ELF64 and 90.30% on i686. Larger source terms magnify the difference in cloned Term AST costs, but these are still synthetic cases. Process RSS includes parsing and startup and is not isolated heap accounting.

## Instrumented structural profile

In the exact primary experiment, both native ABIs measured 960 alternative choicepoints (unchanged), 63 shared continuation anchors, 945 Arc handle clones, 63 successful fallback vector materializations, 15 zero-length owned Vec clones, **78 actual Vec clones containing 2,016 PendingGoal elements**, and zero redos. The original algorithm cloned 960 continuation vectors containing 30,240 PendingGoal elements. This is a 93.33% reduction in copied elements; it is not a count of bytes or CPU cycles.

## Full 10-case matrix

| Case | ELF64 improvement | i686 improvement |
|---|---:|---:|
| `builtin_r64_first` | -6.19% | +1.44% |
| `deep_t16_r64_first` | +93.32% | +90.30% |
| `primary_t16_r64_first` | +89.05% | +88.87% |
| `t16_r1_all16` | -0.55% | +3.54% |
| `t16_r1_first` | +2.35% | -1.57% |
| `t16_r8_all16` | +39.80% | +53.97% |
| `t16_r8_first` | +41.20% | +58.11% |
| `t1_r64_first` | -2.36% | +2.73% |
| `t2_r64_first` | -2.50% | -3.07% |
| `t2_r8_all16` | -0.74% | +3.83% |

Two-clause/R64 first-answer work regressed mildly in this run, and trivial/pure builtin cases fluctuate near zero. The negative-control regression limits were not crossed. Do not summarize this table as a universal scalar speedup.

## Specification -> implementation -> test audit

The actual Rust `Work::TryClause` now carries an owned-or-shared continuation. A shared suffix is constructed only if multiple same-signature candidate heads exist and the suffix is nonempty. Alternative tasks clone the immutable `Arc` handle. The selected clause still goes through the same `fresh_clause`, unifier, trail mark and continuation ordering. The shared vector is materialized when and only when a clause head succeeds, using `Arc::try_unwrap` for last-owner reuse or copying one owned Vec otherwise. Cut still truncates alternatives, not live bindings. Runtime task accounting is unchanged. The profile feature records true Vec copies at the materialization site rather than assuming each choicepoint copies its suffix.

The semantic witness compares Gen16 and Gen17 CLI exit code, complete stdout and stderr for 149 historical/frozen cases plus 16 new deep-continuation, cut, budget, non-ground and enumeration cases, on each native ABI. Unit/integration tests exercise the last Arc owner on redo, cut pruning, partial failure rollback and the 12 prior structural cases. There is no external independent Prolog implementation oracle.

## Controls, representation attacks and resource parity

Both versions use Rust 1.85.1, the same OS runner, release profile, target ABI, source program, query, step and answer limits and external uninstrumented Rust bench harness. All raw nanosecond samples, per-block wins, program hashes, process RSS, exact answer representations, errors and independent native ABI runs are preserved. Program/query parsing precedes the measured `solve()` loop. The process RSS metric includes parsing/process state. Program representation attacks include deep terms, one clause (no sharing), empty suffix (no sharing), 16 choices with full enumeration, cut, failing head, and step budget boundaries.

## Corrections and retirements

1. The first pre-implementation protocol erroneously predicted 64 Arc anchors and 960 handle clones. The empty last suffix is owned, yielding 63 and 945. This was corrected in a separate append-only ledger **before implementation**.
2. The initial profiled CI failed because a newly authored T=1/R64 assertion incorrectly expected 2,016 copied elements instead of zero. This test mistake was repaired and documented; that failing run collected no performance results. It is not a production bug claim.
3. Inferring memory bytes from pending-goal element counts is retired. The observed process RSS is a separate end-to-end maximum and cannot itself prove an allocation mechanism.

## Independent-witness status and uncertainty

No independent external reviewer, reference implementation, Lean proof or ISO conformance result is asserted. Both programs, benchmark harness and test generators are project-authored. Five paired blocks control some ordering effects but do not establish general statistical confidence intervals, independence across runner scheduling or performance portability to other applications. No separate full-program parsing benchmark was conducted.

## Round trip

Requirement (reduce unnecessary continuation copying) -> owned/shared immutable scheduler representation -> identical task/goal order -> exact native ABI and CLI parity -> measured copy counts and direct solve timing -> bounded first-answer benefit. The surviving statement is narrower than a claim about all Prolog systems, all benchmarks, or formal language equivalence.

## Next bounded experiment

Measure persistent/sliced `Work::Resume` suffix storage to address the still observed 2,016 ordinary suffix materializations in the 64-goal first-answer path. First specify how it preserves cut barriers, trail undo and per-task step limits, then compare against immutable Gen17 on first-answer, complete enumeration and small-program negative controls. **Kill** any behavioral mismatch or >10% regression in previously protected small cases; **stop** before WAM, GC or heap rewrites unless new typed evidence requires them.

## Provenance and original data

- Frozen Gen16: `cd880bda3db495d329bdc3b6a0a0a4f654691579`
- Candidate Gen17: `11fa2975f8ca5a40e4e510dec0aea0c37b50361b`
- CI: [exact-run 44277552496](https://github.com/jesusvilela/gprolog/actions/runs/44277552496)
- Raw ELF64 GitHub artifact: 14415103002
- Raw i686 ELF32 GitHub artifact: 14414104435
- GitHub artifacts have 30-day retention; local evidence bundle contains unmodified extracted copies.

## Final evidence tags

**M**: native matched synthetic times, RSS, counted operations, CLI parity on this corpus. **H**: general performance and semantic equivalence. **S**: possible immutable persistent suffix design. **R**: using copy counts as bytes, original false arithmetic for empty last suffix, and full Prolog conformance claims without an independent oracle. **P**: only the conditional combinatorial count identity, not a proved full Prolog theorem.