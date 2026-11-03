from datetime import date
from typing import Optional


def format_short_date(d: Optional[date]) -> str:
    if not d:
        return ''
    return d.strftime('%b %d, %Y')
