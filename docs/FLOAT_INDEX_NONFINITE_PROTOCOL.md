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
