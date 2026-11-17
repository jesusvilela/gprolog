# Generation 13 — Native Rust trail and choicepoints

**Preregistered 17 November 2026, before candidate execution.**

## Object and baseline

The sole runtime is Rust gprolog-native. Prior Rust engine commit
2f4c7b9346c7bcdfcd177907049f67cfe957f4d4 stores cloned HashMap
substitutions in each pending choice state. It is the **same-language
semantic baseline**; GNU Prolog C remains an offline oracle.

Replace per-choice substitution clones with ONE mutable Rust binding
store, an explicit LIFO undo trail and alternative frames storing
trail checkpoints plus pending continuation work. No C/Rust adapters,
ABI shims, fallback compiler, or WAM backend.

## Typed invariants

- Every new binding from variable to term is recorded once in the trail.
- Each alternative stores the exact trail length at its creation.
  Redo restores the trail to that checkpoint BEFORE trying it.
- A failed partially successful equality unification leaves no bindings.
- Disequality speculative unification always rolls back, on both
  success and failure.
- Clause variable IDs remain monotone across backtracking (no reuse).
- Cut discards alternative frames in its owning predicate invocation;
  its live bindings stay in the store until later backtracking to an
  ancestor alternative. Caller continuation cut boundaries are retained.
- Query answer rendering traverses live bindings before any untrail.
- Retain finite-term occurs-check and controlled search budgets.

## Frozen known-answer cases

1. Ancestor: noah, mei, in order.
2. Member, append, repeated variables, list recursion.
3. p(f(a,a)). p(f(a,b)). with p(f(X,X)). => one binding X=a.
4. (X=a,X=b;X=c). => X=c, after failed partial unification.
5. (X=a,X \\= a;X=b). => X=b, after speculative rollback.
6. X=f(X). => no answer, by explicit occurs-check.
7. p(a). p(b). with p(X),!. => only a.
8. Cut BEFORE later alternatives permits those alternatives.
9. Cut followed by fail still blocks fallback clauses.
10. Inner cut preserves caller choices; caller cut prunes child choices.
11. Three levels of recursive rule/semicolon alternatives do not
    leak bindings across redo.
12. Alpha-renaming and fact reversal preserve expected invariants.
13. Unknown predicate, syntax and search budgets remain controlled.
14. Existing 32 Rust tests per ABI pass unchanged.

## Comparison controls

Build the exact prior Rust snapshot commit and new Rust candidate
under the same GitHub Actions Linux environment. For a fixed list
of matching source/query pairs, compare complete ordered stdout,
exit codes and deterministic behavior. Step budget internal work-unit
counts may differ; report separately rather than disguise them.

A structural test rejects cloned per-choice substitution maps.
Both actual ELF64 and i686 ELF32 binaries must execute without
any GNU Prolog C runtime dependency. Historical C compiler CI must
stay green but cannot validate the Rust trail implementation.

For an optional synthetic repeated-choice workload, preserve matched
input and resources, raw wall-time and RSS samples before claiming
any speedup. A passing functional test does not prove a performance
benefit.

## Scope

The new component is a **variable-binding trail**, NOT a full WAM
term heap, garbage collector or native Prolog compiler. AST Terms
continue to own their structure. A compact cell arena and GC are
separate future obligations.

**Kill:** any incorrect or reordered answer, stale binding,
escaped cut, wrong equals/not-unifiable result, runtime crash,
ABI difference, regression or C dependency.

**Stop:** do not add WAM, heap or compatibility wrappers to hide a
rollback defect. Repair the current invariants first.

**Promotion:** H to bounded M for this trail-backed Rust subset only
after both ABIs and a matched same-Rust snapshot differential pass.
Project-authored tests are correlated evidence, not independent review.


## Measured and corrected result — 17 November 2026

The first build run 44118682272 failed to compile after accidentally
dropping public Limits/Solution/SolveError types. Restored in
aa753360; this defect is recorded rather than erased.

Rust tests run 44119226614 then passed **45 tests per ABI** (14
parser/engine unit, seven CLI, ten control, four metamorphic, ten
trail-specific integration). Both ELF64 and actual i686 ELF32 passed.

The initial Rust snapshot comparison run 44119675175 matched
21/21 CLI cases but the 250-fact synthetic runtime registered
0.00 seconds and was **not** useful performance evidence.

The corrected [differential run 44120205901](https://github.com/jesusvilela/gprolog/actions/runs/44120205901)
matched **149/149 complete ordered results**, including source
stdout/stderr/exit statuses for 21 fixed and 128 seeded cases.
Five paired alternating-order synthetic 20,000-fact trials after
warmup recorded:

| Observation | Rust snapshot | Rust trail + lazy choices |
|---|---:|---:|
| Median subprocess wall time | 20.987063 ms | 15.026416 ms |
| Median peak resident memory | 16,428 KiB | 14,136 KiB |

All ten observed runs had the same output hash; raw GitHub Actions
artifact ID **14343264933** includes every sample, source hash and
paired outcome. A wall-clock speed ratio of 1.397x and a 13.95%
memory reduction describe THIS ONE synthetic case. They do not
causally isolate the trail from deferred clause matching and do
not establish broad real-world Prolog improvement.

**Evidence governance:** M for the tested native Rust trail/cut/
backtracking semantics and bounded sample values, H for broad
ISO equivalence and WAM term heap/GC/performance portability.
The snapshot reference and tests are project-authored and correlated;
there is no external independent replication. Full ledger:
RUST_NATIVE_TRAIL_AUDIT.json.


## Cross-ABI strengthening — final observed matrix

[CI 44122164750](https://github.com/jesusvilela/gprolog/actions/runs/44122164750)
compiled the pinned pre-trail snapshot and candidate native Rust
binaries for **both** ELF64 and i686 ELF32. For each ABI, the same
21 fixed plus 128 seeded source/query cases matched complete stdout,
stderr and exit code: **149/149 per ABI, 298 pairs total**. The
source-level no-snapshot structural check passed in both jobs.

The synthetic 20,000-fact workload, first 256 answers, with five
paired alternate-order samples and two warmups per binary gave:

| ABI | Snapshot median wall | Trail+lazy median wall | Snapshot / candidate peak RSS |
|---|---:|---:|---:|
| ELF64 | 22.617368 ms | 16.513267 ms | 16,492 / 14,200 KiB |
| i686 ELF32 | 14.372621 ms | 8.621647 ms | 9,980 / 8,480 KiB |

The observable wall ratios were approximately 1.370x (ELF64) and
1.667x (i686), in separate job environments. **Do not compare their
absolute time scales across machine configurations.** Causal
attribution of speed to trailing alone remains invalid because the
candidate also defers clause unification.

Raw artifacts under run 44122164750: ELF64 **14344499735** and
ELF32 **14346516154**. Each archive includes the typed claim ledger
and the complete generated test/benchmark JSON. Missing independent
external witnesses are explicit validator warnings, not silently
replaced with self-review.
