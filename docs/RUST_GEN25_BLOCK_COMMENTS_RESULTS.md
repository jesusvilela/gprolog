# Generation 25 — Direct nested-comment support unlocks unmodified upstream Prolog

**18 November 2026. Verdict:** A narrowly scoped lexer change recognizes ordinary, Pldoc and *nested* `/* ... */` comments as lexical whitespace in the Rust-native finite Horn-clause parser. The genuine **unchanged, 922-byte** public-domain SWI-Prolog `demo/likes.pl` now parses and executes directly in the patched Rust interpreter. All **12 frozen ordered results** match an independently implemented **SWI-Prolog 9.0.4** interpreter on that same original source; the patched Rust engine also matches the comment-normalized derivative and the released Gen18 interpreter on the derivative. All **264 previously supported Rust CLI cases pass unmodified on both ELF64 and i686**. This is a measured parser-compatibility improvement, not full language conformance or an optimization of Gen19's retired ownership policy.

## Claim and evidence ledger

| Claim | Before | Independent/structural artifact | Observed result | After |
|---|---|---|---|---|
| Original untouched upstream `likes.pl` can run directly on new Rust parser | H | Same Git blob and live SWI executable reference | **12/12 ordered SWI outputs** match directly | M |
| Original released Gen18 rejects this source | M (Gen24) | Frozen Gen18 executable on same file | exit 2, syntax at byte 440, unsupported `0x2f` | M, preserved |
| Nested, unterminated and literal-quoted comment delimiters are lexed safely | H | New Rust unit known-answer and adversarial tests on both native ABIs | All default and feature-gated tests pass | M (tested subset) |
| Previously accepted Prolog programs retain their CLI behavior | H | Existing 264-case strict exact-output differential vs immutable Gen18 | **264/264 per ABI** unchanged | M, bounded |
| This establishes full ISO/SWI syntax support, or a performance advantage | H | No complete syntax suite or timing study | Not established | H |
| The retired Gen19 two-clause eager-owned policy should return | R | No such source change in diff; previous counterexamples | Remains retired | R |

## External source provenance

The original [SWI-Prolog `demo/likes.pl`](https://github.com/SWI-Prolog/swipl-devel/blob/111385b90852dade2b772d074cc55fefa20ee1a9/demo/likes.pl) is pinned to upstream commit `111385b90852dade2b772d074cc55fefa20ee1a9`, Git blob SHA-1 `88f3d2edcb0fb68c99b559676e5982b3780715f6`. The [demo README](https://github.com/SWI-Prolog/swipl-devel/blob/111385b90852dade2b772d074cc55fefa20ee1a9/demo/README.md), blob `fb3850a4dae3c29faea7907d9b3cd48d940fcfaa`, states that all demo files are public domain. Both source files remain **byte-identical** in the repository; the original program SHA256 is `8f83ce408a0885818969424564ca3e2a39d1921828018b066680f8f19651f42d`.

The independent semantic witness is SWI-Prolog 9.0.4 on Linux ELF64, executed on those **original exact source bytes**. The program queries and wrapper/answer translation are project-authored; this is an independent interpreter and third-party original program, *not* an independently authored experimental study.

## Code-level intervention and scope

In the tokenizer loop of `rust/gprolog-native/src/syntax.rs`, a single new branch recognizes the byte pair `/*`. It counts nested openers and closers **iteratively**, advancing only the lexer byte offset until the depth returns to zero. An unclosed block returns a `SyntaxError` at the opening offset. The scanner runs under the existing 2,000,000-source-byte bound without a recursive stack. Slash tokens outside comments are still unsupported. Existing single-line `%` logic and quoted atoms are untouched; a quoted atom containing the literal characters `/* literal */` remains an atom, not a comment.

The nested-comment behavior is an explicit SWI syntax extension, not a universal ISO-language claim. [SWI's nested-comment documentation](https://www.swi-prolog.org/pldoc/man?section=nestedcomments) provides the external behavioral specification.

No changes were made to unification, search, cut handling, choicepoint ownership, term layouts, numeric semantics, memory management, indexing, CLI output or the rejected Gen19 engine.

## Matched, independent and metamorphic controls

The 12 frozen Generation 24 queries cover five true food preferences, two false preferences, and ordered enumeration of `likes`, `indian`, `mild`, `chinese` and `italian`. The long query returns nine distinct foods in the same source order in SWI and Rust. For every query:

1. SWI-Prolog executes **the untouched upstream file** and produces an ordered canonical reference.
2. The patched Rust binary executes **that same original file**, without preprocessing, with a fixed 32-solution / 100,000-step cap.
3. The patched Rust binary executes the separately comment-normalized file to test the parser representation identity.
4. Frozen released Gen18 executes only the normalized derivative, while it must still **reject the original** with the known offset and diagnostic.

**All 12 cases passed the three Rust comparisons to SWI.** The strict historical 264-case Rust CLI output/exit/stderr differential passed on both native ABIs. Default and feature-enabled Rust test suites ran on both; new known-answer unit tests cover ordinary/Pldoc/nested blocks, comments in query positions, `%` within a block, markers preserved in quoted atoms, unterminated outer/inner block detection and unsupported bare slash. The negative tests make an overpermissive lexer fail rather than appear successful.

The published source file and SWI are genuinely external witnesses. However, the source selection, feature patch, test design, output translation and promotion decision share project authorship. All evidence tags remain conditioned on this scope.

## Metric, representation and resource audit

This is a **semantic/compatibility** result, measured as ordered output vectors, status/stderr equality, source hash identity and parser acceptance/rejection. **No native runtime nanoseconds, resource counts or overall performance score are claimed.** SWI and Rust have different implementations and are not compared on elapsed time. Both frozen and patched Rust test the same finite programs and fixed limits. The patched lexer changes only whether block-comments are treated as whitespace; it does **not** prove every syntactic representation of equivalent Prolog text gives the same behavior.

The upstream original is now a directly executable test, unlike the Generation 24 comment-only derivative. This resolves one concrete interface obstruction, not all unsupported Prolog syntax. In particular, arithmetic, dynamic predicates, advanced Unicode lexical forms, constraints, tabling and rational trees are not tested or promoted here.

## Corrections and stop rule

The initial Generation 25 workflow [44370165971](https://github.com/jesusvilela/gprolog/actions/runs/44370165971) failed before running any test because its display name contained an unquoted YAML colon. The [correction ledger](RUST_GEN25_BLOCK_COMMENTS_CORRECTIONS.md) preserves that failure and the formatting-only fix. It is not a negative scientific result.

Source SHA verification, nested-block test variants, fixed limits and independent SWI oracle were frozen before the first successful execution. If a future real upstream source fails, preserve that negative; do not broaden parsing or change engine behavior by implication.

Raw initial completed [dual-ABI Generation 25 workflow 44370400905](https://github.com/jesusvilela/gprolog/actions/runs/44370400905): [ELF64 artifact 14457284534](https://github.com/jesusvilela/gprolog/actions/runs/44370400905/artifacts/14457284534) (12 live SWI cases and 264 Rust differential) and [i686 artifact 14457414222](https://github.com/jesusvilela/gprolog/actions/runs/44370400905/artifacts/14457414222) (264 strict Rust differential). GitHub Actions artifact retention is 30 days. The source program, parser tests, oracle runner and protocol remain in version control.

## Next bounded experiment and evidence map

**Next experiment:** select additional genuinely upstream-authored public-domain Prolog programs, group those accepted without adaptations versus unsupported and semantically divergent, and run a live SWI oracle on each supported program. Primary metric: complete coverage/status vector by syntax class, not an average speed. Controls: programs with no comments, nested blocks, quoted delimiter text and negative parse cases. Kill: any hidden source transformation, source-license ambiguity, an unexplained SWI/Rust mismatch or missing program. Stop: do not add an unrelated language feature or engine optimization to obtain a favorable percentage.

**Evidence:** P not asserted for universal lexer correctness; A for lexical byte/term boundaries and external comment specification; M for concrete parser acceptance, SWI comparison, Rust unit tests and 264-case historical parity; H for broader language conformity or time effects; S for future full corpus; R for retired Gen19 eager two-clause optimization and any claim that one feature fixes all upstream compatibility.
