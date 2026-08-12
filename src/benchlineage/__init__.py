"""BenchLineage public package."""

from .analysis import analyze_run
from .audit import audit_workspace
from .bundle import build_bundle, verify_bundle
from .demo import build_demo
from .eln import build_eln, verify_eln
from .provenance import compare_seals, seal_workspace, verify_seal
from .report import build_report
from .workspace import Workspace

__all__ = [
    "Workspace",
    "analyze_run",
    "audit_workspace",
    "build_bundle",
    "build_demo",
    "build_eln",
    "build_report",
    "compare_seals",
    "seal_workspace",
    "verify_seal",
    "verify_bundle",
    "verify_eln",
]

__version__ = "0.3.2"
