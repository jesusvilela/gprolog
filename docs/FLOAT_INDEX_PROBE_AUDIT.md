# Generation 6: C-level float-indexing probe audit

Status before CI: H / preregistered. Production code remains untouched.

The earlier collision oracle modeled a byte-wise hash and tested correct
ordered answers. It did NOT instrument the actual runtime table. This
experiment modifies wam_inst.c only inside a temporary CI checkout and
records raw C-level events from the real compiled lookup on Linux ELF64
and i686 ELF32, in native and consulted execution.

Frozen prediction: exactly 17 distinct finite dyadic keys hit bucket 17 in
a capacity-18 table. Runtime insertion depths must be 1 through 17;
successful lookups must reach matching keys at depths 1 through 17; an
absent key with the same initial bucket must visit 18 cells and fail.
The duplicate source clause must not create another table key. Every
semantic answer list must exactly equal the separate source-order oracle.
Three deterministic permutations, two execution modes, two ABIs.

Kill gates: wrong value/order, wrong ABI, extra or missing trace, unexpected
home bucket, wrong probe depth, a false hit on a miss, or hang. A tracing
integration defect must be corrected and rerun, not misclassified as success.

Proof ceiling: a successful CI establishes measured C slot traversal only
for this finite synthetic fixture, not an exhaustive binary64 theorem, not
production performance, and not independent third-party reproduction.
Non-finite floats and other operating systems remain unverified. The
trace is disabled in production because the C file is never committed.


## Calibration failure and explicit V2 amendment

The initial [ELF64 attempt, Actions #43955853671](https://github.com/jesusvilela/gprolog/actions/runs/43955853671) compiled successfully and established the prediction on the first native execution: actual C insertion depths 1..17; the same-bucket miss visited 18 slots; the answer oracle matched.

However, consulted execution returned the expected answers without producing a trace from the instrumented C function. The test assumed both execution modes would traverse that C function and failed with "no C trace written". That is an **experimental measurement-scope defect**, not evidence of a wrong Prolog answer. The original V1 all-mode C-trace gate is **NOT MET** and remains recorded as such. We cannot attribute the absence definitively to a particular interpreter implementation without separately tracing its path.

**Amendment V2, made before its CI rerun:** Native compiled execution must emit exact C traces and satisfy all frozen 17/18 probe assertions. Consulted execution must match the same independent semantic answer oracle; absence of a C-function trace is explicitly recorded as a different evidence type. If a consulted trace is emitted, it too must satisfy probe assertions. Either wrong answer remains fatal.

We retain the same three deterministic permutations, two ABIs, and original key set. This is a scope correction, **not** post-hoc promotion of the original V1 gate. Do not claim the C instrumentation covers the consulted interpreter merely because that interpreter returns correct answers.
