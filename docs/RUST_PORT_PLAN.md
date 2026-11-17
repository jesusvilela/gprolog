# Rust-first GNU Prolog — R0 migration contract

> 侘未来 · preserve the semantics, change the substrate only when evidence permits.

## Decision and constraints

**Decision:** stage a Rust migration, NOT a big-bang rewrite of GNU Prolog.
This personal fork retains GNU Prolog 1.6.0's Prolog language,
finite-domain solver, WAM compilation/execution, native backends,
foreign interface and existing test oracles. Any new Rust component must
preserve those observable contracts. Rust's ownership model alone is
not evidence of faster or more correct Prolog semantics.

The repository's `COPYING` states a dual licensing choice:
**LGPL v3 or later, or GPL v2 or later**. Keep GNU Prolog authorship
and licensing notices intact when reusing or modifying its material.
The experimental Rust crate follows that same dual licensing structure;
no wholesale relicensing is claimed. Consult project maintainers/legal
review for any future distribution change.

## Architecture inventory (master at R0 inception)

| Existing subsystem | Repository | Porting risk |
| --- | --- | --- |
| Tokenizing, terms, I/O and built-ins | `src/BipsPl` | Syntax, errors, semantics, locale behavior |
| WAM runtime and memory/state | `src/EnginePl` | Choice points, unification, tagged words, backtracking |
| Prolog -> WAM compiler | `src/Pl2Wam` | Source-order and compilation semantics |
| WAM -> mini-assembly -> assembler backends | `src/Wam2Ma`, `src/Ma2Asm` | Architecture-specific ABI and optimization |
| Finite-domain constraint solver | `src/BipsFD`, `src/EngineFD`, `src/Fd2C` | Constraint propagation and search correctness |
| Foreign/host interface | `src/EnginePl`, `src/BipsPl` | C ABI, memory lifetimes, foreign failure behavior |

## Staged bridge contract

**R0 (this PR):** independently authored Rust decimal conversion
library and C-ABI boundary. No production GNU Prolog file changes.
Use `f64::from_str` with an explicit ASCII Prolog-style decimal-token
grammar and finite-value guard. Preserve signed zero, subnormals,
ties-to-even and representable binary64 bits. Return a status plus
`u64` bit encoding; **do not mutate process-global locale**.
The FFI is a proof-of-interface, not yet plugged into the lexer.

**R1:** optional shadow execution from `Lexer_Number` in a *temporary
integration build*. Feed the same token to both C and Rust. Compare
exact bits under `LC_NUMERIC=C`, then test forced German locale
without changing global state in the Rust component. If all parity
checks pass, propose a feature-flagged Rust parser; default behavior
continues to use C until the full compiler suite passes.

**R2:** model Prolog terms, unification and compiler IR with explicit
representations. Port compiler passes one at a time with differential
WAM listings, source-order answer oracles and native code witness
checks.

**R3:** WAM engine/memory trail/choice-point prototype. Unsafe Rust is
limited to documented ABI and tagged-word operations. Backtracking,
cut, exceptions and garbage/stack management require adversarial
tests against the C engine before replacing any production path.

**R4:** finite-domain solver, constraints and native backends, with
feature-parity/benchmark gates and cross-platform maintenance plans.

**R5:** a distributable Rust-first GNU Prolog only when all earlier
contracts and recursive self-host/bootstrap checks pass, or explicitly
documented incompatibilities are accepted.

## R0 frozen criteria (before CI)

- Rust crate must build and test on **ELF64 and actual i686 ELF32**,
  with a real C loader calling its exported ABI symbol.
- The pre-existing `decimal_exact_oracle.py` 44 cases (39 finite,
  5 correctly infinity-rounded) must all match Rust `u64` results.
- The C loader must witness actual Rust results under both
  `LC_NUMERIC=C` and a verified `de_DE.UTF-8` comma-decimal locale.
  A C `sscanf` control should show locale sensitivity on at least
  the `1.25` representation; the Rust result must remain invariant.
- Reject nonnumeric identifiers, non-finite text (`NaN`, `Infinity`),
  invalid separators, trailing junk, missing decimal digits and
  overflowing decimals without panic or UB. Support signed zero and
  finite underflow-to-zero.
- FFI pointer contract: valid readable pointer to `len` bytes and
  valid writable pointer to `u64` for success; null/oversized
  arguments return an error status. An arbitrary non-null but invalid
  pointer cannot be safely validated by any C ABI.
- The normal GNU Prolog compiler/bootstrap workflow remains green.
- The Rust ABI is **not** linked to production, nor is the full
  GNU Prolog port claimed to exist.

**Kill condition:** any wrong 64-bit result, accepted non-finite token,
unbounded input handling, environment-sensitive Rust bit result,
i686 failure, FFI crash or regression in inherited GNU Prolog checks.

**Stop rule:** do not modify production `lexer_supp.c` or any
compiler/engine file before this R0 interface and R1 shadow test
satisfy the gates. A passing R0 establishes only a bounded
compatibility *candidate*, not production correctness, speedup,
thread safety or independent third-party verification.

## Evidence ledger

- **M / prior C path:** exact 44-case ELF64/i686 decimal and native
  constant witnesses from generation 8 (see
  `docs/EXACT_DECIMAL_BINARY64_PROTOCOL.md`).
- **M / prior startup:** C numeric locale reset and explicit
  adversarial mutation result in `docs/NUMERIC_LOCALE_AUDIT.md`.
- **H / R0:** independent Rust parser preserves those selected values.
- **H / R1–R5:** Rust replacements for GNU Prolog subsystems.
- **R:** any claim that Rust migration or the language alone proves
  Prolog/WAM correctness or performance.

No external independent witness is asserted. Record R0 CI, C ABI
observations and correction history before moving to R1.
