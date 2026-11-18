# Generation 14 — Rust-native predicate dispatch (preregistered, 18 November 2026)

## Frozen object

The Generation 13 `gprolog_native::engine::solve` scans every source clause each time it resolves a user-defined predicate, retaining only clauses whose head has the requested functor and arity. This generation replaces **only that repeated discovery scan** with a Rust-owned lookup table built once per `solve` invocation.

The table maps `name -> arity -> [source indices]`, retaining textual order. It is constructed from the current `Program` on each solve call; no stale global cache, C library, runtime FFI, WAM heap, or foreign Prolog dispatch is permitted. Every selected clause still goes through the existing `TryClause`, clause freshening, unification, trail checkpoint and cut handling.

## Semantics that must not change

1. **Source order / multiplicity:** all matching clauses are attempted in exactly the same order, including duplicate heads.
2. **Variable identity:** `fresh_clause` runs at the same point for every candidate. This preserves the currently printed `_G{id}` identifiers of residual variables as well as logical substitutions.
3. **Search limits:** exactly the same `Work::Resume` and `Work::TryClause` tasks count against `max_steps`; the index lookup itself is not a resolution step, as was the earlier global scan.
4. **Cut / disjunction:** invocation barriers are captured before the same set of alternative clauses is pushed, with unchanged trail marks. Choices after a cut remain available.
5. **Error distinction:** a missing functor/arity still reports `UnknownPredicate`; an existing predicate whose heads cannot unify still fails normally. Unsupported callable terms remain errors.
6. **Mutable public inputs:** rebuilding the index at the start of each `solve` observes edits to the public `Program.clauses` vector made between calls.
7. **Term boundaries:** finite-term occurs-check, rational-tree exclusion, maximum depth behavior, signed-zero bit semantics and the Rust-only no-C contract remain unchanged.

## Tempting but deliberately rejected optimization

First-argument indexing could discard candidate clauses that cannot unify. That would also change the number and timing of `fresh_clause` calls, the printed residual `_G` names, and potentially `StepBudgetExceeded` behavior. Do not adopt it under a mere speed claim. A future semantic contract must explicitly decide how to preserve or revise those observations.

## Preregistered gates

- **Structural:** the fast path must never scan `program.clauses` during predicate resolution. The single index constructor may scan the program exactly once per `solve`.
- **Known answers:** interleaved predicates, duplicate clauses, overloads `p/0`, `p/1`, `p/2`, recursive rules, nested cuts, impossible heads and missing arities.
- **Representation:** insert irrelevant clauses anywhere; retain the intended solutions and compare full CLI observable triples with the frozen pre-trail Rust baseline (commit `2f4c7b9346c7bcdfcd177907049f67cfe957f4d4`), allowing no differences.
- **Stress:** deterministic seeded interleaving of unrelated and target predicates, and non-ground heads that leave printed residual variables.
- **Platforms:** Rust-only tests on actual Linux ELF64 and i686 ELF32, original GNU Prolog bootstrap CI, and the same-Rust full-output differential on both ABIs.
- **Kill condition:** one unexplained difference in ordered answer text, stderr, exit status, cut scope, observable `_G` identities, error type or step-budget outcome, on either ABI. Do not merge.
- **Stop condition:** freeze first-argument and term-arena extensions pending demonstrated semantic equivalence. Keep Generation 14 focused on dispatch.
- **Promotion rule:** label only the bounded indexed-dispatch behavior *measured* after exact-head CI and differential gates pass. Do not claim an isolated speedup without a controlled Generation 13 vs Generation 14 matched benchmark.

## Measurement protocol (separate)

Compare unchanged Generation 13 executable at `dd6375e3fff21026b603c7944dd617ed9b391163` to the candidate on identical runner, ABI, input, toolchain, query, solution count and step budget. Use a synthetic program with many *unrelated* predicate heads and repeated calls to one target predicate (the workload actually addressed by the index), record every paired raw wall/RSS result, and state parsing/process startup overhead. Do not compare this narrow workload against the old 20,000-facts-in-one-predicate trial as though they measured the same effect. No timing is an acceptance gate for correctness.

## Evidence classification

- **M:** Generation 13 test/differential claims, as linked in `RUST_NATIVE_TRAIL_AUDIT.json`.
- **H pending CI:** indexed dispatch preserves all declared observables.
- **S:** a Rust-native predicate catalogue is a stepping stone toward a compiled engine; it is not the WAM.
- **R:** any broad claim that indexed dispatch alone implements first-argument indexing, a native compiler, or full ISO Prolog.

## Amendment (post-measurement; original preregistration preserved)

The eagerly populated catalogue above was **retired for performance**,
not erased or silently replaced. The subsequent, separately preregistered
demand-cache design supersedes its *construction strategy*, not the
semantic invariants. See [the dated correction ledger](RUST_NATIVE_DISPATCH_CORRECTION.md)
and the original unmodified release benchmark artifacts.
