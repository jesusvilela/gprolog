# Generation 14 correction ledger — eager index retired, lazy cache proposed

18 November 2026. This is an append-only performance interpretation correction to
[RUST_NATIVE_DISPATCH_PROTOCOL.md](RUST_NATIVE_DISPATCH_PROTOCOL.md). Do **not**
rewrite or delete the earlier eager-index implementation, workflow failure logs,
or the benchmark's first run. The first design was valid to test and failed its
intended **performance** objective.

## First experiment: eager index at `772bf625` (R for performance interpretation)

The initial implementation created a `HashMap<(String,usize),Vec<usize>>`
with one allocated string key for every distinct predicate signature at
the start of **every** `solve`, even for pure built-in goals.

Matched protocol: frozen Rust Generation 13 baseline
`dd6375e3fff21026b603c7944dd617ed9b391163`; same external
`bench_solve.rs` harness; each program parsed before samples; three
warmups and 20 solve-only nanosamples per implementation; Rust 1.85.1
release, same source/ABI, paired AB/BA blocks, `max_steps=200000`,
`max_solutions=1`, full answer-representation parity required. Process
RSS includes parsing and is not exclusively index memory.

First successful ELF64 data, [workflow run 44257464097](https://github.com/jesusvilela/gprolog/actions/runs/44257464097), before any correction:

| Workload | Gen13 median ns | eager Gen14 median ns | Effect |
| --- | ---: | ---: | --- |
| 10k unrelated heads + 96 target calls | 1,126,526.5 | 1,522,094.0 | candidate 35.1% slower |
| Same source + one target call | 11,567.5 | 1,460,030.0 | large regression |
| Same source + 96 `true` built-ins | 9,164.0 | 1,466,885.0 | severe needless work |
| One-clause program + 96 calls | 48,408.0 | 51,087.5 | candidate slower |

0/5 paired blocks showed candidate faster on all four ELF64 workloads.
These are runner observations, not universal Prolog benchmarks.
The first workflow attempt failed **before timing** because the external
benchmark was compiled with unwind while the release library uses
`panic=abort`. The harness compile was corrected in `772bf625`;
this is not an engine semantic failure.

**Decision:** retire the hypothesis that eager per-solve indexing speeds up
the primary sparse lookup workload. Retain semantic CI and complete
Rust-Rust parity; these never established runtime benefit.

## New prospective mechanism — lazily memoized signature lookup (H)

A narrower implementation creates an initially empty per-`solve`
`HashMap<(String,usize),Vec<usize>>`. Only on the first call of a
**particular** user-defined signature does it scan all source clauses
and cache **all** matching indices, including failed heads and duplicates.
Every later call to the same signature reads those indices without
rescanning. No index is constructed for a query containing only built-ins.

This is a **replacement** for the eager design's once-per-solve
global catalogue, and **amends** the previously frozen structural
requirement. One scan is now allowed per *distinct requested signature*
rather than exactly one global scan. It preserves the behavioral
invariants and retains source order and failed clause attempts.
The compiler, parser, trail, cut rules, term representation and
search-budget policy are unchanged.

## Prospective decision gates, stated before implementing

- **Prediction:** on both ELF64 and i686 ELF32, median solve-only time
  is lower for the `sparse_96` primary workload than pinned Generation 13.
  A single-lookup `single_1`, a built-in-only `builtin_96` and tiny
  program `tiny_96` remain reported as negative controls even when worse.
- **Primary metric:** per-ABI median of the 20 raw `solve()` time samples;
  report all paired-block outcomes and peak RSS separately, never a
  cross-ABI combined scalar.
- **Correctness kill condition:** any unexplained full CLI output,
  stderr/exit, error, generated-variable, cut, or step-budget mismatch.
- **Performance kill condition:** no improvement in `sparse_96` on
  either ABI retires the performance interpretation, even if all tests pass.
- **Stop condition:** no first-argument indexing, WAM term heap, or
  new ontology to rescue this result. If demand caching fails, keep the
  unindexed Generation 13 search baseline as the supported implementation.
- **Promotion rule:** report only measured sparse-signature lookup
  improvement, qualified by the controls, after exact-head dual-ABI
  matched runs, Rust and historical compiler CI, and Rust-only differential.

The initial eager-index performance hypothesis is **R**.
The lazy-cache proposal is **H** until the same matched controls execute.

## Post-correction measured disposition — 18 November 2026

The replacement **lazy demand cache** at source commit
`6e4157140f60bb1dd58abf6a05f9ac126731d98f` passed both ABI
matched benchmark jobs (workflow [44257730505](https://github.com/jesusvilela/gprolog/actions/runs/44257730505)).
The benchmark answered identically in all 5 paired blocks on each ABI.

| Workload | ELF64 Gen13 -> lazy Gen14 (ns) | i686 ELF32 Gen13 -> lazy Gen14 (ns) |
| --- | ---: | ---: |
| `sparse_96`: 10,000 other heads | 1,343,978 -> 76,202.5 (**-94.33%**) | 1,511,643 -> 103,092 (**-93.18%**) |
| `single_1`: one predicate call | 14,112 -> 14,213 (+0.72%) | 15,414 -> 15,654 (+1.56%) |
| `builtin_96`: 96 `true` goals | 8,873 -> 9,226.5 (+3.98%) | 11,977 -> 12,092.5 (+0.96%) |
| `tiny_96`: one-clause program | 58,982 -> 61,479.5 (+4.23%) | 80,640 -> 89,166 (**+10.57%**) |

In the primary sparse workload the candidate was faster in 5/5 paired
blocks for both ABIs. Program parsing, process startup and total elapsed
end-to-end user time are **excluded** from the reported primary metric.
Peak process RSS for that workload was 8,184/8,196 KiB (ELF64 Gen13/lazy)
and 5,128/5,088 KiB (i686); the small variations cannot be attributed
causally to the cache alone.

Untouched raw JSON artifacts: [ELF64 artifact 14407335286](https://github.com/jesusvilela/gprolog/actions/runs/44257730505/artifacts/14407335286)
and [i686 artifact 14406990977](https://github.com/jesusvilela/gprolog/actions/runs/44257730505/artifacts/14406990977).
Each contains 20 samples per variant per case, process RSS, program
SHA256, strict answer equality, controls and AB/BA order. Artifacts have
30-day retention; the benchmark script and the source fixtures remain
versioned and reproducible.

**Evidence tags:** eager-index speedup = **R** (retired). Lazy-cache
synthetic sparse performance = **M** (measured on these two runners).
Full solution-space semantics, ISO conformance, WAM and broad or
end-to-end speedup = **H / unestablished**. All authorship is
correlated: the frozen Generation 13 Rust implementation and
Generation 14 candidate share the project lineage. This is not an
independent outside reproduction.
