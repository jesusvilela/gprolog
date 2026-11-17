// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
use gprolog_native::{parse_program, parse_query, solve, Limits};
use std::{env, fs, process};

const USAGE: &str = "Usage: gprolog-rs <source.pl> '<query.>' [--max-steps N] [--max-solutions N]\nRust-native finite Horn subset: conjunction (,), disjunction (;), and invocation-scoped cut (!).\nUnsupported: if-then (->), arithmetic, rational trees, dynamic code, finite-domain constraints.";

fn execute() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() == 1 && (args[0] == "--help" || args[0] == "-h") {
        println!("{USAGE}");
        return Ok(());
    }
    if args.len() < 2 { return Err(USAGE.into()); }
    let mut limits = Limits::default();
    let mut index = 2;
    while index < args.len() {
        if index + 1 >= args.len() { return Err("missing numeric flag value".into()); }
        let value = args[index + 1].parse::<usize>()
            .map_err(|_| format!("invalid limit for {}", args[index]))?;
        match args[index].as_str() {
            "--max-steps" => limits.max_steps = value,
            "--max-solutions" => limits.max_solutions = value,
            _ => return Err(format!("unknown flag: {}", args[index])),
        }
        index += 2;
    }
    let metadata = fs::metadata(&args[0])
        .map_err(|e| format!("cannot inspect {}: {e}", args[0]))?;
    if metadata.len() > gprolog_native::syntax::MAX_SOURCE_BYTES as u64 {
        return Err("source exceeds size limit".into());
    }
    let text = fs::read_to_string(&args[0])
        .map_err(|e| format!("cannot read {}: {e}", args[0]))?;
    let program = parse_program(&text).map_err(|e| e.to_string())?;
    let query = parse_query(&args[1], program.next_var).map_err(|e| e.to_string())?;
    let solutions = solve(&program, &query, limits).map_err(|e| e.to_string())?;
    if solutions.is_empty() {
        println!("false.");
    } else {
        for solution in solutions {
            if solution.bindings.is_empty() {
                println!("true.");
            } else {
                println!("{}.", solution.bindings.iter().map(|(name, value)|
                    format!("{name} = {value}")).collect::<Vec<_>>().join(", "));
            }
        }
    }
    Ok(())
}
fn main() {
    if let Err(error) = execute() {
        eprintln!("{error}");
        process::exit(2);
    }
}
