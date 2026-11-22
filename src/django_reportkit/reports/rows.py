class QuerysetRows:
    """
    The rows of a report read lazily from a queryset: every iteration runs one query and streams it in chunks with
    iterator(), so a large report never sits in memory and can be read again (for example by a second export).
    """

    def __init__(self, queryset, fields, chunk_size):
        """
        Keep the queryset and the values() fields the columns read.
        """
        self.queryset, self.fields, self.chunk_size = queryset, list(fields), chunk_size

    def __iter__(self):
        """
        Yield one mapping per row, keyed by column field.
        """
        return self.queryset.values(*self.fields).iterator(chunk_size=self.chunk_size)
