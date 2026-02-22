"""
Reporting and Analytics module

Provides:
- Execution history reports
- Pass/fail trend analysis
- Export to CSV/JSON
- Report generation
"""

from ignition_toolkit.reporting.analytics import ExecutionAnalytics
from ignition_toolkit.reporting.export import ReportExporter
from ignition_toolkit.reporting.reports import ReportGenerator

__all__ = [
    "ExecutionAnalytics",
    "ReportGenerator",
    "ReportExporter",
]
