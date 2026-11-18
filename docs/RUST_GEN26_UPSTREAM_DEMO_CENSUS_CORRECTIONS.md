# Generation 26 — correction ledger

**18 November 2026 — source attribution correction before corpus execution.**
The first [Gen26 run 44379688202](https://github.com/jesusvilela/gprolog/actions/runs/44379688202) was stopped by the positive/negative classification self-test, before installing SWI or compiling the Rust engines. Our provenance checker erroneously expected the phrase **“This code does not run”** in the upstream `demo/README.md` when the phrase actually occurs in a source comment inside `demo/colours.pl`. The README introduces the file as a syntax highlighting demonstration but does not itself explicitly say it is non-executable.

The correction moves the marker assertion to the exact, byte-preserved original `colours.pl`, while continuing to verify the README's independently stated public-domain license and all original Git blob SHA-1 IDs. The complete **four-program corpus, upstream pin, unmodified source bytes, CLI probes, expected independent version, twelve `likes.pl` semantic control queries, reference checks and acceptance/kill boundaries have not changed**. This is a self-authored provenance-test error, **not** evidence that SWI or Rust disagrees on any source program. Retain the failed first run and do not count it as a scientific result.

The `colours.pl` entry remains typed as **intentionally non-executable under upstream source documentation** rather than an ordinary runnable source failing conformance; its observed Rust/SWI loader outputs will nevertheless remain in the full original-source census.
