from reportkit.components.table import TableColumn


class Column:
    """
    One report column: the queryset field it reads (a values() path such as "account__name", or an annotation) and how
    pyreportkit shows it. The options are TableColumn's: subtitle, format, currency, decimals, date_format, align, ...
    """

    def __init__(self, field, title, **options):
        """
        Keep the field, the title (it may be a lazy translation) and the TableColumn options.
        """
        if not isinstance(field, str) or not field:
            raise ValueError("Column field must be a non-empty string.")
        self.field, self.title, self.options = field, title, options

    def table_column(self):
        """
        Return the pyreportkit column, translating the title in the active language.
        """
        return TableColumn(key=self.field, title=str(self.title), **{key: str(value) if key == "subtitle" else value for key, value in self.options.items()})

    def __repr__(self):
        """
        Show the field and title.
        """
        return f"Column({self.field!r}, {str(self.title)!r})"
