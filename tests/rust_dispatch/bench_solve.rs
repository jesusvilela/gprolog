// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! External, shared benchmark harness compiled once against each immutable
//! Rust-native library; never included in timed code or baseline source.
use gprolog_native::{parse_program, parse_query, solve, Limits};
use std::{env, fs, hint::black_box, time::Instant};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // source.pl  single-goal-query  repeated-goals  warmups  samples
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 5 {
        return Err("usage: bench_solve source.pl 'target(a).' goals warmups samples".into());
    }
    let program = parse_program(&fs::read_to_string(&args[0])?)?;
    let mut query = parse_query(&args[1], program.next_var)?;
    if query.goals.len() != 1 {
        return Err("benchmark expects one primitive goal (no conjunction)".into());
    }
    let repeat: usize = args[2].parse()?;
    let warmups: usize = args[3].parse()?;
    let samples: usize = args[4].parse()?;
    if repeat == 0 || samples == 0 || repeat > 256 {
        return Err("invalid repetitions (1..256) or sample count".into());
    }
    let primitive = query.goals[0].clone();
    query.goals = vec![primitive; repeat];
    let limits = Limits { max_steps: 200_000, max_solutions: 1 };
    for _ in 0..warmups {
        let _ = black_box(solve(&program, &query, limits)?);
    }
    let mut reference: Option<String> = None;
    let mut nanos = Vec::with_capacity(samples);
    for _ in 0..samples {
        let begin = Instant::now();
        let result = black_box(solve(&program, &query, limits)?);
        let ns = begin.elapsed().as_nanos();
        let representation = format!("{result:?}");
        if let Some(expected) = &reference {
            if expected != &representation { return Err("unstable repeated answers".into()); }
        } else {
            reference = Some(representation);
        }
        nanos.push(ns);
    }
    println!("ANSWERS\t{}", reference.unwrap_or_default());
    for value in nanos { println!("NS\t{value}"); }
    Ok(())
}
