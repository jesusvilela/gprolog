# Generation 13 — Native Rust trail and choicepoints

**Preregistered 17 November 2026, before candidate execution.**

## Object and baseline

The sole runtime is Rust gprolog-native. Prior Rust engine commit
2f4c7b9346c7bcdfcd177907049f67cfe957f4d4 stores cloned HashMap
substitutions in each pending choice state. It is the **same-language
semantic baseline**; GNU Prolog C remains an offline oracle.

Replace per-choice substitution clones with ONE mutable Rust binding
store, an explicit LIFO undo trail and alternative frames storing
trail checkpoints plus pending continuation work. No C/Rust adapters,
ABI shims, fallback compiler, or WAM backend.

## Typed invariants

- Every new binding from variable to term is recorded once in the trail.
- Each alternative stores the exact trail length at its creation.
  Redo restores the trail to that checkpoint BEFORE trying it.
- A failed partially successful equality unification leaves no bindings.
- Disequality speculative unification always rolls back, on both
  success and failure.
- Clause variable IDs remain monotone across backtracking (no reuse).
- Cut discards alternative frames in its owning predicate invocation;
  its live bindings stay in the store until later backtracking to an
  ancestor alternative. Caller continuation cut boundaries are retained.
- Query answer rendering traverses live bindings before any untrail.
- Retain finite-term occurs-check and controlled search budgets.

## Frozen known-answer cases

1. Ancestor: noah, mei, in order.
2. Member, append, repeated variables, list recursion.
3. p(f(a,a)). p(f(a,b)). with p(f(X,X)). => one binding X=a.
4. (X=a,X=b;X=c). => X=c, after failed partial unification.
5. (X=a,X \\= a;X=b). => X=b, after speculative rollback.
6. X=f(X). => no answer, by explicit occurs-check.
7. p(a). p(b). with p(X),!. => only a.
8. Cut BEFORE later alternatives permits those alternatives.
9. Cut followed by fail still blocks fallback clauses.
10. Inner cut preserves caller choices; caller cut prunes child choices.
11. Three levels of recursive rule/semicolon alternatives do not
    leak bindings across redo.
12. Alpha-renaming and fact reversal preserve expected invariants.
13. Unknown predicate, syntax and search budgets remain controlled.
14. Existing 32 Rust tests per ABI pass unchanged.

## Comparison controls

Build the exact prior Rust snapshot commit and new Rust candidate
under the same GitHub Actions Linux environment. For a fixed list
of matching source/query pairs, compare complete ordered stdout,
exit codes and deterministic behavior. Step budget internal work-unit
counts may differ; report separately rather than disguise them.

A structural test rejects cloned per-choice substitution maps.
Both actual ELF64 and i686 ELF32 binaries must execute without
any GNU Prolog C runtime dependency. Historical C compiler CI must
stay green but cannot validate the Rust trail implementation.

For an optional synthetic repeated-choice workload, preserve matched
input and resources, raw wall-time and RSS samples before claiming
any speedup. A passing functional test does not prove a performance
benefit.

## Scope

The new component is a **variable-binding trail**, NOT a full WAM
term heap, garbage collector or native Prolog compiler. AST Terms
continue to own their structure. A compact cell arena and GC are
separate future obligations.

**Kill:** any incorrect or reordered answer, stale binding,
escaped cut, wrong equals/not-unifiable result, runtime crash,
ABI difference, regression or C dependency.

**Stop:** do not add WAM, heap or compatibility wrappers to hide a
rollback defect. Repair the current invariants first.

**Promotion:** H to bounded M for this trail-backed Rust subset only
after both ABIs and a matched same-Rust snapshot differential pass.
Project-authored tests are correlated evidence, not independent review.
