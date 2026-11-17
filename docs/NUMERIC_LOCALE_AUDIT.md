# Generation 9 — GNU Prolog numeric-locale boundary

Evidence state before CI: **H / unverified runtime observation**.
This study checks an existing design, not a new compiler feature.

## Source finding (already established)

`src/EnginePl/engine.c` calls `Set_Locale()` at the start of
`Pl_Start_Prolog`. Its `src/EnginePl/set_locale.h` implementation calls:

```c
setlocale(LC_ALL, "");
setlocale(LC_NUMERIC, "C");
```

The second operation intentionally overrides the numeric locale inherited
from the user's environment. Earlier speculation that `LC_ALL=de_DE.UTF-8`
alone might change normal GNU Prolog numeric token conversion was not
supported by this code and must not be presented as a confirmed bug.

The lexical conversion itself occurs at `Lexer_Number` through C
`sscanf(pl_token.name, "%lf", &pl_token.float_num)`, followed by the
finite-value guard introduced in PR #5. Both facts matter.

## Two separately typed claims

**Startup normalization (H):** An ordinary GNU Prolog process started
under `LC_ALL=de_DE.UTF-8` still uses `LC_NUMERIC=C` and decimal point
`.` when lexing Prolog floating literals. Every source decimal's binary64
value agrees with the integer-rational oracle. Matched C-locale controls
give the same bits.

**Post-initialization mutation resilience (H):** If other native code
modifies `LC_NUMERIC` to a comma-decimal locale *after* startup, the
same Prolog literal still parses identically. This is a **separate
adversarial hypothesis**, not a property implied by Set_Locale().
A failure means that ambient-locale changes by foreign/embedding code
can alter numeric parsing; it does not mean that setting LC_ALL before
ordinary startup bypasses GNU Prolog's guard.

## Fixed inputs and observables

Eight lexemes: 1.25, 0.1, 0.5, 1.0, 1234.5, 12.5e2, 5.0e-324 and
1.7976931348623157e308. These include an invariant value (1.0),
fractional forms, exponent syntax, a subnormal and the largest finite
double. All are independently representable as exact rationals and
compared against the previously retained binary64 oracle.

Three regimes are executed for each value, compiled and consulted:
1. `LC_ALL=C`, no post-start mutation.
2. `LC_ALL=de_DE.UTF-8`, no post-start mutation.
3. `LC_ALL=de_DE.UTF-8`, **test-only forced** post-initialization
   `setlocale(LC_NUMERIC, "de_DE.UTF-8")`.

An opt-in test-only mutation inside `Lexer_Number`, triggered only on
the selected user numeric lexeme, enables regime 3 immediately before
`sscanf` after ordinary startup. No production `engine.c` source is
modified. The same throwaway lexer patch at the actual C call logs the
*effective runtime locale*, decimal separator, lexeme, converted count,
and raw `double` in `%a` form. The harness checks actual bit patterns,
not merely whether a Prolog program prints OK.

Linux Ubuntu 24.04 ELF64 and i686 multilib ELF32 are the two test
ABIs; both use the same locale package. Before each run
`locale -a` must demonstrate availability of `de_DE.utf8`. No
locale name is assumed from the environment alone.

## Frozen decision criteria

- **Primary gate:** both ordinary-startup regimes on both ABIs use the
  C numeric locale and decimal point, convert each of eight source
  tokens to the expected 64-bit pattern, and execute without fatal
  diagnostics. Any absent C trace, wrong effective locale, or
  incorrect value fails.
- **Adversarial gate:** force the German numeric locale only after
  initialization, verify it really became active, then compare bits.
  Any discrepancy *retires the post-initialization invariance claim*
  while preserving the startup result.
- Treat C parser syntax versus C numeric scanning separately.
  A source program returning OK does not prove the token had the right
  value; direct C traces are mandatory.
- The combined CI is designed to report primary success *separately*
  from any adversarial counterexample. A green primary result never
  certifies post-start locale resilience, and a forced mismatch must
  be prominently emitted as a warning and stored in raw JSON.
- Crash, timeout or inability to establish the forced comma-decimal
  locale is a harness/safety failure, **not** an observed locale
  invariance result.

## Scope limitations and stop condition

Project-authored source instrumentation and oracle, two Linux ABI widths
on the same hosted runner family, no independently authored external
witness. `setlocale` affects process-global state in this test;
concurrent-thread interactions and real foreign libraries are outside
the study. No production parser change is authorized merely from
this audit. If post-init mutation demonstrates a bug, first isolate a
genuine embedding use case and assess a portable, behavior-compatible
remediation before touching the production lexer.

## Post-run evidence

Pending CI. Preserve raw stdout, actual locale strings, separators,
C binary64 values, source hashes, and the typed two-claim verdict.


## Measurement-correction record — first attempt (17 November 2026)

[CI #44041966803](https://github.com/jesusvilela/gprolog/actions/runs/44041966803)
executed the C and German-environment controls with 0 ordinary-startup
mismatches on ELF64 (16/16 source/mode combinations). The deliberate
post-start German mutation then produced six early fractional
bit mismatches before the trace decoder raised a Python ValueError on
a later case.

**The incomplete first run is a harness failure, not a completed ABI
result.** C's `%a` hexadecimal-float presentation itself follows
the active numeric locale, emitting a comma-decimal form that
Python `float.fromhex` does not accept. Retain the partial negative
evidence but do not treat that run as a full passed audit.

V2 fixes only the instrument's transport representation: copy the
actual `double` bytes into a 64-bit unsigned integer and emit
`%016llx` integer hex. This is locale-insensitive on the tested
little-endian ELF64/i686 ABIs. The eight decimal lexemes, three
regimes, exact rational oracle and both claim-level decision
criteria stay unchanged. No production C source is altered.


## Second correction: early-engine hook was not a post-start embedding witness

[CI #44042262835](https://github.com/jesusvilela/gprolog/actions/runs/44042262835)
used locale-invariant integer traces. Both ELF64 and ELF32 showed zero
ordinary-startup mismatches across the eight C-environment and eight
German-environment source/mode pairs. The deliberately forced German
locale yielded 14 numeric mismatches per ABI (seven of eight lexemes
in both native compilation and consultation).

Both CI jobs were RED because the harness incorrectly placed eight
**forced-locale consulted fatal diagnostics** into a shared
`harness_errors` field and thereby set
`passed_normal_startup=false`. The normal-startup cases themselves
reported zero failures. The observed fatal diagnostics must not be
silently discounted, but they belong to the adversarial arm.

More importantly, V2 inserted the locale mutation immediately after
`Set_Locale()`, **before full engine initialization**. That is an
early-initialization stress test, *not* an accurate simulation of
foreign code mutating the locale after startup. The prior label
"postinit" was too strong and is retired for V2.

**V3 correction, frozen before new CI:** inject the opt-in German
locale mutation only inside `Lexer_Number` on the specific user
numeric lexeme being tested, immediately before the actual
`sscanf` call. The engine initialization file is no longer patched.
The same eight decimal tokens, three regime types, exact bit oracle,
and two Linux ABI checks are retained.

Report ordinary-startup numeric correctness, intentional mutation
value differences, and mutation-only runtime failures as **three
distinct coordinates**. A failed mutated execution must not change
the startup verdict, but explicitly defeats claims that parsing is
safe under arbitrary external numeric-locale changes. Any mismatch
in effective locale is still a harness invalidation.


## Final V3 results — 17 November 2026

[CI #44042727365](https://github.com/jesusvilela/gprolog/actions/runs/44042727365)
completed both native ELF64 and i686 ELF32 jobs successfully for the
**ordinary-startup claim**. Raw JSON was inspected, not only job status.

| Observation | ELF64 | i686 ELF32 |
|---|---:|---:|
| Normal startup / C environment, compiler + consult | 8/8 correct | 8/8 correct |
| Normal startup / German environment, compiler + consult | 8/8 correct | 8/8 correct |
| Forced German locale after startup, wrong 64-bit values | 14/16 | 14/16 |
| Forced German locale, native compiler nonzero exit | 8/8 | 8/8 |
| Forced German locale, consulted fatal segmentation diagnostic | 8/8 | 8/8 |
| Missing C traces or invalid locale controls | 0 | 0 |

The C trace confirmed a decimal point of `.` and effective locale
`C` for all ordinary-startup source conversions, regardless of the
requested German environment. The opt-in mutation at the source token
changed the effective locale to `de_DE.UTF-8` with a comma separator
in both ELF64 and i686.

For `value(1.25).` the measured C conversion became
`0x3ff0000000000000` (1.0), whereas exact rational conversion
requires `0x3ff4000000000000` (1.25). `value(1.0).` was the one
value control whose numeric bits matched despite the mutation; its
consulted execution nevertheless reported a fatal diagnostic. The
injection caused compiled execution failures across all eight values.

The **24 postinit runtime-failure records per ABI** count multiple
diagnostics per process (compiled nonzero exits, consulted nonzero exits,
consulted fatal diagnostics). They are NOT 24 distinct programs;
the actual tested number is eight source programs and two modes.

Raw CI artifacts (30-day retention):
- `numeric-locale-elf64` ID **14310266352**
- `numeric-locale-elf32` ID **14309912863**

**M / measured, bounded:** normal startup explicitly restores C numeric
locale and preserves all eight expected finite decimal conversions in
both tested execution modes and Linux ABIs, even if the user requests
a German locale through environment variables.

**R / retired:** numeric source parsing remains invariant to an
externally induced change of LC_NUMERIC at the point of conversion.
Wrong C bits and fatal consulted diagnostics under the controlled
mutation are counterexamples. This DOES NOT establish that normal
German-language users experience the defect, nor independently prove
that a particular real foreign library induces it.

The test-only injection mutates the locale immediately before the user
numeric lexeme, after engine startup. It is deliberately adversarial
rather than a supported GNU Prolog configuration. This finding alone
does not justify a global `setlocale` call in every production lexer
operation, which could create thread-safety and host-integration harms.

**Next bounded gate:** reproduce with a genuine foreign predicate or
embedded host that changes locale after full startup, then compare
candidate remedies that avoid process-global locale mutation,
including a C-locale-specific converter where available and portable
fallback behavior. No production lexer patch from this audit.
