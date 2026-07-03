"""
Winter AI -- Mercury-style determinism checker.

HONEST NOTE ON THIS FILE (please read):
Mercury (the logic/functional language) has no maintained apt/deb package for
current Ubuntu/Debian, and the official compiler (mmc) is bootstrapped from
Mercury itself -- building it from source takes 30-60+ minutes and a large
toolchain, which is not practical inside a Render Docker build. Rather than
silently faking a "Mercury" label on ordinary Python (which is what the
previous draft of this project did for several engines), this module is
openly a Python re-implementation of the one Mercury concept that is genuinely
useful here: Mercury's *determinism categories* (det / semidet / multi /
nondet / failure), used to classify how many valid answers a query produced.

If you want the *real* Mercury compiler in the image, see
api/engines/mercury/BUILD_REAL_MERCURY.md for an optional, slow, source-build
Docker stage you can opt into.
"""

from enum import Enum


class Determinism(str, Enum):
    DET = "det"          # exactly one solution, always succeeds
    SEMIDET = "semidet"  # zero or one solution
    MULTI = "multi"      # one or more solutions, always succeeds
    NONDET = "nondet"    # zero or more solutions
    FAILURE = "failure"  # never succeeds


def classify(matches: list) -> dict:
    """Classify a list of candidate answers the way Mercury's mode system
    would classify a predicate call, based on how many solutions it has."""
    n = len(matches)
    if n == 0:
        mode = Determinism.FAILURE
    elif n == 1:
        mode = Determinism.DET
    else:
        mode = Determinism.NONDET

    return {
        "engine": "Mercury (Python re-implementation -- see BUILD_REAL_MERCURY.md)",
        "determinism": mode.value,
        "solution_count": n,
        "trace": f":- pred respond(Query::in, Answer::out) is {mode.value}.  % {n} solution(s) found",
    }
