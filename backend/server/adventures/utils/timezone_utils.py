import pytz


def format_datetime_in_selected_timezone(dt, user_tz):
    if dt is None and user_tz is None:
        return None
    tz = pytz.timezone(user_tz)
    return dt.astimezone(tz).isoformat()