# Generation 22 — symbolic allocation and instruction attribution
Date: 18 November 2026. Read-only offline audit; no interpreter changes.

## Original and held-out artifacts

This is explicitly **post-hoc exploratory decomposition** of already measured Generation 21 execution traces, not an originally preregistered benchmark. The source of the new hypothesis is [first Generation 21 external artifact 14427545662](https://github.com/jesusvilela/gprolog/actions/runs/44302879486/artifacts/14427545662), Valgrind 3.22.0 ELF64, comparing immutable released Gen18 `901c8b58` with rejected Gen19 `c09fff05`.

Before examining detailed call-site data from another GitHub run, freeze the **held-out same-workload replicate** [artifact 14427846479](https://github.com/jesusvilela/gprolog/actions/runs/44305428250/artifacts/14427846479). The replicate differs in CI run and process identity but **does not differ in workload, binary source, compiler or experimental authorship**. This does not count as independent experimental replication and does not establish generalized causal attribution.

## Typed metrics and normalization

**DHAT:** read `dhatFileVersion=2`, `mode=heap`, `pps[]`, `ftbl[]`. Verify all allocation site `tb` and `tbk` sums equal the tool's independently printed overall bytes/blocks. Attribute each allocation site by its **first frame containing a Rust project's `gprolog_native` symbol** or, if absent, its first `alloc::vec` frame. If neither is present, label `unknown`. Strip PC address and executable path but do not conflate symbols across different type names. Group separately by the symbol label; record any `unknown` group. This is a **symbol heuristic**, not an exclusive original source line or direct allocation causal origin.

Let `Δbytes=DHAT_Gen19 - DHAT_Gen18`. `Δblocks` likewise. Report signed differences for all normalized groups before computing shares. Avoid filtering negatives, clipping or assigning unidentified sites to a favored explanation.

**Callgrind:** parse `events: Ir`, `summary: <Ir>` and function sections `fn=(id)`; count each **self/exclusive** instruction line once and exclude the call-arc summary line immediately after `calls=`. Resolve function-name IDs even when referenced by `cfn=`. Verify the sum of exclusive instructions over all functions equals the `summary` exactly. Store signed per-function differences, preserving negative values. Treat `Ir` as Callgrind dynamic instruction references, not hardware retired instructions/cycles.

## Exploratory discovery on artifact 14427545662

On the `first_failure_r128` SOLVE process:
- `Δbytes=994,040-96,912=897,128`; `Δblocks=29,037-4,653=24,384`.
- Grouped DHAT `<gprolog_native::syntax::Term as core::clone::Clone>::clone`: `Δbytes=447,040` and `Δblocks=24,384`.
- Grouped `gprolog_native::engine::solve`: `Δbytes=450,088` and `Δblocks=0`.
- All other normalized group differences sum to **zero** for the exploration run. The two groups explain exactly the net byte increase, *under this specific symbolized grouping*.
- Callgrind `ΔIr=13,524,224-1,904,680=11,619,544`. Six exact libc allocator-management names `_int_malloc`, `_int_free`, `malloc_consolidate`, `malloc`, `free`, `unlink_chunk.isra.0` contribute a signed `ΔIr=8,579,808`, or **73.84%** of the net increase.

These are **already inspected** and must not be presented as held-out validation or preregistered discoveries.

## Frozen prediction for the separate artifact 14427846479

On the same `first_failure_r128` input and *newly observed process identities*:
- Under the same normalization, `Δbytes>0`, `Δblocks>0` and the signed contribution from `Term::clone` + `engine::solve` is **at least 95% of total net `Δbytes`**. Do not clip ratios above 100%: they may indicate offsetting negative groups.
- `Term::clone` alone contributes **at least 90% of net `Δblocks`**.
- Exactly the six preselected libc function names contribute **at least 65% of net `ΔIr`**, with `ΔIr>0`.
- `first_success_r128`, `t3_first_success_r64`, `t1_r128`, and `builtin_r128` control SOLVE DHAT byte/blocks and Callgrind Ir ratios must remain within **[0.9,1.1]** separately (Gen19 / Gen18).
- Every DHAT per-site sum matches its independent tool log totals, and every Callgrind exclusive sum matches `summary`. Missing frames, unknown format, negative/zero denominator or ambiguous symbol normalization is a **hard failure**, not a silently repaired analysis.
- The original 264-case semantic parity from Gen21 is inherited as evidence; this offline analysis does not re-execute the solver.

## Implementation and decision gates

Write a **standalone Python standard-library** analyzer, able to accept two unpacked Generation 21 artifact roots with the six fixed `<case>-<version>-solve-...` files each. Print raw totals, signed per-symbol DHAT and Callgrind differences, source archive SHA256, executable/Valgrind version from JSON/log where available and original file hashes. Do not rely on access tokens, network, Python external dependencies or Linux-only runtime.

Before inspecting the held-out artifact, write the above prediction and the analyzer code; test with synthetic DHAT/Callgrind known-answer fixtures and with the exploratory artifact. Then evaluate the held-out artifact **exactly once** without parameter retuning. Store full results, a correction ledger, and a JSON audit manifest validated under the Recursive Research Auditor skill.

**Kill conditions:** any per-tool cost sum mismatch, missing expected clone or solve group, invalid version/schema, missing held-out raw artifact, held-out threshold failure, or controls outside [0.9,1.1]. A killed held-out prediction does not erase exploratory data or authorize an interpreter optimization.

**Promotion:** mark only a measured *bounded symbol-group correlation* as M on the held-out trace if all gates pass. Attribution to exact source lines, fractions of native runtime, independent study quality, or general Prolog programs remains H. Gen19 T2 owned remains R. No compiler/WAM/GC/heuristic changes. Merge only the analyzer, tests, results and audit when evidence and exact-head CI pass.

## Resource and representation notes

The same Valgrind program affects both versions, but executable layouts, compiler inlining and unsymbolized stack frames can change the grouping. Record `unknown` and all negative groups. A function symbol grouping is *not* a theorem about source-level allocation responsibility; instruction-self attribution and caller/callee cost attribution are different objects. Do not add DHAT bytes and Callgrind instructions.
