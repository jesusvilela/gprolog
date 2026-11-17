// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Predeclared operational cut scope and disjunction semantics tests.
use gprolog_native::{parse_program, parse_query, solve, Limits};

fn values(source: &str, query: &str, variable: &str) -> Vec<String> {
    let program = parse_program(source).expect("valid test program");
    let query = parse_query(query, program.next_var).expect("valid test query");
    solve(&program, &query, Limits { max_steps: 10000, max_solutions: 20 })
        .expect("finite search")
        .iter()
        .map(|solution| solution.bindings.iter()
            .find(|(name, _)| name == variable)
            .expect("named solution variable").1.clone())
        .collect()
}

fn count(source: &str, query: &str) -> usize {
    let program = parse_program(source).unwrap();
    let query = parse_query(query, program.next_var).unwrap();
    solve(&program, &query, Limits { max_steps: 10000, max_solutions: 20 })
        .unwrap().len()
}

#[test]
fn root_cut_prunes_remaining_top_level_alternatives() {
    assert_eq!(values("p(a). p(b).", "p(X), !.", "X"), ["a"]);
    assert_eq!(values("", "X=a;X=b.", "X"), ["a", "b"]);
    assert_eq!(values("", "(X=a;X=b), !.", "X"), ["a"]);
}

#[test]
fn disjunction_binds_less_tightly_than_conjunction() {
    assert_eq!(values("", "X=a,fail;X=b.", "X"), ["b"]);
    assert_eq!(values("", "X=a;X=b,fail.", "X"), ["a"]);
    assert_eq!(count("", "(X=a;X=b),fail."), 0);
    assert_eq!(values("", "X=a ; (X=b, fail).", "X"), ["a"]);
}

#[test]
fn cut_commits_to_first_clause_and_previous_disjunction_branch() {
    let src = "p(X):-(X=a;X=b),!. p(c).";
    assert_eq!(values(src, "p(X).", "X"), ["a"]);
    assert_eq!(count("p:-!,fail. p.", "p."), 0);
    assert_eq!(count("p:- (true,!,fail;true).", "p."), 0);
}

#[test]
fn cut_before_disjunction_preserves_newer_alternatives() {
    let src = "p(X):-!, (X=a;X=b). p(c).";
    assert_eq!(values(src, "p(X).", "X"), ["a", "b"]);
    assert_eq!(values("", "!, (X=a;X=b).", "X"), ["a", "b"]);
}

#[test]
fn child_cut_preserves_caller_choicepoints_and_continuations() {
    let src = "inner(X):-!, (X=a;X=b). inner(c). \
               outer(Z):-(Z=one;Z=two),inner(_).";
    assert_eq!(
        values(src, "outer(Z).", "Z"),
        ["one", "one", "two", "two"]
    );
    let scoped = "inner(X):-!,X=inside. inner(outside). \
                  outer(X):-inner(X);X=outside.";
    assert_eq!(values(scoped, "outer(X).", "X"), ["inside", "outside"]);
}

#[test]
fn caller_cut_discards_deeper_call_alternatives_and_other_clauses() {
    let src = "pick(X):-(X=a;X=b). \
               outer(X):-pick(X),!. outer(c).";
    assert_eq!(values(src, "outer(X).", "X"), ["a"]);
    let src = "p(a). p(b). outer(X):-p(X),!,true. outer(c).";
    assert_eq!(values(src, "outer(X).", "X"), ["a"]);
}

#[test]
fn cut_in_unreached_branch_has_no_effect() {
    assert_eq!(count("p:-(fail, !; true).", "p."), 1);
    assert_eq!(values("", "(fail,!,X=a ; X=b).", "X"), ["b"]);
    assert_eq!(values("", "(X=a;X=b), (true;fail).", "X"), ["a", "b"]);
}

#[test]
fn no_variable_capture_after_cut_and_redo() {
    let a = "inner(X):-(X=a;X=b),!. outer(Y):-inner(Y). outer(c).";
    let b = "inner(T):-(T=a;T=b),!. outer(Q):-inner(Q). outer(c).";
    assert_eq!(values(a, "outer(V).", "V"), ["a", "c"]);
    assert_eq!(values(a, "outer(V).", "V"), values(b, "outer(V).", "V"));
}

#[test]
fn syntax_rejects_unsupported_control_and_unfinished_groups() {
    for text in ["p:- (true;).", "p:- (true,).", "p:- (true;false.",
                 "p:- true -> fail.", "p:- true!fail."] {
        assert!(parse_program(text).is_err(), "should reject {text}");
    }
}

#[test]
fn existing_horn_behavior_still_passes() {
    let src = "parent(ada,noah). parent(noah,mei). \
               ancestor(X,Y):-parent(X,Y). \
               ancestor(X,Y):-parent(X,Z),ancestor(Z,Y).";
    assert_eq!(values(src, "ancestor(ada,Who).", "Who"), ["noah", "mei"]);
    assert_eq!(values("member(X,[X|_]). member(X,[_|T]):-member(X,T).",
                      "member(V,[a,b,c]).", "V"), ["a","b","c"]);
}
