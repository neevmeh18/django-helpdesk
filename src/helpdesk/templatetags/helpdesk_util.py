from datetime import datetime
from django.conf import settings
from django.template import Library
from django.template.defaultfilters import date as date_filter
from django.utils import timezone
from helpdesk.settings import (
    CUSTOMFIELD_DATE_FORMAT,
    CUSTOMFIELD_DATETIME_FORMAT,
    CUSTOMFIELD_TIME_FORMAT,
)


register = Library()


@register.filter
def get(value, arg, default=None):
    """Call the dictionary get function"""
    return value.get(arg, default)


@register.filter(expects_localtime=True)
def datetime_string_format(value):
    """
    :param value: String - Expected to be a datetime, date, or time in specific format
    :return: String - reformatted to default datetime, date, or time string if received in one of the expected formats
    """
    try:
        new_value = date_filter(
            datetime.strptime(value, CUSTOMFIELD_DATETIME_FORMAT),
            settings.DATETIME_FORMAT,
        )
    except (TypeError, ValueError):
        try:
            new_value = date_filter(
                datetime.strptime(value, CUSTOMFIELD_DATE_FORMAT), settings.DATE_FORMAT
            )
        except (TypeError, ValueError):
            try:
                new_value = date_filter(
                    datetime.strptime(value, CUSTOMFIELD_TIME_FORMAT),
                    settings.TIME_FORMAT,
                )
            except (TypeError, ValueError):
                # If NoneType return empty string, else return original value
                new_value = "" if value is None else value
    return new_value


@register.filter
def elapsed_since(value):
    """Return a compact day-aware duration from value to now, or "" if None."""
    if value is None:
        return ""
    now = timezone.now()
    if timezone.is_aware(now) and timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    elif timezone.is_naive(now) and timezone.is_aware(value):
        value = timezone.make_naive(value, timezone.get_current_timezone())
    total_seconds = int((now - value).total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    if hours:
        return f"{hours:02d}h {minutes:02d}m"
    return f"{minutes}m"
