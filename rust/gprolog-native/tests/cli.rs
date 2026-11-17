// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
use std::process::Command;

fn binary(args: &[&str]) -> (i32, String, String) {
    let output = Command::new(env!("CARGO_BIN_EXE_gprolog-rs"))
        .args(args)
        .output().expect("Rust-native CLI must be executable");
    (output.status.code().unwrap_or(-1),
     String::from_utf8(output.stdout).unwrap(),
     String::from_utf8(output.stderr).unwrap())
}

#[test]
fn recursive_ancestors_return_ordered_solutions() {
    let source = concat!(env!("CARGO_MANIFEST_DIR"), "/examples/ancestors.pl");
    let (exit, output, errors) = binary(&[source, "ancestor(ada,Who)."]);
    assert_eq!(exit, 0, "{errors}");
    assert_eq!(output, "Who = noah.\nWho = mei.\n");
}

#[test]
fn recursive_append_uses_native_lists() {
    let source = concat!(env!("CARGO_MANIFEST_DIR"), "/examples/lists.pl");
    let (exit, output, errors) = binary(&[source, "append([a,b],[c],Out)."]);
    assert_eq!(exit, 0, "{errors}");
    assert_eq!(output, "Out = [a,b,c].\n");
}

#[test]
fn member_preserves_clause_order_and_rolls_back_bindings() {
    let source = concat!(env!("CARGO_MANIFEST_DIR"), "/examples/lists.pl");
    let (exit, output, errors) = binary(&[source, "member(X,[a,b,c])."]);
    assert_eq!(exit, 0, "{errors}");
    assert_eq!(output, "X = a.\nX = b.\nX = c.\n");
}

#[test]
fn no_matching_fact_is_false_not_spurious_success() {
    let source = concat!(env!("CARGO_MANIFEST_DIR"), "/examples/ancestors.pl");
    let (exit, output, errors) = binary(&[source, "parent(mei,ada)."]);
    assert_eq!(exit, 0, "{errors}");
    assert_eq!(output, "false.\n");
}

#[test]
fn strict_errors_and_budget_are_visible() {
    let source = concat!(env!("CARGO_MANIFEST_DIR"), "/examples/ancestors.pl");
    let (exit, _, errors) = binary(&[source, "ancestor(ada,Who).", "--max-steps", "1"]);
    assert_eq!(exit, 2);
    assert!(errors.contains("exhausted 1 steps"), "{errors}");
    let (exit, _, errors) = binary(&[source, "parent(ada,noah). unknown."]);
    assert_eq!(exit, 2);
    assert!(errors.contains("end of query"), "{errors}");
    let (exit, _, errors) = binary(&[source, "missing(ada)."]);
    assert_eq!(exit, 2);
    assert!(errors.contains("unknown predicate missing/1"), "{errors}");
}

#[test]
fn scoped_cut_and_later_disjunction_from_standalone_cli() {
    let source = concat!(env!("CARGO_MANIFEST_DIR"), "/examples/control.pl");
    let (code, output, errors) = binary(&[source, "commit(X)."]);
    assert_eq!(code, 0, "{errors}");
    assert_eq!(output, "X = a.\n");

    let (code, output, errors) = binary(&[source, "late(X)."]);
    assert_eq!(code, 0, "{errors}");
    assert_eq!(output, "X = a.\nX = b.\n");
}

#[test]
fn child_cut_does_not_prune_caller_disjunction_in_cli() {
    let source = concat!(env!("CARGO_MANIFEST_DIR"), "/examples/control.pl");
    let (code, output, errors) = binary(&[source, "outer(X)."]);
    assert_eq!(code, 0, "{errors}");
    assert_eq!(output, "X = left.\nX = left.\nX = right.\nX = right.\n");
}
