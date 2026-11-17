# 侘未来 / Direct Rust rewrite — architectural decision (17 November 2026)

## Decision

**Retire the staged C→Rust production-bridge strategy.** The previous
R0 decimal converter and R1 shadow-lexer experiments remain valuable,
reproducible research artifacts, but they are **not** the target
architecture. In particular, we will not ship a permanent dynamic
`dlopen` layer, dual parser feature flags, Rust/C fallbacks, or a
cross-language WAM runtime. A permanent compatibility bridge would
become a second product to maintain.

Start a **standalone, Rust-native Prolog system now**, keeping the C
GNU Prolog implementation only as an *offline differential oracle*.
Its code is not imported into the new runtime, and the native binary
does not load any C/Prolog bridge libraries.

The new entrypoint is `rust/gprolog-native`, initially a safe,
Rust-standard-library-only Horn-clause engine with its own lexer,
parser, unifier, search scheduler, CLI and tests. This is a direct
rewrite **of the architecture**, not a claim that all of GNU Prolog's
implemented functionality has already been reproduced.

## Single native architecture

```mermaid
flowchart LR
    S[Prolog source] --> L[Rust lexer]
    L --> P[Rust parser and AST]
    P --> E[Rust clause index and search engine]
    E --> U[Rust unification/substitution]
    E --> B[Choice stack and depth-first backtracking]
    E --> O[Solutions / Rust CLI]
    R[Historical GNU Prolog C] -. offline test oracle only .-> T[Differential tests]
    O -. same programs .-> T
```

All production runtime edges above are Rust-to-Rust. Rust R0/R1
compatibility reports are archived as evidence, not extended as
permanent modules of the new interpreter.

## First vertical slice — executable, deliberately bounded

- Facts, Horn rules, variable scopes, compound terms, integer and
  finite floating literals, lists, comments and quoted atoms.
- Standardization apart per clause invocation.
- Backtracking in textual clause order, recursive rules, unification
  on *finite* terms, explicit occurs-check as a temporary safety
  choice (this **differs** from GNU Prolog's rational-tree behavior).
- Core predicates `true/0`, `fail/0`, `=/2`, `\\=/2`.
- CLI loads a Prolog file and evaluates a query, printing solutions.
- Resource budgets to avoid silently unbounded search.
- No foreign interface, no GNU Prolog C linking, no WAM backend
  required to run this first executable.

## Explicitly not yet implemented

ISO Prolog operator precedence, cut, disjunction, DCGs, dynamic
predicates, attributed variables, constraint domains, arithmetic,
exception handling, streams, cyclic/rational trees, the WAM bytecode,
GNU Prolog native code generation, foreign predicates, garbage
collection and full bootstrap. These are first-class **Rust
implementation obligations**, not covert calls to the C version.

The first runtime chooses a **safety-oriented occurs-check** and
bounded search instead of silently emulating GNU Prolog's cyclic
term and nontermination semantics. Such differences must be made
visible to tests and users. Do not claim ISO parity before these
semantics are settled.

## Rewriting the rest

A single Rust-native core gradually acquires modules for operator
parsing, goal control, arithmetic, term/heap representation, trail
and choice-point model, WAM instruction execution, the compiler,
finite-domain constraints and native code generation. There is
no separate 'portability base' bridging C subsystems: when a Rust
module replaces functionality, it owns it end-to-end.

The old C root remains frozen in this fork for provenance and
**offline comparative testing only**; no C file is migrated in
place until the new Rust executable supports the intended behavior.
Deprecating the historical C distribution is a separate release
decision, not implied by this work.

## License and evidence boundary

Historical GNU Prolog material retains its original authorship
and `COPYING` dual-license terms (LGPL v3+ OR GPL v2+). The new
Rust-native code uses the same dual licensing choice without
asserting wholesale relicensing of inherited material.

**P/A/M/H/S/R:** R0/R1 decimal compatibility remains M for its
bounded corpus; the present full native rewrite is H until its
binary actually builds and runs. 'Full GNU Prolog rewrite complete'
is H, not M. C parity can supply a reference, but not a proof of
all semantics or an independent third-party verification.

## Preregistered acceptance and stop rule

First vertical slice must build as a **Rust-only binary**, run
multiple solution examples (ancestor, member, append), preserve
variable freshness and clause order, reject cyclic terms safely,
respect search budgets, reject bad input without panic, and pass
CI tests across Linux ELF64 and i686 ELF32 when toolchains permit.

Kill the first-slice 'working engine' claim on a wrong answer,
cross-clause variable capture, failed unification rollback, syntax
acceptance outside the declared subset, a resource-budget bypass
or a crash. No production migration or rewrite completion claim
is authorized from a green smoke test. Once the first executable
is tested, promote only the implemented subset from H to M.
