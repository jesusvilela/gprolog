// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! External, uninstrumented source harness for Valgrind DHAT and Callgrind.
//! PREPARE and SOLVE modes have identical parsing/query preparation.
//! Valgrind counts are PROCESS-WIDE, NOT solve-only and NOT native timings.
use gprolog_native::{parse_program, parse_query, solve, Limits};
use std::{env, fs, hint::black_box, process};

fn main_run() -> Result<(), Box<dyn std::error::Error>> {
    // MODE SOURCE QUERY REPEATS MAX_SOLUTIONS MAX_STEPS
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 6 {
        return Err("usage: external_profile PREPARE|SOLVE source.pl goal. repeat solutions steps".into());
    }
    let mode = args[0].as_str();
    if mode != "PREPARE" && mode != "SOLVE" {
        return Err("mode must be PREPARE or SOLVE".into());
    }
    let src = fs::read_to_string(&args[1])?;
    let program = parse_program(&src)?;
    let mut query = parse_query(&args[2], program.next_var)?;
    if query.goals.len() != 1 {
        return Err("query must consist of exactly one primitive goal".into());
    }
    let repeats: usize = args[3].parse()?;
    let solutions: usize = args[4].parse()?;
    let max_steps: usize = args[5].parse()?;
    if !(1..=128).contains(&repeats) || !(1..=16).contains(&solutions)
        || max_steps == 0
    {
        return Err("invalid bounded probe input".into());
    }
    query.goals = vec![query.goals[0].clone(); repeats];
    black_box(&program);
    black_box(&query);
    if mode == "PREPARE" {
        println!("PREPARED\t{}\t{}\t{}", query.goals.len(), program.next_var, solutions);
    } else {
        let result = black_box(solve(&program, &query, Limits {
            max_steps, max_solutions: solutions,
        })?);
        println!("ANSWERS\t{result:?}");
    }
    Ok(())
}

fn main() {
    if let Err(e) = main_run() {
        eprintln!("{e}");
        process::exit(2);
    }
}
