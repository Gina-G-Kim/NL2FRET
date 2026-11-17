"""NL2FRET: natural-language requirements to FRETish through semi-formal templates, judged by NuSMV (docs/V20_BATCH_DESIGN.md)."""
try:
    from importlib.metadata import PackageNotFoundError, version as _version
    try:
        __version__ = _version("nl2fret")
    except PackageNotFoundError:        # run from a source tree that is not installed
        __version__ = "unknown"
except ImportError:                     # pragma: no cover
    __version__ = "unknown"
