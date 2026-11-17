// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Deterministic rollback and cut challenges for the mutable Rust trail.
use gprolog_native::{parse_program, parse_query, solve, Limits, Solution, SolveError};

fn answers(source: &str, query_text: &str, limit: usize) -> Vec<Solution> {
    let program = parse_program(source).expect("valid program");
    let query = parse_query(query_text, program.next_var).expect("valid query");
    solve(&program, &query, Limits { max_steps: 100_000, max_solutions: limit })
        .expect("finite search")
}
fn values(source: &str, query: &str, name: &str) -> Vec<String> {
    answers(source, query, 512).iter().map(|s|
        s.bindings.iter().find(|(n, _)| n == name)
            .expect("named variable").1.clone()
    ).collect()
}
#[test]
fn failed_partial_binding_does_not_poison_disjunction() {
    assert_eq!(values("", "(X=a,X=b;X=c).", "X"), ["c"]);
    assert_eq!(values("", "(X=f(a),X=f(b);X=g(c)).", "X"), ["g(c)"]);
    assert_eq!(values("", "(X=f(a),X=f(b);X=f(d)),X=f(d).", "X"), ["f(d)"]);
}
#[test]
fn not_unifiable_probe_is_always_untrailed() {
    assert_eq!(values("", "(X=a,X \\= a;X=b).", "X"), ["b"]);
    assert_eq!(values("", "X=a,X \\= b.", "X"), ["a"]);
    assert_eq!(values("", "(X=f(A),X \\= f(b);X=g(c)).", "X"), ["g(c)"]);
}
#[test]
fn candidate_clause_partial_match_rolls_back_before_redo() {
    let src = "p(f(a,b)). p(f(a,a)).";
    assert_eq!(values(src, "p(f(X,X)).", "X"), ["a"]);
    let src = "p(f(a,b)). p(f(c,c)). p(f(d,d)).";
    assert_eq!(values(src, "p(f(X,X)).", "X"), ["c", "d"]);
}
#[test]
fn alias_bindings_trail_across_multiple_levels() {
    assert_eq!(values("", "X=Y,Y=Z,Z=a.", "X"), ["a"]);
    assert_eq!(values("", "(X=Y,Y=a,fail;X=b).", "X"), ["b"]);
    assert_eq!(values("", "(X=f(Y),Y=a,fail;X=f(b)).", "X"), ["f(b)"]);
}
#[test]
fn occurs_check_and_recursive_structural_bindings() {
    assert!(answers("", "X=f(Y),Y=g(X).", 16).is_empty());
    assert_eq!(values("", "X=f(Y),Y=g(a).", "X"), ["f(g(a))"]);
    assert_eq!(values("", "X=f(Y),Y=g(a),X=f(g(a)).", "X"), ["f(g(a))"]);
}
#[test]
fn nested_choicepoints_do_not_leak_between_caller_and_child() {
    let src = "p(a).p(b).q(one).q(two).r(X,Y):-p(X),q(Y).";
    let result = answers(src, "r(X,Y).", 32);
    let pairs: Vec<_> = result.iter()
        .map(|r| (r.bindings[0].1.clone(), r.bindings[1].1.clone())).collect();
    assert_eq!(pairs, [("a".into(),"one".into()),("a".into(),"two".into()),
                       ("b".into(),"one".into()),("b".into(),"two".into())]);
}
#[test]
fn cut_with_newer_choices_does_not_leave_stale_bindings() {
    let src = "choose(a).choose(b). \
        p(X):-choose(X),!, (Y=one;Y=two), X=a. p(c).";
    assert_eq!(values(src, "p(V).", "V"), ["a", "a"]);
    let src = "inner(Z):-!, (Z=a;Z=b). inner(c). \
               outer(X):-(X=one;X=two),inner(_).";
    assert_eq!(values(src, "outer(X).", "X"), ["one","one","two","two"]);
}
#[test]
fn many_clause_alternatives_commit_without_map_snapshots() {
    let mut src = String::new();
    for i in 0..250 { src.push_str(&format!("p(k{i}).\n")); }
    let seq = values(&src, "p(X).", "X");
    assert_eq!(seq.len(), 250);
    assert_eq!(seq[0], "k0");
    assert_eq!(seq[249], "k249");
    assert_eq!(seq[127], "k127");
}
#[test]
fn repeated_solver_invocation_has_no_cross_query_state() {
    let program = parse_program("p(a).p(b).").unwrap();
    let query = parse_query("p(X).", program.next_var).unwrap();
    for _ in 0..8 {
        let outcome = solve(&program, &query, Limits::default()).unwrap();
        assert_eq!(outcome.len(), 2);
        assert_eq!(outcome[0].bindings[0].1, "a");
        assert_eq!(outcome[1].bindings[0].1, "b");
    }
}
#[test]
fn search_limit_error_stays_visible() {
    let p = parse_program("loop:-loop.").unwrap();
    let q = parse_query("loop.",p.next_var).unwrap();
    let err = solve(&p,&q,Limits {max_steps:10,max_solutions:1}).unwrap_err();
    assert!(matches!(err,SolveError::StepBudgetExceeded(10)));
}
