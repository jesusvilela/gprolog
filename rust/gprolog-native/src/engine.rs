// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Standalone Rust depth-first Horn-clause execution (no C or WAM bridge).
use crate::syntax::{Clause, Program, Query, Term};
use std::collections::HashMap;
use std::fmt;

type Substitution = HashMap<usize, Term>;
const MAX_RESOLUTION_DEPTH: usize = 256;

#[derive(Clone, Copy, Debug)]
pub struct Limits {
    pub max_steps: usize,
    pub max_solutions: usize,
}

impl Default for Limits {
    fn default() -> Self {
        Self { max_steps: 100_000, max_solutions: 256 }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Solution {
    pub bindings: Vec<(String, String)>,
}

#[derive(Clone, Debug, PartialEq)]
pub enum SolveError {
    InvalidLimits,
    StepBudgetExceeded(usize),
    UnknownPredicate(String, usize),
    UnsupportedGoal(String),
    InvalidCutBarrier { boundary: usize, available: usize },
}

impl fmt::Display for SolveError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidLimits => write!(f, "search limits must be positive"),
            Self::StepBudgetExceeded(limit) => write!(f, "search exhausted {limit} steps"),
            Self::UnknownPredicate(name, arity) =>
                write!(f, "unknown predicate {name}/{arity}"),
            Self::UnsupportedGoal(goal) =>
                write!(f, "unsupported callable goal: {goal}"),
            Self::InvalidCutBarrier { boundary, available } =>
                write!(f, "cut barrier {boundary} exceeds {available} remaining alternatives"),
        }
    }
}
impl std::error::Error for SolveError {}

#[derive(Clone)]
struct PendingGoal {
    term: Term,
    // Number of pre-existing choice alternatives when owning predicate
    // was invoked. Cut may remove later alternatives, not caller choices.
    cut_barrier: usize,
}

#[derive(Clone)]
struct State {
    goals: Vec<PendingGoal>,
    subst: Substitution,
}

fn root(term: &Term, subst: &Substitution) -> Term {
    let mut node = term.clone();
    // A finite occurs-check prevents cycles at binding time. The extra
    // bound is defensive against corrupt/future substitution input.
    for _ in 0..MAX_RESOLUTION_DEPTH * 1024 {
        if let Term::Var(id) = &node {
            if let Some(bound) = subst.get(id) {
                node = bound.clone();
                continue;
            }
        }
        break;
    }
    node
}

fn occurs(variable: usize, term: &Term, subst: &Substitution, depth: usize) -> bool {
    if depth >= MAX_RESOLUTION_DEPTH {
        // Conservative rejection rather than accepting a potentially
        // recursive substitution we have not inspected.
        return true;
    }
    match root(term, subst) {
        Term::Var(id) => id == variable,
        Term::Struct(_, args) =>
            args.iter().any(|arg| occurs(variable, arg, subst, depth + 1)),
        _ => false,
    }
}

fn unify(a: &Term, b: &Term, subst: &mut Substitution, depth: usize) -> bool {
    if depth >= MAX_RESOLUTION_DEPTH { return false; }
    let lhs = root(a, subst);
    let rhs = root(b, subst);
    match (lhs, rhs) {
        (Term::Var(a), Term::Var(b)) if a == b => true,
        (Term::Var(id), value) | (value, Term::Var(id)) => {
            if occurs(id, &value, subst, 0) { return false; }
            subst.insert(id, value);
            true
        }
        (Term::Atom(a), Term::Atom(b)) => a == b,
        (Term::Integer(a), Term::Integer(b)) => a == b,
        (Term::Float(a), Term::Float(b)) => {
            // Preserve binary64 identity for this first direct interpreter.
            // A more complete ISO-number semantics audit is still required.
            a == b
        }
        (Term::Struct(an, aa), Term::Struct(bn, ba)) => {
            an == bn && aa.len() == ba.len() &&
                aa.iter().zip(ba.iter())
                    .all(|(x, y)| unify(x, y, subst, depth + 1))
        }
        _ => false,
    }
}

fn fresh_term(
    term: &Term,
    mapping: &mut HashMap<usize, usize>,
    next: &mut usize,
) -> Term {
    match term {
        Term::Var(old) => {
            Term::Var(*mapping.entry(*old).or_insert_with(|| {
                let var = *next;
                *next += 1;
                var
            }))
        }
        Term::Struct(name, args) =>
            Term::Struct(name.clone(),
                args.iter().map(|t| fresh_term(t, mapping, next)).collect()),
        other => other.clone(),
    }
}

fn fresh_clause(clause: &Clause, next: &mut usize) -> Clause {
    let mut mapping = HashMap::new();
    Clause {
        head: fresh_term(&clause.head, &mut mapping, next),
        body: clause.body.iter()
            .map(|t| fresh_term(t, &mut mapping, next))
            .collect(),
    }
}

fn show_atom(name: &str) -> String {
    if name == "[]" { return "[]".into(); }
    let simple = name.as_bytes().first().is_some_and(u8::is_ascii_lowercase)
        && name.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_');
    if simple {
        name.to_string()
    } else {
        format!("'{}'", name.replace('\'', "''"))
    }
}

fn show_term(term: &Term, subst: &Substitution, depth: usize) -> String {
    if depth > MAX_RESOLUTION_DEPTH {
        return "<depth-limit>".into();
    }
    let value = root(term, subst);
    match value {
        Term::Var(id) => format!("_G{id}"),
        Term::Atom(name) => show_atom(&name),
        Term::Integer(n) => n.to_string(),
        Term::Float(bits) => {
            let mut text = f64::from_bits(bits).to_string();
            if !text.contains('.') && !text.contains('e') && !text.contains('E') {
                text.push_str(".0");
            }
            text
        }
        Term::Struct(name, args) if name == "." && args.len() == 2 => {
            let mut cells = Vec::new();
            let mut current = Term::Struct(name, args);
            for _ in 0..MAX_RESOLUTION_DEPTH {
                match root(&current, subst) {
                    Term::Struct(n, args) if n == "." && args.len() == 2 => {
                        cells.push(show_term(&args[0], subst, depth + 1));
                        current = args[1].clone();
                    }
                    Term::Atom(n) if n == "[]" => {
                        return format!("[{}]", cells.join(","));
                    }
                    tail => {
                        return format!("[{}|{}]",
                            cells.join(","), show_term(&tail, subst, depth + 1));
                    }
                }
            }
            "<list-depth-limit>".into()
        }
        Term::Struct(name, args) => {
            let values: Vec<_> = args.iter()
                .map(|x| show_term(x, subst, depth + 1)).collect();
            format!("{}({})", show_atom(&name), values.join(","))
        }
    }
}

pub fn solve(program: &Program, query: &Query, limits: Limits)
    -> Result<Vec<Solution>, SolveError>
{
    if limits.max_solutions == 0 || limits.max_steps == 0 {
        return Err(SolveError::InvalidLimits);
    }
    let mut next_var = query.next_var.max(program.next_var);
    let mut stack = vec![State {
        goals: query.goals.iter().cloned()
            .map(|term| PendingGoal { term, cut_barrier: 0 })
            .collect(),
        subst: HashMap::new(),
    }];
    let mut solutions = Vec::new();
    let mut steps = 0;
    while let Some(state) = stack.pop() {
        if steps >= limits.max_steps {
            return Err(SolveError::StepBudgetExceeded(limits.max_steps));
        }
        steps += 1;
        if state.goals.is_empty() {
            let bindings = query.variables.iter().map(|(name, id)| {
                (name.clone(), show_term(&Term::Var(*id), &state.subst, 0))
            }).collect();
            solutions.push(Solution { bindings });
            if solutions.len() >= limits.max_solutions { return Ok(solutions); }
            continue;
        }
        let mut remaining = state.goals.into_iter();
        let pending = remaining.next().expect("nonempty checked");
        let rest: Vec<PendingGoal> = remaining.collect();
        let cut_barrier = pending.cut_barrier;
        let goal_value = root(&pending.term, &state.subst);
        match &goal_value {
            Term::Atom(name) if name == "!" => {
                if cut_barrier > stack.len() {
                    return Err(SolveError::InvalidCutBarrier {
                        boundary: cut_barrier,
                        available: stack.len(),
                    });
                }
                // This discards choices created since invocation entry,
                // including earlier body disjunctions and same-predicate
                // alternative clauses, while preserving caller choices.
                stack.truncate(cut_barrier);
                stack.push(State { goals: rest, subst: state.subst });
                continue;
            }
            Term::Struct(name, args) if name == "," && args.len() == 2 => {
                let mut goals = Vec::with_capacity(rest.len() + 2);
                goals.push(PendingGoal {
                    term: args[0].clone(),
                    cut_barrier,
                });
                goals.push(PendingGoal {
                    term: args[1].clone(),
                    cut_barrier,
                });
                goals.extend(rest);
                stack.push(State { goals, subst: state.subst });
                continue;
            }
            Term::Struct(name, args) if name == ";" && args.len() == 2 => {
                let mut right = Vec::with_capacity(rest.len() + 1);
                right.push(PendingGoal {
                    term: args[1].clone(),
                    cut_barrier,
                });
                right.extend(rest.iter().cloned());
                stack.push(State {
                    goals: right,
                    subst: state.subst.clone(),
                });
                let mut left = Vec::with_capacity(rest.len() + 1);
                left.push(PendingGoal {
                    term: args[0].clone(),
                    cut_barrier,
                });
                left.extend(rest);
                stack.push(State {
                    goals: left,
                    subst: state.subst,
                });
                continue;
            }
            Term::Atom(name) if name == "true" => {
                stack.push(State { goals: rest, subst: state.subst });
                continue;
            }
            Term::Atom(name) if name == "fail" => continue,
            Term::Struct(name, args) if name == "=" && args.len() == 2 => {
                let mut subst = state.subst;
                if unify(&args[0], &args[1], &mut subst, 0) {
                    stack.push(State { goals: rest, subst });
                }
                continue;
            }
            Term::Struct(name, args) if name == "\\=" && args.len() == 2 => {
                let mut tentative = state.subst.clone();
                if !unify(&args[0], &args[1], &mut tentative, 0) {
                    stack.push(State { goals: rest, subst: state.subst });
                }
                continue;
            }
            _ => {}
        }

        let Some((name, arity)) = goal_value.functor() else {
            return Err(SolveError::UnsupportedGoal(
                show_term(&goal_value, &state.subst, 0)));
        };
        let clauses: Vec<_> = program.clauses.iter()
            .filter(|clause| clause.head.functor() == Some((name, arity)))
            .collect();
        if clauses.is_empty() {
            return Err(SolveError::UnknownPredicate(name.into(), arity));
        }
        // The barrier belongs to THIS invocation, before pushing its
        // alternative clauses; caller continuation goals keep their own
        // previous barriers (never blindly relabel the entire rest).
        let invocation_barrier = stack.len();
        for clause in clauses.into_iter().rev() {
            let new_clause = fresh_clause(clause, &mut next_var);
            let mut new_subst = state.subst.clone();
            if unify(&goal_value, &new_clause.head, &mut new_subst, 0) {
                let mut goals: Vec<PendingGoal> = new_clause.body.into_iter()
                    .map(|term| PendingGoal {
                        term,
                        cut_barrier: invocation_barrier,
                    })
                    .collect();
                goals.extend(rest.iter().cloned());
                stack.push(State { goals, subst: new_subst });
            }
        }
    }
    Ok(solutions)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::syntax::{parse_program, parse_query};

    fn answers(program: &str, query: &str) -> Vec<Solution> {
        let program = parse_program(program).unwrap();
        let query = parse_query(query, program.next_var).unwrap();
        solve(&program, &query, Limits::default()).unwrap()
    }

    #[test]
    fn ancestors_backtrack_in_source_order() {
        let src = "parent(ada,noah). parent(noah,mei). \
            ancestor(X,Y):-parent(X,Y). \
            ancestor(X,Y):-parent(X,Z),ancestor(Z,Y).";
        let found = answers(src, "ancestor(ada,Who).");
        assert_eq!(found.len(), 2);
        assert_eq!(found[0].bindings[0], ("Who".into(), "noah".into()));
        assert_eq!(found[1].bindings[0], ("Who".into(), "mei".into()));
    }

    #[test]
    fn list_member_and_append() {
        let member = "member(X,[X|_]). member(X,[_|T]):-member(X,T).";
        let found = answers(member, "member(V,[a,b,c]).");
        let vals: Vec<_> = found.iter().map(|x| x.bindings[0].1.as_str()).collect();
        assert_eq!(vals, ["a", "b", "c"]);
        let append = "append([],Ys,Ys). \
          append([X|Xs],Ys,[X|Zs]):-append(Xs,Ys,Zs).";
        let found = answers(append, "append([a,b],[c],Out).");
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].bindings[0], ("Out".into(), "[a,b,c]".into()));
    }

    #[test]
    fn repeated_variables_and_local_clause_scopes() {
        let found = answers("pair(a,a). pair(a,b).", "pair(X,X).");
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].bindings[0].1, "a");
        let found = answers("a(X):-b(X). b(z). b(k).", "a(Who).");
        assert_eq!(found.len(), 2);
    }

    #[test]
    fn equality_inequality_and_occurs_check() {
        assert_eq!(answers("", "X = f(a), X \\= f(b).").len(), 1);
        assert_eq!(answers("", "X = f(X).").len(), 0);
        assert_eq!(answers("", "X = a, X \\= a.").len(), 0);
        assert_eq!(answers("", "true.").len(), 1);
        assert_eq!(answers("", "fail.").len(), 0);
    }

    #[test]
    fn depth_first_choice_limit_and_budget() {
        let p = parse_program("nat(z). nat(s(X)):-nat(X).").unwrap();
        let q = parse_query("nat(V).", p.next_var).unwrap();
        let result = solve(&p, &q, Limits { max_steps: 100, max_solutions: 3 }).unwrap();
        assert_eq!(result.len(), 3);
        let q = parse_query("loop.", p.next_var).unwrap();
        assert!(matches!(solve(&p, &q, Limits::default()),
                         Err(SolveError::UnknownPredicate(_, 0))));
        let p = parse_program("loop:-loop.").unwrap();
        let q = parse_query("loop.", p.next_var).unwrap();
        assert!(matches!(solve(&p, &q, Limits {max_steps: 10, max_solutions: 1}),
                         Err(SolveError::StepBudgetExceeded(10))));
    }

    #[test]
    fn floats_and_failure_rollback() {
        assert_eq!(answers("f(-0.0). f(0.0).", "f(X).").len(), 2);
        assert_eq!(answers("p(f(a,a)). p(f(a,b)).", "p(f(X,X)).").len(), 1);
        assert_eq!(answers("", "X = 1, X = 2.").len(), 0);
    }
}
