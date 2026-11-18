"""Frozen Generation 21 paired-workload source bytes.

Do not reorder or modify fixture definitions after data collection;
source SHA256 and ordered answers are part of the provenance envelope.
"""

DEEP = "f(g(h(a,b),k(c,d)),[a,b,c],q(r(s(t))))"
DEEP_BAD = "f(g(h(a,b),k(c,d)),[a,b,c],q(r(s(v))))"


def fixtures():
    facts = lambda t, term="a": f"target({term}).\n" * t
    yield ("first_failure_r128", "target(b).\ntarget(a).\n", "target(a).", 128, 1)
    yield ("first_success_r128", facts(2), "target(a).", 128, 1)
    yield ("first_failure_r32", "target(b).\ntarget(a).\n", "target(a).", 32, 1)
    yield ("first_failure_deep_r64",
           f"target({DEEP_BAD}).\ntarget({DEEP}).\n", f"target({DEEP}).", 64, 1)
    yield ("t3_first_success_r64", facts(3), "target(a).", 64, 1)
    yield ("t1_r128", facts(1), "target(a).", 128, 1)
    yield ("builtin_r128", "", "true.", 128, 1)


def valgrind_fixtures():
    for case in fixtures():
        if case[0] != "first_failure_r32":
            yield case
