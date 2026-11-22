import re


class ReportAccessMixin:
    """
    Provide report identity, URL patterns and access permissions.
    """

    slug = None
    login_required = True
    permission_required = None

    @classmethod
    def get_slug(cls):
        """
        Return the name the report's URLs are named after: slug, or the class name in kebab case.
        """
        return cls.slug or re.sub(r"(?<!^)(?=[A-Z])", "-", cls.__name__).lower()

    @classmethod
    def get_key(cls):
        """
        Return the import path a background job uses to find the report class again.
        """
        return f"{cls.__module__}.{cls.__qualname__}"

    @classmethod
    def urls(cls):
        """
        Return the URL patterns of this report's preview and exports, for include().
        """
        from ...views.urls import report_urlpatterns  # Deferred: views import reports.

        return report_urlpatterns(cls)

    @classmethod
    def api_urls(cls, **view_options):
        """
        Return the Django REST Framework URL patterns of this report's JSON preview and exports, for include().
        """
        from ...rest.urls import report_api_urlpatterns  # Deferred: optional, needs djangorestframework.

        return report_api_urlpatterns(cls, **view_options)

    @classmethod
    def has_permission(cls, user):
        """
        Return whether the user may see the report: logged in unless login_required is False, then
        permission_required (a permission name or a list of them).
        """
        if cls.login_required and not getattr(user, "is_authenticated", False):
            return False

        if cls.permission_required is None:
            return True

        required = (cls.permission_required,) if isinstance(cls.permission_required, str) else cls.permission_required
        return bool(user and user.has_perms(required))
