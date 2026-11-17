# Generation 7: non-finite and boundary float semantics

Evidence status prior to execution: H / unverified. Do not infer Prolog
NaN or infinity literal syntax from arithmetic code. The lexer uses C
sscanf("%lf") at the token conversion site, while arithmetic has
distinct evaluation-error branches for NaN and infinity.

Matched comparison: pinned goal-expansion-only historical compiler SHA
12b4284378a59098b9004fe2b454ad9c19536370 against the current
post-merge GNU Prolog fork. Both build independently with matching flags
on a single Ubuntu 24.04 job, using ELF64 or verified i686 ELF32.
Generated source files are identical by SHA-256 and run both compiled
native and consulted execution separately.

Twenty predeclared cases cover finite controls, maximum finite double,
subnormal and underflow boundaries, positive/negative exponent overflow,
signed zero, lexical atoms nan/inf/infinity (not assumed float values),
and arithmetic overflow, division by zero and invalid arithmetic.
Per-case WAM emission, native compilation status, native execution
status, consulted status, raw exit code and diagnostic output are retained.

Predeclared gates: candidate-only crash, timeout, compiler or execution
status difference, successful output difference, incorrect finite-control
answer or missing float WAM dispatch fails the experiment. Shared
rejection is recorded as rejection, NOT conformance. A common crash
also blocks a claim of safe non-finite handling. An observed success on
a boundary input does not establish ISO float semantics.

Stop rule: no production compiler modifications before a minimal failing
reproducer is isolated. A failure could be a harness issue; preserve the
raw outcome and repair that issue explicitly rather than suppressing it.


## Calibration failure: false-green classification in first run

Initial CI run [#44031111427](https://github.com/jesusvilela/gprolog/actions/runs/44031111427)
passed the 20-case comparison on ELF64 and i686, but raw JSON inspection
revealed a defective classifier: the consulted GNU Prolog engine prints
"Fatal Error: Segmentation Violation" for overflowing POSITIVE exponent
tokens and exits with a routine nonzero code, rather than propagating a
negative SIGSEGV status. The harness labelled this as an ordinary error.
That first green CI was INVALID as an audit of safe non-finite behavior.

The same bad-address diagnosis occurred in BOTH the pinned historical
compiler and the current fork on both ABIs. Compiled mode rejected
generated WAM tokens containing inf or -inf with "float expected".
The case with a negative overflowing literal was accepted in consulted
mode in both versions while native compilation rejected it. This
sign-dependent behavior is an observation, not yet an explanation.

**V2 correction (made after inspecting raw artifacts):**
classify textual fatal segmentation diagnostics as crash_diagnostic,
even when exit code is 1. A crash shared by both versions is a failed
safe-input gate, not a clean parity success. Preserve the original
20-case scope and outputs unchanged. Additionally run a separate
five-fixture *posthoc* minimization to locate whether a trivial
standalone overflowing fact, rather than full indexing, can reproduce
the crash; these extra cases do not alter the primary gate.

A red V2 CI is the honest outcome if the shared overflow crash
persists. No lexical fix, runtime modification or claim of NaN/Inf
syntax support is authorized by this experiment alone.


## Results: V2 diagnostic classifier, 17 November 2026

Corrected [CI #44031708229](https://github.com/jesusvilela/gprolog/actions/runs/44031708229)
FAILED both ELF64 and i686 ELF32 jobs, exactly as the safety gate
requires: four of the 20 frozen cases generated the diagnostic
"Fatal Error: Segmentation Violation" during consulted execution,
despite a normal nonzero exit code. The pinned historical compiler and
the post-float-index fork had IDENTICAL behavior.

| Case | Both native compilers | Both consulted engines |
| :-- | :-- | :-- |
| 1.7976931348623159e308 | rejected WAM: float expected | fatal segmentation diagnostic |
| 1.0e309 | rejected WAM: float expected | fatal segmentation diagnostic |
| 1.0e9999 | rejected WAM: float expected | fatal segmentation diagnostic |
| Arithmetic with 1.0e309 | rejected WAM: float expected | fatal segmentation diagnostic |
| -1.0e309 | rejected WAM: float expected | succeeds with matching answers |
| Finite/subnormal/underflow/atom controls | passed | passed |
| exp(1000.0) | caught float_overflow | caught float_overflow |
| Division by zero | caught zero_divisor | caught zero_divisor |

Observed WAM output for positive overflow includes get_float(inf,0)
in the historical compiler versus switch_on_float([(inf,...),...])
in the float-index candidate. Both generated forms are rejected by
the WAM parser. This does NOT establish accepted non-finite syntax.

The five additional posthoc minimizers give stronger localization:
a trivial file containing value(1.0e309). with an initialization
directive that simply halts reproduces the fatal diagnostic in both
compilers on both ABIs. A corresponding negative-overflow fact and a
finite fact do NOT. An ordinary unification goal using the positive
overflow literal also fails; an indexed predicate is unnecessary.

Raw 30-day CI artifacts: nonfinite-elf64 (ID 14305242828) and
nonfinite-elf32 (ID 14305861852).

Evidence ledger:
- M: no candidate-only status or success-output divergence in 20
  fixed cases on the two tested Linux ABIs
- R: the original false-green nonfinite safety verdict and the claim
  that nonzero exit status without a negative signal implies harmless
  rejection; the V2 crash gate correctly fails
- H: exact C-level cause of positive-overflow segfault; supported
  lexical error policy; cross-platform and independent replication

This is an UNRESOLVED SHARED CRASH, not a float-indexing regression.
The audit PR stays draft and no source-level lexer fix is merged merely
because this triage found a likely boundary.


## Remediation follow-up (separate branch)

The original unsafe behavior was observed BEFORE a lexer fix.
[Draft PR #5](https://github.com/jesusvilela/gprolog/pull/5)
places a finite-range check directly after C float token conversion.
Its ELF64 and i686 ELF32 regressions passed in CI run 44032592587.
This does not rewrite the historical failed verdict. The raw
first-run and corrected-red artifacts remain the evidence for the
pre-fix problem, and the new suite supplies separate fix evidence.
