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

side_effect(1.5, one) :- assertz(trace(one)).
side_effect(1.5, two) :- assertz(trace(two)).
side_effect(2.5, three) :- assertz(trace(three)).

check(Name, Goal) :-
    (call(Goal) -> format('PASS ~w~n', [Name])
    ; format('FAIL ~w~n', [Name]), halt(1)
    ).

main :-
    check(duplicate_float,
        (findall(X, pick(1.5, X), L),
         L == [first, second, wildcard])),
    check(another_float,
        (findall(X, pick(3.5, X), L), format('TRACE float 3.5 answers=~w~n', [L]), L == [three, wildcard])),
    check(float_absent_fallback,
        (findall(X, pick(19.5, X), L), L == [wildcard])),
    check(signed_zero,
        (findall(X, pick(-0.0, X), L),
         L == [neg_zero, pos_zero, wildcard])),
    check(signed_zero_reverse,
        (findall(X, pick(0.0, X), L),
         L == [neg_zero, pos_zero, wildcard])),
    check(integer_fallback,
        (findall(X, pick(2, X), L), L == [integer, wildcard])),
    check(atom_fallback,
        (findall(X, pick(atom, X), L), L == [atom, wildcard])),
    check(list_fallback,
        (findall(X, pick([x], X), L), L == [list, wildcard])),
    check(structure_fallback,
        (findall(X, pick(f(x), X), L), L == [structure, wildcard])),
    check(interleaved_order,
        (findall(X, interleaved(1.5, X), L),
         L == [before, middle, after])),
    check(cut,
        (findall(X, cut_choice(1.5, X), L), L == [first])),
    check(side_effect_order,
        (retractall(trace(_)),
         findall(X, side_effect(1.5, X), L),
         findall(T, trace(T), Traces),
         L == [one, two], Traces == [one, two])),
    check(variable_call_order,
        (findall(X, pick(X, first), L), L == [1.5])),
    format('ALL 13 FLOAT INDEXING CHECKS PASSED~n', []),
    halt.

:- initialization(main).
