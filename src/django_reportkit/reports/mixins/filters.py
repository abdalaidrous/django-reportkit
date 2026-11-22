from functools import cached_property

from django.contrib.auth import get_user_model

from ...errors.exceptions import ReportFilterError


class ReportFilterMixin:
    """
    Resolve the requesting user, bind the filter form and expose the validated filter values.
    """
    filter_form = None

    @cached_property
    def user(self):
        """
        Return the user the report is built for, or None.
        """
        return get_user_model()._default_manager.filter(pk=self.params.user_id).first() if self.params.user_id else None

    @cached_property
    def form(self):
        """
        Return the bound filter form, or None when the report has no filters.
        """
        return self.filter_form(self.params.querydict() or None) if self.filter_form else None

    @cached_property
    def filters(self):
        """
        Return the cleaned filter values; an empty mapping when nothing is filled in.
        """
        if self.form is None or not self.form.is_bound:
            return {}

        if not self.form.is_valid():
            raise ReportFilterError(self.form.errors)

        return {name: value for name, value in self.form.cleaned_data.items() if value not in (None, "", [], ())}
