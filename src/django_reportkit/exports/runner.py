from tempfile import TemporaryFile

from django.utils.translation import override
from reportkit.builders import ReportExport


class ExportRunner:
    """
    Write a report in one format to a temporary file on disk, never to memory, ready to be streamed or stored.
    """

    @staticmethod
    def write(report, format, target):
        """
        Export the report to a path or a binary stream in its language.
        """
        with override(report.params.language):
            ReportExport.export_to(report.document(), format.exporter, target, report.context(), **format.options())

    @classmethod
    def to_temporary_file(cls, report, format):
        """
        Return an open temporary file holding the export, positioned at its start; closing it deletes it.
        """
        spool = TemporaryFile()
        try:
            cls.write(report, format, spool)
        except BaseException:
            spool.close()
            raise
        spool.seek(0)
        return spool
