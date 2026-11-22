from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import override
from django.views import View

from reportkit.exporters.html.exporter import HtmlExporter

from ..errors import ReportFilterError, error_response
from ..exports import FORMATS
from .mixins import ReportViewMixin


class ReportPreviewView(ReportViewMixin, View):
    """
    Show one page of the report as HTML, with its filters, page links and download links; the totals cover every
    filtered row, not only the page shown.
    """

    template_name = "django_reportkit/preview.html"

    def get(self, request):
        """
        Render the filters and the current page of the report.
        """
        report = self.get_report()

        try:
            page = report.get_page(request.GET.get("page"))
            document = self.render_page(report, page)
        except ReportFilterError:
            return self.render_preview(request, report, status=400)
        except Exception as error:
            return error_response(request, error, report)

        return self.render_preview(request, report, page, document)

    def render_preview(self, request, report, page=None, document=None, status=200):
        """
        Render the preview template with its filters, pagination and HTML document.
        """
        return render(request, self.template_name, self.context(report, page, document), status=status)

    @staticmethod
    def render_page(report, page):
        """
        Return the complete HTML document of one page of rows.
        """
        import reportkit.exporters.html  # noqa: F401

        with override(report.params.language):
            return HtmlExporter().export(report.document(rows=page.object_list), report.context()).decode("utf-8")

    def context(self, report, page, document):
        """
        Return the template context: the report HTML goes in an iframe so its styles never mix with the site's.
        """
        return {
            "report": report,
            "form": report.form,
            "page_obj": page,
            "document": document,
            "query": report.params.urlencode(),
            "downloads": self.downloads(report),
            "direction": report.params.direction,
        }

    @staticmethod
    def downloads(report):
        """
        Return the available export formats and their download URLs.
        """
        query = report.params.urlencode()
        suffix = f"?{query}" if query else ""

        return [(FORMATS[name].label, reverse(f"{report.get_slug()}-export", kwargs={"format": name}) + suffix) for name in report.formats if name in FORMATS]
