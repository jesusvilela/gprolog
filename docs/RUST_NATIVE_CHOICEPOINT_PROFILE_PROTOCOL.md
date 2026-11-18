# Generation 16 — Rust-native choicepoint cost: frozen instrumentation contract
Date: 18 November 2026. Baseline production master: 2528697368fa2d930029b6c1efa9528745e91f61 (merged PR #14).

## Narrow question
When the Rust-only solver evaluates a predicate with many clauses, what execution objects are created before the first successful answer? Separate clause-alternative scheduling, continuation cloning, ordinary pending-goal materialization, binding writes, undo, cut pruning, and actual redo. Do not infer runtime time attribution from operation counts.

## Preregistered analytic prediction
Program: exactly sixteen facts target(a). Query: 64 successive target(a) goals, represented in the public Query.goals vector. Limits: max_solutions=1 and max_steps=200000. Source order: all first clauses succeed with no binding writes, cuts or failures.

Under the *current* Work::Resume and Work::TryClause Rust algorithm:
- 64 predicate dispatches and 64 first TryClause executions.
- (16 - 1) * 64 = 960 clause alternatives created.
- 960 clones of clause continuation vectors.
- (16 - 1) * (0 + 1 + ... + 63) = 30,240 pending-goal elements cloned into clause alternatives.
- (0 + 1 + ... + 63) = 2,016 pending-goal elements materialized into rest vectors by the 64 Resume tasks.
- No redo pop, no binding undo, no cut pruning; at least 960 discarded but never resumed alternatives when max_solutions=1 returns.
- Pending choice high-water mark: 960. (All clause alternatives remain waiting.)

These are **analytical predictions** to be checked against feature-gated counters at the existing live code points. They are not memory bytes, heap allocation counts or wall time estimates.

## Instrumented quantities (typed, non-aggregated)
- user_predicate_dispatches: count actual requested user predicate goals.
- try_clause_tasks: count executed Work::TryClause tasks.
- work_resume_tasks: count executed Work::Resume tasks, including empty success continuation.
- clause_choices_pushed: count actual clause alternative ChoicePoint pushes.
- disjunction_choices_pushed: count disjunction ChoicePoint pushes.
- clause_continuation_vectors_cloned: count rest.clone() calls for TryClause alternatives.
- clause_continuation_goals_cloned: sum of lengths of those cloned rest vectors (not bytes).
- resume_suffix_goals_materialized: sum of length of the new rest after splitting each non-empty Resume.
- disjunction_rest_goals_cloned: elements copied by rest.iter().cloned() for the right disjunct.
- choicepoints_redone: actual popping of pending alternatives for backtracking.
- cut_choicepoints_pruned: alternatives truncated by invocation-scoped cut.
- binding_writes: calls to BindingStore::bind; binding_undo_writes: actual trail elements removed by undo_to.
- maximum_pending_choices: high-water count after pushing an alternative.
- total_search_steps: engine Work task iterations counted against max_steps.

These are deterministic *logical operation counts* under a particular execution path. The counter updates themselves add CPU work only under the diagnostic Cargo feature; the production solver and original C files must remain unchanged when the feature is disabled. Thread-local reset/read API is test-only evidence, not an operational public monitoring or compiler feature.

## Frozen tests and controls
1. Known-answer 16x64 program: exact predicted counts above and one successful answer.
2. Control T=1,R=64: 0 clause alternatives and 2,016 suffix elements materialized; separate term materialization from clause cloning.
3. T=16,R=1: 15 alternatives but 0 continuation terms cloned; test that choicepoint creation and deep continuation copying are not the same metric.
4. T=2,R=64: 64 alternatives, 2,016 continuation terms cloned.
5. Backtracking control with two solutions: positive choicepoints_redone and binding undo, with expected ordered answers.
6. Cut control: choices pruned without redo, and post-cut alternatives remain valid.
7. Failure control: partial unification followed by rollback, with positive undo.
8. Exact uninstrumented Rust CI and immutable frozen 149-case differential to guard against unintended source-path drift.

## Evidence and decision rules
- Correctness kill: any mismatch with analytically predicted counts, answer ordering, cut semantics, trail rollback, ABI build, or disabled-feature differential.
- Interpretation kill: if clones are counted only by tracing a separate surrogate rather than the executing push site, retire the count-based claim.
- No separate timing attribution from instrumentation; timing comparisons require a separately preregistered, semantically equivalent implementation ablation without instrumentation.
- Stop: do not change the live representation, introduce WAM, term heap, GC or first-argument indexing in this PR. Report counters before proposing an alternative continuation representation.
- Promotion: measured structural counts (M) only for the exact profiled subset with passing Linux ELF64/i686 jobs; analytic predictions (P only as arithmetic under an operational model, not Prolog semantic theorem). Broad bottleneck explanation remains H until a controlled A/B isolation exists.

## Representation and independence caveats
Different term shapes (ground constants vs deep terms), source clause order, disjunctions, recursion, cut, repeated goals vs nested conjunction, max_solutions and multiple answers may change profiles. The same authorship created the code, the profile patch and the tests; a second author or independent profiler is not yet available. Do not claim independent replication.
