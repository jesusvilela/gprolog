# Generation 18 — pull-request source identity correction

18 November 2026. The primary measured run [44280316675](https://github.com/jesusvilela/gprolog/actions/runs/44280316675) was triggered by GitHub's `pull_request` event. The Rust benchmark collected its actual candidate checkout commit using `git rev-parse HEAD`:

- **Candidate checkout SHA:** `778a48a2e6c0e9f1411338a2739c8490b7e49601` (synthetic PR merge commit).
- **Actual PR head at that moment:** `a38f58e019269d9b478da3c6598784b0970b016d`.
- **Frozen Gen17 base parent:** `46b536889e1b461af9e6cddb7f50239eec5697f5`.
- **Both complete Git tree SHAs:** `80293c32a7b8b52de251633700f16f6f908851e1`.

GitHub REST commit inspection confirmed that the synthetic commit has **two parents (base and PR head)** and an *identical source tree* to the actual PR-head commit. Therefore the original timed binaries were constructed from the intended exact source bytes, but reporting the synthetic commit as though it *were* the branch-head SHA would be inaccurate.

**Fix (post-measurement, no engine edit):** CI now tests checked-out tree equality against `github.event.pull_request.head.sha` when applicable. The original benchmark JSON and original run remain unmodified. On push events without a PR merge ref, the tested commit is already the branch head. If future base changes cause tree divergence, the job fails, requiring a new preregistered interpretation rather than silently rebasing evidence.

**Evidence tag:** source-tree identity **A** (verified by Git object identity); measured behavior **M** only for the tested source tree; independent language conformance remains **H**.
