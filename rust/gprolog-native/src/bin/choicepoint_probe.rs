// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Diagnostic-only machine-readable execution counters; no C or WAM bridge.
use gprolog_native::{parse_program, parse_query, solve, Limits};
use gprolog_native::engine::{clear_choicepoint_profile, read_choicepoint_profile};
use std::{env, fs, process};

fn run() -> Result<(), Box<dyn std::error::Error>> {
    // argv: source.pl query. repeated_goals max_solutions max_steps
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 5 {
        return Err("usage: choicepoint-probe SOURCE QUERY REPEAT SOLUTIONS STEPS".into());
    }
    let program = parse_program(&fs::read_to_string(&args[0])?)?;
    let mut query = parse_query(&args[1], program.next_var)?;
    if query.goals.len() != 1 {
        return Err("query must parse to one primitive goal".into());
    }
    let times: usize = args[2].parse()?;
    if !(1..=256).contains(&times) {
        return Err("repeat must be 1..=256".into());
    }
    query.goals = vec![query.goals[0].clone(); times];
    let limits = Limits {
        max_solutions: args[3].parse()?,
        max_steps: args[4].parse()?,
    };
    clear_choicepoint_profile();
    let answers = solve(&program, &query, limits)?;
    let p = read_choicepoint_profile();
    println!("ANSWERS\t{answers:?}");
    let counters: [(&str, u64); 18] = [
        ("user_predicate_dispatches", p.user_predicate_dispatches),
        ("try_clause_tasks", p.try_clause_tasks),
        ("work_resume_tasks", p.work_resume_tasks),
        ("clause_choices_pushed", p.clause_choices_pushed),
        ("disjunction_choices_pushed", p.disjunction_choices_pushed),
        ("clause_continuation_vectors_cloned", p.clause_continuation_vectors_cloned),
        ("clause_continuation_goals_cloned", p.clause_continuation_goals_cloned),
        ("shared_continuation_anchors", p.shared_continuation_anchors),
        ("shared_continuation_handle_clones", p.shared_continuation_handle_clones),
        ("shared_continuation_fallback_copies", p.shared_continuation_fallback_copies),
        ("resume_suffix_goals_materialized", p.resume_suffix_goals_materialized),
        ("disjunction_rest_goals_cloned", p.disjunction_rest_goals_cloned),
        ("choicepoints_redone", p.choicepoints_redone),
        ("cut_choicepoints_pruned", p.cut_choicepoints_pruned),
        ("binding_writes", p.binding_writes),
        ("binding_undo_writes", p.binding_undo_writes),
        ("maximum_pending_choices", p.maximum_pending_choices as u64),
        ("total_search_steps", p.total_search_steps),
    ];
    for (key, value) in counters {
        println!("COUNT\t{key}\t{value}");
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        process::exit(2);
    }
}
