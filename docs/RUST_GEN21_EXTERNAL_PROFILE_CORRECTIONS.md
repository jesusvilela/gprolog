# Generation 21 correction ledger — CI setup, not changed scientific prediction

18 November 2026. The initial [push workflow 44302879486](https://github.com/jesusvilela/gprolog/actions/runs/44302879486) passed: both native Rust ABIs, 264 strict CLI parity cases each, and the separate ELF64 third-party Valgrind 3.22.0 six-cell profiling.

A duplicate pull_request-triggered job on the same source tree remained longer in the `apt-get install valgrind` step. The workflow was changed **only** to check if Valgrind was already installed, use `--no-install-recommends`, and bound `apt` commands with `timeout` (commit `8523fb60`). No interpreter source, fixture, benchmark gate, Valgrind invocation, sampling rule or interpretation was altered. The original successful run retains its original source SHA and raw output; no later-run identity is invented.

A new final-head verification is required after report/manifest additions. The independent experimental-author limitation and process-wide profiling overhead remain unresolved rather than being suppressed.
