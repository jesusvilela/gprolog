# Generation 24 — unmodified upstream Prolog source and independent executable semantic oracle
Frozen 18 November 2026, prior to any Generation 24 CI execution.

## Source and license authority

The source is **the exact third-party authored file**, not a paraphrase or reconstructed relation:
- Upstream repository: [SWI-Prolog/swipl-devel](https://github.com/SWI-Prolog/swipl-devel), immutable commit `111385b90852dade2b772d074cc55fefa20ee1a9`.
- Upstream path: `demo/likes.pl`, Git blob SHA-1 `88f3d2edcb0fb68c99b559676e5982b3780715f6`.
- Upstream source-license statement: `demo/README.md`, blob SHA-1 `fb3850a4dae3c29faea7907d9b3cd48d940fcfaa`, explicitly **all files in this demo directory are public domain**. The `likes.pl` file separately says “Copyright: Public domain.” Preserve both originals, attributed with source tree and commit.
- The original already includes external independent authorship (credits Essex University course demonstration), but we do not claim to know the original instructional author's name beyond the upstream record.

Both frozen raw files are copied byte-for-byte into `tests/rust_upstream_corpus/upstream/`. CI uses `git hash-object` on each original file to assert Git blob identity. Any normalization or adapted derivative **must be generated at runtime in a separate temporary path and never overwrite the raw source**.

## Exact frozen compatibility finding to test, not a silent repair

The Generation 18 Rust lexer skips line comments introduced by `%` but does **not** skip `/* ... */` block comments. The original public-domain `likes.pl` contains a `/** <examples> ... */` documentation block. The original is therefore **expected to fail parsing** with the current Rust CLI. We must record:
- direct original-file parser exit status and stderr;
- unchanged SHA and byte length;
- the unsupported syntax marker, not misclassify it as a Prolog logical semantic failure.

A separately labeled **comment-only normalization** removes exactly one balanced `/* ... */` documentation comment while preserving every clause and the rest of the bytes in order. No predicate editing, fact ordering, term modification, invented helper rules, rewriting of block comment content as executable code, or removal of other unsupported syntax is allowed. If the source has more than one block, unterminated block, nested block, an unexpected source hash, or the normalized source still fails, stop and log the negative instead of applying further repairs.

The exact statement is “Original externally authored program: unsupported by the current lexer; one comment-normalized derivative: possibly supported,” **not** “unmodified third-party benchmark passes.”

## Independent live semantic oracle

Run SWI-Prolog `swipl` (report exact version) against the **original unmodified** upstream file for all frozen queries. Use SWI's `findall/3` and `write_canonical/1` to obtain independently executed ordered bindings. The reference is externally implemented Prolog, not project-authored Python list algebra.

On the **separate** normalized derivative, run each query through frozen **released Gen18** `901c8b58c12fbe8b79f70b0118f951f3ed2fcf21` and **retired Gen19** `c09fff05d9b3dd43fb90014278e3a98d701d3640` CLI. Require exact ordered answers, stdout, stderr and exit-status parity with the SWI reference as translated into the Rust CLI's documented plain-atom output envelope. For each query record:
- query, variable (if any), solution count limit and steps limit;
- raw SWI output and executable version;
- Rust CLI per-version ordered output and status;
- source Git SHA and both original and normalized SHA256;
- whether result classification is supported/no-support/adapted;
- any negative event without suppressing further cases.

Queries are **frozen**:
1. `likes(sam,dahl).` (true);
2. `likes(sam,tandoori).` (true);
3. `likes(sam,chips).` (true);
4. `likes(sam,chop_suey).` (true);
5. `likes(sam,pizza).` (true);
6. `likes(sam,curry).` (false; Indian but not mild);
7. `likes(sam,unknown).` (false);
8. `likes(sam,Food).` (enumerate all solutions);
9. `indian(Food).` (enumerate);
10. `mild(Food).` (enumerate);
11. `chinese(Food).` (enumerate);
12. `italian(Food).` (enumerate).

Do not hand-enter SWI's solutions as the same reference oracle. Record independent `swipl` output; the only project-authored transformation is the *format conversion* from its canonical, plain-atom list to the Rust CLI display syntax. The output parser must reject unexpected compounds, escaped atoms, cyclic terms, strings or syntax not in the frozen plain-atom domain. The origin of SWI result data must remain explicit.

## Outcome vector and limits

**Primary metric:** 12-element vector of per-query ordered output concordance for both Rust versions versus live SWI, plus original-source Rust parse rejection. It is *not* a speed metric. The earlier Generation 23 direct-solve performance data are unaffected and cannot be pooled with this experiment.

- Exact primary pass: the full original file executes under SWI; unmodified file fails under the Rust lexer **for its one documentation block**; exactly one comment-only normalization occurs; both frozen Rust engines match all 12 SWI reference results.
- Kill: original upstream blob differs from pinned Git SHA; license unclear; normalization touches clauses; SWI unavailable or version undocumented; any actual Rust–SWI answer mismatch or unexpected error; missing ordered answer.
- Resource parity: same source clauses after comment normalization, same query and independent reference, pinned immutable Rust versions, fixed solution and step caps. SWI may have different internal optimizations; **do not compare wall times**.
- Error decomposition: separate *source/parser* incompatibility, *predicate semantics* mismatch, *operational resource limits*, *oracle infrastructure* error, and *reference formatting* mismatch.
- Evidence M is allowed only for exact bounded CLI/independent-oracle observations on this specific public-domain source, not ISO or GNU Prolog compliance generally.
- This is one externally maintained demonstration program, **not** a representative real-application benchmark or a distributional study.

## CI and merge decision

One native ELF64 Ubuntu runner with pinned Rust 1.85.1 and an explicitly versioned distro `swi-prolog-nox` package. Installation uses a finite timeout and logs dependencies; a missing reference is a **hard evidence failure**, not a test skip. No i686-SWI reference is claimed, though the earlier Gen23 i686 behavioral corpus remains a separate artifact.

Only the original public-domain upstream files, compatibility/semantic harness, frozen protocol, raw results, corrections and audit documentation may merge. No lexer fix or Rust engine optimization is authorized. A following task can propose native block-comment parser support in an entirely separate PR after an independently verified program requires it.

**Stop:** do not modify source clauses, relax query limits or introduce a general Prolog compatibility claim to rescue any mismatch. Record negative results for external review.

## P/A/M/H/S/R governance

P conditional: the independent answer reference is Prolog's `findall` semantics within the static finite program; A: plain-atom canonical output translation, one comment deletion preserves clause tokens; M after verified execution: source hash, Rust parser failure and SWI-vs-Rust ordered results; H: other programs, operational equivalence and performance; S: full external corpus; R: treating authored reconstruction in Gen23 as independently written benchmark or silently calling comment-stripped source unmodified.
