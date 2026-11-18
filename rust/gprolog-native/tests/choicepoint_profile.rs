// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Exact path counters for the existing Rust-only solver, compiled with
//! --features choicepoint-profile. No production profiling overhead.
#![cfg(feature = "choicepoint-profile")]

use gprolog_native::{parse_program, parse_query, solve, Limits};
use gprolog_native::engine::{clear_choicepoint_profile, read_choicepoint_profile};

fn ground_first_solution(target_facts: usize, repeated_goals: usize) {
    let source = "target(a).\n".repeat(target_facts);
    let program = parse_program(&source).unwrap();
    let mut query = parse_query("target(a).", program.next_var).unwrap();
    let primitive = query.goals[0].clone();
    query.goals = vec![primitive; repeated_goals];
    clear_choicepoint_profile();
    let answers = solve(&program, &query, Limits {
        max_steps: 200_000, max_solutions: 1,
    }).unwrap();
    let observed = read_choicepoint_profile();
    let suffix = repeated_goals * (repeated_goals - 1) / 2;
    let created = (target_facts - 1) * repeated_goals;
    assert_eq!(answers.len(), 1);
    assert_eq!(observed.user_predicate_dispatches, repeated_goals as u64);
    assert_eq!(observed.try_clause_tasks, repeated_goals as u64);
    assert_eq!(observed.work_resume_tasks, repeated_goals as u64 + 1);
    assert_eq!(observed.total_search_steps, (2 * repeated_goals + 1) as u64);
    assert_eq!(observed.resume_suffix_goals_materialized, suffix as u64);
    assert_eq!(observed.clause_choices_pushed, created as u64);
    assert_eq!(observed.clause_continuation_vectors_cloned, created as u64);
    assert_eq!(observed.clause_continuation_goals_cloned,
               ((target_facts - 1) * suffix) as u64);
    assert_eq!(observed.maximum_pending_choices, created);
    assert_eq!(observed.disjunction_choices_pushed, 0);
    assert_eq!(observed.disjunction_rest_goals_cloned, 0);
    assert_eq!(observed.choicepoints_redone, 0);
    assert_eq!(observed.cut_choicepoints_pruned, 0);
    assert_eq!(observed.binding_writes, 0);
    assert_eq!(observed.binding_undo_writes, 0);
}

#[test]
fn analytic_sparse_first_solution_counts() {
    for (target_facts, repeated_goals) in [
        (1, 1), (1, 64), (2, 64), (16, 1), (16, 8),
        (16, 64), (32, 64),
    ] {
        ground_first_solution(target_facts, repeated_goals);
    }
}

#[test]
fn backtracking_uses_a_saved_choice_and_undoes_a_binding() {
    let program = parse_program("p(a). p(b).").unwrap();
    let query = parse_query("p(X).", program.next_var).unwrap();
    clear_choicepoint_profile();
    let answers = solve(&program, &query, Limits {
        max_steps: 100, max_solutions: 2,
    }).unwrap();
    let observed = read_choicepoint_profile();
    let vals: Vec<_> = answers.iter().map(|s| s.bindings[0].1.as_str()).collect();
    assert_eq!(vals, ["a", "b"]);
    assert_eq!(observed.clause_choices_pushed, 1);
    assert_eq!(observed.choicepoints_redone, 1);
    assert_eq!(observed.binding_writes, 2);
    assert_eq!(observed.binding_undo_writes, 1);
}

#[test]
fn cut_prunes_older_choices_but_not_new_disjunction() {
    let program = parse_program(
        "choose(a). choose(b). p(X):-choose(X),!, (Z=one;Z=two). p(c)."
    ).unwrap();
    let query = parse_query("p(X).", program.next_var).unwrap();
    clear_choicepoint_profile();
    let answers = solve(&program, &query, Limits {
        max_steps: 1000, max_solutions: 2,
    }).unwrap();
    let observed = read_choicepoint_profile();
    assert_eq!(answers.len(), 2);
    assert!(answers.iter().all(|s| s.bindings[0].1 == "a"));
    assert_eq!(observed.cut_choicepoints_pruned, 2);
    assert_eq!(observed.disjunction_choices_pushed, 1);
    assert_eq!(observed.choicepoints_redone, 1);
}

#[test]
fn failed_partial_head_unification_is_rolled_back() {
    let program = parse_program("p(f(a,b)). p(f(c,c)).").unwrap();
    let query = parse_query("p(f(X,X)).", program.next_var).unwrap();
    clear_choicepoint_profile();
    let answers = solve(&program, &query, Limits {
        max_steps: 1000, max_solutions: 1,
    }).unwrap();
    let observed = read_choicepoint_profile();
    assert_eq!(answers.len(), 1);
    assert_eq!(answers[0].bindings[0].1, "c");
    assert_eq!(observed.clause_choices_pushed, 1);
    assert_eq!(observed.choicepoints_redone, 1);
    assert_eq!(observed.binding_writes, 2);
    assert_eq!(observed.binding_undo_writes, 1);
}
