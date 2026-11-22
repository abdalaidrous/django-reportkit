from django.utils.translation import gettext_lazy as _
from django.utils.translation import override
from reportkit.builders import ReportBuilder, TableBuilder
from reportkit.rendering.context import RenderingContext


class ReportDocumentMixin:
    """
    Build presentation-only ReportKit documents from prepared report data.
    """

    title = ""
    columns = ()
    total_label = _("Total")
    page = {"margin": "12mm"}
    page_number = "{page} / {pages}"
    table_title = None
    table_style = None
    table_component_style = None

    def get_title(self):
        """
        Return the localized report title.
        """
        return str(self.title)

    def get_columns(self):
        """
        Return the configured report columns.
        """
        return list(self.columns)

    def get_totals(self):
        """
        Return the prepared report totals.
        """
        return None

    def total_row(self):
        """
        Build the display row from prepared totals.
        """
        totals = self.get_totals()
        columns = self.get_columns()

        if not totals or not columns:
            return None

        return {**totals, columns[0].field: str(self.total_label)}

    def context(self):
        """
        Build the rendering context for the report language.
        """
        return RenderingContext(language=self.params.language, direction=self.params.direction)

    def table(self, rows):
        """
        Build the report table from prepared data.
        """
        return self.table_builder(rows).build()

    def table_builder(self, rows):
        """
        Configure the table columns, rows, totals, and presentation.
        """
        columns = (column.table_column() for column in self.get_columns())
        builder = TableBuilder().columns(*columns).rows(rows).totals(self.total_row()).title(self.table_title)
        self.configure_table(builder)
        return builder

    def configure_table(self, builder):
        """
        Apply optional table and component styles.
        """
        if self.table_style is not None:
            builder.table_style(self.table_style)

        if self.table_component_style is not None:
            builder.style(self.table_component_style)

    def build(self, builder, table):
        """
        Compose the report layout with its table and page numbering.
        """
        return builder.add(table).page_number(self.page_number)

    def document(self, rows=None):
        """
        Build the ReportKit document using the supplied or complete rows.
        """
        with override(self.params.language):
            builder = self.document_builder()
            table = self.table(rows if rows is not None else self.get_rows())
            return self.build(builder, table).build()

    def document_builder(self):
        """
        Initialize the report builder with page settings.
        """
        return ReportBuilder(self.get_title()).page(**self.page)

    def html(self, rows=None):
        """
        Render the report document as a complete HTML string.
        """
        import reportkit.exporters.html  # noqa: F401
        from reportkit.exporters.html.exporter import HtmlExporter

        with override(self.params.language):
            return HtmlExporter().export(self.document(rows), self.context()).decode("utf-8")