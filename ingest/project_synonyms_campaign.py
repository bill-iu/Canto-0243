"""Shim — moved to tools.campaigns.project_synonyms_campaign (CONTEXT § 戰役工具)."""
from __future__ import annotations

import runpy
import sys
import warnings

warnings.warn(
    "ingest.project_synonyms_campaign moved to tools.campaigns.project_synonyms_campaign; "
    "use: python -m tools.campaigns.project_synonyms_campaign",
    DeprecationWarning,
    stacklevel=2,
)

from tools.campaigns import project_synonyms_campaign as _impl

if __name__ == "__main__":
    runpy.run_module("tools.campaigns.project_synonyms_campaign", run_name="__main__")
else:
    # Full module swap so tests can patch ingest.project_synonyms_campaign._private
    sys.modules[__name__] = _impl
