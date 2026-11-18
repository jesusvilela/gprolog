# Generation 25 — parser-only nested block comment compatibility
Pre-registered 18 November 2026; no engine/search/ownership changes.

## Evidence and source of requirement

Generation 24 [PR #24](https://github.com/jesusvilela/gprolog/pull/24) used a genuine public-domain upstream [SWI-Prolog `demo/likes.pl`](https://github.com/SWI-Prolog/swipl-devel/blob/111385b90852dade2b772d074cc55fefa20ee1a9/demo/likes.pl), pinned Git blob `88f3d2edcb0fb68c99b559676e5982b3780715f6`. Under both released Gen18 and rejected Gen19, the exact original file failed Rust lexing at byte 440 because `/* ... */` comments were unsupported. A separately labeled comment-only derivative matched **12/12 ordered live SWI-Prolog 9.0.4 outputs** in both engines; the **264-case** historical Rust differential also passed. This is a measured parsing obstruction, not a proof of broad language conformance.

SWI-Prolog documents **nested block comments** (an extension to ISO handling): [Nested comments](https://www.swi-prolog.org/pldoc/man?section=nestedcomments). Scope this feature to correct lexical skipping of both ordinary and nested `/* ... */` delimiters while preserving the original `%` single-line comment behavior and quoted atoms.

## Exact intervention (one tokenizer branch)

In `rust/gprolog-native/src/syntax.rs`, after whitespace/`%` comment handling but before token production, recognize the byte pair `/*`. Advance a bounded depth counter on nested openers and decrement on closers until it reaches zero. Skip its content as whitespace and resume normal tokenization. Reject EOF before the closing delimiter with a syntax error at the **opening byte offset**. Do not recognize comment markers inside quoted atoms. Do not accept standalone slash, alter numeric/string literals, or modify the grammar of ordinary goals and clauses.

**Out of scope:** nested-comment tokenizer is not an ISO standards certificate; no dynamic predicates, arithmetic, full Unicode lexical support, rational trees, term heap, WAM, garbage collection, continuation ownership, or choicepoint algorithm changes.

## Frozen independent semantic and structural gates

1. **Unit known answers:** simple `/* */` and `/** Pldoc */` source comments; nested comments; `%` inside block; block after a clause and at EOF; malformed unterminated outer/inner comments; slash syntax still rejected; quoted atoms containing literal `/* ... */` unchanged.
2. **Metamorphic behavior:** inserting block comments between clauses or tokens in supported programs leaves the parsed solutions and variable-binding ordering unchanged; comments in the *query* are also accepted.
3. **Full unmodified upstream source:** run all 12 Generation 24 queries **directly on original 922-byte public-domain `likes.pl`, without generating a derivative**. Reference is independent SWI-Prolog on the exact same original source (the version is recorded). Require identical ordered stdout, stderr and exit. A separate comment-only normalized file may be used as a within-Rust control, but cannot replace the original.
4. **Regression:** compare the new engine CLI to frozen released Gen18 on the historical **264 already-supported input cases**, requiring exact stdout/stderr/exit; compare existing compiler and feature-gated Rust tests. The old interpreter's expected rejection of upstream original is a control, not counted as a semantic regression.
5. **Resource parity:** pinned Rust 1.85.1 release, same upstream source blob SHA and limits (`max_solutions=32`, `max_steps=100000`) across reference and candidate. The source programs include no untrusted dynamic execution; validate original public-domain license. No benchmark time or aggregate speed claim.

## Promotion and kill conditions

- **Prediction H:** the direct, unmodified upstream program now parses and matches all 12 live SWI ordered answers, while historical 264 cases and tokenizer negative tests remain unchanged.
- **Primary metric:** exact 12-query independent SWI versus original-source new-Rust output vector, plus source hash, parser boundary tests and 264-case parity.
- **Kill:** original source hash/permission mismatch, nested-comment error, swallowed quoted delimiters, unterminated-block acceptance, any original-source SWI output mismatch, regression in previously supported programs, missing independent reference or source identification.
- **Stop:** do not introduce a new ownership policy or extend this parser patch to unrelated syntax features to rescue a mismatch. Retire a failed feature if needed.
- **Promotion:** M for bounded source acceptance and ordered outputs; P conditional for lexer invariants tested under concrete cases; H for general ISO/SWI Prolog compatibility. Merge only code, tests, protocol, strict execution evidence and correction ledger on a fully green exact PR head.

## Evidence governance

P/A/M/H/S/R: P refers only to any exact code property that receives a proof (none is promised); A contains byte-oriented comment and quoted-atom lexical assumptions; M is the post-execution parser and oracle observations; H generality beyond tests; S full language architecture outside scope; R the Gen19 eager-owned optimization and any statement that parser support alone proves semantic compatibility.

No external author independently authored the **new lexer patch**. The SWI executable and upstream file supply independent semantic witnesses only for the tested subset; project-authored tests remain correlated.
