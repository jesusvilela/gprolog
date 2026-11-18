# Generation 26 — correction ledger

**18 November 2026 — source attribution correction before corpus execution.**
The first [Gen26 run 44379688202](https://github.com/jesusvilela/gprolog/actions/runs/44379688202) was stopped by the positive/negative classification self-test, before installing SWI or compiling the Rust engines. Our provenance checker erroneously expected the phrase **“This code does not run”** in the upstream `demo/README.md` when the phrase actually occurs in a source comment inside `demo/colours.pl`. The README introduces the file as a syntax highlighting demonstration but does not itself explicitly say it is non-executable.

The correction moves the marker assertion to the exact, byte-preserved original `colours.pl`, while continuing to verify the README's independently stated public-domain license and all original Git blob SHA-1 IDs. The complete **four-program corpus, upstream pin, unmodified source bytes, CLI probes, expected independent version, twelve `likes.pl` semantic control queries, reference checks and acceptance/kill boundaries have not changed**. This is a self-authored provenance-test error, **not** evidence that SWI or Rust disagrees on any source program. Retain the failed first run and do not count it as a scientific result.

The `colours.pl` entry remains typed as **intentionally non-executable under upstream source documentation** rather than an ordinary runnable source failing conformance; its observed Rust/SWI loader outputs will nevertheless remain in the full original-source census.

## Exit-zero with ERROR diagnostics (after first complete source census)

**18 November 2026 — representational correction, not source or query modification.**
The [first complete successful run 44379921375](https://github.com/jesusvilela/gprolog/actions/runs/44379921375)
captured all four sources, 12/12 external SWI ordered likes results and 264/264 historical Rust cases. The raw SWI-Prolog 9.0.4 loader returned **exit code 0** for all four sources, but `trace.pl`, `unicode.pl`, and intentionally non-executable `colours.pl` emitted **ERROR** diagnostics to stderr. The initial label `loaded_with_diagnostics` risked incorrectly implying successful source parsing despite errors.

Rename this **reporting-only** category to `process_exit0_with_diagnostics` and explicitly preserve the Boolean `stderr_has_error_diagnostic`. The actual source probe command, raw exit codes, original stderr, source blob hashes, semantic oracle, test inputs, parser behavior, four-file denominator and positive-control gates are unchanged. The first complete raw artifact [14462258854](https://github.com/jesusvilela/gprolog/actions/runs/44379921375/artifacts/14462258854) remains immutable. This is a **post-observation interpretation correction** and is not a preregistered discovery.

After the correction a future final-head run is required before merging. Report the three diagnostic-bearing SWI exit-zero executions as **not clean loads**. Do not infer that every individual Prolog clause was successfully loaded.
