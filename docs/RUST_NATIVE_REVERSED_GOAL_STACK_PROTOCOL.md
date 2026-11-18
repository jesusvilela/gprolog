# Generation 18: reversed pending-goal stack (preregistered 18 November 2026)

## Frozen object and reference

Immutable Generation 17 baseline:
`46b536889e1b461af9e6cddb7f50239eec5697f5`.
Generation 17 stores each `Work::Resume` continuation as
`Vec<PendingGoal>` in *execution order*. Every executed goal
currently decomposes that vector into an iterator, takes the first
element, and collects all remaining elements into a newly allocated
`Vec`. The Generation 16/17 live profiler reports
`resume_suffix_goals_materialized=R(R-1)/2` for a chain of R
successful primitive goals, even if none of them creates alternatives.

The proposed intervention changes the **internal order of every pending
Resume and TryClause continuation** to reverse execution order, so
`Vec::pop()` retrieves the next goal, leaving the suffix in the *same*
vector allocation. The implementation must invert all constructors of
these vectors, including initial queries, clause bodies, comma,
disjunction and backtracking, without changing the parser, Term AST,
choice order, substitutions, Arc sharing, trail or Work task counts.

## Conditional structural prediction

For R successive builtin `true` or single-clause `target(a)`
goals, max_solutions=1, no cuts/failures:
- `Work::Resume` still executes R+1 times (including final success);
- `resume_suffix_goals_materialized` changes from R(R-1)/2 to **0**
  because rest is not reconstructed;
- `Work::TryClause` count and `total_search_steps` are unchanged;
- `clause_choices_pushed` and Arc/Vec continuation-copy counters
  retain exactly the Generation 17 values in tested cases.

These are predictions about explicitly instrumented Rust code paths,
**not** byte allocation counts or time attribution.

For R=128, the old scheduler rebuilds suffixes containing 8,128
pending-goal elements. The new representation should rebuild none.
For R=64, the old count is 2,016 and the new one zero.

## Semantic invariants

1. Goal execution order is identical: for [A,B,C], the first
   executed goal remains A. Reverse *storage*, never resolution order.
2. A body [B1,B2] runs before caller continuation, and in source order.
3. Conjunction `(A,B)` puts B on the stack *under* A.
4. Disjunction `(A;B)` executes A first and queues B with the same
   caller suffix. It may clone one immutable suffix as before.
5. Clause indexing, source order, duplicates, `fresh_clause`,
   generated `_G` names, choicepoint barriers, `!`, binds and undo
   remain unchanged.
6. Identical `max_steps` semantics. Goal suffix reversal must not
   elide any `Work::Resume` or `Work::TryClause` task.
7. The `Arc<Vec<PendingGoal>>` from Generation 17 carries the same
   reversed representation for *every owner*, including redone choices
   after others have been cut or discarded.
8. No C GNU Prolog runtime dependency; same ABI ELF64 and native i686
   ELF32, toolchain and feature-disabled Rust public API.

## Frozen test plan

- Direct Rust tests: one-, two-, three-goal order; body-before-caller;
  nested conjunction/disjunction; duplicate clauses; cut before and
  after alternatives; partial unification failure with rollback;
  `\=` speculative unification; step-budget exact boundary;
  generated variable identifiers and complete answer sequences.
- The same **165-case Gen17 full CLI differential** against the
  immutable Gen17 binary on each ABI, plus deterministic extra
  representation attacks (nested comma/semicolon, cuts and recursive
  continuations). Full stdout/stderr/exit *must* match.
- Diagnostic counters on both native ABIs:
  `resume_suffix_goals_materialized=0`; Work counts unchanged;
  source ordered choices, actual backtracking, undo and cut counts
  unchanged on existing analytic controls.
- One-to-one uninstrumented Rust A/B: compile the same external
  `bench_continuations.rs` harness separately against fixed
  Generation 17 and candidate Rust release libraries with
  `panic=abort`, no profiling feature. 5 alternating AB/BA blocks,
  three warmups and 4 raw nanosecond solves per block/variant, one
  runner per ABI, full ordered answer repr parity and all raw
  samples retained.

### Preregistered benchmark cells

- `builtin_r128`: 128 `true` primitive goals with a minimal source;
  **primary A** (no predicate alternatives, isolates Resume).
- `single_clause_r128`: 128 `target(a)` goals, one fact;
  **primary B** (same Resume issue plus clause execution).
- `builtin_r64` and `single_clause_r64`: repeat-length controls.
- `t2_r128`, `t16_r64`: multiple-matching-clause costs and
  Gen17 sharing preserved.
- `t16_r8_all16`: full enumeration and redo resource control.
- `deep_t16_r64`: ground nested-structural term copy control.
- `t16_r1`: empty suffix (negative).
- `t1_r1`: trivial overhead (negative).
- `t16_r64_all16`: many alternatives with 16 requested solutions.

All cells, including slowdowns, must be retained. `max_steps=200000`.
Record process peak RSS separately, not as allocation attribution.

**Primary performance gate:** both primary A and B must have at
least 10% lower median solve-only time AND candidate faster in >=4
of five paired blocks **on each ABI**. Negative-control and
enumeration slowdowns above 15% on either ABI forbid promotion.
These are heuristic decision rules, not statistical confidence
intervals. No cross-ABI scalar pooling.

## Kill conditions and stop

- Semantic: any unexplained full-output difference, residual variable,
  source order, `!`, undo, step-budget error or task count mismatch.
- Structural: a nonzero `resume_suffix_goals_materialized` on the
  fixed straight-line corpus or a lost expected choicepoint/cut.
- Performance: either primary gate fails on either ABI, or an explicit
  listed negative control/enumeration case regresses >15%. Preserve
  results and do not merge optimization on speed grounds.
- No repair by introducing a WAM, new term heap, new control model or
  GC. Production `master` remains Gen17 until all final-head gates
  pass and failures/corrections are documented.

## Epistemic status

- M: Generation 17 88-89% target improvement, native CLI tests, and
  its operation counters (for their own frozen workloads).
- H: reverse-stack speedup and full Rust semantic parity, until CI.
- P conditional: the original R(R-1)/2 count for copies performed
  by the observed old algorithm, not a general Prolog bound.
- S: a future persistent suffix/continuation object, only if
  reverse-`Vec` is inadequate.
- R: general language conformance, wall-time inferred from counts
  alone, or treating Rust profiler counters as heap bytes.

Correlated implementation and tests are not an external independent
witness. Multi-solution production workloads, different CPUs,
allocators, parser/launch cost, and post-change resource behavior
outside the fixed grid remain unresolved.
