// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Direct Rust-native finite Horn-clause Prolog engine.
//! Intentionally does not link, load, or require the C GNU Prolog runtime.
pub mod syntax;
pub mod engine;

pub use engine::{solve, Limits, Solution, SolveError};
pub use syntax::{parse_program, parse_query, Clause, Program, Query, SyntaxError, Term};
