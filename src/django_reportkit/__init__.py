"""
Django reports on top of pyreportkit.
"""

from django.db.models import Avg, Count, Max, Min, Sum

from .reports import Column, ModelReport, Report, ReportParams

__version__ = "0.1.0"
__all__ = ["Avg", "Column", "Count", "Max", "Min", "ModelReport", "Report", "ReportParams", "Sum"]
