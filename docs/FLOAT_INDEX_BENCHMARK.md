# Float-indexing benchmark: preregistered scope

Baseline **GNU Prolog goal-expansion-only** commit:
\`12b4284378a59098b9004fe2b454ad9c19536370\` (\`feature/goal-expansion\`, PR #1).

Candidate: exact \`feature/float-indexing\` head triggering the workflow, PR #2.

**Hypothesis (H):** on a static 128-key float predicate with uniformly distributed bound first-argument calls, new float indexing reduces native execution time by at least 10% versus the earlier compiler.

## Reproduction

GitHub Actions \`.github/workflows/float-index-benchmark.yml\` independently checks out and builds **both** commits, using identical \`./configure --with-install-dir=in-place; make; make install\` steps on one Ubuntu 24.04 runner. It uses the same source generator for both and checks source hashes, native answers, generated WAM instructions, and raw runs before producing measurements.

The standalone runner accepts two installed binary directories:

\`\`\`sh
python3 tests/float_indexing/benchmark.py \
  --baseline-bin /path/to/base/bin \
  --candidate-bin /path/to/new/bin \
  --baseline-ref BASE_SHA --candidate-ref NEW_SHA \
  --samples 7 --warmups 1 --loops 12000 \
  --output float-index-benchmark.json
\`\`\`

The six *separate*, synthetic workloads are:

- **float_uniform (primary):** 128 float facts, 64 deterministic permuted successful keys per sweep
- **float_tail:** 128 float facts, accesses concentrated in the last 32 source clauses (adversarial)
- **float_miss:** 128 float facts, 64 misses per sweep
- **mixed_float:** 96 float, 16 integer and 16 atom facts, 64 mixed-type successful queries per sweep
- **atom_control:** float-free 128-atom predicate with the same probe schedule, to detect control drift
- **variable_control:** 64 float facts, first-argument variable enumerated with \`findall/3\`

All benchmark programs are generated **before either compiler is invoked**. Source equality is SHA-256 checked. Both compilers build the same workloads and compare integer analytical totals; any failure aborts the measurement. Candidate WAM must have the float switch; baseline WAM must not; the atom control must stay on the historic instruction path.

## Locked interpretation rule

Primary observable: **median paired baseline/candidate native wall-time ratio** over seven alternating-order pairs after a warmup. Greater than 1 is faster for the candidate. A seeded paired bootstrap percentile interval (2,000 resamples) is printed as *within-run descriptive uncertainty*, **not** a cross-host confidence guarantee.

A narrow synthetic advantage may be described only if:
1. Primary median ratio ≥1.10 and lower bootstrap percentile >1.0.
2. Atom-only negative-control median ratio remains within [0.85, 1.15].
3. Every baseline/candidate run returns the same independently generated expected result.
4. The structurally expected WAM instructions are actually emitted.

Report *all* raw pairs, ratios, run order, compiler timings, native executable sizes, and peak RSS when supported. A negative result **retires this performance hypothesis for this workload**; it must not be rescued by changing thresholds after seeing data. A positive result does **not** imply speedup on real applications, different hardware, general call patterns, 32-bit platforms, or ISO correctness. Variable and mixed workloads are representation/control attacks; unexpected deviations must be investigated. No parallel CIs or unmatched source configurations count as evidence.

## Known limitations

Compiled-program startup is included in wall time. GitHub runner CPU frequency, contention, and caches are uncontrolled. The generated queries are synthetic and can overstate advantages. The bootstrap shares the same host and source generator and is **not independent replication**. Toolchain and OS parity is within this one run; compiler binaries differ in the exact feature under test. No pre-existing published independent performance oracle is claimed.
