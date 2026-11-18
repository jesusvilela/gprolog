# Generation 26 — exact, unmodified SWI-Prolog demo-directory compatibility census

**Preregistered 18 November 2026, before executing any Gen26 runner.**

## Scope, sampling and licensing

Enumerate *all four* `.pl` programs in the public-domain `demo/` directory at **SWI-Prolog/swipl-devel** commit `111385b90852dade2b772d074cc55fefa20ee1a9`, as returned by the official GitHub repository contents API. These are **not** random samples of all Prolog programs, production workloads or the SWI test suite. Directory census is complete at this exact commit only:

| Upstream program | Original Git blob SHA1 | Preexisting source-note meaning |
|---|---|---|
| `demo/likes.pl` | `88f3d2edcb0fb68c99b559676e5982b3780715f6` | Small food-preference knowledge base |
| `demo/trace.pl` | `5dd10ee3d9176c0792afbf874c50844679b93659` | Cyclic-map debugger exercise; arithmetic and identity tests |
| `demo/unicode.pl` | `c7132cc2cee914b6fc132cdd4f22e25010bd6e36` | Unicode syntax/operators, potentially incompatible with older SWI |
| `demo/colours.pl` | `52391491930d72df055298b28a7d9487847de140` | Syntax-coloring *demonstration*, explicitly **not runnable** in upstream README |

Upstream public-domain notice `demo/README.md` Git blob `fb3850a4dae3c29faea7907d9b3cd48d940fcfaa` says **all files in demo directory public domain**. Preserve the exact upstream source and README bytes (Git blob and SHA256), origin repository and immutable commit. Never modify source in place. Include the original sources in CI artifacts even if parsing fails.

## Research question and representation

After merged Gen25 `ef2c9869d2224a4c8ee1dbba6df965c8fd286e6f` added nested `/*...*/` comments, which upstream Prolog demo programs **load completely unmodified** into the current native Rust finite Horn-clause subset? What *independently observed and typed* limitations remain?

**Version controls:** comparison Rust baseline is merged Gen24 `fb9e05acd87e3fe71052e83ef38f26b9c12701d3` (no block comment support); candidate is exact Gen25 implementation in this branch's PR HEAD. Both use Rust 1.85.1 release, ELF64, default (feature-disabled) configuration. No code in `rust/gprolog-native/` may change.

**The exact load probe** for Rust is a complete CLI invocation:
`gprolog-rs <unaltered file.pl> 'true.' --max-solutions 1 --max-steps 100000`.
Classify separately:
- `accepted_and_true`: exit 0, stdout `true.\n`, stderr empty (program parsed and query completed).
- `syntax_rejection`: exit 2, diagnostic containing `syntax at byte`, raw stderr retained.
- `runtime_or_other_failure`: any other result, with raw exit/stdout/stderr (do not silently coerce).
- Error offset, message and log are *observations*, not inferred proof that exactly one feature is missing.

The independent SWI load probe is `swipl -q -f none -s <unaltered file.pl> -g true -t halt`, reporting actual SWI version, raw exit/stdout/stderr, and **three-way** categories: clean load, loaded with diagnostics, failed load. This is NOT a conformance oracle for non-executable demos or modern syntax under the pinned distro's possibly older SWI-Prolog. `colours.pl` is expected **intentionally non-executable** according to the upstream README and must not count as a comparable working-program mismatch. If `unicode.pl` fails on distro SWI 9.0.4, preserve this independent version-dependent failure as a limitation, not a Rust-specific conclusion.

**Positive semantic control:** For `likes.pl` only, repeat the **same 12 Gen24 frozen queries** with live SWI-Prolog reading the exact original file and the current Rust parser reading exactly the same original file, checking full ordered stdout/stderr/exit with fixed 32 solution/100000 step Rust bounds. No preprocessing or file normalization permitted for *any* of the four original files.

**Historical control:** current parser vs earlier merged Gen24 for 264 previously supported Rust CLI source/query cases, exact stdout/stderr/exit equality. All four original source blobs must match recorded Git SHAs. The no-block-comment Gen24 version is expected to reject `likes.pl` at byte 440; the Gen25 candidate is expected to accept it directly. For the other files, record outcomes with no predeclared sign-only acceptance gate.

## Primary outcome and interpretation

**Primary metric:** typed **four-program** table: pinned original source blob and size; upstream executability label (README-backed); Rust Gen24 and Gen25 parsing/CLI outcome with raw diagnostics; external SWI-Prolog load outcome and interpreter version. Secondary: 12/12 original `likes.pl` ordered semantic matches and 264/264 historical Rust CLI matches.

Do not conflate `Rust accepted` with `SWI runnable`, count SWI errors as Rust errors, or call `#passed/4` an ISO Prolog compliance rate. List the numerator and denominator only for this pinned directory (and explicitly distinguish the one intended invalid source and a SWI version-incompatible source if observed). Do not automatically exclude invalid programs from the denominator: preserve the complete four-row census and classify status separately.

**Predictions (H):** `likes.pl` will change from baseline syntax rejection to candidate accepted, with 12 SWI answers. Other three programs are likely to exercise directives, arithmetic, rich Unicode, or nonexecutability beyond current grammar; do not preregister exact Rust error offsets for them.

**Kill:** original blob/license mismatch, hidden source editing, missing SWI interpreter version, malformed CLI report, 12-query semantic oracle mismatch on `likes.pl`, or 264 historical regression. The study must still record *negative coverage results* for unsupported demo programs even if the experiment's pass flag is false.
**Stop:** no parser/engine changes inside this census, no broadening corpus after examining results, no reclassification to inflate acceptance. Another lexer feature requires a new source-backed PR, hypothesis and negative controls.
**Promotion:** M for the exact four-row source-directory census and independent `likes` subset correctness, after complete original-source tests and evidence/provenance checks. Not measured: global language-compliance percentage, production runtime, logical completeness, algorithmic complexity, memory or WAM performance.

## Independence and evidence map

- **P:** not asserted for full parser correctness; only exact structural SHA comparison is deterministic.
- **A:** the typed distinction between syntax acceptance, runtime behavior, reference load success and intended demo nonexecutability.
- **M:** the four raw CLI/reference observations and twelve `likes` matches after CI.
- **H:** how many of the wider upstream programs will run or what feature fixes are most cost-effective.
- **S:** multi-repository third-party licensed corpus and measured compatibility frontiers.
- **R:** reintroducing retired Gen19 eager continuation ownership or interpreting a four-file census as an ISO conformance rate.

A real independent interpreter is used to test semantics *only for `likes.pl`*. The corpus and loader outcome categories are project-authored; no independent experimental author or auditor is claimed.
