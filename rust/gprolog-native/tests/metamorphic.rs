// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Deterministic adversarial tests, independent of the CLI smoke examples.
use gprolog_native::{parse_program, parse_query, solve, Limits};
use std::panic::catch_unwind;

fn output(program: &str, query: &str, limit: usize) -> Vec<String> {
    let p = parse_program(program).unwrap();
    let q = parse_query(query, p.next_var).unwrap();
    solve(&p, &q, Limits { max_steps: 5000, max_solutions: limit }).unwrap()
        .into_iter().flat_map(|sol| sol.bindings)
        .map(|(_, val)| val).collect()
}

#[test]
fn alpha_renaming_and_clause_order_are_observable() {
    let a = "link(a,b). link(a,c). path(X,Y):-link(X,Y). \
             path(X,Y):-link(X,Z),path(Z,Y).";
    let b = "link(a,b). link(a,c). path(P,Q):-link(P,Q). \
             path(P,Q):-link(P,R),path(R,Q).";
    let first = output(a, "path(a,Value).", 10);
    let second = output(b, "path(a,Result).", 10);
    assert_eq!(first, second);
    assert_eq!(first, ["b", "c"]);

    let reordered = "link(a,c). link(a,b). path(X,Y):-link(X,Y).";
    assert_eq!(output(reordered, "path(a,Result).", 10), ["c", "b"]);
}

#[test]
fn bounded_answers_do_not_leak_substitution_across_branches() {
    let src = "item(a). item(b). item(c).";
    assert_eq!(output(src, "item(V).", 2), ["a", "b"]);
    assert_eq!(output(src, "item(V).", 3), ["a", "b", "c"]);
    assert_eq!(output("f(a,a). f(a,b). f(b,b).", "f(X,X).", 10), ["a", "b"]);
}

#[test]
fn controlled_deep_nesting_is_rejected() {
    let mut input = String::from("p(");
    for _ in 0..140 { input.push_str("f("); }
    input.push('a');
    for _ in 0..140 { input.push(')'); }
    input.push_str(").");
    let error = parse_program(&input).unwrap_err();
    assert!(error.message.contains("nesting limit"), "{error}");
}

#[test]
fn seeded_representation_attack_does_not_panic_or_hang() {
    let alphabet = b"abcXYZ012.!?:=,()[]|%\\'_-+ ;\n";
    let mut state: u64 = 0xa74f_5921_1e17_0917;
    for i in 0..512 {
        let length = (i * 11 % 97) + 1;
        let mut text = String::new();
        for _ in 0..length {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            text.push(alphabet[(state as usize) % alphabet.len()] as char);
        }
        assert!(catch_unwind(|| parse_program(&text)).is_ok(),
                "parser panicked on corpus index {i}, {text:?}");
    }
}
