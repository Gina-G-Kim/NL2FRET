"""NL2FRET judging package.

Judge design (see docs/DESIGN.md): LTL equivalence and entailment of a generated FRET past-time formula against the NASA reference formula, in the
style of Danso et al. (SecDev 2026): three NuSMV queries per pair (Equiv, Sound, Compl), N/M when a query fails.
"""
__version__ = "1.2.0"
