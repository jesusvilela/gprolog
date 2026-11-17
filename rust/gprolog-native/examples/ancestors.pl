% Plain definite Horn clauses, preserved source order.
parent(ada, noah).
parent(noah, mei).
ancestor(X,Y) :- parent(X,Y).
ancestor(X,Y) :- parent(X,Z), ancestor(Z,Y).
