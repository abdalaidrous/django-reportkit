from enum import Enum

from ..conf import reportkit_settings
from ..errors.exceptions import ExportTooLargeError


UNLIMITED = "xlsx-data"


class Delivery(Enum):
    """
    How an export reaches the user.
    """

    DIRECT = "direct"
    BACKGROUND = "background"


class ExportPolicy:
    """
    Decide whether an export runs directly, in the background, or is refused according to configured row limits.
    """

    @classmethod
    def decide(cls, format, rows, formats):
        """
        Validate the export size and return its delivery method.
        """
        cls.validate_size(format, rows, formats)
        return cls.delivery(format, rows)

    @staticmethod
    def validate_size(format, rows, formats):
        """
        Reject exports exceeding the format's maximum row limit.
        """
        maximum = reportkit_settings.MAX_ROWS.get(format.name)

        if maximum is not None and rows > maximum:
            alternative = UNLIMITED if UNLIMITED in formats and format.name != UNLIMITED else None
            raise ExportTooLargeError(format.name, rows, maximum, alternative)

    @staticmethod
    def delivery(format, rows):
        """
        Choose direct or background delivery using the configured direct row limit.
        """
        direct = reportkit_settings.DIRECT_LIMITS.get(format.name)
        return Delivery.BACKGROUND if direct is not None and rows > direct else Delivery.DIRECT
