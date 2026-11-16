# Float-indexing benchmark: preregistered scope

Baseline **GNU Prolog goal-expansion-only** commit:
`12b4284378a59098b9004fe2b454ad9c19536370` (`feature/goal-expansion`, PR #1).

Candidate: exact `feature/float-indexing` head triggering the workflow, PR #2.

**Hypothesis (H):** on a static 128-key float predicate with uniformly distributed bound first-argument calls, new float indexing reduces native execution time by at least 10% versus the earlier compiler.

## Reproduction

GitHub Actions `.github/workflows/float-index-benchmark.yml` independently checks out and builds **both** commits, using identical `./configure --with-install-dir=in-place; make; make install` steps on one Ubuntu 24.04 runner. It uses the same source generator for both and checks source hashes, native answers, generated WAM instructions, and raw runs before producing measurements.

The standalone runner accepts two installed binary directories:

```sh
python3 tests/float_indexing/benchmark.py \
  --baseline-bin /path/to/base/bin \
  --candidate-bin /path/to/new/bin \
  --baseline-ref BASE_SHA --candidate-ref NEW_SHA \
  --samples 7 --warmups 1 --loops 12000 \
  --output float-index-benchmark.json
```

The six *separate*, synthetic workloads are:

- **float_uniform (primary):** 128 float facts, 64 deterministic permuted successful keys per sweep
- **float_tail:** 128 float facts, accesses concentrated in the last 32 source clauses (adversarial)
- **float_miss:** 128 float facts, 64 misses per sweep
- **mixed_float:** 96 float, 16 integer and 16 atom facts, 64 mixed-type successful queries per sweep
- **atom_control:** float-free 128-atom predicate with the same probe schedule, to detect control drift
- **variable_control:** 64 float facts, first-argument variable enumerated with `findall/3`

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


## First bounded measurement — 16 November 2026

**Exact execution record:** [GitHub Actions #43898849916](https://github.com/jesusvilela/gprolog/actions/runs/43898849916) (successful); compiled candidate `a1098e229ff83a3d2004b5edcb6b5a86299a55ed` against fixed baseline `12b4284378a59098b9004fe2b454ad9c19536370`. The 30-day raw artifact is named `float-index-paired-observations` (ID `14241261189`).

Environment: Ubuntu 24.04 runner, x86-64, reported 4 visible CPUs, Python 3.12.3. All compiler builds, WAM instruction checks, and analytical answers succeeded before timing. All six paired benchmarks completed successfully.

| Workload | Baseline median (s) | Candidate median (s) | Paired median ratio |
|---|---:|---:|---:|
| Float uniform (**primary**) | 0.559387 | 0.078323 | **7.222×** |
| Float tail | 0.970009 | 0.098073 | **9.932×** |
| Float miss | 1.309206 | 0.276617 | **4.737×** |
| Mixed float/integer/atom | 0.609847 | 0.053874 | **11.327×** |
| Atom-only negative control | 0.055531 | 0.054137 | 1.015× |
| Variable-call control | 0.011664 | 0.011510 | 0.999× |

Primary paired bootstrap percentile interval: **[7.133×, 7.274×]** across seven pairs sampled within the *same* runner. This is descriptive within-run variation; it must not be presented as a general population or cross-platform confidence interval.

The atom-only control ratio satisfied the preregistered [0.85, 1.15] parity gate, and the primary ratio exceeded the 1.10 threshold. This supports a bounded **M (measured)** result for this generated workload, **not** a claim of universal Prolog acceleration.

### Resource parity and costs

In the primary float-uniform workload:

- **Native compilation median:** 0.087626 s baseline versus 0.089480 s candidate (**1.021× compilation cost**), based on three sequential per-version compilations. The difference is small and should not be called significant.
- **Native executable size:** 1,054,824 bytes baseline versus 1,059,136 bytes candidate (**+4,312 bytes**, about 0.41%).
- **Median recorded peak RSS:** 5,540 KB baseline versus 5,516 KB candidate, essentially unchanged at this resolution.

All raw per-sample execution times, execution order, compiler timings, generated WAM SHA-256 values, executable sizes, and available RSS readings are retained in the artifact. The source hash was matched between both compiler versions.

### Claim ledger and correction history

| Claim | Status | Evidence or obstruction |
|---|---|---|
| Float-specific WAM dispatch executes | **M / observed** | Emitted instructions and native results checked, not merely source inspection |
| Answers and ordering remain intact in fixtures | **M / observed** | Prior 13 semantic tests per native and consulted path; separate paired benchmark answer oracles |
| Native performance improves on uniform float synthetic calls | **M / measured** | 7.222× median paired ratio, with negative controls |
| Performance improves in general applications | **H / unresolved** | No application corpus, independent OS/architecture replication or representative workload distribution |
| Finite literal semantics on tested i686 ABI | **M / observed** | Multilib ELF32 baseline/candidate semantic differential, Actions #43939319562 |
| Non-finite float semantics and other ABIs are preserved | **H / unresolved** | No NaN/infinity fixture or independent OS/machine proof |
| The prior early `findall/3` failure was a runtime bug | **R / retired** | Original test leaked an instantiated variable between cases |
| Green build with checked-in WAM alone proved float dispatch | **R / retired** | Initial build reused stale bootstrap WAM; corrected and WAM emission asserted |

### Next smallest independent witness

Re-run the pinned commits on a separately managed, appropriately isolated system with different OS/CPU, since i686 multilib has now passed on the same Linux host family. Use existing application-derived static predicates and query distributions; keep source, compilation settings, and semantic oracles matched. If the real workload shows no gain, retain the synthetic measurement but retire any extrapolation to practical speedups.

The benchmark workflow now runs on relevant compiler or benchmark-source changes, rather than every documentation-only push. This reduces unnecessary runner usage while preserving the manual-dispatch option.


## Second semantic gate — adversarial source-order oracle (16 November 2026)

[Linux x86-64 differential + matched benchmark run #43938946712](https://github.com/jesusvilela/gprolog/actions/runs/43938946712) completed successfully on commit `c15affb4c40dab8a4ac2126ee2e5b22b0c24d1af`.

The new `tests/float_indexing/differential.py` generates **99-clause programs with 43 bound-key queries** for each of three deterministic source permutations (seeds 20261116, 271828, 314159). A separate Python reference model computes ordered answer lists directly from source clauses with numeric binary64 equality, rather than replaying either Prolog implementation. The same generated source is compiled and consulted by **both** compilers. All **12 tested execution paths per ABI** produced exactly the expected output.

The cases cover signed zero; adjacent representable values around 0.1; 5.0e-324 and 1.0e-320 subnormals; minimum-normal and maximum-finite-scale literals; mixed integer, atom, structure and list heads; missing keys; wildcard-headed clauses interleaved in source; an unbound first argument; and a cut-based predicate. This is a bounded deterministic regression test, not exhaustive floating-point verification.

The same run reran the float-uniform microbenchmark: **6.007x paired median speedup**, versus **7.222x** in the earlier run. Both remain positive within their synthetic scope, but the between-run difference demonstrates that within-run bootstrap intervals are **not** cross-run or cross-machine confidence intervals. No speedup has been measured on a real application-derived float workload.

### i686 / ELF32 ABI gate

[32-bit i686 multilib run #43939319562](https://github.com/jesusvilela/gprolog/actions/runs/43939319562), commit `53a79891cc90bdb15311ae5dc014f626f5d66db4`, **passed**. Both the fixed historical compiler and float-indexed compiler were built with i686 target settings, and `readelf` confirmed all four `gprolog`/`gplc` binaries were **ELF32**. The same three 99-clause / 43-query permutations passed native and consulted execution for both builds: 12/12 execution paths.

This tests a distinct **32-bit ABI** where float words are split across the WAM representation, but it still runs under a Linux x86-64 GitHub host with a multilib userland. It is not independent 32-bit hardware reproduction, not a Windows or ARM compatibility result, and not a NaN/infinity certification. The underlying float table must continue to use full double keys rather than truncating to 32-bit words.

Raw evidence is retained as GitHub Actions artifacts for both runs (30-day artifact retention), not copied into the committed source tree. The source generator, oracle, and compiler changes remain correlated project-authored evidence; external review is still a gate.
