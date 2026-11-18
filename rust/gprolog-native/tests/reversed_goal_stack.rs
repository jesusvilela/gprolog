// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Generation 18: verify execution order is invariant under reversed storage.
use gprolog_native::{parse_program, parse_query, solve, Limits, SolveError};

fn answers(program: &str, query: &str, limit: usize)
    -> Result<Vec<Vec<(String, String)>>, SolveError>
{
    let p = parse_program(program).unwrap();
    let q = parse_query(query, p.next_var).unwrap();
    solve(&p, &q, Limits { max_steps: 20_000, max_solutions: limit })
        .map(|xs| xs.into_iter().map(|s| s.bindings).collect())
}

#[test]
fn sequential_goals_execute_in_source_order() {
    assert!(answers("", "X=a, X=b.", 16).unwrap().is_empty());
    let observed = answers("", "X=a, Y=b, Z=c.", 16).unwrap();
    assert_eq!(observed.len(), 1);
    assert_eq!(observed[0], [
        ("X".into(), "a".into()),
        ("Y".into(), "b".into()),
        ("Z".into(), "c".into()),
    ]);
}

#[test]
fn clause_body_executes_before_callers_suffix() {
    let src = "a(x). a(y). b(y). p(X):-a(X),b(X).";
    let got = answers(src, "p(Z),Z=y.", 16).unwrap();
    assert_eq!(got.len(), 1);
    assert_eq!(got[0][0], ("Z".into(), "y".into()));
}

#[test]
fn nested_conjunction_disjunction_preserves_four_answer_order() {
    let observed = answers("", "(X=a;X=b),(Y=one;Y=two).", 8).unwrap();
    let pairs: Vec<_> = observed.iter().map(|s|
        (s[0].1.as_str(), s[1].1.as_str())).collect();
    assert_eq!(pairs, [
        ("a", "one"), ("a", "two"),
        ("b", "one"), ("b", "two"),
    ]);
}

#[test]
fn grouped_vs_flat_conjunction_produces_same_order() {
    let src = "p(a). p(b). q(k). q(l).";
    let left = answers(src, "p(X),q(Y),true.", 16).unwrap();
    let right = answers(src, "(p(X),q(Y)),true.", 16).unwrap();
    assert_eq!(left, right);
}

#[test]
fn cut_eliminates_previous_choices_not_postcut_alternatives() {
    let src = "choose(a). choose(b). p(X,Y):-choose(X),!, (Y=one;Y=two). p(c,three).";
    let observed = answers(src, "p(X,Y).", 10).unwrap();
    assert_eq!(observed.len(), 2);
    let pairs: Vec<_> = observed.iter().map(|s|
        (s[0].1.as_str(), s[1].1.as_str())).collect();
    assert_eq!(pairs, [("a", "one"), ("a", "two")]);
}

#[test]
fn long_straight_line_builtins_have_original_step_budget() {
    let program = parse_program("").unwrap();
    let mut query = parse_query("true.", program.next_var).unwrap();
    query.goals = vec![query.goals[0].clone(); 128];
    assert!(matches!(solve(&program, &query, Limits {
        max_steps: 128, max_solutions: 1
    }), Err(SolveError::StepBudgetExceeded(128))));
    assert_eq!(solve(&program, &query, Limits {
        max_steps: 129, max_solutions: 1
    }).unwrap().len(), 1);
}

#[test]
fn cut_and_trail_restoration_do_not_depend_on_storage_orientation() {
    let src = "v(f(a,b)). v(f(c,c)). v(f(d,d)).";
    let found = answers(src, "v(f(X,X)), X \\= c; X=ok.", 16).unwrap();
    assert_eq!(found.len(), 2);
    assert_eq!(found[0][0], ("X".into(), "d".into()));
    assert_eq!(found[1][0], ("X".into(), "ok".into()));
}
