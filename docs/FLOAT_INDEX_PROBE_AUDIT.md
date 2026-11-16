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


## V2 observed results — 16 November 2026

[Successful Actions run #43956222956](https://github.com/jesusvilela/gprolog/actions/runs/43956222956)
executed the corrected protocol at commit a3af0c758b79667eb170c8b8e9e1ca7c39b7d9de.

| Observable | Linux ELF64 | Linux ELF32 (i686 multilib) |
|---|---:|---:|
| Native semantic checks by seed | 3/3 | 3/3 |
| Consulted semantic checks by seed | 3/3 | 3/3 |
| Native C insertion keys | 17 per seed | 17 per seed |
| Native measured insertion depths | 1..17 | 1..17 |
| Native measured hit depths | 1..17 | 1..17 |
| Native colliding missing-key depth | **18** | **18** |
| Consulted C-function trace | Not observed | Not observed |

All observations used the same dyadic float collision fixture and the
project-authored, hash-independent source-order answer oracle. The raw
hex-float keys and C lookup records are retained in 30-day workflow
artifacts: float-probe-elf64 (ID 14271662425) and float-probe-elf32
(ID 14269099971). No source file altered by the instrumentation script
was committed; the normal master runtime remains bit-for-bit as before
this experiment.

**Claim ledger:** Original V1 requirement that both modes execute the
instrumented C function was *retired / not met*. The narrower V2
native C-level observation is *M / measured*, accompanied by a separate
consulted semantic control. This does not certify the consulted-mode
internal lookup algorithm, independent physical 32-bit hardware,
unusual non-finite values, or all possible hash collisions.

**Strongest surviving result:** at 17/18 occupancy on two Linux ABIs,
the real native C lookup terminates after exactly 18 probes for a
distinct key hashing to the same home bucket, and returns the expected
complete answer lists for all tested hits. **Most damaging remaining
obstruction:** correlated project-authored fixtures, no independent
application workload or non-finite-value oracle.

**Next bounded experiment:** inspect GNU Prolog's lexer/parser and
arithmetic error paths for NaN and infinity independently of float
indexing, then compare parsed/compiled/consulted behavior under a
pre-registered accept/error/crash decision matrix. Any candidate-only
crash or inconsistent semantic answer is a blocker. If both compilers
reject a representation, record unsupported syntax instead of inventing
a NaN-valued Prolog literal.
