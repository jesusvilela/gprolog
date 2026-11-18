# Generation 21 — third-party heap and instruction audit (pre-registered)
Date: 2026-11-18. Independent *profiling mechanism*, not an independent study.

## Freeze, object and source identity

- Production baseline is the **immutable Generation 18 Rust implementation**
  at \`901c8b58c12fbe8b79f70b0118f951f3ed2fcf21\`.
- The deliberately rejected experimental comparison is Generation 19
  at \`c09fff05d9b3dd43fb90014278e3a98d701d3640\`.
- Current master is the Generation 20 diagnostics/documentation squash
  \`ee2194452b34f3ce727c6ab2c4cada89579ea505\`, with Gen18
  interpreter semantics intact.
- Neither frozen implementation may be changed or patched. Gen19 stays
  retired and unmerged. Rust 1.85.1 native release library on Linux
  ELF64 and i686 ELF32. Identical external harness source, matching
  source program and query bytes, limits and compiler flags.

## Question and evidence floor

Generation 19 showed 8–11x uninstrumented direct-solve regression for
T=2, R=128 with first same-signature clause failing. Generation 20's
**author-created GlobalAlloc** probe measured 4,228 to 28,612 Rust
allocation requests and 0 to 8,128 PendingGoal copies in that regime.
Do independent third-party heap and dynamic-instruction instruments
corroborate those *directions* on the exact frozen native binaries,
while separate, uninstrumented release timings reproduce the runtime
regression? 

The new witness is independent **instrument software** (Valgrind DHAT
and Callgrind), *not* an independent author, specification, semantic
oracle or experiment. The tool's sampling mode changes runtime; never
treat times obtained under Valgrind as native CPU timing.

## Two separate measurement lanes — no scalar collapse

### Lane A: native, uninstrumented Rust direct-solve timing
On each native ABI, link the **identical** existing
\`tests/rust_choicepoint/bench_continuations.rs\` into each frozen,
feature-disabled release library. The timed region is a single
\`solve()\` call; input parsing, program construction, answer formatting,
process launch excluded. Three warmups/launch. Five alternating AB/BA
paired blocks × four nanosamples per role: 20 raw solve times per
version, cell and ABI. Record complete ordered answer representation,
peak process RSS (not solve-only), source SHA256, compiler toolchain,
process exit and stderr.

Frozen timing cells:
- \`first_failure_r128\`: T2 facts target(b),target(a); query target(a),
  R=128. **Primary**: retired Gen19 must be slower than released Gen18
  by at least 3x median on each ABI and slower in >=4/5 blocks.
- \`first_success_r128\`: T2 duplicate target(a) facts, R=128, first
  head succeeds. **Control**, no >15% slowdown in either direction
  (reported regardless of outcome).
- \`first_failure_r32\`: same head mismatch R=32; secondary scaling.
- \`first_failure_deep_r64\`: nested deep mismatched head R=64; secondary.
- \`t3_first_success_r64\`: three matching facts, sharing branch
  identical across versions; control with <=15% median difference.
- \`t1_r128\`: one fact, and \`builtin_r128\`: true/0 only; controls
  with <=15% median difference.

Kill if any full ordered answer mismatch or unaccounted target/ABI
discrepancy; a timing-prediction miss retires the timing-replication
claim without altering the source or experiment.

### Lane B: external Valgrind evidence, Linux x86_64 only
Build one shared **external** Rust binary against each frozen release
library, without \`choicepoint-profile\`, defining a \`PREPARE\` mode
(parse/expand/query without solve), or a \`SOLVE\` mode (same
preparation, one solve). Keep same compiler version and flags,
and binary entrypoint. No on-the-fly Rust GlobalAlloc counters.
Install \`valgrind\` on Ubuntu 24.04 and record its version.

Run **DHAT** (\`--tool=dhat\`) and **Callgrind**
(\`--tool=callgrind --cache-sim=no --branch-sim=no\`), with fixed
\`--*-out-file\` and external tool logs retained. Parse the DHAT
reported **process-lifetime** total allocated heap bytes and blocks
from Valgrind's own log, and Callgrind's process-wide **dynamic
instruction references** (\`summary\` cost). Both include parsing,
startup, formatting and Valgrind/tool overhead. Also execute PREPARE
controls to bound—not magically subtract—those costs. Do not claim
isolation to \`solve()\`, hardware cycles, or native runtime.
Callgrind instruction counts are under Valgrind's dynamic binary
instrumentation, not processor retired instructions.

Frozen external-profile cells:
1. \`first_failure_r128\` — **primary**. For the SOLVE process,
   rejected Gen19 is predicted to exceed Gen18 in DHAT
   heap blocks and bytes by >=3x each, and Callgrind dynamic
   instruction references by >=2x (all measured on ELF64 only).
2. \`first_success_r128\` — matching head control: report full values
   whether it favors either representation.
3. \`t3_first_success_r64\` — same ownership branch: under both
   variants, DHAT heap blocks/bytes and Callgrind instruction totals
   should be within 10% in either direction.
4. \`t1_r128\` — one-head source control.
5. \`builtin_r128\` — no predicate source control.
6. \`first_failure_deep_r64\` — deep failing-first control, report
   bytes and instructions without an extra threshold.
Each SOLVE mode is paired with PREPARE using **identical** source/query
bytes on the *same* compiler/ABI. Raw PREPARE results are retained;
do not assume exact linear subtraction because lifetimes differ.

Valgrind dependencies, libc versions, cache/timing behavior, JIT
instrumentation and allocation accounting remain possible
confounds. No i686 Valgrind claims; i686 is independently assessed
only by lane A native timings.

## Exact-output and source parity gates

- Before profiling, replay the frozen existing **264-case Rust CLI
  full stdout/stderr/exit differential** on each native ABI; do not
  mistake a failed performance gate for broken semantics.
- Confirm both immutable Git source commit SHAs and the working
  branch PR-head source-tree equivalence (pull-request synthetic
  merge-commit behavior).
- The PREPARE and SOLVE *external-profile* harnesses must emit equal
  output between versions for the same input/mode. Valgrind exit
  nonzero, missing output, negative counters, mismatched answers
  or source-tree mismatch are hard errors.
- Any external measurement source/format issue produces **no
  promoted claim**. Save all raw observations and update the
  correction ledger; do not silently relax thresholds.
- Tool versions, OS/architecture and CI-run IDs must be traceable.

## Promotion and merger

- M: matched native timings separately by ABI, and externally
  measured process-wide DHAT/Callgrind counts on ELF64 if gates pass.
- H: causal attribution of time to copying or allocation; ISO Prolog
  equivalence beyond tested subset; causal hardware cache metrics.
- R: Gen19's fixed T2-owned optimization.
- S: alternative representation, unimplemented and out of scope.
- Independent witness **in instrument implementation**, not source
  authorship. No peer-reviewed external reproduction.

Merge only tests, external harness, CI, immutable inputs, results and
claim audit after exact-head checks pass. Never merge a change to
\`rust/gprolog-native/src\` or the rejected Gen19 algorithm. If third-
party profiling fails, preserve diagnostic failure and stop. No WAM,
GC, new term heap or new ownership heuristic to rescue the result.
