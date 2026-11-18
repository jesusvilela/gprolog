# Generation 23 — Published list relations and externally grounded task transfer

**2026-11-18. Verdict:** Both native ELF64 and i686 benchmarks passed all fourteen independent Python list-algebra answer-oracle tests, along with all 264 frozen full-output Rust differential cases per architecture. **Twelve task cases** were selected from publicly documented list relations (Learn Prolog Now! and SWI-Prolog documentation), but each small executable Horn-clause program was reconstructed by the project to fit the existing finite-term Rust subset. Results show *heterogeneous* cost: repeated list concatenation and late membership deteriorate under the retired Generation 19 ownership policy, while most one-shot relational queries remain near parity. No interpreter code was changed, and no universal Prolog speed claim is justified.

## Claim and evidence ledger

| Claim | Before | Artifact | Result | After |
|---|---|---|---|---|
| Natural list relations reproduce the synthetic 8–11× first-failed-head runtime regression | H | Two-ABI 12-case vector with full raw nanosamples | Not reproduced at that magnitude: max **1.404×** ELF64 / **1.377×** i686 in these chosen tasks | **R** for uniform generalization |
| Repeated ordinary list-processing calls can be slower with Gen19 | H | Matched feature-disabled release `solve()` timing, five alternating AB/BA blocks per ABI | Append, late membership, naive reverse and accumulator reverse show modest-to-moderate penalties | **M**, bounded |
| Gen18/Gen19 preserve the selected list-task answers | H | Independent Python list algebra oracle + exact native CLI equality | **14/14 oracle cases** and **264/264 historical CLI cases per ABI** | **M**, tested subset |
| Every two-clause invocation incurs an observable Gen19 speed penalty | H | One-shot concat/split/member/prefix cases | Many ratios near 1; some below 1 | **R** as a generalization |
| The public source provides independently authored executable benchmark files | H | Published documentation vs project-built Horn definitions | False: the **relations are externally specified**, implementations and tests project-authored | **R** |

## Complete preregistered result vector

Ratios below are **rejected Gen19 median direct-solve time / released Gen18 median**. A value above one means the retired policy was slower. Each of the 14 cells contains 5 paired blocks × 4 raw samples per role per ABI, plus three unmeasured warmups per invocation, with complete ordered answer representation equality. No selected cells are omitted.

| Published relation case | ELF64 Gen19/Gen18 | ELF64 slower blocks | i686 Gen19/Gen18 | i686 slower blocks |
|---|---:|---:|---:|---:|
| `append_ground_r8` | 1.404× | 5/5 | 1.377× | 4/5 |
| `append_answer_r1` | 1.004× | 2/5 | 0.997× | 3/5 |
| `append_split_r1` | 1.014× | 2/5 | 1.004× | 3/5 |
| `append_wrong_r1` | 1.012× | 2/5 | 1.007× | 3/5 |
| `naive_ground_r2` | 1.079× | 5/5 | 1.111× | 5/5 |
| `naive_answer_r1` | 1.122× | 5/5 | 1.069× | 5/5 |
| `acc_ground_r4` | 1.129× | 5/5 | 1.179× | 5/5 |
| `acc_answer_r1` | 0.991× | 2/5 | 1.010× | 3/5 |
| `member_late_r8` | 1.254× | 5/5 | 1.271× | 5/5 |
| `member_all_r1` | 1.001× | 3/5 | 0.985× | 2/5 |
| `select_duplicate_r1` | 0.993× | 3/5 | 1.018× | 4/5 |
| `prefix_all_r1` | 1.013× | 2/5 | 0.997× | 3/5 |
| `single_fact_r8` | 1.008× | 3/5 | 1.005× | 4/5 |
| `builtin_true_r8` | 0.972× | 2/5 | 0.983× | 1/5 |

The two null controls, `single_fact_r8` and `builtin_true_r8`, remained inside the frozen **[0.8,1.2]** median ratio region on both ABIs. All required source hashes, full stdout/stderr/exit checks and process return codes passed. Non-overlapping source hashes do not by themselves prove independent compilation or real-production representativeness.

## Strongest surviving result

Five external-task cases showed a slower Gen19 median with at least 4/5 slower paired blocks on **both** architectures: `append_ground_r8`, `naive_ground_r2`, `naive_answer_r1`, `acc_ground_r4`, and `member_late_r8`. The largest penalty was **1.4043×** (ELF64) / **1.3770×** (i686) for eight consecutive *ground* concatenations. The late-membership case was **1.2543×** / **1.2709×**. This is compatible with, but does not independently prove, the earlier attribution to eager continuation cloning on repeated first-head failures.

Across **all twelve** published-relation cases, Gen19 had a higher median in **10/12 ELF64 cases** and **9/12 i686 cases**, but only **5/12 ELF64** and **6/12 i686** additionally had >=4/5 slower blocks. The purely descriptive geometric-mean ratios were **1.0784×** and **1.0792×**, respectively, *not* population averages of real Prolog applications. No multiple-testing-adjusted inferential claim or confidence interval is asserted.

## Load-bearing obstruction: source and workload independence

This corpus is **not** an independently authored program benchmark. It consists of familiar mathematical list relations selected from external manuals and taught examples, followed by independent-from-Rust (but project-authored) adaptations into this solver's finite Horn-clause grammar. It cannot establish transfer to complex Prolog applications, other engines' specific implementation strategies, arithmetic, dynamic predicates, tabling, non-ground general constraints, rational trees, or WAM-generated code. The user-defined `member_of`, `select_one`, `prefix_of` relations are not SWI-Prolog's optimized library implementation.

The Python oracle evaluates expected results by ordinary Python list concatenation/reversal, ordered enumeration, prefix generation and element deletion. That supplies a **separate algorithmic interpretation of finite ground lists**, but neither an independently written Prolog interpreter nor an ISO Prolog compliance oracle. Ordered enumeration is conditional on the author's specific clause order; it cannot be generalized to every Prolog library.

## Specification → live implementation → test

The source-backed task families are `append/3` and two list reversals from *Learn Prolog Now!* chapters 6.1–6.2; member/select/prefix relations follow their published SWI-Prolog documentation. The executable program is only a shallow reconstruction for the subset. The live compiled Rust engine is **exact Gen18** against the retired, unmerged **Gen19** commit, each with `choicepoint-profile` **disabled**, linked into an identical external benchmark harness. The 264-case historical output differential is a same-project regression guard. Cases with repeated queries use only **fully ground goals**, preventing accidental shared query-variable aliasing across repetitions; variable-result and enumeration cases always use `repeat=1`.

All case source SHA256 values, repeated goals, maximum solutions, raw ordered output, five block orders, raw 20-sample arrays and peak process RSS are in both GitHub Actions artifacts. The two-ABI [summary CSV](../tests/rust_external_corpus/results/gen23_two_abi_summary.csv) retains all 14 cells and their external task URLs. No original published source file or author attribution is presented as a separate software executable in this repository.

## Direction, type, controls, resource parity

The principal observable is **direct `solve()` elapsed nanoseconds**, not process startup, parsing, output formatting, peak RAM or allocator calls. The sign convention is Gen19/Gen18. Differences in *semantically equivalent* goals expressed with one-shot versus repeated-ground invocations are not treated as gauge-invariant: work performed and search path differ. The same source/query and Rust 1.85.1 compiler/ABI are matched *within each pair*, and no ELF64+i686 pooling occurs.

Controls `single_fact_r8` and `builtin_true_r8` were predeclared to flag broad unrelated drift, and both passed on each ABI. The false-concat case stayed near parity, which is negative evidence against reducing the mechanism to a mere clause count. Cases with enumeration and multiple solutions produced the independently expected *ordered* output.

Each cell has only five blocks per architecture and is vulnerable to host contention, very short-duration timing noise, generator selection, cache and allocator effects. Signed ratios and complete raw observations are retained, with no clipping, winsorization, p-value harvesting or post-hoc drop. The externally documented list tasks represent one **narrow educational workload family**, not an unbiased industry workload distribution.

## Original sources, version and audit history

- *Learn Prolog Now!* by Patrick Blackburn, Johan Bos and Kristina Striegnitz: [Append §6.1](https://lpn.swi-prolog.org/lpnpage.php?pageid=lpn-htmlse24&pagetype=html); [List reversal §6.2](https://lpn.swi-prolog.org/lpnpage.php?pageid=lpn-htmlse25&pagetype=html).
- SWI-Prolog official [list predicates](https://www.swi-prolog.org/pldoc/man?section=lists), [append/3](https://www.swi-prolog.org/pldoc/man?predicate=append%2F3), [select/3](https://www.swi-prolog.org/pldoc/man?predicate=select%2F3).
- First successful complete [dual-ABI run 44312393215](https://github.com/jesusvilela/gprolog/actions/runs/44312393215); [ELF64 raw artifact 14430164859](https://github.com/jesusvilela/gprolog/actions/runs/44312393215/artifacts/14430164859); [i686 raw artifact 14431096651](https://github.com/jesusvilela/gprolog/actions/runs/44312393215/artifacts/14431096651). GitHub Actions retains artifacts 30 days. Source fixtures, Python oracle and native workflow are versioned in Git.

**First-run correction status:** no semantic/oracle deviation, performance kill, missing cell, or benchmark code repair occurred. Only new source-linked analysis/reporting files followed the first successful run; a final exact-head CI must still pass before any merge.

## Round-trip and bounded next experiment

Question about transfer → externally documented list relations → parser-compatible, author-reconstructed Horn source → independent Python finite-list truth oracle and two pinned Rust engines → matched CLI/timing measurements → case-level effects and negative controls → original question. The round-trip **does not** return evidence about unbiased real-world workloads; that remainder remains explicit.

**Next bounded experiment:** an independently licensed, externally authored Prolog test corpus, with exact upstream commit and source-license retention, split into (a) supported unmodified programs, (b) explicitly adapted programs, (c) unsupported language features. Freeze selection before running the two Rust versions, preserve unsupported negatives, and compare behavior to an independently executed reference Prolog system on the **common semantic subset**. **Kill:** any unsupported extension silently dropped, semantic mismatch not recorded, incomparable source bytes or unavailable independent oracle. **Stop:** no engine optimization, WAM, GC or new memory model until the benchmark's semantics, provenance and coverage are credible.

**Evidence map:** P conditional for Python finite-list algebra; A for semantic relation↔Horn encoding; M for bounded native ratio and ordered-answer observations; H for wider application transfer and causal attribution; S for future external corpus/design; R for rejected Gen19 fixed T2-owned policy and any universal 8–11× slowdown extrapolation.
