# Generation 17 preregistration arithmetic correction (before implementation)

At the first protocol commit `2b621edf25fd37c9429de420e05ebc619530bf73`,
the predicted Arc handle counts were inadvertently calculated as though
an Arc were created for the **last** pending goal. But the same frozen
design explicitly keeps continuations **owned when empty**.

For T=16 matching clauses and R=64 successful successive goals:
- **960** clause alternatives still exist: (16-1) * 64.
- **63** nonempty continuations receive an Arc anchor, not 64.
- **945** Arc handles are cloned for alternatives, not 960.
- **15** empty owned continuation vectors are cloned for alternatives
  on the last goal (zero PendingGoal elements copied).
- **63** successful Arc-backed TryClause executions materialize
  nonempty Vec continuations, totaling 2,016 PendingGoal elements.
- Thus the truthful existing counters for **actual Vec.clone calls**
  should record **78** cloned Vec objects, containing **2,016**
  PendingGoal elements. A Vec of zero elements is still a Vec clone.
- No redo for max_solutions=1, and all 960 queued choices are unused.

The original protocol is not rewritten; this document is a visible,
preimplementation correction to its contradictory numeric predictions.
Any report must cite this corrected ledger alongside the protocol.
No implementation or benchmark code existed on the branch before
this correction was committed.
