# 侘未来 / gprolog-rs — Rust-native vertical slice

**Rust is the runtime. No C engine. No permanent interoperability layer.**

This experimental executable is an initial direct rewrite, **not full GNU
Prolog compatibility**. It contains its own source tokenizer, AST parser,
finite-term unifier, clause instantiation, depth-first backtracking,
solution rendering and command-line entrypoint. It is independent of the
earlier Rust C-ABI float-decimal experiment and can run without building
any part of the historical GNU Prolog source tree.

## Build and try

```sh
cargo +1.85.1 test --manifest-path rust/gprolog-native/Cargo.toml
cargo +1.85.1 run --manifest-path rust/gprolog-native/Cargo.toml -- \
  rust/gprolog-native/examples/ancestors.pl 'ancestor(ada,Who).'
cargo +1.85.1 run --manifest-path rust/gprolog-native/Cargo.toml -- \
  rust/gprolog-native/examples/lists.pl 'append([a,b],[c],Out).'
```

Expected ancestor answers: `Who = noah.` then `Who = mei.`.
Expected append answer: `Out = [a,b,c].`

## What works now

- ASCII atoms and quoted atoms; integers (i64), finite f64 tokens (including
  signed zero), variables, compound terms, lists and Prolog comments.
- Definite Horn facts and clauses, comma-conjunction, semicolon-disjunction,
  parenthesized control groups and invocation-scoped cut, plus recursive rules,
  fresh rule variables, a depth-first choice stack and ordered answers.
- Builtins `true/0`, `fail/0`, `=/2`, `\\=/2`.
- Finite-term occurs-check **enabled**, explicitly not GNU Prolog's
  rational-tree default. A user-controlled maximum number of search
  steps and solutions, with errors instead of silent resource exhaustion.
- Rust-only implementation: no `dlopen`, `libgprolog`, `gcc` or
  external Rust crate in the live interpreter.

## Not yet implemented

Full ISO operator precedence, if-then, arithmetic, negation, DCGs,
dynamic predicates, cyclic terms, attributed variables, the WAM,
native code generation, garbage collection, foreign predicates,
constraints and finite-domain solver, ISO error terms and full
bootstrap/compatibility tests.

This first proof of executability must not be confused with a completed
rewrite. The C GNU Prolog implementation remains an *offline test oracle*,
not a hidden execution dependency. See
[direct rewrite decision](../../docs/RUST_NATIVE_REWRITE.md).

Dual license: LGPL-3.0-or-later OR GPL-2.0-or-later. Historic GNU Prolog
material and authorship remain governed by root `COPYING`.


## The new control-flow path

The example program at examples/control.pl exercises both commitment
and choices created after commitment:

- Run query commit(X). to obtain X = a. only, even though other
  clauses and choices exist.
- Run query late(X). to obtain X = a. followed by X = b.,
  since those choices were created **after** the cut.
- Run query outer(X). to obtain left, left, right, right:
  the cut inside inner/1 does not erase outer/1's alternatives.

The directly executed tests and their expectations are in
tests/control.rs and tests/cli.rs. Consult the frozen operational
protocol at ../../docs/RUST_NATIVE_CONTROL.md.

**Representation boundary:** this engine still clones substitutions
per choice state. The control scopes are now testable, but a mutable
term heap, trail/unwind rules, attributed constraints and compiled
WAM execution remain later native Rust obligations. No C fallback.
