# Collision-resistance gate — preregistered before CI

## Exact question
Can the new static float first-argument switch silently confuse two numerically
distinct binary64 keys, lose source-order answers for duplicated heads, or
mis-handle an unsuccessful lookup after a linear-probing wraparound?

This is an adversarial *correctness* gate, not a benchmark or speedup claim.
Existing PR #2 may remain draft, but a candidate wrong answer blocks promotion
regardless of prior benchmark results.

## Frozen construction
The table allocator uses a capacity of `n + 1` for `n` distinct float keys.
The test creates exactly **17 distinct float keys**, hence capacity **18**.
Every key must hash to the final initial bucket (slot **17**) under both
32-bit and 64-bit C `unsigned long` arithmetic on little-endian Linux.
A further absent key must have that same home bucket.

Each key is an exact dyadic decimal, of the form `±integer.125`, so there
is no decimal-rounding ambiguity between the Python oracle and GNU Prolog.
No non-finite literals enter the fixture. The generator reconstructs the
runtime's byte-wise hash only to *choose the collision keys*; it asserts the
slot number for every selected key on both ABI widths. This is **not**
independent proof of the hash algorithm.

A duplicate clause for one existing key is inserted at a seed-dependent
source position, without increasing the table's distinct-key count.
Three deterministic permutations change insertion, lookup and duplicate
answer order while preserving collision pressure.

## Independent semantic oracle
Separately from hash generation, a source-order Python model computes
expected answer lists using ordinary numeric equality of binary64 values.
The oracle never uses the hash value, table placement, or the candidate
implementation. Test queries include all 17 hits, a second hit on the
duplicated key, a missing *same-home-bucket* float, a missing other-bucket
float, integer and atom negative controls, and unbound-first-argument
enumeration of all clauses.

Each fixture runs through four paths: fixed historical compiler
`12b4284378a59098b9004fe2b454ad9c19536370` and candidate branch,
both **native** and **consulted**. The candidate must actually emit
`switch_on_term_flt/6` and exactly one `switch_on_float/1` table containing
17 distinct numeric keys. The baseline must not emit candidate-only WAM.

The same script is used in x86-64 and strict ELF32 multilib workflows,
checking the actual `gprolog` executable header. Raw JSON is retained as
a 30-day CI artifact.

## Decision
**Pass:** every expected ordered result is byte-identical for all four
compiler/execution paths and all three permutations on both ABIs; the
collision construction and WAM structure assertions also pass.

**Kill condition:** any wrong, missing or extra answer; unexpected order;
timeout/probing failure; absent-key false positive; missing WAM dispatch;
incorrect ABI; or baseline/compiler source mismatch. A failure must be
diagnosed rather than hidden by reducing collision density.

**Scope boundary:** not an independent external audit, not exhaustive,
not a NaN/infinity test, and not a test of big-endian, Windows LLP64,
or concurrent/dynamic table modification. The recorded linear-probe depth
is an analytic estimate from the source logic, not an instrumented counter.


## Execution results — after preregistration, 16 November 2026

**ELF64:** [CI run #43942693160](https://github.com/jesusvilela/gprolog/actions/runs/43942693160)
**ELF32 / i686 multilib:** [CI run #43942693018](https://github.com/jesusvilela/gprolog/actions/runs/43942693018)

Both runs **passed** the collision oracle. Inspection of the archived raw JSON shows:

| Exact observable | ELF64 | ELF32 |
|---|---:|---:|
| Candidate and baseline binaries inspected | ELF64 | ELF32 |
| Distinct keys in one candidate table | 17 | 17 |
| Table capacity (`n+1`) | 18 | 18 |
| Hash-model home bucket for every key | 17 | 17 |
| Missing key also hashes to slot 17 | Yes | Yes |
| Clauses per permutation | 18 (incl. duplicate) | 18 (incl. duplicate) |
| Bound queries per permutation | 22 | 22 |
| Source permutations | 3 | 3 |
| Native/consulted × baseline/candidate paths | **12/12 passed** | **12/12 passed** |

Sample collision keys: `30.125`, `-91.125`, `-208.125`,
`-229.125`. These keys were selected by a deterministic fixture
generator; they are not human-chosen proof cases. All 18 values (17 keys
plus missing key) have modeled home slot 17 under **both** 32-bit and
64-bit unsigned arithmetic. The code path is then exercised as a
black-box by both compiled and consulted Prolog.

**Verdict:** the narrow *finite-key collision-identity/termination/
ordering* claim survives on the two tested Linux ABIs, under these
three deterministic source permutations. The historical compiler
gives the expected answers without the new float switch; the candidate
emits the new switch and gives the same expected answers.

The raw artifacts are GitHub Actions attachments:
`float-index-paired-observations` (ID 14262879306) and
`float-index-i686-oracle` (ID 14263891203). They have 30-day
retention, while this protocol and hashes remain in version control.

**Residual limits:** generated witness and oracle share a project
author; the hash collision construction follows the same source
algorithm rather than independent runtime instrumentation; actual
lookup probe counts were not measured; no infinity/NaN, alternative
float semantics, Windows LLP64, big-endian, or other CPU/OS evidence.
A finite test set is not a proof of all floating-point hash cases.
