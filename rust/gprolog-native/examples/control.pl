% Rust-native control choices, no C runtime or WAM fallback.
choose(a).
choose(b).
commit(X) :- choose(X), !.
commit(c).
late(X) :- !, (X=a;X=b).
outer(X) :- (X=left;X=right), inner(_).
inner(X) :- !, (X=ok;X=also_ok).
inner(other).
