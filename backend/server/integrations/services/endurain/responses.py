"""Reading the bodies Endurain sends back, across its legacy and RFC 9457 error shapes."""

import requests


def problem_message(data, default: str) -> str:
    """Read a human-readable error from either a legacy or RFC 9457 body."""
    if isinstance(data, dict):
        for key in ('detail', 'title'):
            value = data.get(key)
            if value:
                return str(value)
    return default


def _is_html_response(response: requests.Response) -> bool:
    raw = response.headers.get('Content-Type', '')
    if not isinstance(raw, str):
        return False
    media_type = raw.split(';', 1)[0].strip().lower()
    return media_type in {'text/html', 'application/xhtml+xml'}


# Distinct from a JSON null body, which older list routes used for "no activities".
UNUSABLE_BODY = object()


def read_json(response: requests.Response):
    """Parse a JSON body. HTML and other non-JSON payloads are unusable."""
    if _is_html_response(response):
        return UNUSABLE_BODY
    try:
        return response.json()
    except ValueError:
        return UNUSABLE_BODY
