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
