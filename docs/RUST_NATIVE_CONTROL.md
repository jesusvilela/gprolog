# Rust-native control-flow gate: invocation-scoped cut and disjunction

Evidence before experiment: H. Previously measured Horn-clause subset is not evidence
for cut or disjunction.

## Claim

The Rust-only engine can implement control semantics without a C/WAM bridge:
disjunction (;), lower precedence than conjunction (,); parenthesized goal groups;
cut (!), scoped to the current predicate invocation; and top-level cut. Cut
must discard prior choices in its invocation but preserve alternatives created
after it and must not cross the caller's invocation boundary.

## Operational model

Each pending goal carries the cut-barrier of its predicate invocation. On
entry to a predicate, record the search-stack length before pushing clause
alternatives. Clause-body goals get the new barrier; caller continuation
goals retain their earlier barrier. On cut, truncate only the choice stack
to that barrier. Conjunction and disjunction use the same depth-first stack.
Substitution snapshots remain until the control semantics have been verified;
this is NOT yet a WAM heap/trail implementation.

## Frozen known-answer cases

1. Root cut: p(a). p(b). / query p(X), !. => only X=a.
2. Disjunction: p(X):-(X=a;X=b). / query p(X). => a, b.
3. Clause commit: p(X):-(X=a;X=b),!. p(c). / p(X). => a only.
4. Cut+failure: p:-!,fail. p. / p. => zero answers.
5. Cut BEFORE choices: p(X):-!, (X=a;X=b). / p(X). => a, b.
6. Inner cut: inner(X):-!, (X=a;X=b). inner(c).
   outer(Z):-(Z=one;Z=two),inner(_). / outer(Z).
   => one, one, two, two.
7. Caller cut: pick(X):-(X=a;X=b). outer(X):-pick(X),!. outer(c).
   / outer(X). => a only.
8. Precedence: X=a,fail;X=b. => b.
9. Grouping: (X=a;X=b),fail. => no answers.
10. Scoped alternatives: outer(X):-inner(X);X=outside.
    inner(X):-!,X=inside. / outer(X). => inside, outside.
11. Previous Horn clause ancestor/member/append/occurs-check regressions pass.

Metamorphic attacks: alpha-renaming, source clause reorder, insert a
semantically neutral true in a goal chain, and insert fail into one branch.
All tests compare actual answer ORDER, not just number of answers.

## Preregistered kill/stop rule

One extra/missing/out-of-order answer, cut leaking into the caller,
cut failing to commit, variable-capture, resource-limit bypass, unsupported
operator silently accepted, crash, C-runtime dependency, or ELF32 regression
blocks promotion. Do not add a WAM trail/heap to rescue broken scope handling.
Fix the explicit choice-point model first.

The known unsupported features remain: if-then (->), negation, dynamic
predicates, arithmetic, full ISO operators, attributed constraints, and
rational-tree unification. Treat atom ! in a goal as control, without
claiming full quoted-atom semantic coverage.

Promotion rule: H to bounded M only for implemented scope/precedence
semantics on these cases on ELF64 and i686. Not complete GNU Prolog.
Project-authored tests are correlated evidence, not an external witness.


## Measured first execution — 17 November 2026

The implementation's first complete, instrument-free Rust test run
on [Actions #44073608503](https://github.com/jesusvilela/gprolog/actions/runs/44073608503)
passed on Linux ELF64 and genuine i686 ELF32. Per ABI the Rust-only
engine completed 11 existing parser/engine tests, 7 actual CLI tests,
10 invocation-scoped control tests and 4 metamorphic tests
(**32/32 passed**, zero failures). The historical GNU Prolog
[compiler run #44073608537](https://github.com/jesusvilela/gprolog/actions/runs/44073608537)
also passed, although it does not constitute independent cut
verification of the Rust implementation.

The test-only 512-seed malformed-input parser check remains within
the metamorphic family; do not count those cases as independent ISO
reference witnesses.

**Bounded M result:** cut scope, disjunction precedence, nested
caller alternatives and source-order answers matched the predeclared
small corpus on both ABIs. This is project-authored testing. The
algorithm retains copied substitution snapshots, so neither mutable
heap/trail correctness nor performance superiority is established.

**Remaining obstruction:** real Prolog's extensive control and
lifetime semantics (if-then, meta-call, module scope, rational trees)
are not yet represented. The next work should compare snapshots with
an explicit Rust trail/choicepoint prototype under the SAME tests,
not add a C/Rust adapter or claim full compatibility.
