// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Generation 14: indexed predicate dispatch must leave search semantics intact.
use gprolog_native::{parse_program, parse_query, solve, Limits, SolveError};

fn run(source: &str, query: &str, steps: usize, solutions: usize)
    -> Result<Vec<Vec<(String, String)>>, SolveError>
{
    let p = parse_program(source).unwrap();
    let q = parse_query(query, p.next_var).unwrap();
    solve(&p, &q, Limits { max_steps: steps, max_solutions: solutions })
        .map(|items| items.into_iter().map(|item| item.bindings).collect())
}

#[test]
fn interleaved_predicates_and_duplicate_heads_retain_source_order() {
    let src = "q(x). p(a). r(m). p(b). q(y). p(a). p(c).";
    let vals = run(src, "p(X).", 1000, 20).unwrap();
    assert_eq!(vals.into_iter().map(|a| a[0].1.clone()).collect::<Vec<_>>(),
               ["a", "b", "a", "c"]);
}

#[test]
fn predicate_arity_and_unknown_are_distinguished() {
    let src = "p. p(a). p(a,b). q(z).";
    assert_eq!(run(src, "p.", 1000, 5).unwrap().len(), 1);
    assert_eq!(run(src, "p(X).", 1000, 5).unwrap()[0][0].1, "a");
    assert_eq!(run(src, "p(X,Y).", 1000, 5).unwrap().len(), 1);
    assert!(matches!(run(src, "p(X,Y,Z).", 1000, 5),
                     Err(SolveError::UnknownPredicate(_, 3))));
}

#[test]
fn known_predicate_with_impossible_heads_fails_not_unknown() {
    assert!(run("p(a). q(b). p(c).", "p(z).", 1000, 5).unwrap().is_empty());
}

#[test]
fn cut_does_not_prune_caller_and_keeps_choices_after_cut() {
    let src = "noise(1). pick(a). noise(2). pick(b). \
               inner(X):-!, (X=one;X=two). inner(three). \
               outer(P,X):-pick(P),inner(X).";
    let result = run(src, "outer(P,X).", 10000, 10).unwrap();
    let pairs: Vec<_> = result.into_iter()
        .map(|r| (r[0].1.clone(), r[1].1.clone())).collect();
    assert_eq!(pairs, [("a".into(),"one".into()),("a".into(),"two".into()),
                       ("b".into(),"one".into()),("b".into(),"two".into())]);
}

#[test]
fn indexing_does_not_alter_step_budget_or_residual_variable_identity() {
    // Several clauses with the right functor but impossible heads MUST still
    // enter TryClause. First-argument pruning is deliberately not enabled.
    let src = "noise(x). p(a,0). p(b,1). noise(y). p(c,2). p(d,3).";
    let out = run(src, "p(z,Y).", 1000, 10).unwrap();
    assert!(out.is_empty());
    assert!(matches!(run(src, "p(z,Y).", 1, 10),
                     Err(SolveError::StepBudgetExceeded(1))));
    let residual = run("noise(x). p(X). noise(y).", "p(Y).", 1000, 5).unwrap();
    assert_eq!(residual.len(), 1);
    assert!(residual[0][0].1.starts_with("_G"));
}

#[test]
fn per_solve_index_observes_public_program_mutations() {
    let mut p = parse_program("p(a).").unwrap();
    let q = parse_query("p(X).", p.next_var).unwrap();
    assert_eq!(solve(&p, &q, Limits::default()).unwrap().len(), 1);
    p.clauses.push(parse_program("p(b).").unwrap().clauses.remove(0));
    let answers = solve(&p, &q, Limits::default()).unwrap();
    assert_eq!(answers.into_iter().map(|s| s.bindings[0].1.clone())
                   .collect::<Vec<_>>(), ["a", "b"]);
}

#[test]
fn deterministic_interleaving_matches_contiguous_target_clauses() {
    let mut split = String::new();
    let mut contiguous = String::new();
    for i in 0..64 {
        split.push_str(&format!("noise{}(a). p(k{}). ", i, i));
        contiguous.push_str(&format!("p(k{}). ", i));
    }
    let left = run(&split, "p(X).", 1000, 64).unwrap();
    let right = run(&contiguous, "p(X).", 1000, 64).unwrap();
    assert_eq!(left, right);
}
