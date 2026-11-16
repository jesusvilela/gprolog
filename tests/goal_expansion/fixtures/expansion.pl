% All aliases below deliberately lack runtime definitions. Successful execution
% of their callers therefore demonstrates that the compiler applied the hook.
goal_expansion(alias(X), X=expanded).
goal_expansion(square(X, Y), Y is X*X).
goal_expansion(chain(X), middle(X)).
goal_expansion(middle(X), X=chained).
goal_expansion(identity, identity).
goal_expansion(cycle_a, cycle_b).
goal_expansion(cycle_b, cycle_a).
goal_expansion(wrapped(X), (wrapped(X), true)).
goal_expansion(choice, first).
goal_expansion(choice, second).
goal_expansion(bad_bind(X), true) :- X=bound.
goal_expansion(bad_alias(X, Y), true) :- X=Y.
goal_expansion(failed(X), _) :- X=bound, fail.
goal_expansion(inherited(X), X=inherited).
goal_expansion(explode, _) :- throw(skipped_goal_was_expanded).

term_expansion(make_generated, (generated(X) :- alias(X))).
term_expansion(make_two, [(generated_one(X) :- alias(X)),
                        (generated_two(X) :- chain(X))]).

native_result(X) :- alias(X).
specialized_square(Y) :- square(7, Y).
chain_result(X) :- chain(X).
conjunction(X, Y) :- alias(X), chain(Y).
disjunction(X) :- (alias(X); chain(X)).
conditional(X) :- (fail -> alias(X); chain(X)).
soft_conditional(X) :- (true *-> alias(X); chain(X)).
negation :- \+ (alias(X), X=wrong).
meta_call(X) :- call(alias(X)).
meta_once(X) :- once(alias(X)).
meta_catch(X) :- catch(throw(ball), ball, alias(X)).
cut_scope(X) :- (alias(X), !).
cut_scope(fallback).
variable_call(G) :- G.
sample(X) --> {alias(X)}.
make_generated.
make_two.

:- if(fail).
skipped :- explode.
:- endif.

% Arguments to arbitrary predicates are data, even when they look like goals.
data(alias(X), X).

check(Name, Goal) :-
    ( call(Goal) -> format('PASS ~w~n', [Name])
    ; format('FAIL ~w~n', [Name]), halt(1)
    ).

main :-
    check(native, native_result(expanded)),
    check(arithmetic_specialization, specialized_square(49)),
    check(chain, chain_result(chained)),
    check(conjunction, conjunction(expanded, chained)),
    check(disjunction, (findall(X, disjunction(X), Choices), Choices==[expanded,chained])),
    check(conditional, conditional(chained)),
    check(soft_cut, soft_conditional(expanded)),
    check(negation, negation),
    check(call, meta_call(expanded)),
    check(once, meta_once(expanded)),
    check(catch, meta_catch(expanded)),
    check(cut_scope, (findall(X, cut_scope(X), Cuts), Cuts==[expanded])),
    check(variable_call, variable_call(true)),
    check(dcg, phrase(sample(expanded), [])),
    check(term_expansion, generated(expanded)),
    check(term_expansion_list, (generated_one(expanded), generated_two(chained))),
    check(data, (data(alias(V), V), var(V))),
    check(runtime_expand, expand_goal(alias(V), V=expanded)),
    check(runtime_variable, (expand_goal(V, W), V==W, var(V))),
    check(runtime_identity, expand_goal(identity, identity)),
    check(runtime_cycle, expand_goal(cycle_a, cycle_a)),
    check(runtime_wrapper, expand_goal(wrapped(V), (wrapped(V), true))),
    check(first_solution, (findall(E, expand_goal(choice, E), Es), Es==[first])),
    check(steadfast, \+ expand_goal(choice, second)),
    check(no_hook_match, expand_goal(untouched(V), untouched(V))),
    check(failed_hook_unwinds, (expand_goal(failed(V), failed(V)), var(V))),
    check(reject_binding,
          catch((expand_goal(bad_bind(_), _), fail),
                error(permission_error(modify, goal_expansion_input, _), _), true)),
    check(reject_aliasing,
          catch((expand_goal(bad_alias(_, _), _), fail),
                error(permission_error(modify, goal_expansion_input, _), _), true)),
    consult('inherit_target.pl'),
    check(inherited_consult, inherited_result(inherited)),
    format('ALL 29 GOAL EXPANSION CHECKS PASSED~n', []),
    halt.

:- initialization(main).
