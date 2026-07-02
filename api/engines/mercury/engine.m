% Winter AI - Mercury determinism-check engine (reference implementation)
%
% NOTE: The Mercury compiler (`mmc`) is not available through the standard
% Debian/Ubuntu apt repositories that Render.com (and most Docker base
% images) can reach, so this module is not compiled or executed at runtime
% in this deployment. It is kept as the authoritative reference for the
% algorithm; `../mercury/determinism.py` is a faithful, tested Python port
% of the exact same logic and is what actually runs in the pipeline.
%
% If you have the Mercury toolchain available (e.g. building from source,
% or via a custom base image with the Mercury PPA), you can compile this
% with: mmc --make engine

:- module engine.
:- interface.
:- import_module io.
:- import_module float.

:- pred determinism_check(float::in, float::in, float::in, string::out,
    io::di, io::uo) is det.

:- implementation.
:- import_module string.

% top_score:      best retrieval match score
% second_score:   second-best retrieval match score
% confidence_min: minimum score to consider an answer "confident"
%
% Ambiguous when the top two scores are nearly tied (within 0.05);
% low-confidence when the top score falls below confidence_min.
determinism_check(TopScore, SecondScore, ConfidenceMin, Result, !IO) :-
    Gap = TopScore - SecondScore,
    ( if Gap < 0.05, TopScore > 0.0 then
        Result = "ambiguous"
    else if TopScore < ConfidenceMin then
        Result = "low_confidence"
    else
        Result = "confident"
    ),
    io.write_string("Winter AI: determinism check -> ", !IO),
    io.write_string(Result, !IO),
    io.nl(!IO).

:- pred main(io::di, io::uo) is det.
main(!IO) :-
    determinism_check(0.42, 0.10, 0.15, _Result, !IO).
