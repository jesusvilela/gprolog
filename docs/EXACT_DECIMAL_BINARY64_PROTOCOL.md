# Generation 8 — exact decimal-to-binary64 audit

Status before execution: **H / preregistered**. No production compiler or
runtime C sources are changed. GitHub Actions instruments two disposable
source checkouts and preserves the raw measured bit patterns.

## Claim and baseline

For 44 fixed exact-decimal inputs, the actual GNU Prolog lexer and parser
must produce the same IEEE 754 binary64 value as an independently coded
integer/rational round-to-nearest-even reference. Finite input cases must
also compile and consult successfully. Inputs whose mathematically
correct rounding result is infinity must be rejected *before term
construction* by the current fork.

Compare historical commit 46a32b7c2f0d2bbf904152543445315331498a8a
(pre-lexer guard) to the current fork on the **39 finite cases only**.
The historical version is *not* run on the five overflow cases, since
the original positive-overflow crash is already documented in
Actions #44031708229. Both versions are compiled with the same flags
for each Linux ABI, ELF64 and i686 ELF32.

## Independent arithmetic method and controls

The Python oracle parses each decimal string as an exact Fraction,
computes its binary exponent using integer length/comparison, and
rounds the significand by integer division with ties to even. It does
not call C sscanf/strtod to calculate the primary expected bit pattern.
Known canonical bit encodings and secondary Python conversions check the
algorithm, but do not constitute external third-party replication.

The fixed seed is 20261117. The set contains 44 cases (39 finite, five
infinite after correct rounding), including:

- Exact largest finite binary64 and decimals one integer below, exactly
  at and one integer above the overflow rounding midpoint
- Exact half-smallest-subnormal tie and decimals immediately below/above
- Exact largest subnormal, smallest normal and their rounding midpoint
- Underflow to positive and negative zero, with negative sign bit checked
- Equivalent spellings for 0.5 and 0.1, negative decimal terms
- Twelve deterministic positive/negative dyadic values near tiny ranges

The longest token is 774 characters, below the lexer token buffer of
1 MB. Exact long decimals are generated, not hand-transcribed.

## Actual measured values

The test harness adds C hex-float %a logging to Lexer_Number's scanned
numeric value, guard acceptance, and the parser's Pl_Put_Float term
creation site (including the separate unary-minus branch). The
instruments live only in temporary runner checkouts and are never
committed to the production lexer/parser. All 64 bits are reconstructed
from the logged C values and compared against the exact rational oracle.

The compiled/consulted source is identical for baseline and candidate
on finite cases; source SHA-256 is recorded. A known-answer predicate
must compile, run, and consult correctly.

## Locked kill gate

One incorrect binary64 bit, sign bit, wrong guard outcome, incorrect
compiled/consulted execution, missing C source trace, unexpected
historical/candidate finite disagreement, crash, timeout or wrong ABI
blocks promotion. A shared defect is not a pass. The expected bits must
not be retroactively updated based on observed Prolog output.

If test instrumentation itself fails, preserve that diagnostic, repair
the test harness in a separate commit and rerun with the SAME 44
expectations. No compiler fix or generalized IEEE/ISO claim follows
merely from creating this experiment.

## Resource and interpretation limits

Historical/candidate compile within one runner per ABI with matched
flags. The cases, oracle and C instruments were developed in the same
project; there is no independent reviewer, operating system, compiler
vendor or physical 32-bit hardware validation. A successful test may be
reported as measured binary64 behavior **for this finite corpus only**,
not universal correct rounding or external reproduction.

Post-run evidence must be appended below; until then status stays H.


## First observation and additional preregistered native witness

[Initial run #44035119464](https://github.com/jesusvilela/gprolog/actions/runs/44035119464)
passed the original 44-case test on both ELF64 and ELF32, as recorded
in raw artifacts decimal-exact-elf64 (14307011908) and
decimal-exact-elf32 (14306394345). The lexer and parser C %a traces
matched every expected finite binary64 pattern on both compiler
versions, and the guarded fork rejected five infinity-rounded inputs.

**Residual limitation of V1:** compiler-side parser-term trace is taken
*before* native WAM machine-code emission, and native fixture success
only proves a predicate with an unbound argument can succeed. It does
not independently establish the final compiled constant's binary bits.
This is a specification-to-measurement gap, not a demonstrated defect.

**Additional V2 gate (frozen before the new CI execution):** instrument
the actual compiled runtime's Pl_Get_Float(double n, WamWord arg) C call
in the temporary ELF64 and i686 ELF32 source worktrees. Run each finite
compiled program with a dedicated trace file and require at least one
native get-float event whose 64-bit value EXACTLY equals the same
predeclared rational oracle. All such events must match (including the
negative-zero sign). The event must originate in the executed native
binary, not in the compiler's parsing/serialization pass. Continue
requiring the original 44 cases and the same frozen expected values.

**V2 kill condition:** absent runtime C event, mismatched emitted bit,
wrong ABI, any parser/lexer regression or runtime crash. A failed event
hook is a harness problem until its call path is independently shown;
never rewrite the expected bits to rescue a failure. Keep V1 evidence
unchanged and label the V2 witness separately.
