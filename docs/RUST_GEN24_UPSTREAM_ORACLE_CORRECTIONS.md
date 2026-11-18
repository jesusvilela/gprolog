# Generation 24 — correction ledger

**18 November 2026 — before final-head promotion.** The first successful raw external-oracle run [44367811617](https://github.com/jesusvilela/gprolog/actions/runs/44367811617) verified 12/12 SWI-Prolog reference answers and 264/264 historical comparisons. The untouched third-party upstream source failed the Rust parser at **byte 440** for an unsupported `/` character, as preregistered; the temporary derivative was produced by removing exactly **one 125-byte documentation block**. Neither frozen engine source was edited.

**Resource-cap correction:** the original `compare_swi.py` chose `max_solutions=max(1, len(SWI_answers)+2)` for each Rust CLI query. That is enough to check the observed small answer sequences but is an *oracle-dependent bound*, not the same independently fixed cap for every query. This conflicts with the protocol's resource-parity intention. Before accepting a final result, replace it with **32 solutions** for every case and retain **100,000 steps**. Add `validate_provenance.py` to verify both CLI command lines and raw outputs, and require a **fresh final-head rerun** with all controls. The earlier run is retained as initial evidence, not silently relabeled.

The frozen third-party upstream Git commit, source blob, license, 12 queries, solution order, independent SWI interpreter, source normalization rule, and comparison criteria were not changed. This correction tightens resource parity and cannot guarantee success by construction. A failure after the correction must be reported, not masked.

## Base-branch update and provenance-guard correction

**18 November 2026 — PR #23 merged while draft PR #24 was open.**
[Run 44368764941](https://github.com/jesusvilela/gprolog/actions/runs/44368764941)
failed during its *first Git provenance step*, before compiling either engine,
loading SWI or evaluating a query. The GitHub checkout was a synthetic merge
commit whose parents were the newly merged master `190ec6f9` and Gen24
PR head `c0a03954`. The previous guard wrongly asserted equality of
`HEAD^{tree}` and `PR_HEAD^{tree}`. A synthetic merge necessarily
includes legitimate unrelated master changes (the newly merged Gen23
files), so that equality does not hold even though every Gen24 file
is preserved exactly. This is a **provenance harness failure**, not a
negative semantic test result.

**Narrow correction:** If the checkout is a PR merge commit, verify
its second parent is the exact PR head and compare every authored
Gen24 file's Git blob between the synthetic merge and PR head. If
the checkout is the PR head itself, retain the original whole-tree
check. Continue to verify original upstream `likes.pl` and
`README.md` against their immutable external blob IDs. Preserve
the original failed run as evidence of the mistaken check.

No frozen query, original source, derivative, solution cap, reference
program, published source, baseline code or decision criterion is
changed. Do not count this job as a completed semantic experiment.
