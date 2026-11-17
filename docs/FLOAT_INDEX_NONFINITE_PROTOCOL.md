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
