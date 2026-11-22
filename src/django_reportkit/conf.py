from django.conf import settings

DEFAULTS = {
    "PAGINATE_BY": 50,
    # Rows above which a format is generated in the background instead of during the request; None never moves it.
    "DIRECT_LIMITS": {"pdf": 2000, "docx": 2000, "xlsx": 20000, "xlsx-data": 100000, "html": 5000},
    # Rows above which a format is refused with a suggestion to use another one; None has no limit.
    "MAX_ROWS": {"pdf": 50000, "docx": 50000, "xlsx": 100000, "xlsx-data": None, "html": 20000},
    "JOB_BACKEND": "django_reportkit.jobs.backends.ThreadBackend",
    "JOB_STORAGE": "default",  # A key of settings.STORAGES.
    "JOB_DIRECTORY": "reports",
    "JOB_TTL_HOURS": 24,
    "STATUS_POLL_SECONDS": 3,
    "PDF_WORKERS": 1,
}


class ReportKitSettings:
    """
    Read settings.REPORTKIT over the defaults on every access, so overridden settings (as in tests) apply at once.
    """

    def __getattr__(self, name):
        """
        Return one setting; dictionaries are merged key by key over their defaults.
        """
        if name not in DEFAULTS:
            raise AttributeError(f"Unknown django-reportkit setting: {name}")
        configured = getattr(settings, "REPORTKIT", {}).get(name, DEFAULTS[name])
        if isinstance(DEFAULTS[name], dict):
            return {**DEFAULTS[name], **configured}
        return configured


reportkit_settings = ReportKitSettings()
