# Generation 9 — GNU Prolog numeric-locale boundary

Evidence state before CI: **H / unverified runtime observation**.
This study checks an existing design, not a new compiler feature.

## Source finding (already established)

\`src/EnginePl/engine.c\` calls \`Set_Locale()\` at the start of
\`Pl_Start_Prolog\`. Its \`src/EnginePl/set_locale.h\` implementation calls:

\`\`\`c
setlocale(LC_ALL, "");
setlocale(LC_NUMERIC, "C");
\`\`\`

The second operation intentionally overrides the numeric locale inherited
from the user's environment. Earlier speculation that \`LC_ALL=de_DE.UTF-8\`
alone might change normal GNU Prolog numeric token conversion was not
supported by this code and must not be presented as a confirmed bug.

The lexical conversion itself occurs at \`Lexer_Number\` through C
\`sscanf(pl_token.name, "%lf", &pl_token.float_num)\`, followed by the
finite-value guard introduced in PR #5. Both facts matter.

## Two separately typed claims

**Startup normalization (H):** An ordinary GNU Prolog process started
under \`LC_ALL=de_DE.UTF-8\` still uses \`LC_NUMERIC=C\` and decimal point
\`.\` when lexing Prolog floating literals. Every source decimal's binary64
value agrees with the integer-rational oracle. Matched C-locale controls
give the same bits.

**Post-initialization mutation resilience (H):** If other native code
modifies \`LC_NUMERIC\` to a comma-decimal locale *after* startup, the
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
1. \`LC_ALL=C\`, no post-start mutation.
2. \`LC_ALL=de_DE.UTF-8\`, no post-start mutation.
3. \`LC_ALL=de_DE.UTF-8\`, **test-only forced** post-initialization
   \`setlocale(LC_NUMERIC, "de_DE.UTF-8")\`.

An instrumentation-only patch after \`Set_Locale()\` in a throwaway CI
\`engine.c\` allows regime 3; the real \`master\` source is untouched.
Another throwaway patch at the actual C \`sscanf\` call logs the
*effective runtime locale*, decimal separator, lexeme, converted count,
and raw \`double\` in \`%a\` form. The harness checks actual bit patterns,
not merely whether a Prolog program prints OK.

Linux Ubuntu 24.04 ELF64 and i686 multilib ELF32 are the two test
ABIs; both use the same locale package. Before each run
\`locale -a\` must demonstrate availability of \`de_DE.utf8\`. No
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
witness. \`setlocale\` affects process-global state in this test;
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
result.** C's \`%a\` hexadecimal-float presentation itself follows
the active numeric locale, emitting a comma-decimal form that
Python \`float.fromhex\` does not accept. Retain the partial negative
evidence but do not treat that run as a full passed audit.

V2 fixes only the instrument's transport representation: copy the
actual \`double\` bytes into a 64-bit unsigned integer and emit
\`%016llx\` integer hex. This is locale-insensitive on the tested
little-endian ELF64/i686 ABIs. The eight decimal lexemes, three
regimes, exact rational oracle and both claim-level decision
criteria stay unchanged. No production C source is altered.
