# Compiler evolution in this fork

Base: GNU Prolog 1.6.0 source at `55fd5878acb069b9067da905794627388137076e`.
First slice: branch `feature/goal-expansion`, 2026-11-16.

Preserve GNU's native-code backend and ISO behavior. Transfer documented
capabilities through small implementations with semantic tests. This is not a
merge of other engines or a claim of comparative performance.

## First slice: programmable goal specialization

Inspired by SWI's documented [goal_expansion/2](https://www.swi-prolog.org/pldoc/doc_for?object=goal_expansion/2)
and [expand_goal/2](https://www.swi-prolog.org/pldoc/doc_for?object=expand_goal/2).
Implementation is original, within GNU's existing expansion and source-reader
architecture. No SWI implementation code was copied.

```prolog
goal_expansion(square(X, Y), Y is X*X).
compute(Y) :- square(7, Y).
```

The literal call in `compute/1` becomes arithmetic before WAM/native code
generation. The runtime need not define `square/2` for this caller. No automatic
cost or safety claim is made about a user-supplied transformation.

Hooks are automatically embedded like `term_expansion/2`; helper predicates need
`compiler_mode(embed)` or `compiler_mode(embed_compile)`. Both native compilation
and `consult/1` use the hook, including hooks exported by the default consult
include file. Hook definitions themselves keep their unexpanded bodies.

`expand_goal/2` uses the first successful hook result and follows rewrites until
unchanged or a previously visited goal is encountered. It traverses conjunction,
disjunction, hard/soft conditionals, negation, `call/1`, `once/1` and `catch/3`.
It leaves variables and arbitrary predicate arguments alone. Ancestor identity
prevents finite rewrite cycles and repeated wrapping of an existing goal;
unbounded production of distinct goals can still diverge and is the author's
responsibility.

Successful hooks must not instantiate or alias input variables. Violations
raise `permission_error(modify, goal_expansion_input, Goal)` and abort compilation.
A failing hook's bindings unwind normally. Rewrite authors remain responsible
for preserving runtime answers, cut scope, exceptions and side effects.

Scope limits: no arbitrary `meta_predicate/1` traversal, module lookup rules,
source-location API, directive/initialization expansion, or automatic runtime
`assertz/1` rewriting. `expand_term/2` retains its existing API. DCG and
term-expanded clauses pass through goal expansion as normal clause bodies.
This is a documented compatibility subset, not full SWI emulation.

## Verification

Build GNU Prolog using the upstream `INSTALL` and `src/WINDOWS` instructions.
On Windows use a source/build path without spaces. Run:

```text
python tests/goal_expansion/run.py --bin-dir <in-place-or-installed-bin>
cd src
make check
make check-e
make check-i
```

The runner requires a rejected unsafe rewrite, 29 assertions in native code and
the same 29 in consulted bytecode, including expansion inherited by a subsequent
consult. JSON output includes exact commands and logs. A bootstrap comparison
checks generated WAM against a second compilation; it is not ISO conformance.
See `.agent/notes.md` for local environment evidence and any unfinished checks.

The `Compiler checks` GitHub Actions workflow builds on Ubuntu 24.04, runs the
same semantic fixtures and then all three upstream bootstrap modes. Its checkout
action is pinned to a verified commit. Remote CI results must be reported
separately from local Windows verification.

## Next slices, not yet implemented

| Quality | Inspiration | Acceptance gate |
|---|---|---|
| Better clause selection | SWI/YAP indexing | Ordered-answer, variable, cut and dynamic-update equivalence before timing; begin with one bounded static optimization |
| Assertions and mode information | Ciao/CiaoPP | Explicit declarations with diagnostics first; no speculative optimization based on unproved modes |
| Incremental compilation | WAMpy's synthesis workload | Measure compilation separately, preserve dependency invalidation and compare equal language subsets |
| Tabled recursion | XSB | Define resolution/negation semantics, answer ordering and memory lifetime before VM changes |
| Host-language integration | Trealla/Scryer/Clausal | Reuse GNU's C interface; resource ownership and backtracking tests before new bindings |

Native JIT is not assumed to be necessary: GNU already emits native code. New
features must earn their complexity on measured workloads. Proprietary SICStus
code is not a source for copying implementation.
