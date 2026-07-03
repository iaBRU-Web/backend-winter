% =============================================================================
% Winter AI -- Prolog Knowledge & Translation Engine (SWI-Prolog)
% Real facts + rules with unification and backtracking. Notably demonstrates
% *transitive* translation (en -> fr -> rw) that a flat lookup table cannot
% do on its own: Prolog chains translate/3 facts via a recursive rule.
% Invoked as: swipl knowledge.pl <lang> <token1> <token2> ...
% =============================================================================

:- initialization(main, main).

% ---- Intent keyword facts --------------------------------------------------
keyword(greeting, en, hello).  keyword(greeting, en, hi).
keyword(greeting, fr, bonjour). keyword(greeting, fr, salut).
keyword(greeting, rw, muraho).  keyword(greeting, rw, bite).

keyword(thanks, en, thanks).   keyword(thanks, en, thank).
keyword(thanks, fr, merci).
keyword(thanks, rw, murakoze).

keyword(identity, en, name).   keyword(identity, en, who).
keyword(identity, fr, appelles).
keyword(identity, rw, witwa).

% ---- Direct translation facts (base cases) --------------------------------
translate(en, hello, fr, bonjour).
translate(en, hello, rw, muraho).
translate(en, thanks, fr, merci).
translate(en, thanks, rw, murakoze).
translate(en, friend, fr, ami).
translate(en, friend, rw, inshuti).
translate(en, water, fr, eau).
translate(en, water, rw, amazi).
translate(en, good, fr, bon).
translate(en, good, rw, byiza).
translate(fr, bonjour, rw, muraho).
translate(fr, merci, rw, murakoze).

% Symmetric closure
translate_sym(L1, W1, L2, W2) :- translate(L1, W1, L2, W2).
translate_sym(L1, W1, L2, W2) :- translate(L2, W2, L1, W1).

% Transitive closure: chain through an intermediate language (real recursion,
% real backtracking -- this is the payoff of using Prolog instead of a dict).
translate_chain(L1, W1, L2, W2) :- translate_sym(L1, W1, L2, W2).
translate_chain(L1, W1, L2, W2) :-
    translate_sym(L1, W1, Mid, WMid),
    Mid \= L2,
    translate_sym(Mid, WMid, L2, W2).

% ---- Query drivers ----------------------------------------------------------
matched_intents(Lang, Tokens, Intents) :-
    findall(I, (member(T, Tokens), keyword(I, Lang, T)), Raw),
    list_to_set(Raw, Intents).

find_translation(Word, Target, Result) :-
    ( translate_chain(en, Word, Target, Result) -> true
    ; translate_chain(fr, Word, Target, Result) -> true
    ; translate_chain(rw, Word, Target, Result) -> true
    ; Result = none ).

main(Argv) :-
    ( Argv = [LangAtom|TokenAtoms] -> true ; LangAtom = en, TokenAtoms = [] ),
    atom_string(LangA, LangAtom), Lang = LangA,
    maplist(atom_string, TokenAtomsA, TokenAtoms),
    ( matched_intents(Lang, TokenAtomsA, Intents) -> true ; Intents = [] ),
    format("ENGINE: Prolog (SWI-Prolog)~n"),
    format("MATCHED_INTENTS: ~w~n", [Intents]),
    ( TokenAtomsA = [FirstTok|_], Lang \= en, find_translation(FirstTok, en, EnWord), EnWord \= none
      -> format("BACK_TRANSLATION: ~w -> en:~w~n", [FirstTok, EnWord])
      ;  format("BACK_TRANSLATION: none~n")
    ),
    format("TRACE: findall(I, (member(T,Tokens), keyword(I,~w,T)), Raw), list_to_set(Raw, Intents)~n", [Lang]),
    halt.
main(_) :- halt.
