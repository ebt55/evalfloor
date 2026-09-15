"""eval-floor: what score does an answer with no content in it already get?

A scorer is a function of a completion and a target, so a content-free
completion can be fed straight into an eval's real scorer over its real dataset.
No model is called, the cost is zero and the result is deterministic.
"""

__version__ = "0.1.0"

#: The dependency pins this measurement is only valid under. Written into every
#: generated results file. See NOTES.md for why these two versions specifically.
PINNED_INSPECT_AI = "0.3.263"
PINNED_INSPECT_EVALS = "0.20.0"


def installed_pins() -> dict[str, str]:
    """The versions actually installed right now, not the ones we asked for."""
    import importlib.metadata as md

    pins: dict[str, str] = {}
    for dist in ("inspect_ai", "inspect_evals"):
        try:
            pins[dist] = md.version(dist)
        except Exception:
            pins[dist] = "not installed"
    return pins
