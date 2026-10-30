import re

from django.conf import settings

# BCP-47-ish tag: "en", "pt-BR", "zh-hans". No lists, q-values, or separators.
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,8}(?:[-_][A-Za-z0-9]{1,8})*$")


def resolve_request_language(request) -> str:
    """Pick the user's preferred language tag for external lookups.

    Precedence: explicit ?language=, the UI locale forwarded by the SvelteKit
    proxy (X-AdventureLog-Locale), the locale cookie for direct API clients,
    the browser Accept-Language header, then LANGUAGE_CODE. Always returns a
    single validated tag so it is safe to use as an HTTP header value.
    """
    params = getattr(request, "query_params", {})
    candidates = (
        params.get("language"),
        request.headers.get("X-AdventureLog-Locale"),
        request.COOKIES.get("locale"),
        request.headers.get("Accept-Language", ""),
        settings.LANGUAGE_CODE,
    )
    for candidate in candidates:
        if not candidate:
            continue
        primary = str(candidate).split(",")[0].split(";")[0].strip()
        if _LANGUAGE_RE.match(primary):
            return primary
    return settings.LANGUAGE_CODE
