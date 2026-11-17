# Rust migration R1 — shadow the live GNU Prolog numeric lexer

Evidence before execution: **H**. R0 locale-independent Rust conversion
passed a standalone C ABI test on both Linux ABIs. It was **not** yet
used by GNU Prolog itself; R1 must close exactly that gap.

## Test-only integration seam

On an expendable CI source checkout only, instrument the code in
src/BipsPl/lexer_supp.c immediately after its existing finite-decimal
sscanf guard. Dynamically load libgprolog_float_decimal.so through
dlopen/dlsym when GPROLOG_RUST_SHADOW_LIB is present.

**The original C numeric value and lexer status remain authoritative.**
The Rust component receives precisely the byte string from
pl_token.name at that conversion site. Record typed Rust status, C
accept/reject status and each raw binary64 u64 bit pattern. The
instrumentation logs; it does not replace, clamp, normalize or
modify the C conversion, error string or token stream.

Run the pinned 44-case generation-8 exact-rational decimal corpus:
39 finite and five overflow values. Compile and consult identical
small Prolog source files under two environments: LC_ALL=C and
LC_ALL=de_DE.UTF-8. Normal GNU Prolog startup should restore its
numeric C locale in either environment. For each finite literal,
verify the Rust and C observed bits equal the exact rational oracle.
For an overflow, require both paths to reject; never equate Rust
status 0 with successful Prolog execution.

Unary plus/minus in Prolog can be tokenized separately from the
numeric literal. Compare signless lexer lexemes against the magnitude
of the exact rational oracle. Prior generation-8 tests covered the
sign bit after Prolog term construction and native machine emission.

## Matched controls and invariants

- Original compiler C path remains the live path, with exactly the
  same result/status under all shadow inputs.
- Both a compiled native executable and a consulted execution must
  preserve the known-answer outcome for each finite test.
- Every C numeric lexer trace must contain an actual Rust C ABI call
  for that *same* Prolog source token.
- Every overflow must yield controlled original Prolog errors and no
  runtime crash; the shadow observes rejection but cannot fix C.
- Each source file is byte-identical across C/German environments
  and checked by SHA-256.
- Actual Rust cdylib, GNU Prolog compiler and C runtime executable
  classes must match verified Linux ELF64 or i686 ELF32.
- The Rust library is pinned Rust 1.85.1 and built from this fork.

## Predeclared kill/stop criteria

**Kill:** any incorrect C answer, Rust/C status disagreement,
one-bit finite mismatch (including underflow and subnormal bits),
missing shadow C ABI call, failure to reject overflow, unexpected
native/consulted crash, bad ABI or missing locale. Do not
post-hoc rewrite the 44 numeric expectations.

**Stop:** do not link Rust into the production GNU Prolog executable
or replace sscanf until R1 passes in both modes and on both ABIs,
and a separate performance/FFI lifecycle/threat-model review is
performed. Even successful R1 is a *measured shadow compatibility*
candidate, not a full Rust port, a memory-safety proof, or evidence
of universal ISO Prolog conformance.

## Security and ownership

The temporary C source obtains a Rust symbol via dlopen and does not
retain Prolog input pointers after the call. Null or invalid pointer
safety is governed by the Rust ABI contract. When the shadow
environment variable is unset, the temporary C build preserves
normal GNU Prolog execution (though the extra unused C loader code
exists in the test binary). No production source patch is committed.

Original GNU Prolog COPYING: dual LGPL v3+ or GPL v2+.
Independent external review is outstanding.

Post-CI results: not yet measured. Preserve failures and correction
history if the instrumented program exercises a different path.

## R1 execution result — 17 November 2026

[Actual R1 CI #44047896700](https://github.com/jesusvilela/gprolog/actions/runs/44047896700) passed on Linux ELF64 and genuine i686 ELF32. Each ABI exercised 44 frozen source values in both C and German startup environments, for 88 source/environment cases. Each case was evaluated through the compiled and consulted GNU Prolog paths. Raw JSON inspection found 188 actual lexer-to-Rust C ABI shadow events per ABI, zero wrong C/Rust classification or bit results, and zero Prolog known-answer/overflow failures. The number of events exceeds the nominal 176 source/mode pairs because the compiler/consultation paths can lex the same literal more than once; count events, not independent source fixtures.

The signed-negative-zero case is correctly compared only at the positive lexical magnitude; the earlier Generation 8 end-to-end term/native constant test supplies separate sign-bit evidence. Five overflow cases per locale were rejected by both implementations without a crash. Under German *startup environment*, GNU Prolog still normalized the numeric locale to C, as independently observed in Generation 9.

Both instrumented builds passed the original goal-expansion and float-indexing semantic regressions with the shadow inactive. The native GNU Prolog production source files are untouched by this PR; the C observer is injected in the temporary Actions checkout only.

Raw evidence with 30-day artifact retention: rust-r1-elf64 ID **14312606438** and rust-r1-elf32 ID **14313020084**. The independently authored Rust crate, C loader, test oracle, fixture generator, and audit protocol are still controlled within the same research project; no external third-party replication is implied.

**Evidence status:** R1 H -> M for this 44-case, two-locale, two-ABI, two-path corpus. It is not a production replacement, nor a measured performance/safety improvement. The next gate is an optional, reversible production feature flag with live C fallback, plus FFI lifetime tests, all standard bootstrap suites and workload performance comparisons. No feature flag is implemented by this PR.
