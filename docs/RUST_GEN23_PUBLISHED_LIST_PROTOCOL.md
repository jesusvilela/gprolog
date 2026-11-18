# Generation 23 — externally documented list relations, held-out from the prior two-clause stress program

**Pre-registration date:** 18 November 2026. **Scope:** diagnostic comparison only; no compiler or engine change. This generation is permitted to publish *negative* results. Do not optimize or choose another corpus after observing outcomes.

## Exact question and evidence baseline

Do the large Generation 19 eager-owned continuation regressions observed in synthetic repeated `target/1` calls transfer to ordinary list-processing programs whose *mathematical relations were chosen from independent public instructional/reference documentation*?

**Immutable engines:** released Gen18 source `901c8b58c12fbe8b79f70b0118f951f3ed2fcf21` and rejected Gen19 source `c09fff05d9b3dd43fb90014278e3a98d701d3640`. Generation 22's master `47f19aee79ff26fa9206977759aae3a309b17c4f` contains audit/CI only and retains the released Gen18 solver.

This is *not* a random sample of real production Prolog programs, nor an independently authored benchmark implementation. Selection of external task families happens before measurements, but minimal executable programs are **independently reconstructed here** from documented relations to stay within the current parser's Horn-clause subset. Do not mislabel them verbatim third-party program files or independent testing. The only genuine external witness is the original published relation/task specification.

**Documented program families and authorship:**
- Blackburn, Bos and Striegnitz, *Learn Prolog Now!*, chapter 6.1 [append](https://lpn.swi-prolog.org/lpnpage.php?pageid=lpn-htmlse24&pagetype=html), and chapter 6.2 [naive / accumulator reverse](https://lpn.swi-prolog.org/lpnpage.php?pageid=lpn-htmlse25&pagetype=html). The task contrasts structurally different list-reversal algorithms.
- SWI-Prolog publicly documented [append/3](https://www.swi-prolog.org/pldoc/man?predicate=append%2F3) and [list member, prefix and select relations](https://www.swi-prolog.org/pldoc/man?section=lists). These define the public behavior, not necessarily the same operational implementation.
- No claims about SWI-specific last-element determinism or predicate indexing: our reconstruction uses the classical two-clause Horn relations, which are not identical to optimized SWI library internals.

The exact source text and query for every cell is frozen in `tests/rust_external_corpus/fixtures.py` and must have recorded SHA256 before execution. The suite has **twelve external-relation workloads** plus two self-authored unchanged-path null controls, with one source/query/limit combination per case. Cases cover concat/splitting, failed concat, naive reverse, accumulator reverse, late membership, enumeration with duplicates and prefix generation. They were not selected using previous Gen18/Gen19 results.

## Independent correctness oracle

A separate, **Python standard-library list algebra** reference computes expected ordered CLI answers from list concatenation, reversal, ordered membership, prefix enumeration and single-element deletion, without using either Prolog implementation. All fourteen frozen expectations must be computed in the reference and match the actual CLI `stdout`, stderr and exit exactly for **both** immutable engines. Only valid finite, acyclic, ground input lists are considered. No general Prolog operational semantics or ISO proof is claimed.

For source programs requiring Prolog-only answer enumeration, the reference outputs the documented left-to-right depth-first order of the self-authored two-clause program. This order is an **assumption of this representation**; it is not a guarantee for every standard library implementation. The independent list algebra is not an external live Prolog oracle.

## Metrics / resource parity

**Native direct `solve()` latency, not CLI or parse time.** Use the same external Rust `tests/rust_choicepoint/bench_continuations.rs` harness linked against frozen, feature-disabled Rust 1.85.1 release libraries. For each ABI (ELF64 and true i686 ELF32) use five alternating AB/BA paired blocks, four timed nanosecond calls per variant/block after three warmups per invocation: **20 raw timed calls per version/case/ABI**. Complete ordered answer representation must agree across variants on every invocation; separately check full CLI stdout/stderr/exit against the Python oracle. Peak process RSS is recorded but is not a `solve()` allocation metric. Store exact source SHA256, query, repeat factor, limits, per-block order, every raw timestamp and external documented task link.

The existing **264-case frozen Rust strict CLI differential** is an invariant regression guard, not independent Prolog conformance. Both native ABIs must pass.

## Primary outcome and negative controls

This is an exploratory *transfer* test, not an optimization promotion benchmark. Do **not** make a gate guaranteeing that Gen19 is slower. For all twelve external-relation workloads report signed ratio `median(Gen19)/median(Gen18)` with values below, near or above one retained. The preregistered **primary effect** is the *full twelve-case vector* plus a signed block-win count per case, separately per ABI. The null hypothesis of no transfer is not discarded based on a post-hoc threshold. Report geometric mean descriptively only with full distributions and an explicit denominator, never as universal Prolog speed.

**Controls:** `single_fact_r8` and `builtin_true_r8` must produce exactly the expected `true.` and have uninstrumented median time ratios within **[0.8,1.2]**. The benchmark kill rule includes any >20% control difference in either direction, source identity mismatch, numerical sample invalidity, or CLI/oracle mismatch. Such a failed control is **data**; do not retune it or drop the cell to obtain a merge.

**Prediction (H):** recursive list programs that fail a first clause and carry a non-empty rest may show a measurable Gen19 penalty, but the extreme 8–11× factor from a repeated synthetic T2/R128 workload need not transfer. The prior syntax/reference corpus does not prove a numerical lower bound on performance. Report how many external cases show candidate slowdown with >=4/5 paired blocks and median >1, how many are near or faster, and any contrary/negative evidence.

**Stop:** no adaptive policy, new Term representation, indexing, WAM, GC, heap or compiler change. No experiment-specific micro-optimization. A future held-out third-party authored corpus needs its own source/compatibility/license audit.

## P/A/M/H/S/R and merge decision

- **P conditional:** reference Python algebra is correct on the finite lists it explicitly constructs; not a proof of Prolog semantics.
- **A:** the chosen classical Horn encodings correspond to documented list relations; transfer to SWI internals is not presumed.
- **M after execution only:** bounded native Rust two-ABI ratios and exact CLI/reference outputs for the fourteen fixtures.
- **H:** generalization to real application workloads or causal CPU-time attribution from Gen21/22 call-site observations.
- **S:** an independently maintained, licensed third-party benchmark corpus plus external Prolog execution witness.
- **R:** the failed Generation 19 two-clause owned representation; any claim its failure is universal or its opposite universally best.

Merge diagnostics, task provenance, sources, results and CI only after final-head checks, corrections and audit; do not change the Rust-native interpreter or reintroduce Gen19.
