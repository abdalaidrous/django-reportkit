from dataclasses import dataclass, field

from django.http import QueryDict
from django.utils.translation import get_language

# Query parameters that drive the views, not the report filters.
RESERVED = ("page", "page_size", "format")
RTL_LANGUAGES = ("ar", "fa", "he", "ur")


@dataclass(frozen=True)
class ReportParams:
    """
    Everything a report is built from, in a form that can be stored with a background job: the filter values (lists
    of strings, as in a query string), the user, the language and the request context the report resolved from the
    request (JSON-ready values such as a selected tenant or property id, see Report.request_context).
    """

    data: dict[str, list[str]] = field(default_factory=dict)
    user_id: int | None = None
    language: str = "en"
    context: dict = field(default_factory=dict)

    @classmethod
    def from_request(cls, request, context=None):
        """
        Read the filter values from the query string, the user and language of the request, and the given context.
        """
        data = {key: request.GET.getlist(key) for key in request.GET if key not in RESERVED}
        user = getattr(request, "user", None)
        user_id = user.pk if user is not None and user.is_authenticated else None
        return cls(data=data, user_id=user_id, language=get_language() or "en", context=dict(context or {}))

    @classmethod
    def from_json(cls, value):
        """
        Restore parameters stored with a job.
        """
        data = {key: list(values) for key, values in value.get("data", {}).items()}
        return cls(data=data, user_id=value.get("user_id"), language=value.get("language", "en"), context=dict(value.get("context") or {}))

    def to_json(self):
        """
        Return the parameters as JSON-ready data.
        """
        return {"data": self.data, "user_id": self.user_id, "language": self.language, "context": self.context}

    def querydict(self):
        """
        Return the filter values as a QueryDict, as forms expect.
        """
        query = QueryDict(mutable=True)
        for key, values in self.data.items():
            query.setlist(key, values)
        return query

    def urlencode(self):
        """
        Return the filter values as a query string, to keep them across pages and export links.
        """
        return self.querydict().urlencode()

    @property
    def direction(self):
        """
        Return the text direction of the language.
        """
        return "rtl" if self.language.split("-")[0] in RTL_LANGUAGES else "ltr"
