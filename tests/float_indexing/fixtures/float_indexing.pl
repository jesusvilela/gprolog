% Static clause indexing must preserve the same answer sequence as linear search.
% Keep several float keys so a switch table (not merely a direct jump) is used.
pick(1.5, first).
pick(1.5, second).
pick(2.5, two).
pick(3.5, three).
pick(4.5, four).
pick(5.5, five).
pick(6.5, six).
pick(7.5, seven).
pick(-0.0, neg_zero).
pick(0.0, pos_zero).
pick(2, integer).
pick(atom, atom).
pick([x], list).
pick(f(x), structure).
pick(_, wildcard).

% A variable-headed clause must stay between the indexed segments.
interleaved(1.5, before).
interleaved(X, middle) :- X = 1.5.
interleaved(1.5, after).

cut_choice(1.5, first) :- !.
cut_choice(1.5, second).
cut_choice(2.5, other).

:- dynamic(trace/1).

side_effect(1.5, one) :- assertz(trace(one)).
side_effect(1.5, two) :- assertz(trace(two)).
side_effect(2.5, three) :- assertz(trace(three)).

% Each case is a separate predicate: no variables leak between tests.
% In particular the list returned by findall/3 must be fresh in every case.
test_duplicate_float :-
    findall(X, pick(1.5, X), L),
    L == [first, second, wildcard].

test_another_float :-
    findall(X, pick(3.5, X), L),
    L == [three, wildcard].

test_float_absent_fallback :-
    findall(X, pick(19.5, X), L),
    L == [wildcard].

test_signed_zero :-
    findall(X, pick(-0.0, X), L),
    L == [neg_zero, pos_zero, wildcard].

test_signed_zero_reverse :-
    findall(X, pick(0.0, X), L),
    L == [neg_zero, pos_zero, wildcard].

test_integer_fallback :-
    findall(X, pick(2, X), L),
    L == [integer, wildcard].

test_atom_fallback :-
    findall(X, pick(atom, X), L),
    L == [atom, wildcard].

test_list_fallback :-
    findall(X, pick([x], X), L),
    L == [list, wildcard].

test_structure_fallback :-
    findall(X, pick(f(x), X), L),
    L == [structure, wildcard].

test_interleaved_order :-
    findall(X, interleaved(1.5, X), L),
    L == [before, middle, after].

test_cut :-
    findall(X, cut_choice(1.5, X), L),
    L == [first].

test_side_effect_order :-
    retractall(trace(_)),
    findall(X, side_effect(1.5, X), L),
    findall(T, trace(T), Traces),
    L == [one, two],
    Traces == [one, two].

test_variable_call_order :-
    findall(X, pick(X, first), L),
    L == [1.5].

check(Name, Goal) :-
    ( call(Goal) -> format('PASS ~w~n', [Name])
    ; format('FAIL ~w~n', [Name]), halt(1)
    ).

main :-
    check(duplicate_float, test_duplicate_float),
    check(another_float, test_another_float),
    check(float_absent_fallback, test_float_absent_fallback),
    check(signed_zero, test_signed_zero),
    check(signed_zero_reverse, test_signed_zero_reverse),
    check(integer_fallback, test_integer_fallback),
    check(atom_fallback, test_atom_fallback),
    check(list_fallback, test_list_fallback),
    check(structure_fallback, test_structure_fallback),
    check(interleaved_order, test_interleaved_order),
    check(cut, test_cut),
    check(side_effect_order, test_side_effect_order),
    check(variable_call_order, test_variable_call_order),
    format('ALL 13 FLOAT INDEXING CHECKS PASSED~n', []),
    halt.

:- initialization(main).
