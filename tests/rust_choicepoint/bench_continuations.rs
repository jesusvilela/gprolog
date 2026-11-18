// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! External uninstrumented solve-only A/B witness: same source compiled against
//! frozen Gen16 and Gen17 Rust libraries on each native Linux ABI.
use gprolog_native::{parse_program, parse_query, solve, Limits};
use std::{env, fs, hint::black_box, time::Instant};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // argv: source.pl query repeat warmups samples max_solutions max_steps
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 7 {
        return Err("usage: bench_continuations SOURCE QUERY REPEAT WARMUPS SAMPLES MAX_SOLUTIONS MAX_STEPS".into());
    }
    let program = parse_program(&fs::read_to_string(&args[0])?)?;
    let mut query = parse_query(&args[1], program.next_var)?;
    if query.goals.len() != 1 {
        return Err("benchmark requires exactly one primitive goal".into());
    }
    let repeat: usize = args[2].parse()?;
    let warmups: usize = args[3].parse()?;
    let samples: usize = args[4].parse()?;
    let max_solutions: usize = args[5].parse()?;
    let max_steps: usize = args[6].parse()?;
    if !(1..=128).contains(&repeat) || !(1..=16).contains(&max_solutions)
        || !(1..=40).contains(&samples) || warmups > 40 || max_steps == 0
    {
        return Err("invalid benchmark limits".into());
    }
    let primitive = query.goals[0].clone();
    query.goals = vec![primitive; repeat];
    let limits = Limits { max_steps, max_solutions };
    for _ in 0..warmups {
        black_box(solve(&program, &query, limits)?);
    }
    let mut reference: Option<String> = None;
    let mut nanos: Vec<u128> = Vec::with_capacity(samples);
    for _ in 0..samples {
        let start = Instant::now();
        let result = black_box(solve(&program, &query, limits)?);
        let elapsed = start.elapsed().as_nanos();
        let repr = format!("{result:?}");
        if let Some(expected) = &reference {
            if *expected != repr { return Err("inconsistent ordered answers".into()); }
        } else {
            reference = Some(repr);
        }
        nanos.push(elapsed);
    }
    println!("ANSWERS\t{}", reference.expect("samples positive"));
    for ns in nanos { println!("NS\t{ns}"); }
    Ok(())
}
