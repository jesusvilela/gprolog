# Generation 20 — allocation requests and continuation-copy audit
Frozen before harness implementation, 18 November 2026.

## Question and immutable sources

Why did the rejected Generation 19 **T=2 owned Vec** policy produce an
8–11× runtime increase on ground repeated calls when the first
same-signature clause fails, even though 264 full-output cases per ABI
remained equal?

The **released reference** is Gen18 Rust engine commit
\`901c8b58c12fbe8b79f70b0118f951f3ed2fcf21\` (PR #17).
The **rejected contrast** is Gen19 initial candidate source commit
\`c09fff05d9b3dd43fb90014278e3a98d701d3640\`
(PR #18, closed, never merged). Neither solver is to be edited.

Build both with pinned Rust 1.85.1, release, feature
\`choicepoint-profile\` and the identical **external** Rust diagnostic
binary. True Linux x86_64 ELF64 and i686 ELF32; no historical GNU
Prolog C linkage. The diagnostic harness belongs to a docs/tools-only
branch based on the *released* engine.

## Prediction (H), split by actual execution regime

For exactly two same-signature clauses and R sequential ground calls
(max_solutions=1), count source signature candidates, not actual
unification-successful clauses.

**Regime A: first head succeeds.**
- In Gen18, R−1 nonempty continuations get Arc anchors/handles, R−1
  fallback Vec clones, and one empty final Vec alternative clone.
- In Gen19, there are zero Arc anchors, zero Arc handles, and R owned
  Vec clones.
- Both copy R(R−1)/2 PendingGoal **elements**.
- Relative *total Rust allocation requests* are unknown until
  instrumented. Fewer Arc requests does not prove lower wall time.

**Regime B: first head fails and second succeeds.**
- Gen18 shares the R−1 nonempty suffixes while trying the first
  clause. On that failure its pending alternative becomes the
  **unique Arc owner**, so Arc::try_unwrap succeeds **without copying
  the vector** (one empty continuation alternative clone at the
  last goal).
- Gen19 copies the Vec eagerly R times, totaling R(R−1)/2
  PendingGoal elements, regardless of whether the first head fails.
- For R=128 this is 8,128 copied goal elements in the candidate and
  zero in released Gen18, while both still queue R alternatives and
  execute 2R TryClause tasks.
- Prediction: Gen19 requests **more allocations and more aggregate
  allocator bytes** than Gen18 in the failure-first cases on each
  ABI, with deeper term shapes magnifying the difference.
- The measured 8–11× time difference from Gen19 is separately known
  (M). The causal contribution of specific allocations is **H**.

**Regime C: first succeeds, second fails or is never inspected;**
the same logical execution as A for the first-answer limit. This
control detects whether the mere presence of the second head
changes the scheduler without that head executing.

**Regime D: no matching head, one head, 3+ heads, or builtin-only.**
Both immutable engines take the same ownership branch, so
source-scope-specific structural counts should match. Allocator
counts may differ slightly because of different compiled machine
code, heap state, and allocations unrelated to continuations.
Do not falsely require bitwise byte equality across builds.

## Instrumentation contract (no solver source edits)

The **same external binary**, linked against each instrumented Rust
library separately, defines a \`System\`-delegating \`GlobalAlloc\`.
It enables tracking around **only** one \`solve()\` call after parsing,
query duplication, warmups and \`clear_choicepoint_profile()\`. It
disables tracking *before* formatting answers or printing results.
Track:
- Successful \`alloc\` and \`alloc_zeroed\` request count and
  summed \`Layout::size()\` requested bytes;
- Successful \`realloc\` request count, summed old and new requested
  sizes (not actual copied bytes);
- \`dealloc\` call count and summed \`Layout::size()\` freed;
- Live \`ChoicepointProfile\` source counters: clause choices,
  try/resume tasks, copied Vecs, copied PendingGoal elements,
  Arc anchors/handle clones/fallback copies, redo, trail undo and
  step count;
- Complete Debug answer representation, input source SHA256,
  source bytes, command args, compiler target, source commit.

The allocator instrumentation is process-wide, although the probe
invokes \`solve()\` from a single thread. The counter covers all Rust
heap requests during \`solve()\`, **not exclusively** continuation
allocations. Bytes are *requested layout sizes*: not RSS,
allocator overhead, memory bandwidth, bytes physically copied,
or peak live memory. Snapshots and error handling must be kept
outside the tracking window. Reallocation requested sizes cannot be
added to allocation sizes as if they were disjoint unique bytes.

Three untimed/untallied warmups per process, then four tracked
executions per block per role, with five paired AB/BA blocks, on each
ABI. Retain every raw measurement, no clipping, no cross-ABI pooling.
The existing uninstrumented Gen19 performance measurements remain a
**separate** experiment and are not recomputed using this instrument.

## Frozen fixtures (each with full answer + control counters)

1. \`t2_first_success_r128\` — two identical target(a) facts.
2. \`t2_first_failure_r128\` — target(b), then target(a), query target(a).
3. \`t2_first_success_r32\`.
4. \`t2_first_failure_r32\`.
5. \`t2_first_failure_deep_r64\` — deep mismatch first.
6. \`t2_first_success_deep_r64\` — deep match first.
7. \`t2_both_fail_r128\` — no successful target at first call, zero solutions.
8. \`t2_enumerate_r8\` — duplicate facts, 16 requested solutions.
9. \`t3_first_failure_r64\` — 3 candidate clauses, first mismatched.
10. \`t3_first_success_r64\` — 3 identical facts.
11. \`t1_r128\` — one clause, no choicepoint.
12. \`builtin_r128\` — true/0 only.
13. \`t16_first_success_r64\` — many shared alternatives.

No per-cell samples are omitted based on whether they support the
mechanism. Explicit controls prevent falsely claiming that any
allocation difference is unique to continuation ownership.

## Primary decision and kill conditions

Primary **structural** gate, separately on both native ABIs:
- For \`t2_first_failure_r128\`, released Gen18 must show
  zero cloned PendingGoal elements and zero Arc fallback copies;
  Gen19 must show exactly **8128** cloned PendingGoal elements
  and zero Arc anchors. Both queue 128 clause alternatives and
  produce exactly the same ordered answers.
- In the same case, candidate median *successful allocation
  request count* and *sum of requested alloc bytes* must both
  exceed Gen18's, and candidate must exceed Gen18 in at least
  four of five paired blocks for both metrics. This is a
  mechanistic allocation correlation, **not a causal time proof**.
- \`t2_first_success_r128\` must show the same cloned-goal-element
  count in both variants; \`t3_first_success_r64\` must show
  identical Arc/Vec source counters across variants.
- Every case must preserve complete ordered Debug answers,
  source bytes, requested solutions and error/exit behavior.

**Kill:** missing intended counters; counter mutation from
profiling the wrong code path; unexpected output difference; failure
of 8,128 vs 0 analytic prediction; missing reproducible allocation
contrast; native ABI build failure; or an allocator error/recursion
when tracking. If an allocation prediction fails, retire **only**
that causal story. Negative results may still be merged as honest
diagnostic evidence if ABI tests and safety checks succeed.
Do not change the solver or choose new regimes after seeing results.

**Stop:** no additional optimization implementation, no WAM,
term heap, GC, dynamic sharing threshold or compiler redesign.
Only diagnostic harness, frozen protocol, raw data and audit may
be merged into \`master\`.

**Promotion:** M for bounded Rust allocator requests and logical
copy counters, only after complete raw two-ABI artifacts and
reproducible controls. H for causal attribution of time and general
application workloads. R remains the failed T=2 owned heuristic.
No ISO Prolog conformance claim or independent external witness.

## Provenance and round-trip audit

Known measured Gen19 performance/artifacts:
- [failed PR #18](https://github.com/jesusvilela/gprolog/pull/18),
  [two-ABI failed-gate run 44290905287](https://github.com/jesusvilela/gprolog/actions/runs/44290905287),
  [negative results preserved on master](../RUST_NATIVE_TWO_CLAUSE_OWNERSHIP_NEGATIVE.md).
- This harness/analysis is project-author correlated with the
  implementation. Passing self-authored analytic controls is not
  independent reproduction.

Original requirement -> frozen ownership variants -> actual live
Rust code paths -> bounded source counters and globally requested
heap allocations -> matched paired raw observations -> typed
partial-order comparison -> narrowed explanation of Gen19 failure.
Remainder: allocator internals, term-node clone attribution, system
time, cache behavior, external Prolog semantics, and workload
representativeness.
