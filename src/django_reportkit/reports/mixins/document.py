
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override
from reportkit.builders import ReportBuilder, TableBuilder
from reportkit.rendering.context import RenderingContext


class ReportDocumentMixin:
    """
    Build presentation-only ReportKit documents from prepared rows, columns and totals.
    """

    title = ""
    columns = ()
    total_label = _("Total")
    page = {"margin": "12mm"}
    page_number = "{page} / {pages}"
    table_title = None
    table_style = None  # A ReportKit TableStyle (density, stripes, borders, header style).
    table_component_style = None  # A ReportKit Style for the table box (margins, direction, ...).

    def get_title(self):
        """
        Return the report title.
        """
        return str(self.title)

    def get_columns(self):
        """
        Return the report columns.
        """
        return list(self.columns)

    def get_totals(self):
        """
        Return the totals prepared by the application, keyed by column field, or None; they cover every row.
        """
        return None

    def total_row(self):
        """
        Return the prepared totals with the display label in the first column, or None.
        """
        totals = self.get_totals()
        if not totals:
            return None

        columns = self.get_columns()
        if not columns:
            return None

        return {columns[0].field: str(self.total_label), **totals}

    def context(self):
        """
        Return the ReportKit rendering context for the report language.
        """
        return RenderingContext(language=self.params.language, direction=self.params.direction)

    def table(self, rows):
        """
        Build the report table over the rows, using the prepared totals of every row.
        """
        return self.table_builder(rows).build()

    def table_builder(self, rows):
        """
        Configure the table columns, rows, totals, title and presentation styles.
        """
        builder = TableBuilder().columns(*(column.table_column() for column in self.get_columns())).rows(rows).totals(self.total_row()).title(self.table_title)

        if self.table_style is not None:
            builder.table_style(self.table_style)

        if self.table_component_style is not None:
            builder.style(self.table_component_style)

        return builder

    def build(self, builder, table):
        """
        Lay the report out; override to add headers, footers, charts or QR codes around the table.
        """
        return builder.add(table).page_number(self.page_number)

    def document(self, rows=None):
        """
        Return the ReportKit document over the given rows (every row by default), in the report language.
        """
        with override(self.params.language):
            builder = ReportBuilder(self.get_title()).page(**self.page)
            return self.build(builder, self.table(rows if rows is not None else self.get_rows())).build()
