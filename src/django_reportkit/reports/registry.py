from django.core.exceptions import ImproperlyConfigured

# Path segments the generic URLs use for themselves; no report may take them as its slug.
RESERVED_SLUGS = {"jobs"}


class ReportRegistry:
    """
    Keep the reports a project exposes through the generic URLs, by slug. Register with the @register decorator in an
    app's reports.py, which Django imports at startup.
    """

    _reports = {}

    @classmethod
    def register(cls, report_class):
        """
        Register a report class under its slug; usable as a class decorator.
        """
        slug = report_class.get_slug()
        if slug in RESERVED_SLUGS:
            raise ImproperlyConfigured(f"The report slug '{slug}' is reserved.")
        registered = cls._reports.get(slug)
        if registered is not None and registered is not report_class:
            raise ImproperlyConfigured(f"Two reports use the slug '{slug}': {registered.get_key()} and {report_class.get_key()}.")
        cls._reports[slug] = report_class
        return report_class

    @classmethod
    def get(cls, slug):
        """
        Return the report class registered under the slug, or None.
        """
        return cls._reports.get(slug)

    @classmethod
    def all(cls):
        """
        Return the registered report classes in slug order.
        """
        return [cls._reports[slug] for slug in sorted(cls._reports)]


register = ReportRegistry.register
