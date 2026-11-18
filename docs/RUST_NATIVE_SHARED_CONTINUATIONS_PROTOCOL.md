# Generation 17: shared immutable clause continuations (pre-registered 2026-11-18)

## Freeze and motivation

This is a **bounded representation experiment**, not a general WAM replacement.
Immutable baseline Rust-native solver: commit
`cd880bda3db495d329bdc3b6a0a0a4f654691579` (Generation 16 / PR #15).
Generation 16's dual-ABI live profiling measured 960 queued but unresumed
clause alternatives and 30,240 pending-goal-element copies in the
16-fact / 64-consecutive-goal / first-solution case.

Hypothesis (H): it is possible to share *immutable* clause continuation
suffixes among alternative `TryClause` tasks, avoiding per-choice deep
`Vec<PendingGoal>::clone()` calls while preserving the exact search
semantics, and this reduces uninstrumented direct solve time for that case.

## Frozen design intervention

Replace `Work::TryClause.continuation: Vec<PendingGoal>` with one
internal owned-or-shared representation. Use an owned vector when only
one matching clause or when the continuation is empty; for multiple
matching clauses and nonempty rest, allocate a single `Arc<Vec<PendingGoal>>`
and clone the Arc handle for each queued alternative. Only the
chosen successful clause obtains an owned vector, either via
`Arc::try_unwrap` after all other owners disappear, or by cloning
the vector **once upon successful head unification** while other
alternatives still share it.

Neither `PendingGoal`, the resolver's `Term` AST, substitution trail
nor the execution step counter changes. Shared continuations are immutable.
The `Arc` must be scoped to a single predicate invocation; no global
cache, no C runtime bridge, and no garbage collector.

## Semantic contract (must not change)

- **Exact source-order attempts:** all same-signature candidate heads
  are still scheduled, including incompatible heads and duplicates.
- **Identical `fresh_clause` calls:** freshening takes place at precisely
  the same executed `TryClause` tasks. Residual `_G{id}` identities
  and observable query bindings remain identical.
- **Identical search step accounting and limit errors:** neither the
  shared-handle creation nor materialization adds or removes a
  `Work::TryClause` or `Work::Resume` task.
- **Scoped cut:** the invocation barrier is captured *before*
  pushing its own alternatives; cut truncates pending branches
  without rolling back current bindings.
- **Rollback:** same trail marks and undo order for failure and redo.
- **Full enumerations:** a continuation shared by several alternatives
  must stay alive when first answer returns and later redos execute.
- **Mutable program between `solve` calls:** all continuation and
  signature caching remains per solve; no stale cross-run state.
- **Profiling is truthful:** Generation 16 counters named
  `clause_continuation_vectors_cloned` and
  `clause_continuation_goals_cloned` must now measure **actual**
  Vec copying at the materialization point (not the number of
  alternative tasks). Add separate counts of Arc handle clones,
  Arc-backed continuation creations, and Arc-to-owned fallback copies.

## Analytic predictions (structural, not a timing claim)

For T=16 identical facts and R=64 successive ground first-success
calls, max_solutions=1:
- still 960 clause choicepoints created, zero used
- 960 shared Arc handles cloned
- 64 Arc-backed continuation anchors created
- the first successful clause needs 63 actual fallback full Vec clones,
  with 2016 pending-goal elements copied; the final continuation is empty
  and stays owned (no Arc)
- no trail undo and no redo
- original Gen16 eager copies: 960 Vec clones and 30,240 goal elements

Counted goal elements are not allocated bytes or a claim about time.
For T=1 or empty continuations, retain owned vector behavior without
allocating any Arc.

## Independent matched benchmark plan

Immutable Gen16 baseline vs candidate, the **same external Rust-only
harness** separately linked to each release library with `panic=abort`.
Pinned Rust 1.85.1, same runner, ABI, toolchain, source program/query,
query limits and full ordered answer representation per sample. Linux
ELF64 and genuine i686 ELF32. Five AB/BA paired blocks, three warmups
per run, four solve-only nanosamples per block per variant. Record
per-block samples, median, signed change, 5-block wins, per-process peak
RSS, source SHA256, exit/stderr and source commit IDs. Never pool ABIs.

Preregistered cells:
1. **primary**: T16/R64 first solution, ground fact.
2. deep primary: T16/R64 first solution, nested structural ground terms
   (detects term-size sensitivity, same copied-element count).
3. T2/R64 first solution (small alternative multiplicity).
4. T16/R8 first solution (short continuation).
5. T16/R1 first solution (empty continuation, negative control).
6. T1/R64 first solution (no choices, negative control).
7. 64 `true` goals (no predicate, negative control).
8. T16/R1 enumerate 16 solutions (redo/rollback control).
9. T16/R8 enumerate 16 solutions (shared continuation must survive redo).
10. T2/R8 enumerate 16 solutions (two-head backtracking geometry).

All exact cases, including negative measurements, must be reported.
The primary performance gate is at least **10% lower median solve
time and 4/5 paired-block wins on BOTH ABIs**; no worse than 10% on
either T1/R64 or T16/R1 and no worse than 15% in full enumeration.
These are heuristics, not confidence intervals or a guarantee for
general Prolog workloads.

## Kill and stop rules

- **Correctness kill:** any unaccounted difference in ordered output,
  variable identities, stderr/exit, errors, max-step boundary, cut
  or binding rollback, either native ABI. No merge.
- **Performance kill:** primary gate fails on either ABI, or an
  explicitly listed control regression exceeds its threshold.
  Report the negative result and keep the implementation experimental.
- **Stop:** do not introduce a WAM, first-argument index, term heap,
  mutable sharing, generational GC or other redesign to rescue results.
  The original Gen16 baseline stays in master until all gates pass.
- **Promotion:** measured bounded direct solve speedup (M) only after
  exact-head native tests, frozen full-output differential and matched
  raw A/B. No ISO Prolog or real application runtime claim.

## Remainder and evidence tags

H: shared-continuation speedup prior to measurement; M: Generation 16
counter profiles; S: future continuation representation possibilities;
R: inferring bytes/allocations or wall time from copied-element counts.
The tests and benchmark are authored within the same project. No
independent external reproduction. Cold-cache, allocator effects,
process startup, parsing, deep nesting, data shapes, maximally adversarial
backtracking and ecosystem conformance remain unresolved.
