from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from ..conf import reportkit_settings
from ..errors.exceptions import UnknownFormatError

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@dataclass(frozen=True)
class ExportFormat:
    """
    One downloadable format: the pyreportkit exporter it uses, the file it produces and how to export large reports.
    """

    name: str
    exporter: str
    extension: str
    content_type: str
    label: str

    def options(self):
        """
        Return the pyreportkit export options; imported lazily so missing optional exporters fail only when used.
        """
        if self.name == "pdf":
            from reportkit.exporters.pdf import PdfOptions

            return {"options": PdfOptions(workers=reportkit_settings.PDF_WORKERS)}
        if self.name == "xlsx-data":
            from reportkit.exporters.excel import ExcelOptions

            return {"options": ExcelOptions(mode="data", streaming=True)}
        return {}

    def filename(self, slug):
        """
        Return the download file name.
        """
        return f"{slug}.{self.extension}"


FORMATS = {
    "pdf": ExportFormat("pdf", "pdf", "pdf", "application/pdf", _("PDF")),
    "xlsx": ExportFormat("xlsx", "xlsx", "xlsx", XLSX, _("Excel")),
    "xlsx-data": ExportFormat("xlsx-data", "xlsx", "xlsx", XLSX, _("Excel (data)")),
    "docx": ExportFormat("docx", "docx", "docx", DOCX, _("Word")),
    "html": ExportFormat("html", "html", "html", "text/html; charset=utf-8", _("HTML")),
}


def get_format(report, name):
    """
    Return the export format when the report offers it.
    """
    if name not in report.formats or name not in FORMATS:
        raise UnknownFormatError(name)
    return FORMATS[name]
