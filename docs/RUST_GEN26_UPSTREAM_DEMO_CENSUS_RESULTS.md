# Generation 26 — Complete public-domain SWI-Prolog demo-directory compatibility census

**18 November 2026. Verdict (original complete run):** The exact `.pl` census of [SWI-Prolog/swipl-devel `demo/`](https://github.com/SWI-Prolog/swipl-devel/tree/111385b90852dade2b772d074cc55fefa20ee1a9/demo) at frozen upstream commit `111385b90852dade2b772d074cc55fefa20ee1a9` comprises **four original public-domain source files**, totaling 11,642 program bytes. All were tested **unmodified** against feature-disabled Rust Gen24 and Gen25 and against a live independently implemented SWI-Prolog 9.0.4 loader. **Rust Gen25 accepted one of four original files (`likes.pl`), up from none of four in Gen24; the other three remain parser-rejected.** Only `likes.pl` loaded in the SWI 9.0.4 process without diagnostic stderr. The other three returned process code zero but emitted `ERROR` diagnostics; they must **not** be called clean or fully successfully loaded. This is an exact *single directory* census, not a population estimate of language compatibility, validity or industrial workload relevance.

## Claim and evidence ledger

| Claim | Before | Primary witness | Result | After |
|---|---|---|---|---|
| Nested-comment support increases unmodified source acceptance in this directory | H | Exact upstream original bytes + Gen24/25 CLI | `likes.pl` changes from parser error to accepted; other 3 reject; **0/4 → 1/4** | M, one pinned directory |
| SWI loader exit 0 implies all source files loaded cleanly | H | SWI 9.0.4 raw exit/stderr per file | False. Three exit-zero cases include `ERROR:` lines | **R** |
| `colours.pl` is intended as runnable code | H | Original source comment says “This code does not run” | False; it is a syntax-highlighting demonstration | **R** |
| Gen25 preserves already-supported Rust behavior | H | 264 strict Gen24/Gen25 CLI tests, exact stdout/stderr/status | **264/264** identical on ELF64 | M, tested subset |
| Gen25 and independent SWI agree on original `likes.pl` semantics | M from Gen25 | New 12-query SWI original-source execution and Rust controls | **12/12** identical ordered results | M, repeated |
| The four-file census estimates ISO Prolog conformity or native performance | H | No representative sampling, no timing and three externally diagnostic files | Not established | H |

## Four-source original byte census and operational classification

The table reports **exact process observations** using the fixed load probe `gprolog-rs <source> true. --max-solutions 1 --max-steps 100000` and SWI `swipl -q -f none -s <source> -g true -t halt`. A Rust success means this single source parsed and the `true.` query succeeded; it does **not** establish correctness of arbitrary predicates in that file.

| Public-domain original | Bytes | Gen24 Rust | Merged Gen25 Rust | SWI-Prolog 9.0.4 loader |
|---|---:|---|---|---|
| `likes.pl` | 922 | syntax rejection at byte 440, `/` | **accepted; `true.`** | **clean load**, process exit 0 |
| `trace.pl` | 4,591 | syntax rejection byte 0, `/` | syntax rejection byte 3199, `+` | exit 0 **with syntax ERROR** at line 114 |
| `unicode.pl` | 3,939 | syntax rejection byte 626, UTF-8 `0xe2` | same rejection byte 626 | exit 0 **with syntax ERROR** at lines 43 and 73 |
| `colours.pl` | 2,190 | syntax rejection byte 0, `/` | syntax rejection byte 109, `/` in predicate indicator | exit 0 **with ERROR/WARNING diagnostics**; original says deliberately non-executable |

Under the corrected typed label, the external SWI load tally is **one `clean_load` and three `process_exit0_with_diagnostics`**. This label records operating-system exit and stderr simultaneously; it never treats an `ERROR` line as successful source semantics. No upstream source was silently omitted from the denominator. `colours.pl` is typed as an intentionally non-executable syntax-highlighting demonstration **on the authority of a comment in `colours.pl` itself**, not a misattributed statement in the README.

### Exact provenance

| Program | Immutable upstream Git blob SHA1 | Original SHA256 |
|---|---|---|
| `likes.pl` | `88f3d2edcb0fb68c99b559676e5982b3780715f6` | `8f83ce408a0885818969424564ca3e2a39d1921828018b066680f8f19651f42d` |
| `trace.pl` | `5dd10ee3d9176c0792afbf874c50844679b93659` | `e4cfe14c4ae0475349849165c448bad134053e167a58d285592ad55e2012070f` |
| `unicode.pl` | `c7132cc2cee914b6fc132cdd4f22e25010bd6e36` | `e292cbdddaeba2f6f7e2ad892fd5dae6cfb2c34d064d4d322b2a10d9fd6ce11b` |
| `colours.pl` | `52391491930d72df055298b28a7d9487847de140` | `cc826905682bc6782c3cbe1a4ea83987776203eb04369f0cf0517b195c7a38dd` |

The pinned [upstream README](https://github.com/SWI-Prolog/swipl-devel/blob/111385b90852dade2b772d074cc55fefa20ee1a9/demo/README.md), Git blob `fb3850a4dae3c29faea7907d9b3cd48d940fcfaa`, states that all demo files are public domain. Exactly those four `.pl` originals and the README are versioned byte for byte in `tests/rust_demo_coverage/upstream/`. The source pin is upstream SHA-1 and is not the SHA256 hash, which is recorded separately. Entire `.pl` corpus size: 11,642 bytes.

## Most damaging obstruction and source-interpretation constraints

An external-reference process returning **0** does **not** establish it parsed or loaded all its input, especially when stderr contains explicit `ERROR:` lines. Source versions are also not matched across the upstream `2026-11-18` commit and the Ubuntu package **SWI-Prolog 9.0.4**: a modern Unicode demonstration may use notation the older reference does not accept. The three SWI diagnostic-bearing examples cannot therefore establish *Rust-specific semantic disagreement*. `colours.pl` is explicitly intentionally non-executable; counting it as a normal required successful program would be misleading.

By contrast, the Rust parser negative offsets identify **the earliest rejected byte** in the complete source, not every unsupported feature. At byte 3199 `trace.pl` reaches a `+` in `Distance is Step+Rest`, which is beyond the current finite Horn subset; `unicode.pl` reaches a non-ASCII operator byte; `colours.pl` reaches a predicate-indicator slash in a module-export list. The source bodies may contain further unsupported syntax. **Do not infer that adding a single new token would make these entire programs runnable.**

## Specification → implementation → test and resource parity

The preregistered object is four independent original third-party text files, not project-generated reconstructions. The implementation runs the exact same source files unmodified through two separately compiled Rust interpreter versions, with identical `true.` probes and the same source cap/step settings. The external SWI loader is separately developed; it uses its own source-loading semantics, and its stdout/stderr/exit are retained in full. The source note about `colours.pl` comes from that exact original source and is preserved with the file's upstream blob.

A separately executed **12-case live SWI semantic oracle** on the unmodified `likes.pl` supplies ordered Prolog answers and three Rust representation controls: new Rust on original, new Rust on Gen24's comment-only derivative and frozen released Gen18 on the derivative. All twelve cases passed; any evidence about the other three files is **load-level only**. The previous 264-case Gen24-versus-Gen25 strict CLI differential also passed. No hardware-cycle, source runtime, memory-use or WAM benchmarks were performed here.

No per-file score is clipped, missing, source-transformed or discarded; the interpretation is typed by interpreter and result domain. The four rows cannot be averaged with ELF32 results or synthetic time samples from Generations 19–23.

## Corrections and independent-witness status

The first [run 44379688202](https://github.com/jesusvilela/gprolog/actions/runs/44379688202) stopped before any scientific probe because the project-authored self-test looked for the `colours.pl` nonexecutable note in README rather than `colours.pl` itself. The [correction ledger](RUST_GEN26_UPSTREAM_DEMO_CENSUS_CORRECTIONS.md) documents the fixed source of authority with unchanged upstream blobs.

The [first complete run 44379921375](https://github.com/jesusvilela/gprolog/actions/runs/44379921375) passed all four source identity checks, the 12-case SWI oracle, the four-file Rust/SWI load census and the historical 264-case strict Rust differential. [Raw artifact 14462258854](https://github.com/jesusvilela/gprolog/actions/runs/44379921375/artifacts/14462258854) retains full original and observed byte/diagnostic information. The analysis subsequently renamed `loaded_with_diagnostics` to the more precise `process_exit0_with_diagnostics` because all three SWI diagnostic-bearing files include **`ERROR:` lines despite process exit 0**. This was a correction of *reporting representation after observing data*, explicitly not a preregistered discovery; the original artifact remains unchanged.

The SWI interpreter and its third-party authored sources are independent witnesses for the observed loader behavior; SWI supplies an **independent semantic witness only for `likes.pl`**. The census design, code, interpretation and audit are project-authored, so there is no independent experimental researcher, externally validated compliance score or unbiased population sample.

## Honest continuation

**Next bounded task:** use this exact source-backed obstruction inventory to isolate a *single* independently documented next syntax feature, such as operator-token handling, and ask if adding it truly increases complete, unmodified upstream-source acceptance—not whether it fixes the earliest byte error. Preserve other unsupported features and external SWI version mismatches. Freeze target program(s), current first-failure offsets, minimal syntax change, independent tests and kill conditions before implementing. **Kill** on any formerly supported semantic regression, unintended source adaptation or unverifiable external reference. **Stop** before expanding into arithmetic execution, module systems, WAM, GC or search heuristics merely to improve this four-file acceptance count.

**P/A/M/H/S/R:** P not asserted for language conformance; A for source encoding and process-diagnostic interpretation; M for the four-row raw census, 12-case SWI positive reference and 264 historical outputs after final-head replay; H for broader feature lift generalization and semantic correctness beyond `likes.pl`; S for separately licensed multi-project corpora; R for equating SWI exit code 0 with a clean source load or equating directory acceptance with an ISO compliance percentage.
