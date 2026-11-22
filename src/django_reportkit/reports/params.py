from dataclasses import dataclass, field

from django.http import QueryDict
from django.utils.translation import get_language

# Query parameters that drive the views, not the report filters.
RESERVED = ("page", "format")
RTL_LANGUAGES = ("ar", "fa", "he", "ur")


@dataclass(frozen=True)
class ReportParams:
    """
    Everything a report is built from, in a form that can be stored with a background job: the filter values (lists
    of strings, as in a query string), the user and the language.
    """

    data: dict[str, list[str]] = field(default_factory=dict)
    user_id: int | None = None
    language: str = "en"

    @classmethod
    def from_request(cls, request):
        """
        Read the filter values from the query string, and the user and language of the request.
        """
        data = {key: request.GET.getlist(key) for key in request.GET if key not in RESERVED}
        user = getattr(request, "user", None)
        user_id = user.pk if user is not None and user.is_authenticated else None
        return cls(data=data, user_id=user_id, language=get_language() or "en")

    @classmethod
    def from_json(cls, value):
        """
        Restore parameters stored with a job.
        """
        return cls(data={key: list(values) for key, values in value.get("data", {}).items()}, user_id=value.get("user_id"), language=value.get("language", "en"))

    def to_json(self):
        """
        Return the parameters as JSON-ready data.
        """
        return {"data": self.data, "user_id": self.user_id, "language": self.language}

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
