# Generation 27 — Seven licensed, unmodified Prolog programs across SWI and Scryer

**Date:** 18 November 2026. **Verdict:** On a **seven-item, purposively selected, byte-preserved cohort from two public Prolog projects**, independent system **SWI-Prolog 9.0.4** loads **four sources cleanly** (one familiar food-preference example and three *new* SWI core test modules). The merged Rust finite Horn-clause interpreter loads **only the familiar `likes.pl`** among those four; the three separately BSD-2-licensed SWI test modules are rejected at the predicate-indicator slash in a module declaration. The three Scryer sources are also Rust syntax-rejected, but the Ubuntu SWI-Prolog loader emits actual `ERROR:` diagnostics for unavailable libraries, so **they are not clean reference-load eligibility cases**. The prior `likes.pl` independent **12/12 ordered-answer** and **264/264 historical strict CLI** controls passed. No interpreter implementation was changed.

## Claim and evidence ledger

| Claim | Before | Witness | Result | After |
|---|---|---|---|---|
| Other externally authored files can load cleanly in SWI but still be rejected by Rust | H | Three exact SWI-Prolog BSD-2 core test modules, SWI 9.0.4 + Rust ELF64 | All three SWI clean, all three Rust reject | M, seven-source cohort |
| Nested-comment support alone makes Prolog modules executable in Rust | H | Gen24/Gen26 parser and exact slash offsets | False for these three clean modules | R as blanket interpretation |
| All original Scryer examples can be treated as clean SWI semantic references | H | Three original example files with SWI stderr | All three have `ERROR:` on missing libraries despite exit 0 | R for this reference environment |
| Rust unmodified `likes.pl` behavior remains correct for selected queries | M from Gen25/26 | Independent SWI, fresh 12-case original-source execution | 12/12 ordered answers match | M |
| Previously supported Rust queries preserve behavior | M from Gen26 | Frozen 264-case exact stdout/stderr/exit regression | 264/264 unchanged | M |
| An acceptance fraction from this selected cohort describes ISO, GNU or commercial Prolog coverage | H | No random sampling, incomplete language and mixed reference compatibility | Not established | H |

## Complete preregistered seven-program outcome vector

The census uses **raw, unmodified upstream sources**, a frozen Gen24 Rust baseline (`fb9e05ac`), frozen merged Gen26 Rust (`dbaf3af2`) with the Gen25 nested-comment parser, and the independently developed SWI-Prolog 9.0.4 runtime. SWI **clean load** means exit 0 with **both stdout and stderr empty**; exit 0 with `ERROR` diagnostics is not clean.

| Source | Frozen Gen24 Rust | Frozen Gen26 Rust | SWI-Prolog 9.0.4 | First rejected byte in Gen26 |
|---|---|---|---|---:|
| `swi/demo/likes.pl` | syntax rejection | **accepted, `true.\n`** | clean | — |
| `swi/tests/core_lang/test_list.pl` | syntax rejection | syntax rejection | **clean** | 1628, `/` |
| `swi/tests/core_lang/test_unify.pl` | syntax rejection | syntax rejection | **clean** | 1678, `/` |
| `swi/tests/core_lang/test_bags.pl` | syntax rejection | syntax rejection | **clean** | 1628, `/` |
| `scryer/src/examples/least_time.pl` | syntax rejection | syntax rejection | exit 0 **with ERROR and warnings** | 393, `/` |
| `scryer/src/examples/plres.pl` | syntax rejection | syntax rejection | exit 0 **with ERROR and warnings** | 1544, `-` |
| `scryer/src/examples/echo_server.pl` | syntax rejection | syntax rejection | exit 0 **with ERROR and warnings** | 35, `/` |

### Bounded counts — typed and not population rates

- Seven original source files and three original licence/provenance documents matched immutable Git blob SHA1 identities and source SHA256 checks.
- **SWI-clean: 4/7**, composed of one public-domain SWI demo and three individually BSD-2-licensed core test modules. **SWI process exit 0 with `ERROR:`: 3/7**, all Scryer examples.
- **Rust Gen24 accepted: 0/7; merged Gen26 accepted: 1/7**, `likes.pl` only.
- Within the **four SWI-clean** originals, **Rust accepted: 1/4**, rejected 3/4. This is a *conditional, small sample count*, not an unbiased acceptance probability.
- Of the six Rust source rejections, the first fatal byte is `/` for **five**, and `-` for **one**. An earliest unsupported token is **not** a proof that adding that token would enable the entire source.

The original exact source SHA256, Git SHA1, compiler/reference roles, sizes, per-file error and warning counts, source origin and licence are permanently recorded in [`gen27_source_census.csv`](../tests/rust_cross_origin_corpus/results/gen27_source_census.csv). Complete raw stdout/stderr/exit triples, all 12 SWI semantic query outputs, 264 historical comparisons and the ten upstream bytes-preserved files are in the first [GitHub Actions run 44391070625, raw artifact 14467771741](https://github.com/jesusvilela/gprolog/actions/runs/44391070625/artifacts/14467771741). Artifact retention is 30 days; the original sources, licence notices, source hashes and this summary remain in Git.

## Concrete compatibility obstruction (and what is *not* a cause)

The three newly examined SWI core test modules have full BSD-2 source headers and load without stderr under SWI-Prolog 9.0.4. Their first Rust syntax errors occur at the `/` in `test_list/0`, `test_unify/0` and `test_bags/0` **inside module declarations**, after skipping the initial long licence blocks. The parent (`:- module(...)`) requires a *module/declaration parser and semantics*, not merely another standalone slash token. Other directives, imports, plunit declarations and test goals remain beyond the demonstrated Rust subset. The byte-offset observation does not prove a module implementation would suffice to make all three files runnable.

The three Scryer-origin programmes are originally authored and legally archived under their [BSD-3-Clause root license](https://github.com/mthom/scryer-prolog/blob/47f2c4e7cf9232137e2d43c7190c5504eb1a0045/LICENSE), but their reference environment matters: SWI 9.0.4 reports `library(dcgs)`, `library(format)`, `library(sockets)` or `library(reif)` as unavailable depending on the program. **SWI process exit 0 did not mean clean loading.** These are interpreter-dialect/dependency failures, not a valid independent claim that the Prolog source is malformed or has incorrect logical semantics.

## Source rights, exact representation, and independence

**SWI originals:** frozen [upstream `111385b9`](https://github.com/SWI-Prolog/swipl-devel/tree/111385b90852dade2b772d074cc55fefa20ee1a9). `demo/likes.pl` and its archived `demo/README.md` are explicitly public-domain. The SWI test-suite `tests/COPYING` warns that **not all files in the suite are BSD-2**. For that reason we selected only `test_list.pl`, `test_unify.pl` and `test_bags.pl`, each with its **own full explicit BSD-2 redistribution terms**, left unmodified in its source header. We do not claim generic BSD rights for every SWI test.

**Scryer originals:** frozen [upstream `47f2c4e7`](https://github.com/mthom/scryer-prolog/tree/47f2c4e7cf9232137e2d43c7190c5504eb1a0045/src/examples), with unchanged root **BSD 3-Clause** license and source attributions. `plres.pl` also retains original author Markus Triska's public-domain note. No library, directive, comment, goal, clause or file ordering was edited to make source parse in Rust.

**Independent witness:** SWI-Prolog 9.0.4 is an implementation separate from Rust, and its loader examines Scryer-authored source under a distinct code base. The SWI-Prolog project also authored the SWI test files, so **origin independence is asymmetric**: SWI's own test fixtures and its executable are not independent source authors. Our corpus selection, loader classifiers, verification tests and report share project authorship. This is independent *software-path* evidence, **not** a separately authored research replication.

## Specification → live code → tests and resource parity

The requirement is exact **source-loading coverage**, not comprehensive Prolog semantics. The live path is `gprolog-rs <original.pl> 'true.' --max-solutions 1 --max-steps 100000` for each frozen Rust version, and `swipl -q -f none -s <original.pl> -g true -t halt`. Source hashes and permissions are checked before any engine execution. The Rust query is deliberately trivial: `accepted_and_true` means full program source parsing and one `true` goal completed, **not** that every predicate in the file is correct.

A separate 12-query original-source `likes.pl` SWI reference tests ordered solutions, including negative cases and nine-food enumeration, with Rust solution limit **32** and max steps **100000**. It passed all twelve independently executed output comparisons. A historical 264-case Gen24→Gen26 exact CLI comparison also passed. The known-answer suite attacks incorrect treatment of stderr-bearing SWI exits as successful, silently accepted `false.\n` as Rust success, and invalid licences/source hashes.

Both Rust engines are built feature-disabled with pinned Rust 1.85.1, exact ELF64, identical `true.` queries, solution limits and sources. SWI-Prolog is not compared on performance, memory, cycles or internal resource consumption. No time distribution, pooled score or causal optimization claim is promoted.

## Correction and negative result governance

No source replacement, test selection change, reference-answer-dependent cap, or measurement threshold adjustment was required on the first complete [run 44391070625](https://github.com/jesusvilela/gprolog/actions/runs/44391070625). Three Scryer diagnostic-bearing sources and three Rust-rejected but SWI-clean modules are **valid negative evidence** under the original protocol. The [correction ledger](RUST_GEN27_CROSS_PROJECT_SOURCE_CORRECTIONS.md) records the unchanged corpus and explicit reason none was excluded.

**Most damaging limitation:** All six additional sources fail Rust loading. And a clean SWI load does not establish the intended behavior of those sources' predicates. Thus this generation demonstrates *a broader genuine compatibility gap*, **not** added capability or complete semantic equivalence on new programs.

## Round-trip, next bounded experiment, and P/A/M/H/S/R

Original program provenance → exact source and licence snapshot → independent SWI and pinned Rust loader → complete seven-row typed observations → conditional source acceptance interpretation → original question: the round trip preserves original source bytes, exact error/stderr, and a clear **three-source SWI-clean yet Rust-rejected remainder**. It does not transport full program semantics or industrial population representativeness.

**Next bounded experiment:** choose **one deliberately minimal, independently licensed pure Prolog module**, with pinned source and external SWI semantics, as a new fixture; freeze its exact module/declaration and query requirements. Test whether module-aware loading truly makes the *entire original* executable while preserving the current 12 SWI `likes` cases and 264 regression suite. **Prediction:** module syntactic forms might be the first obstruction for SWI-clean examples, but slash-token acceptance alone will not suffice. **Primary metric:** original-source loader acceptance and ordered SWI outputs; **kill:** any hidden rewrite, SWI-vs-Rust solution mismatch, module namespace leakage, or old regression; **stop:** do not add arithmetic/CLP, WAM, GC, owners or unknown extensions just to increase a denominator.

**Evidence tags:** **P** none claimed for general source loader; **A** explicit source, license and diagnostic representation; **M** exact seven-case source cohort loader outcomes and 12-case independent original-source `likes` semantics; **H** general cross-project portability or future module feature effects; **S** broader multi-project semantic corpus; **R** uniform conformance rates from selected sources and prior Gen19 eager continuation policy.
