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
