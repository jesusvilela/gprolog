# Crossover CI correction ledger - 18 November 2026

The initial 24-case A/B run on workflow
[44264680827](https://github.com/jesusvilela/gprolog/actions/runs/44264680827)
passed both native ABIs and produced the dated, versioned
crossover_summary.csv and raw artifacts. Those numbers remain unchanged.

## QA error after publication

A subsequent post-publication check on run
[44265711068](https://github.com/jesusvilela/gprolog/actions/runs/44265711068)
mistakenly asserted *exact equality* between fresh CI runner
nanosecond medians and the previously observed versioned CSV medians.
The check failed on ELF64 **after the fresh 24/24 solver-answer
parity test passed**. There is no reason for runtime nanoseconds
from different CI runs to be bit-for-bit identical.

The first run's ELF64 primary case (N=10000,T=1,R=64):
563975 -> 37697 ns (-93.32%). The new-run ELF64 primary case:
873622.5 -> 52447 ns (-94.00%, 5/5 paired blocks won).
Different absolute timing values here do *not* signal a semantic
regression, and a cross-run exact-time assertion is invalid.

The correct reproducibility contract distinguishes:

1. **Deterministic:** immutable source commits, case definitions,
   per-case program SHA256, N/T/R, query, target-count, ABI,
   complete answer representation, error behavior and result schema.
2. **Statistical observations:** per-block raw nanoseconds, medians,
   variance, RSS and percentage effects, which may differ each run.
3. **Decision consistency:** the preregistered *primary* positive
   N=10000,T=1,R=64 case should still exceed >=10% median reduction
   with at least 4/5 candidate-faster blocks **on each ABI**.
   Smaller-effect cells are reported, not required to repeat identical
   classifications between runners.

### Fix and scope

Remove exact medians / percentages / block-win equality across
different runs. Validate source hashes, case types and shape; validate
each fresh run's own raw samples and complete answers; independently
retest the frozen primary benefit gate. Do not modify either frozen
Rust engine, the versioned CSV, or earlier run artifacts.

**Evidence tag:** erroneous cross-run exact timing assertion = R
(retired). Initial run measurements = M for their recorded run;
replication status = H until both corrected exact-head ABI jobs finish.

The previous check failure is an **audit-harness specification error**,
not an error observed in the Prolog interpreter.
