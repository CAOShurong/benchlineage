"""BenchLineage public package."""

from .analysis import analyze_run
from .audit import audit_workspace
from .demo import build_demo
from .provenance import seal_workspace, verify_seal
from .report import build_report
from .workspace import Workspace

__all__ = [
    "Workspace",
    "analyze_run",
    "audit_workspace",
    "build_demo",
    "build_report",
    "seal_workspace",
    "verify_seal",
]

__version__ = "0.1.1"
