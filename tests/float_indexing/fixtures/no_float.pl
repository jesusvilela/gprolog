plain(a, one).
plain(b, two).
plain(3, three).
plain(f(x), four).
main :-
    (plain(a, one), plain(b, two), plain(3, three), plain(f(x), four) ->
        write('NO FLOAT SUCCESS'), nl, halt
    ; halt(1)
    ).
:- initialization(main).
