:- initialization(main, main).

main :-
    current_prolog_flag(argv, [Term|_]),
    atom_string(Term, S),
    catch(
        (
            open('api/brain.txt', read, Stream),
            read_string(Stream, _, BrainContent),
            close(Stream),
            (
                sub_string(BrainContent, _, _, _, S)
            ->  format("found: ~w~n", [S])
            ;   format("not found: ~w~n", [S])
            )
        ),
        _Error,
        format("error reading brain.txt~n")
    ).
