# Generation 24 — Genuine upstream Prolog source and independent SWI reference

**Research verdict (initial run, final-head confirmation required):** Unlike Generation 23's project-reconstructed list relations, this study uses an **unaltered upstream-authored source file** from SWI-Prolog's public-domain demo directory. The original `demo/likes.pl` cannot be parsed by the released Rust lexer, solely because the file contains a documentation block in `/* ... */` notation. Both frozen Rust versions reject the original at **byte 440** (unsupported token `0x2f`). After removing exactly that one documentation block into a separately labeled temporary derivative, the interpreter reproduces **12/12 independently executed SWI-Prolog 9.0.4 ordered-query results** in both Gen18 and retired Gen19. The 264-case historical Rust differential also passes. This is evidence about one externally authored program under explicit comment-only normalization—not a claim of unmodified source compatibility or general ISO Prolog conformance.

## Claim and evidence ledger

| Claim | Before | Artifact | Result | After |
|---|---|---|---|---|
| Untouched upstream likes.pl is directly accepted by the native Rust parser | H | Exact original bytes, both Rust stderr/exit | **False**: exit 2, syntax byte 440, unsupported '/' in Pldoc block | R |
| One documentation-comment deletion preserves clause behavior on this program | H/A | Original SWI-Prolog execution vs two Rust CLIs on separate normalized derivative | **12/12 ordered matches per engine** | M, conditional on one-file translation |
| Tests now rely on independent Prolog executable, not just Python algebra | H | Live **SWI-Prolog 9.0.4** on the original upstream source | All 12 canonical reference outputs captured | M |
| This establishes general GNU/ISO Prolog semantics or performance | H | Single educational program, no timing measurements | **Not established** | H |
| Gen19's eager T2 policy should be reinstated | R | Previous generations' measured regression | No new performance evidence | R |

## Identity, public-domain rights, and exact transformation

Upstream commit [`111385b9`](https://github.com/SWI-Prolog/swipl-devel/commit/111385b90852dade2b772d074cc55fefa20ee1a9): [`demo/likes.pl`](https://github.com/SWI-Prolog/swipl-devel/blob/111385b90852dade2b772d074cc55fefa20ee1a9/demo/likes.pl) has Git blob SHA1 `88f3d2edcb0fb68c99b559676e5982b3780715f6`; [`demo/README.md`](https://github.com/SWI-Prolog/swipl-devel/blob/111385b90852dade2b772d074cc55fefa20ee1a9/demo/README.md) has blob `fb3850a4dae3c29faea7907d9b3cd48d940fcfaa` and says all demo files are public domain. Original source also says “Copyright: Public domain.” Both originals are stored byte-for-byte in `tests/rust_upstream_corpus/upstream/`.

| Representation | Length | SHA256 |
|---|---:|---|
| Original untouched upstream program | 922 bytes | `8f83ce408a0885818969424564ca3e2a39d1921828018b066680f8f19651f42d` |
| Comment-normalized temporary derivative | 797 bytes | `95e2f114becb51036b9fb6d2c1a99f661e1ba3035c4ee26a0d0f6f5075ced21a` |
| Removed documentation block only | 125 bytes | `8ada062219f689bca76a89e92a385280b9fdd64da5f7e5b2ae82b7c1ae2ef6a4` |

The original was **never overwritten**. The normalization refuses multiple, nested or unexpected blocks. The comparison's conditional assumption is that deleting a *comment* does not change the operative Prolog clauses.

## Exact independent semantic observations

SWI-Prolog 9.0.4 evaluated all 12 queries on **the original program**, using `findall/3` and `write_canonical/1`. The reference output is transformed into the native Rust CLI's bounded plain-atom display without using any Rust result to construct the oracle.

| Query group | Reference outcome | Both Rust versions on derivative |
|---|---|---|
| Five positive ground likes (dahl, tandoori, chips, chop_suey, pizza) | one `ok` for each | match |
| Two negative ground likes (curry, unknown) | empty list of solutions | match |
| `likes(sam,Food)` | dahl, tandoori, kurma, chow_mein, chop_suey, sweet_and_sour, pizza, spaghetti, chips | match, same order |
| `indian(Food)` | curry, dahl, tandoori, kurma | match, same order |
| `mild(Food)` | dahl, tandoori, kurma | match, same order |
| `chinese(Food)` | chow_mein, chop_suey, sweet_and_sour | match, same order |
| `italian(Food)` | pizza, spaghetti | match, same order |

The negative `likes(sam,curry)` is particularly useful: it exercises a first clause's failed mildness test despite curry satisfying the Indian predicate. The positive `chips` fact and Chinese/Italian branches exercise alternatives and backtracking. **These are not external benchmark performance measurements.**

## Load-bearing limitation and implementation drift

The exact upstream `likes.pl` file contains `/** <examples>...` Pldoc. The current native Rust tokenizer recognizes `%` line comments but does not tokenize `/* ... */`. The first original-file failing byte is therefore a **parser representation boundary**, not a contradiction of the logical meaning of the file. A successful comment-normalized derivative must never be elevated to a claim of unmodified upstream compatibility. The original external Prolog program is not an independently authored performance corpus; it is one public-domain educational example.

The implementation initially selected each Rust solution cap using the SWI output count. The [append-only correction](RUST_GEN24_UPSTREAM_ORACLE_CORRECTIONS.md) replaces this with the **fixed cap 32** across all queries to preserve stronger parameter parity, independently checked in a fresh CI run. Original measurements remain unchanged in the first artifact.

## Tests, controls and resource parity

- Exact source and license Git SHA1; original raw/normalized SHA256, removal position and byte count.
- Unexpected original-file success is a failure of the frozen compatibility prediction. Both engines instead returned exit 2, no stdout, with the same syntax error.
- Live externally implemented SWI semantics vs separately compiled frozen Gen18 and rejected Gen19 CLIs; canonical flat plain-atom parsing rejects non-domain terms, compounds and malformed outputs.
- Positive, negative, full enumeration and internal fact-alternative controls. 12 cases per Rust variant with complete stdout/stderr/exit equality.
- Historical 264-case same-project Rust CLI differential remains a **correlated regression check**, not a second independent semantic oracle.
- ELF64 only for this source; pinned Rust 1.85.1 and SWI-Prolog 9.0.4. No benchmark times, heterogeneous efficiency claims, memory-speed comparisons or i686 extrapolations.
- Project-author-defined queries and output translator remain correlated; independent implementation of SWI and third-party authorship of upstream program provide distinct, substantive witnesses for the **tested semantic subset**, not an independent entire study.

## Correction governance and bounded continuation

**P/A:** One comment deletion is a conditional semantic no-op for this exact source; the one-file byte comparison is witnessed, not a general Prolog comment grammar proof. **M:** Original lexer error, SWI reference and 12 ordered matches after final-head fixed-cap test. **H:** broader Prolog source compatibility, non-ground algebra, dynamic features, arbitrary comment syntax, general performance. **S:** multi-source independently authored corpus and formalized source-type coverage. **R:** calling the normalized derivative unmodified, or claiming Gen23's program encodings were third-party-authored.

**Next bounded experiment:** inspect additional **unmodified** public-domain SWI demo files, split parser-supported vs unsupported by syntax, and compare only strictly compatible original bytes against a live SWI witness without source preprocessing. If none are supported, record the coverage failure, then separately propose a well-scoped block-comment lexer patch with independent regression tests. Kill on hidden transformation, unsupported feature suppression, or any semantic mismatch. Stop without WAM/GC/ownership heuristic changes. A genuine unmodified source acceptance rate is the next typed evidence, not a universal correctness percentage.
