# Guard overflowing decimal float literals at the lexer boundary

Companion research: audit/float-nonfinite-boundary, GitHub Actions
44031708229. Historical goal-expansion-only and the current float-index
fork BOTH crash during consultation of a single positive overflow fact,
including value(1.0e309)., on Linux ELF64 and i686 ELF32.

This draft remediation changes only src/BipsPl/lexer_supp.c. After sscanf
converts a numeric token, it rejects values outside +/- DBL_MAX or NaN
using portable double comparisons. It DOES NOT reject finite subnormals
or finite underflow to signed zero, and does not change the arithmetic
evaluation of expressions such as exp(1000.0).

Reject an unrepresentable token through the existing parser error
channel before term construction. Exact lexer wording is part of this
bounded test contract, not an ISO-standard diagnosis claim.

The regression suite contains seven finite/atom controls and six
unrepresentable positive/negative literals. Each case tests standalone
native compilation and consulted input. No fatal segmentation diagnostic,
timeout, silently accepted invalid literal, or rejected finite control
is allowed. A nonzero error by itself is not sufficient; the controlled
finite-literal diagnostic must appear for invalid cases.

Both tests must pass on Linux ELF64 and genuine i686 ELF32; the inherited
compiler checks must remain green. Keep the PR draft until observed.
Even a pass will not prove correctness of every possible decimal string,
locale, operating system or non-finite arithmetic path.


## Observed result, 17 November 2026

[ELF64 + i686 ELF32 Actions #44032592587](https://github.com/jesusvilela/gprolog/actions/runs/44032592587)
passed all 13 tests per ABI (7 finite/atom controls and 6 positive
or negative out-of-range decimal float tokens). The overflow inputs
now produce a deterministic syntax error: finite floating point literal
expected here. They do not trigger the fatal consulted segmentation
diagnostic previously reproduced on both compiler generations.

The native compiler returns a nonzero status on invalid literals.
The consulted executable prints the syntax error and may still
return exit status 0 while displaying an interactive prompt, so the
regression gate asserts diagnostic content and absence of fatal
signals rather than naively treating exit 0 as successful parsing.

Existing goal-expansion, float-indexing, and native/emulated/interpreted
bootstrap suites also passed on this fix branch in
[Actions #44032620862](https://github.com/jesusvilela/gprolog/actions/runs/44032620862).

This is a bounded **measured** safety remediation on two Linux ABI
configurations, not a proof of every numeric input or operating system.
Unlike the original branch's added float indexing, this patch modifies
shared lexer behavior inherited from GNU Prolog 1.6.0.

## Correction history

The original audit produced a false green result because a fatal
diagnostic with exit status 1 was labeled a normal syntax error.
The corrected audit remained RED (run 44031708229), and the minimal
positive overflow fact showed the crash does not require float
indexing. The remediation is tracked separately; the failed
historical evidence is retained in the linked audit files.
