# Generation 16 — exact Rust choicepoint profile
18 November 2026 | Evidence: M for bounded instrumented behavior

## Verdict

All 12 profiled cases passed analytic/control checks on both native Linux
ELF64 and i686 ELF32, using the actual Rust solver control-flow sites.
The first-success workload with 16 matching facts and 64 consecutive
goals creates **960 clause alternatives**, clones **960 continuation
vectors containing 30,240 pending-goal elements**, and performs
**zero redo pops**. It also materializes **2,016 ordinary pending-goal
suffix elements** while scheduling successive Resume tasks. This
isolates a concrete *structural* source of waste without making a
causal wall-time attribution or allocating a number of bytes.

### Reproducible execution

- Source commit: experiment branch at
  [a445565c](https://github.com/jesusvilela/gprolog/commit/a445565c143cc630830ee3656582cb27121eed47)
  (runtime profile feature gated; production master
  [25286973](https://github.com/jesusvilela/gprolog/commit/2528697368fa2d930029b6c1efa9528745e91f61)
  unchanged).
- Exact dual-ABI CI: [run 44274185198](https://github.com/jesusvilela/gprolog/actions/runs/44274185198),
  both jobs successful. Feature-disabled and feature-enabled native Rust
  tests passed for each ABI. No GNU Prolog C runtime link.
- Complete per-case JSON outputs: [ELF64 artifact 14413483522](https://github.com/jesusvilela/gprolog/actions/runs/44274185198/artifacts/14413483522);
  [i686 ELF32 artifact 14413881947](https://github.com/jesusvilela/gprolog/actions/runs/44274185198/artifacts/14413881947).
  Artifacts retained by GitHub Actions for 30 days.
- Exact executable inputs/expected counters:
  [tests/rust_choicepoint/profile.py](../tests/rust_choicepoint/profile.py)
  and [feature integration tests](../rust/gprolog-native/tests/choicepoint_profile.rs).
  Protocol frozen before instrumentation:
  [RUST_NATIVE_CHOICEPOINT_PROFILE_PROTOCOL.md](RUST_NATIVE_CHOICEPOINT_PROFILE_PROTOCOL.md).

## First-answer analytic and instrumented profiles

The following values matched **exactly on both ABIs**:

| Matching clause heads T | Sequential goals R | Clause alternatives created | Continuation vectors cloned | Continuation goal-elements cloned | Redo pops |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 0 | 0 | 0 | 0 |
| 1 | 64 | 0 | 0 | 0 | 0 |
| 2 | 64 | 64 | 64 | 2,016 | 0 |
| 16 | 1 | 15 | 15 | 0 | 0 |
| 16 | 8 | 120 | 120 | 420 | 0 |
| **16** | **64** | **960** | **960** | **30,240** | **0** |
| 32 | 64 | 1,984 | 1,984 | 62,496 | 0 |

In all first-success cases, every queued clause alternative remains
unresumed at the instant max_solutions=1 terminates. The additional
Resume suffix materialization for R=64 is 2,016 elements for all T.
With T=16,R=64 the peak pending choicepoint count is 960, and
the executed TryClause task count is only 64.

### Formula, conditional on this exact execution path

For T matching clause heads, R successive ground calls, first
clause always succeeding, no cuts and max_solutions=1:

- Choicepoint pushes = (T-1) R.
- Clause continuation vector clones = (T-1) R.
- Pending-goal *elements* cloned into those continuations =
  (T-1) R(R-1)/2.
- Pending-goal *elements* materialized into a new rest vector =
  R(R-1)/2.
- Redo pops = 0.

This is a combinatorial fact about the inspected Rust scheduler
under declared assumptions, **not** a theorem about GNU Prolog,
Prolog complexity in general or a measured number of allocations.
A PendingGoal contains a potentially nested Term AST, so elements
cloned are not a reliable proxy for allocated bytes.

## Negative and perturbation controls

- Deep-term shape target(f(a,b,c,d,e)) (T=16,R=64):
  still 960 alternative vectors and 30,240 continuation elements
  despite potentially different per-term copy costs. The counter
  does *not* measure cloned AST size.
- Builtin-only true/0 repeated 64 times: zero clause choicepoints
  and zero clause-continuation copies, yet 2,016 Resume suffix
  elements materialized. Hence suffix materialization is a distinct
  mechanism from clause alternative cloning.
- Two-solution p/1: 1 alternative pushed, 1 redo popped,
  2 binding writes, 1 binding undo. This is a positive control for
  actual backtracking rather than assuming no redo globally.
- Partial failed-head unification: 1 alternative pushed and redone,
  2 writes and 1 rollback. This controls the failure/rollback path.
- Cut followed by new disjunction: 2 pre-cut alternatives pruned,
  1 new disjunction alternative created and then redone; cut
  scope remains local to the predicate invocation.

All measured counters passed their expected-field checks (12/12
cases per ABI). This is author-correlated implementation + test
evidence, not an external independent Prolog language oracle.

## Interpretation and next experiment

The strongest surviving result is **excess eager construction of
unresumed alternatives**, not the claim that those operations account
for all observed milliseconds. Counting them under a diagnostic
feature changes the instruction stream. The uninstrumented
performance effects in Generation 15 remain separate measurements.

Load-bearing unresolved issues:
(1) how much runtime is due to cloning AST terms versus creating
containers, (2) whether shared continuations alter cut/trail/step
semantics, (3) behavior under multiple solutions, failing clauses,
nested disjunction, deep terms and recursive goals.

**Bounded next experiment:** compare the current Vec-clone choicepoint
representation to a representation-sharing alternative (e.g.
immutable reference-counted continuation suffixes) with the exact
same search-step accounting and ordered outcomes, first on a frozen
corpus and then in matched per-ABI timing/RSS runs. Preserve
first-solution and full-enumeration controls. Kill any
unexplained CLI difference, cut/rollback failure or increased
worst-case resource use; do not merge a redesign merely because
a synthetic microbenchmark improves.

## Evidence labels

- **M:** 12 case-level operational counter profiles on both ABIs;
  compiled default and feature-enabled Rust tests.
- **P (conditional arithmetic):** the T/R polynomial counts for the
  specified execution path; not a formal Lean proof.
- **H:** any runtime causality, superiority of shared continuations,
  full ISO or GNU Prolog parity.
- **S:** persistent suffix representation as a design target.
- **R:** treating copied-element counts as bytes, allocations, CPU
  time or universal Prolog complexity.
