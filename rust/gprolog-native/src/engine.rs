// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Standalone Rust depth-first Horn-clause execution (no C or WAM bridge).
use crate::syntax::{Clause, Program, Query, Term};
use std::collections::HashMap;
use std::fmt;

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


/// One mutable binding store per search, never per-choice copied maps.
#[derive(Default)]
struct BindingStore {
    values: HashMap<usize, Term>,
    trail: Vec<usize>,
}
impl BindingStore {
    fn mark(&self) -> usize { self.trail.len() }
    fn bind(&mut self, var: usize, value: Term) {
        debug_assert!(!self.values.contains_key(&var));
        self.values.insert(var, value);
        self.trail.push(var);
    }
    fn undo_to(&mut self, mark: usize) {
        assert!(mark <= self.trail.len(), "invalid trail checkpoint");
        while self.trail.len() > mark {
            let var = self.trail.pop().expect("checked trail length");
            self.values.remove(&var);
        }
    }
}
#[derive(Clone)]
struct PendingGoal {
    term: Term,
    cut_barrier: usize,
}
/// Deferred branch; only the chosen clause is unified with live bindings.
enum Work {
    Resume(Vec<PendingGoal>),
    TryClause {
        goal: Term,
        clause_index: usize,
        continuation: Vec<PendingGoal>,
        invocation_barrier: usize,
    },
}
struct ChoicePoint {
    trail_mark: usize,
    next: Work,
}
fn root(term: &Term, bindings: &BindingStore) -> Term {
    let mut node = term.clone();
    for _ in 0..MAX_RESOLUTION_DEPTH * 1024 {
        match &node {
            Term::Var(id) => {
                if let Some(bound) = bindings.values.get(id) {
                    node = bound.clone();
                    continue;
                }
                return node;
            }
            _ => return node,
        }
    }
    node
}
fn occurs(variable: usize, term: &Term, bindings: &BindingStore, depth: usize) -> bool {
    if depth >= MAX_RESOLUTION_DEPTH { return true; }
    match root(term, bindings) {
        Term::Var(id) => id == variable,
        Term::Struct(_, args) =>
            args.iter().any(|arg| occurs(variable, arg, bindings, depth + 1)),
        _ => false,
    }
}
/// Destructive unifier: caller must undo writes after any failed match.
fn unify(a: &Term, b: &Term, bindings: &mut BindingStore, depth: usize) -> bool {
    if depth >= MAX_RESOLUTION_DEPTH { return false; }
    let lhs = root(a, bindings);
    let rhs = root(b, bindings);
    match (lhs, rhs) {
        (Term::Var(a), Term::Var(b)) if a == b => true,
        (Term::Var(id), value) | (value, Term::Var(id)) => {
            if occurs(id, &value, bindings, 0) { return false; }
            bindings.bind(id, value);
            true
        }
        (Term::Atom(a), Term::Atom(b)) => a == b,
        (Term::Integer(a), Term::Integer(b)) => a == b,
        (Term::Float(a), Term::Float(b)) => a == b,
        (Term::Struct(an, aa), Term::Struct(bn, ba)) => {
            an == bn && aa.len() == ba.len() &&
                aa.iter().zip(ba.iter())
                    .all(|(x, y)| unify(x, y, bindings, depth + 1))
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

fn show_term(term: &Term, bindings: &BindingStore, depth: usize) -> String {
    if depth > MAX_RESOLUTION_DEPTH {
        return "<depth-limit>".into();
    }
    let value = root(term, bindings);
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
                match root(&current, bindings) {
                    Term::Struct(n, args) if n == "." && args.len() == 2 => {
                        cells.push(show_term(&args[0], bindings, depth + 1));
                        current = args[1].clone();
                    }
                    Term::Atom(n) if n == "[]" => {
                        return format!("[{}]", cells.join(","));
                    }
                    tail => {
                        return format!("[{}|{}]",
                            cells.join(","), show_term(&tail, bindings, depth + 1));
                    }
                }
            }
            "<list-depth-limit>".into()
        }
        Term::Struct(name, args) => {
            let values: Vec<_> = args.iter()
                .map(|x| show_term(x, bindings, depth + 1)).collect();
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
    let mut bindings = BindingStore::default();
    let mut alternatives: Vec<ChoicePoint> = Vec::new();
    let mut active = Some(Work::Resume(query.goals.iter().cloned()
        .map(|term| PendingGoal { term, cut_barrier: 0 }).collect()));
    let mut solutions = Vec::new();
    let mut steps = 0;
    loop {
        let task = match active.take() {
            Some(task) => task,
            None => match alternatives.pop() {
                Some(point) => {
                    // Redo from precisely the point saved for that choice.
                    bindings.undo_to(point.trail_mark);
                    point.next
                }
                None => break,
            },
        };
        if steps >= limits.max_steps {
            return Err(SolveError::StepBudgetExceeded(limits.max_steps));
        }
        steps += 1;
        match task {
            Work::TryClause { goal, clause_index, continuation, invocation_barrier } => {
                let fresh = fresh_clause(&program.clauses[clause_index], &mut next_var);
                let mark = bindings.mark();
                if unify(&goal, &fresh.head, &mut bindings, 0) {
                    let mut goals: Vec<PendingGoal> = fresh.body.into_iter()
                        .map(|term| PendingGoal { term, cut_barrier: invocation_barrier })
                        .collect();
                    goals.extend(continuation);
                    active = Some(Work::Resume(goals));
                } else {
                    // A mismatched compound head may have bound a prefix.
                    bindings.undo_to(mark);
                }
            }
            Work::Resume(goals) => {
                if goals.is_empty() {
                    let answers = query.variables.iter().map(|(name, id)| {
                        (name.clone(), show_term(&Term::Var(*id), &bindings, 0))
                    }).collect();
                    solutions.push(Solution { bindings: answers });
                    if solutions.len() >= limits.max_solutions { return Ok(solutions); }
                    // Redo via the nearest pending choicepoint.
                    continue;
                }
                let mut remaining = goals.into_iter();
                let pending = remaining.next().expect("nonempty checked");
                let rest: Vec<PendingGoal> = remaining.collect();
                let cut_barrier = pending.cut_barrier;
                let goal_value = root(&pending.term, &bindings);
                match &goal_value {
                    Term::Atom(name) if name == "!" => {
                        if cut_barrier > alternatives.len() {
                            return Err(SolveError::InvalidCutBarrier {
                                boundary: cut_barrier, available: alternatives.len(),
                            });
                        }
                        // Cut forgets alternatives, NOT live bindings.
                        alternatives.truncate(cut_barrier);
                        active = Some(Work::Resume(rest));
                        continue;
                    }
                    Term::Struct(name, args) if name == "," && args.len() == 2 => {
                        let mut next = Vec::with_capacity(rest.len() + 2);
                        next.push(PendingGoal { term: args[0].clone(), cut_barrier });
                        next.push(PendingGoal { term: args[1].clone(), cut_barrier });
                        next.extend(rest);
                        active = Some(Work::Resume(next));
                        continue;
                    }
                    Term::Struct(name, args) if name == ";" && args.len() == 2 => {
                        let mut right = Vec::with_capacity(rest.len() + 1);
                        right.push(PendingGoal { term: args[1].clone(), cut_barrier });
                        right.extend(rest.iter().cloned());
                        alternatives.push(ChoicePoint {
                            trail_mark: bindings.mark(), next: Work::Resume(right),
                        });
                        let mut left = Vec::with_capacity(rest.len() + 1);
                        left.push(PendingGoal { term: args[0].clone(), cut_barrier });
                        left.extend(rest);
                        active = Some(Work::Resume(left));
                        continue;
                    }
                    Term::Atom(name) if name == "true" => {
                        active = Some(Work::Resume(rest));
                        continue;
                    }
                    Term::Atom(name) if name == "fail" => continue,
                    Term::Struct(name, args) if name == "=" && args.len() == 2 => {
                        let mark = bindings.mark();
                        if unify(&args[0], &args[1], &mut bindings, 0) {
                            active = Some(Work::Resume(rest));
                        } else {
                            bindings.undo_to(mark);
                        }
                        continue;
                    }
                    Term::Struct(name, args) if name == "\\=" && args.len() == 2 => {
                        let mark = bindings.mark();
                        let unifiable = unify(&args[0], &args[1], &mut bindings, 0);
                        // Speculative unification never retains its writes.
                        bindings.undo_to(mark);
                        if !unifiable { active = Some(Work::Resume(rest)); }
                        continue;
                    }
                    _ => {}
                }

                let Some((name, arity)) = goal_value.functor() else {
                    return Err(SolveError::UnsupportedGoal(
                        show_term(&goal_value, &bindings, 0)));
                };
                let clauses: Vec<usize> = program.clauses.iter().enumerate()
                    .filter_map(|(i, clause)|
                        (clause.head.functor() == Some((name, arity))).then_some(i))
                    .collect();
                if clauses.is_empty() {
                    return Err(SolveError::UnknownPredicate(name.into(), arity));
                }
                // Capture the invocation's caller alternatives BEFORE
                // pushing this predicate's alternative clauses.
                let invocation_barrier = alternatives.len();
                let mark = bindings.mark();
                for &index in clauses.iter().skip(1).rev() {
                    alternatives.push(ChoicePoint {
                        trail_mark: mark,
                        next: Work::TryClause {
                            goal: goal_value.clone(), clause_index: index,
                            continuation: rest.clone(), invocation_barrier,
                        },
                    });
                }
                active = Some(Work::TryClause {
                    goal: goal_value, clause_index: clauses[0],
                    continuation: rest, invocation_barrier,
                });
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
    #[test]
    fn undo_trail_restores_partial_compound_unification() {
        let mut store = BindingStore::default();
        let before = store.mark();
        let pattern = Term::Struct("pair".into(), vec![Term::Var(100), Term::Var(100)]);
        let value = Term::Struct("pair".into(),
            vec![Term::Atom("a".into()), Term::Atom("b".into())]);
        assert!(!unify(&pattern, &value, &mut store, 0));
        assert_eq!(store.trail.len(), 1);
        assert!(store.values.contains_key(&100));
        store.undo_to(before);
        assert_eq!(store.mark(), before);
        assert!(store.values.is_empty());
    }

    #[test]
    fn trail_preserves_bindings_before_a_later_checkpoint() {
        let mut store = BindingStore::default();
        assert!(unify(&Term::Var(0), &Term::Var(1), &mut store, 0));
        let saved = store.mark();
        assert!(unify(&Term::Var(1), &Term::Atom("a".into()), &mut store, 0));
        assert_eq!(root(&Term::Var(0), &store), Term::Atom("a".into()));
        store.undo_to(saved);
        assert_eq!(root(&Term::Var(0), &store), Term::Var(1));
        assert!(!store.values.contains_key(&1));
        store.undo_to(0);
        assert_eq!(root(&Term::Var(0), &store), Term::Var(0));
    }

    #[test]
    fn not_unifiable_probe_never_commits_partial_bindings() {
        let p = parse_program("").unwrap();
        let q = parse_query("(X=f(A), X \\= f(b); X=g(c)).", p.next_var).unwrap();
        let result = solve(&p, &q, Limits::default()).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].bindings[0], ("X".into(), "g(c)".into()));
    }

}
