"""Frozen Gen23 list-relation corpus with external published TASK provenance.

The executable Horn clauses are freshly reconstructed from standard list
relations to fit the limited Rust parser. They are NOT verbatim SWI files or
an independently authored benchmark. A pure Python list oracle supplies
ordered expected answers without executing either Rust version.
"""
from dataclasses import dataclass
import hashlib

LPN_APPEND = "https://lpn.swi-prolog.org/lpnpage.php?pageid=lpn-htmlse24&pagetype=html"
LPN_REVERSE = "https://lpn.swi-prolog.org/lpnpage.php?pageid=lpn-htmlse25&pagetype=html"
SWI_LISTS = "https://www.swi-prolog.org/pldoc/man?section=lists"

APPEND = (
    "append([],Ys,Ys).\n"
    "append([X|Xs],Ys,[X|Zs]):-append(Xs,Ys,Zs).\n"
)
NAIVE = (
    APPEND
    + "naiverev([],[]).\n"
    + "naiverev([X|Xs],Zs):-naiverev(Xs,Ys),append(Ys,[X],Zs).\n"
)
ACCUMULATOR = (
    "revacc(Xs,Ys):-reva(Xs,[],Ys).\n"
    "reva([],Ys,Ys).\n"
    "reva([X|Xs],Acc,Ys):-reva(Xs,[X|Acc],Ys).\n"
)
MEMBER = (
    "member_of(X,[X|_]).\n"
    "member_of(X,[_|Xs]):-member_of(X,Xs).\n"
)
SELECT = (
    "select_one(X,[X|Ys],Ys).\n"
    "select_one(X,[Y|Ys],[Y|Zs]):-select_one(X,Ys,Zs).\n"
)
PREFIX = (
    "prefix_of([],_).\n"
    "prefix_of([X|Xs],[X|Ys]):-prefix_of(Xs,Ys).\n"
)


def render(items):
    return "[" + ",".join(items) + "]"


def binding(name, items):
    return f"{name} = {render(items)}.\n"


def member_answers(items):
    return "".join(f"X = {x}.\n" for x in items)


def split_answers(items):
    return "".join(
        f"P = {render(items[:i])}, S = {render(items[i:])}.\n"
        for i in range(len(items) + 1)
    )


def select_answers(target, items):
    return "".join(
        binding("R", items[:idx] + items[idx+1:])
        for idx, value in enumerate(items) if value == target
    )


def prefix_answers(items):
    return "".join(binding("P", items[:i]) for i in range(len(items) + 1))


@dataclass(frozen=True)
class Case:
    name: str
    family: str
    source: str
    query: str
    repeat: int
    max_solutions: int
    expected_stdout: str
    reference_url: str
    source_type: str = "reconstructed_standard_Horn_relation"

    @property
    def source_sha256(self):
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()

    def as_metadata(self):
        return {
            "name": self.name, "family": self.family,
            "source_sha256": self.source_sha256, "source_bytes": len(self.source.encode()),
            "query": self.query, "repeats": self.repeat,
            "max_solutions": self.max_solutions, "max_steps": 100000,
            "reference_url": self.reference_url, "source_type": self.source_type,
            "oracle_stdout": self.expected_stdout, "oracle_stderr": "", "oracle_exit": 0,
        }


def cases():
    xs = ["a", "b", "c", "d", "e"]
    four = xs[:4]
    three = xs[:3]
    yield Case(
        "append_ground_r8", "append", APPEND,
        "append([a,b,c],[d,e],[a,b,c,d,e]).", 8, 1, "true.\n", LPN_APPEND
    )
    yield Case(
        "append_answer_r1", "append", APPEND,
        "append([a,b,c],[d,e],R).", 1, 1, binding("R", three + xs[3:]),
        LPN_APPEND
    )
    yield Case(
        "append_split_r1", "append", APPEND,
        "append(P,S,[a,b,c]).", 1, 4, split_answers(three), LPN_APPEND
    )
    yield Case(
        "append_wrong_r1", "append", APPEND,
        "append([a,b,c],[d,e],[a,b,c,d]).", 1, 1, "false.\n", LPN_APPEND
    )
    yield Case(
        "naive_ground_r2", "naive-reverse", NAIVE,
        "naiverev([a,b,c,d],[d,c,b,a]).", 2, 1, "true.\n", LPN_REVERSE
    )
    yield Case(
        "naive_answer_r1", "naive-reverse", NAIVE,
        "naiverev([a,b,c,d,e],R).", 1, 1,
        binding("R", list(reversed(xs))), LPN_REVERSE
    )
    yield Case(
        "acc_ground_r4", "accumulator-reverse", ACCUMULATOR,
        "revacc([a,b,c,d,e],[e,d,c,b,a]).", 4, 1,
        "true.\n", LPN_REVERSE
    )
    yield Case(
        "acc_answer_r1", "accumulator-reverse", ACCUMULATOR,
        "revacc([a,b,c,d,e],R).", 1, 1,
        binding("R", list(reversed(xs))), LPN_REVERSE
    )
    yield Case(
        "member_late_r8", "member", MEMBER,
        "member_of(d,[a,b,c,d]).", 8, 1, "true.\n", SWI_LISTS
    )
    yield Case(
        "member_all_r1", "member", MEMBER,
        "member_of(X,[a,b,c,d]).", 1, 4,
        member_answers(four), SWI_LISTS
    )
    yield Case(
        "select_duplicate_r1", "select", SELECT,
        "select_one(b,[a,b,c,b],R).", 1, 2,
        select_answers("b", ["a","b","c","b"]), SWI_LISTS
    )
    yield Case(
        "prefix_all_r1", "prefix", PREFIX,
        "prefix_of(P,[a,b,c]).", 1, 4,
        prefix_answers(three), SWI_LISTS
    )
    yield Case(
        "single_fact_r8", "internal-null", "fact(ok).\n",
        "fact(ok).", 8, 1, "true.\n", "internal:null",
        source_type="author_null_control"
    )
    yield Case(
        "builtin_true_r8", "internal-null", "",
        "true.", 8, 1, "true.\n", "internal:null",
        source_type="author_null_control"
    )


def self_test():
    items = list(cases())
    assert len(items) == 14
    assert len({x.name for x in items}) == len(items)
    assert sum(c.source_type == "author_null_control" for c in items) == 2
    assert split_answers(["a", "b"]) == (
        "P = [], S = [a,b].\nP = [a], S = [b].\nP = [a,b], S = [].\n"
    )
    assert select_answers("b", ["a","b","c","b"]) == (
        "R = [a,c,b].\nR = [a,b,c].\n"
    )
    assert prefix_answers(["a", "b"]) == (
        "P = [].\nP = [a].\nP = [a,b].\n"
    )
    assert member_answers(["a","b"]) == "X = a.\nX = b.\n"
    for c in items:
        assert c.query.endswith(".")
        assert c.max_solutions > 0 and c.repeat > 0 and len(c.source_sha256) == 64
        assert c.expected_stdout.endswith("\n")
        if c.source_type == "author_null_control":
            assert c.reference_url == "internal:null"
        else:
            assert c.reference_url.startswith("https://")
    print("GEN23 independent Python list algebra oracle: 14 cases / 12 external-source tasks PASS")


if __name__ == "__main__":
    self_test()
