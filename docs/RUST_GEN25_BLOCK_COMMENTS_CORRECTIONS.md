# Generation 25 — correction ledger

**18 November 2026 — workflow parsing only.** The first Generation 25 push
run [44370165971](https://github.com/jesusvilela/gprolog/actions/runs/44370165971)
was rejected by GitHub Actions with zero jobs: the workflow's unquoted
display name included the token `: ` as a plain YAML scalar, which
violated YAML syntax. No Rust tests, SWI reference, source compilation
or historical differential executed in that invalid workflow. The fix
quotes only the display name. It changes no Rust source, source hash,
test fixture, implementation invariant or scientific acceptance gate.

The repository's other existing Rust workflows may run because the
parser source changed. They remain separate check requirements and
should not be bypassed if relevant checks fail.
