class ReportError(Exception):
    """
    Base class of the errors django-reportkit shows to users with a friendly message.
    """


class ReportFilterError(ReportError):
    """
    The filter form is invalid; errors holds the form errors.
    """

    def __init__(self, errors):
        """
        Keep the form errors.
        """
        super().__init__("The report filters are invalid.")
        self.errors = errors


class UnknownFormatError(ReportError):
    """
    The requested export format is not offered by the report.
    """

    def __init__(self, format):
        """
        Keep the format name.
        """
        super().__init__(f"Unknown or disabled export format: {format}")
        self.format = format


class ExportTooLargeError(ReportError):
    """
    The report has more rows than the format allows; alternative names a format that can hold it, if any.
    """

    def __init__(self, format, rows, limit, alternative=None):
        """
        Keep the numbers needed to explain the refusal.
        """
        super().__init__(f"{rows} rows exceed the {format} limit of {limit}.")
        self.format, self.rows, self.limit, self.alternative = format, rows, limit, alternative
