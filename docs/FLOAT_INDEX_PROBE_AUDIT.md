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
