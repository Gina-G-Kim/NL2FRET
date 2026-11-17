"""Locations used by the tools.
PACKAGE  the directory of this package (code and the small resources: data/, prompts/, templates*/, fret_check/variable_policy.md).
PROJECT  the project root of a source checkout, which holds the research data (data/), docs/, runs/ and scripts/. It is two levels above the package directory (src/nl2fret);
         set the environment variable NL2FRET_HOME to point to a checkout when the package is installed elsewhere.
"""
import os
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
PROJECT = Path(os.environ.get("NL2FRET_HOME") or PACKAGE.parents[1])
