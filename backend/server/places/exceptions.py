class LLMUnavailableError(Exception):
    """Raised whenever the LLM ranking pipeline cannot be used: not configured
    (LLM_API_KEY unset), the provider call failed, or timed out.

    Callers (Django views) MUST catch this and degrade gracefully — per the
    Trilho blueprint invariant I4, the LLM provider being down/unconfigured
    can never take the rest of the API down with it. The correct response is
    "suggestions feature unavailable", not a 500.
    """

    pass
