# Generation 19 — two-clause owned continuation, frozen before implementation
**Date:** 18 November 2026. **Immutable release baseline:** `901c8b58c12fbe8b79f70b0118f951f3ed2fcf21`, Generation 18 merged PR #17.

## Explicit, falsifiable hypothesis (H)
With **exactly two** matching predicate heads and a nonempty continuation, the Generation 18 solver allocates an `Arc<Vec<PendingGoal>>`, clones one Arc handle, then (if the first head succeeds) clones the pending goal suffix *once* during `Arc::try_unwrap` fallback. With two candidates, an owned Vec choicepoint also clones the suffix *once* (but earlier, even if the first head later fails). The Arc therefore does not reduce **the number of goal elements cloned** for an ordinary successful first-head invocation; it may add heap/atomic-refcount overhead. But the alternative owned path can regress badly on a long suffix when the first head fails and the second succeeds, where the original Arc path may unwrap without any deep copy. We must measure both regimes.

**Single intervention:** keep `ClauseContinuation::Owned(rest)` and `copy_for_choice()` for 1 or 2 matching clauses; use shared `Arc<Vec<PendingGoal>>` **only when `clauses.len() >= 3 && !rest.is_empty()`**. No dynamic threshold, term-shape heuristic, first-argument pruning, WAM, GC, mutable aliasing or new binding model. A clause with the correct signature but an impossible head **still counts** toward `clauses.len()`, which is source-signature cardinality, not matched head unification.

## Semantic invariants
- Same ordered candidate clause indices, including structural failures/duplicates.
- Same `fresh_clause` call order and residual variable names, every step count and budget error, same actual first answer/full enumeration, same `!` cut-barrier, disjunction branch order, rollback/trail and binding writes.
- Same reversed `Work::Resume` stack and `Arc` sharing for 3+ candidates.
- T=2 still pushes exactly one `ChoicePoint` per invocation; only continuation ownership differs. No hidden eager lookahead/unification or early pruning.

## Structural predictions (a conditionally derivable count, not bytes/cycles)
For T=2 matching ground successful facts, R sequential ground calls, max_solutions=1, only the first clause executed:
- T=2: `Arc` anchors = 0, handles = 0, fallback materializations = 0.
- Cloned Vec continuations = R (one per pushed alternative), containing R(R-1)/2 goal elements in aggregate, **exactly equal in element count to the released T=2 first-success implementation**.
- Choicepoint pushes = R, actual redos = 0, maximum pending choices = R; pending-goal suffix re-materializations = 0 (Gen18 reversed stack).
- For T>=3 the Generation 18 Arc/Vec counters are unchanged; for T=1 no choicepoint or clone.
- For first-head *failure*, the owned T=2 policy copies the pending suffix when queuing the alternative even though the original shared implementation might later unwrap it without a fallback. A regression here is a deliberate falsification control.

## Frozen matched experiment
Immutable Generation 18 baseline vs candidate, separate uninstrumented release Rust libraries compiled with Rust 1.85.1 against the **same external benchmark harness**. Native ELF64 and native i686 ELF32, matched source/query/limits, `panic=abort`; 5 AB/BA blocks, 3 warmups each launch, 4 raw nanosecond solves per block/variant; separately retain full ordered answer representation, SHA256 of source, median solve-only nanos, five block wins and per-process peak RSS. Do not pool architectures or infer heap bytes from RSS.

**Fixed cells** (all required regardless of outcome; stop at the first structural/semantic failure but preserve observations):
1. `t2_r128_success`: two identical `target(a).` clauses, 128 calls, first answer — primary **A**.
2. `t2_r32_success`: same, 32 calls — primary **B**.
3. `t2_r128_deep_success`: two deep identical target terms, 128 calls — copy-cost control.
4. `t2_r32_deep_success`: same, 32 calls.
5. `t2_r128_first_failure`: `target(b).`, `target(a).` and ground query `target(a).`, 128 calls — **mandatory adversarial control** (first head fails; second succeeds).
6. `t2_r32_first_failure`: same at R=32.
7. `t2_r64_first_failure_deep`: T=2 deep first head fails, 64 calls — copy-cost adversary.
8. `t2_r8_all16`: two matching facts, 8 sequential calls, enumerate 16 solutions.
9. `t2_r1_all2`: two matching facts, one goal, enumerate 2 solutions.
10. `t3_r64_success`: three matching facts, 64 calls — Arc preservation control.
11. `t16_r64_success`: 16 matching facts, 64 calls — Gen17 sharing preservation control.
12. `t1_r128_success`: one fact, 128 calls — no-choicepoint control.
13. `builtin_r128`: `true` x128 — builtin-only control.

**Primary promotion gate:** both A and B must produce >= **5% lower median** direct solve time and >=4/5 faster paired blocks on **each** ABI. **Regression kill:** any first-failure cell or deep-success cell >10% slower, or any enumeration or T>=3/t1/builtin control >10% slower, on either ABI. Control limits are intentionally strict: do not merge an optimization that buys a minor normal-case improvement at the cost of large failure-path regressions.

## Required semantic/structural CI
- All default Rust tests, all opt-in profiler tests, and existing frozen 241-case full CLI output/stderr/exit differential against the exact Gen18 `master` commit, *not* a stale Gen17 binary.
- Additional fixed cut, failed compound-head rollback, generated variable ID, step-budget edge and source-order probe cases. No borrowed `Arc` may outlive solve.
- Feature-only profiler: compare all 12 established live cases, updating analytic expectations *only* for T=2, and add T=3. Check T=2 owned counters and fail-head behavior. Existing transition-count/freshness requirements remain intact.
- The benchmark gate may be **failed by a negative result** without implying a semantic regression. Preserve the raw artifact even on failure.

## Stop, interpretation and evidence boundary
Do not modify the algorithm after inspecting outcomes to make a gate pass. A failed primary or control performance gate retires only **this fixed threshold-3 policy**; it does not erase the successful Gen18 baseline nor justify unbounded heuristic exploration. This branch may publish a negative evidence note and close without merging code. A positive result may be promoted to `master` only after final exact-head CI and audit.

Evidence tags: **M** existing Generation 17/18 Rust subset tests, synthetic solve-only observations; **H** this two-clause threshold hypothesis; **P conditional** copy counts under the inspected execution path; **S** a future term-aware adaptive policy requiring its own scope; **R** any universal speedup or ISO conformance inferred from these matched self-authored tests. There is no independent external Prolog oracle or source author.
