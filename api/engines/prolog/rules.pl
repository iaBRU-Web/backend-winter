% Winter AI - Prolog decision engine
% Real forward-chaining logic run by SWI-Prolog (swipl), not simulated.
% Called as: swipl -q -g main -t halt rules.pl -- "<lowercased prompt text>"
%
% Classifies the user's intent and a lightweight sentiment score by
% matching tokens against word-fact tables. Prints one line of JSON to
% stdout so the Python orchestrator can parse it without extra deps.

:- set_prolog_flag(encoding, utf8).

% ---- Word tables (facts) --------------------------------------------------
greeting_word(hello). greeting_word(hi). greeting_word(hey). greeting_word(greetings).
greeting_word(bonjour). greeting_word(salut). greeting_word(bonsoir).
greeting_word(muraho). greeting_word(bite). greeting_word(mwaramutse). greeting_word(mwiriwe).

thanks_word(thank). thanks_word(thanks). thanks_word(thx). thanks_word(merci).
thanks_word(murakoze). thanks_word(urakoze).

wellbeing_word(how). wellbeing_word(ca). wellbeing_word(va). wellbeing_word(amakuru).

farewell_word(bye). farewell_word(goodbye). farewell_word(revoir). farewell_word(murabeho).

identity_word(who). identity_word(name). identity_word(qui). identity_word(nde). identity_word(witwa).

capability_word(can). capability_word(help). capability_word(peux). capability_word(ubasha). capability_word(mfasha).

architecture_word(work). architecture_word(architecture). architecture_word(layers). architecture_word(engines).
architecture_word(fonctionnes). architecture_word(ukora).

positive_word(good). positive_word(great). positive_word(love). positive_word(happy). positive_word(excellent).
positive_word(bon). positive_word(bien). positive_word(super). positive_word(meza). positive_word(byiza).

negative_word(bad). negative_word(terrible). negative_word(hate). negative_word(sad). negative_word(angry).
negative_word(mauvais). negative_word(triste). negative_word(mbi).

% ---- Helpers ---------------------------------------------------------------
split_tokens(Text, Tokens) :-
    split_string(Text, " \t\n,.!?;:", " \t\n,.!?;:", Parts0),
    exclude(==(""), Parts0, Parts),
    maplist([S,A]>>atom_string(A, S), Parts, Tokens).

any_match(Tokens, PredName) :-
    Goal =.. [PredName, T],
    member(T, Tokens),
    call(Goal), !.

count_matches(Tokens, PredName, Count) :-
    Goal =.. [PredName, T],
    aggregate_all(count, (member(T, Tokens), call(Goal)), Count).

% ---- Intent classification (ordered, first match wins - like a cond) -------
classify(Tokens, greeting)     :- any_match(Tokens, greeting_word), !.
classify(Tokens, thanks)       :- any_match(Tokens, thanks_word), !.
classify(Tokens, wellbeing)    :- any_match(Tokens, wellbeing_word), !.
classify(Tokens, farewell)     :- any_match(Tokens, farewell_word), !.
classify(Tokens, identity)     :- any_match(Tokens, identity_word), !.
classify(Tokens, capabilities) :- any_match(Tokens, capability_word), !.
classify(Tokens, architecture) :- any_match(Tokens, architecture_word), !.
classify(_,      knowledge_query).

sentiment(Tokens, positive) :-
    count_matches(Tokens, positive_word, P),
    count_matches(Tokens, negative_word, N),
    P > N, !.
sentiment(Tokens, negative) :-
    count_matches(Tokens, positive_word, P),
    count_matches(Tokens, negative_word, N),
    N > P, !.
sentiment(_, neutral).

json_escape(In, Out) :-
    string_chars(In, Cs),
    maplist(escape_char, Cs, Escaped),
    atomic_list_concat(Escaped, Out).
escape_char('"', '\\"') :- !.
escape_char('\\', '\\\\') :- !.
escape_char(C, C).

% ---- Entry point -------------------------------------------------------------
main :-
    current_prolog_flag(argv, Argv),
    ( Argv = [RawText|_] -> true ; RawText = "" ),
    string_lower(RawText, Lower),
    split_tokens(Lower, Tokens),
    classify(Tokens, Intent),
    sentiment(Tokens, Sentiment),
    length(Tokens, NTokens),
    json_escape(Lower, SafeLower),
    format("{\"intent\": \"~w\", \"sentiment\": \"~w\", \"tokens\": ~w, \"engine\": \"prolog\", \"input\": \"~w\"}~n",
           [Intent, Sentiment, NTokens, SafeLower]).
