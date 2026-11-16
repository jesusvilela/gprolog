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

## Second slice: static first-argument float indexing (experimental)

Branch target: `feature/float-indexing` based on the goal-expansion branch.
The earlier GNU compiler intentionally treated float heads as unindexed.
The new source path separates float heads into their own clause-key bucket
and uses `switch_on_term_flt/6` plus `switch_on_float/1` only when
a multi-clause indexing group contains float heads. Without a float bucket,
it still emits the historical `switch_on_term/5`, avoiding global WAM churn.
WAM-to-MA accepts both instruction formats for staged self-hosting.

Float switch tables store complete doubles and verify actual numeric equality
after hash collisions. Both signs of zero use the same hash key; NaN is not
a matching key. Variable-headed clauses remain as ordered segments; cuts and
answer sequences must be unchanged. The change is confined to static clause
indexing; dynamic predicates, multi-argument indexing and JIT are excluded.

Run `python3 tests/float_indexing/run.py --bin-dir ./bin` after an
in-place build. Then run `cd src && make check && make check-e && make check-i`.
These are acceptance gates, not a performance claim.

### Evidence and bootstrap provenance (16 November 2026)

- A fresh single-pass checkout build, not an artificial file-touch rebuild,
  passed Ubuntu 24.04 CI in
  [Actions run 43896491891](https://github.com/jesusvilela/gprolog/actions/runs/43896491891)
  for commit `97d5e1027600ebc89ebb3e4ced9ee39ab8db2c6a`.
- The runner inspects emitted WAM: static float predicates use both
  `switch_on_term_flt/6` and `switch_on_float/1`, while a float-free
  comparator retains historical `switch_on_term/5`.
- 13 semantic checks passed in **each** of native and consulted paths,
  including duplicate keys, wildcard fallbacks, signed zeros, cuts,
  side-effect order, and variable calls; the parent goal-expansion suite
  passed its 29 checks in each path.
- Native, emulated, and interpreted fixed-point bootstrap checks passed.
  Generated `first_arg.wam`, `indexing.wam`, and `wam_emit.wam`
  are committed in the feature branch and synchronized with their sources.

Two earlier failures were diagnostic, not a reason to weaken requirements:
the original tests reused a bound `L` variable between calls inside
`main/0`, and initial CI silently reused stale checked-in WAM artifacts.
Each test is now isolated into its own predicate; CI now tests the actual
generated float instructions and verifies a regular source checkout.

### Matched old-versus-new benchmark — observed, not generalized

A preregistered CI comparison between the pinned goal-expansion baseline
(`12b4284378a59098b9004fe2b454ad9c19536370`) and the float-indexing
candidate (`a1098e229ff83a3d2004b5edcb6b5a86299a55ed`)
passed [Actions run 43898849916](https://github.com/jesusvilela/gprolog/actions/runs/43898849916).
The uniform float-hit synthetic fixture returned a **7.222x** median paired
native execution speedup across seven alternating-order pairs. An atom-only
negative control returned **1.015x** and a variable-call control **0.999x**.
For the primary workload, compiled executable size rose 4,312 bytes and
median compilation time from 0.087626 to 0.089480 seconds. Peak RSS was
essentially unchanged. See [preregistered protocol and results](FLOAT_INDEX_BENCHMARK.md) and [evidence manifest](FLOAT_INDEX_AUDIT.json)
for the exact scope, other workloads, costs, and retired interpretations.

**Limits:** this is a synthetic benchmark on one Ubuntu 24.04 x86-64 runner,
not a general-purpose Prolog performance claim or a complete ISO conformance
proof. A separate i686 multilib check now verifies ELF32 builds and matching finite-literal behavior, but does not verify unusual non-finite float semantics or other platforms.
The bootstrap and benchmark suites are authored within this fork and are
not independent reproduction. PR #2 remains draft pending independent,
real-workload and cross-platform review.


### Cross-ABI semantic witness — bounded

[Adversarial x86-64 differential CI](https://github.com/jesusvilela/gprolog/actions/runs/43938946712) and [i686 ELF32 differential CI](https://github.com/jesusvilela/gprolog/actions/runs/43939319562) both passed three seeded 99-clause programs and 43 queries against a distinct Python source-order oracle, using historical baseline and new candidate compilers in native and consulted modes. The i686 toolchain check confirms both compiler binaries are actually ELF32. This is *not* independent OS/hardware or NaN/infinity evidence; see [scope and results](FLOAT_INDEX_BENCHMARK.md) for limitations.


### Generation 5: near-saturated collision and wraparound oracle

[ELF64 CI #43942693160](https://github.com/jesusvilela/gprolog/actions/runs/43942693160)
and [i686 ELF32 CI #43942693018](https://github.com/jesusvilela/gprolog/actions/runs/43942693018)
pass 17-key same-home-bucket collision tests with a 17/18 occupied
float switch, a duplicate key and same-bucket absent lookups. The
baseline/candidate native/consulted paths matched a separate
source-order oracle for 3 permutations on each ABI (24 paths total).
See [preregistered test scope and caveats](FLOAT_INDEX_COLLISION_PROTOCOL.md).
The hash-model collision addresses were checked in the retained JSON,
not measured as C runtime counters. No NaN, infinity, dynamic mutation,
or independent external reproduction claims follow.
