member(X,[X|_]).
member(X,[_|Tail]) :- member(X,Tail).
append([],Ys,Ys).
append([X|Xs],Ys,[X|Zs]) :- append(Xs,Ys,Zs).
