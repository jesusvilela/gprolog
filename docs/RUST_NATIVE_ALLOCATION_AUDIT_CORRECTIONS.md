# Generation 20 — correction ledger

## 18 November 2026: initial diagnostic CI was not an allocation result

The first diagnostic [workflow run 44294857980](https://github.com/jesusvilela/gprolog/actions/runs/44294857980)
reached the release-library selection step on ELF64 only to fail with
`Expected exactly one Rust feature-enabled release rlib`. Existing
Rust unit and profile integration tests had succeeded; no comparative
allocation samples had yet been collected.

**Build-harness confound:** the test step and the external diagnostic
library step reused the same Cargo target directory. Different
compilation invocations can leave multiple hashed `.rlib` outputs
there; alternatively a missing output could trigger the same broad
guard. The logged first failure did not print the matched file count,
so the exact cardinality is not established from that run alone.
This ambiguity is retained rather than calling it a solver bug.

**Correction, without modifying either immutable interpreter:**
run tests with `/tmp/alloc-gen{18,19}-tests-target` and build each
feature-enabled release library in a separate
`/tmp/alloc-gen{18,19}-target`; print the found library paths before
asserting there is exactly one. This prevents test artifacts from
being misidentified as benchmark-library input. The fixed Gen18
and Gen19 source SHAs, probe, problem grid, predicted counters,
falsification gates and first-run record remain unchanged.

Evidence: failing CI = **M** for a harness failure, not for allocator
requests. Causal source-count and allocation claims remain **H**
until the new exact-head dual-ABI results exist. No benchmark gate
is relaxed.
