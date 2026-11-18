# Generation 27 — Licensed, cross-project, unmodified Prolog source compatibility

**Frozen 18 November 2026 before any Generation 27 CI execution.**

## Question, sample, and permission

Does the merged Rust-native Gen25 parser accept any **additional unmodified, externally authored source program that loads cleanly in SWI-Prolog**, beyond its known `likes.pl` positive control? Independently, which concrete syntax boundaries separate Rust parsing from third-party source loading?

A **fixed seven-file purposive cohort**, not a random population sample:

| ID | Upstream project / path | Original Git blob SHA1 | Rights basis |
|---|---|---|---|
| `swi_likes` | SWI-Prolog/swipl-devel `demo/likes.pl` | `88f3d2edcb0fb68c99b559676e5982b3780715f6` | public-domain `demo/README.md` |
| `swi_test_list` | SWI-Prolog/swipl-devel `tests/core_lang/test_list.pl` | `2d2c0efb0e087f7ba3efa2f327d34c0acf352f2f` | explicit BSD-2 terms in source |
| `swi_test_unify` | SWI-Prolog/swipl-devel `tests/core_lang/test_unify.pl` | `24a3ddcbe02f8e54bedfbab6df887eed1cde170f` | explicit BSD-2 terms in source |
| `swi_test_bags` | SWI-Prolog/swipl-devel `tests/core_lang/test_bags.pl` | `a79eaa47096310207453adf98d3c6cd0c8a93cca` | explicit BSD-2 terms in source |
| `scryer_least_time` | mthom/scryer-prolog `src/examples/least_time.pl` | `2b599b6028fb9712c830e1dc5a11e0e2947b2374` | Scryer BSD-3-Clause root LICENSE; original Mark Thom credit |
| `scryer_plres` | mthom/scryer-prolog `src/examples/plres.pl` | `9bc2931bed606280c86e680410f7def39768e4ef` | Scryer BSD-3-Clause root LICENSE; original Markus Triska public-domain attribution |
| `scryer_echo_server` | mthom/scryer-prolog `src/examples/echo_server.pl` | `4543e60dae09b0435ec5babd092cbb1df5ed5faa` | Scryer BSD-3-Clause root LICENSE |

Commit pins:
- SWI source commit `111385b90852dade2b772d074cc55fefa20ee1a9`. Licence/source authorities: `demo/README.md` Git blob `fb3850a4dae3c29faea7907d9b3cd48d940fcfaa`, `tests/COPYING` Git blob `22bde7dfaceafad0fb8c58cc629c0090cc91c161`, plus BSD-2 source headers on **each** of three selected test files. **Do not assume every file in SWI tests is BSD; some are GPL; the three selected files each have their own explicit BSD terms.**
- Scryer source commit `47f2c4e7cf9232137e2d43c7190c5504eb1a0045`, `LICENSE` Git blob `c6b5e60894896b32bd9a90404fbe6bf8fc023e1f`, BSD 3-Clause.

All seven original program files and three original rights documents are copied **byte for byte**, retaining upstream credit and conditions. No preprocessing, comment removal, module-directive rewriting, executable snippets fabricated from the originals, inferred licence transfer, or changed source byte accepted. Source SHA256 and Git blob SHA1 are both recorded at execution. If any copyright, source blob or licence check fails, **kill the run before compiling**.

This selection is **intentionally heterogeneous**, not an unbiased sample: three SWI plunit modules, three Scryer examples (attributed-variable/constraint, resolution, sockets/IO) and a proven positive SWI demo. Clean-loading status is a **post-execution observed filter**, with the complete seven-record denominator preserved. Never choose replacement programs or exclude reference-negative sources after seeing the outcomes.

## Frozen source compatibility observations

Freeze immutable Rust candidate at **Gen26 merged `dbaf3af2b417893fcb636f196507aaaab905c286`** (no engine code changes). Historical parser baseline at **Gen24 `fb9e05acd87e3fe71052e83ef38f26b9c12701d3`**; Gen25 introduced nested comments. Build both as release feature-disabled binaries using Rust 1.85.1 and actual ELF64.

For **each exact original source**:
- `swipl -q -f none -s ORIGINAL.pl -g true -t halt`; report SWI version and raw `exit/stdout/stderr`. Clean = `exit=0` and **both** stdout/stderr empty. Exit-zero with any stdout or stderr is `process_exit0_with_output_or_diagnostics`, never automatically accepted/clean. Nonzero is `failed_load`. Record `ERROR:` and `Warning:` independently in stderr and do not suppress them. Treat load as a *syntactic/operational* witness only, **not** a semantic oracle for unspecified predicates.
- `gprolog-rs ORIGINAL.pl 'true.' --max-solutions 1 --max-steps 100000` with Gen24 and frozen Gen26. `accepted_and_true` iff exact `(exit=0,stdout='true.\\n',stderr='')`; `syntax_rejection` iff exit=2 and stderr contains `syntax at byte`; any other result is `runtime_or_other_failure`. Preserve exact first error byte, without interpreting it as the only unsupported feature.
- Never infer SWI syntax compatibility from a Rust failure, or claim `SWI clean` implies the file's predicates satisfy their intended behavior. For a program that SWI loads clean but Rust rejects, explicitly record the gap.

**Independent semantic positive:** `likes.pl` alone has the 12 frozen [Gen25 independent SWI reference](../RUST_GEN25_BLOCK_COMMENTS_RESULTS.md) queries. Re-execute SWI on the untouched original and the identical frozen Rust candidate on that original with fixed 32 solutions / 100000 steps, requiring the same ordered stdout/stderr/status. This is a real external program + separately implemented Prolog oracle, **not** an independent authorship of our experiment. The `likes.pl` original SHA must be identical to the already archived Gen26 positive control.

**Historical negative controls:** 264 strict previously supported Rust CLI cases, comparing immutable Gen24 to frozen Gen26 on the same inputs and ABI; record all. Unchanged source and no interpreter modifications are hard invariants. No WAM, heap, GC, ownership, indexing, direct solve nanoseconds or throughput data are part of this experiment.

## Decision, metrics and stop rules

**Primary metric:** the typed **seven-file** source/origin/license SHA, source sizes, SWI loader triplets with diagnostic severity, Gen24 and Gen26 Rust loader triplets, all raw statuses, and counts for the **predeclared SWI-clean subset** as well as all seven files. This is not a general ISO/SWI compatibility percentage and not a benchmark of speed. Print the actual clean subset and rejected records; do not hide non-clean SWI sources or treat their Rust errors as conformance violations.

**Prediction (H):** `likes.pl` remains accepted by merged Rust and yields 12 independent SWI answers; other third-party sources containing `:- module`, `:- use_module`, attribute goals, DCG, or sockets may fail parsing or loading. No exact other-file acceptance/failure rates or SWI diagnostic-free status were preregistered.

**Kill:** any changed upstream blob/rights notice, missing reference version, unexpected positive-control `likes.pl` error or answer drift, 264-case historical mismatch, silently normalized source, malformed tool output, or intentionally non-independent reference mislabeled as independent validation. A clean-loading third-party source rejected by Rust is a **measured negative**, *not* a CI failure or warrant to widen parser syntax inside this experiment.

**Stop:** no new language implementation feature in this census; no retries with modified original files; no post-hoc re-selection; no aggregate accept/7 promoted to industry or ISO language compatibility. If no new clean-and-Rust-accepted program appears, preserve that negative result. A separate source-backed feature (e.g. module declarations) requires its own preregistered PR and semantic/historical controls.

**Promotion:** M for exact bounded seven-source outcomes and the original `likes.pl` 12-query semantic control after fresh final-head CI; H remains on unseen sources, external generality and full predicates' correctness. P/A/M/H/S/R: **P** not asserted for general Prolog syntax; **A** for source/lexer status and loader semantics; **M** for raw externally sourced observations; **H** for wider multi-project transfer; **S** future supported subset conformance; **R** retired Gen19 ownership acceleration and any global compliance scalar inferred from these data.

### Source provenance, scope and independent witnessing

SWI is an independent runtime for Scryer-origin sources but shares organizational origin with SWI test-source authors, so **SWI-as-witness is differently independent for different sources**. Programme selection, classification code, unit tests, audit and outcome interpretation are project-authored. No independently authored full experiment is claimed.

This is a *seven-item purposive cross-project census*. Unlike Gen26's full four-file directory census, these seven filenames are explicitly chosen, not complete directories and not a random sample. All original selected files must appear in both repository and raw CI artifacts even when an interpreter fails to load them.
