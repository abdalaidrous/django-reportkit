from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReportKitConfig(AppConfig):
    """
    Django application for pyreportkit reports: templates, the ReportJob model and its cleanup command.
    """

    name = "django_reportkit"
    label = "django_reportkit"
    verbose_name = _("Reports")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Import every installed app's reports module, so reports registered with @register are known at startup.
        """
        from django.utils.module_loading import autodiscover_modules

        autodiscover_modules("reports")
