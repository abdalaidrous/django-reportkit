"""
Django reports on top of pyreportkit.
"""

from django.db.models import Avg, Count, Max, Min, Sum

from .reports import Column, ModelReport, Report, ReportParams, register

__version__ = "0.2.0"
__all__ = ["Avg", "Column", "Count", "Max", "Min", "ModelReport", "Report", "ReportParams", "Sum", "register"]
