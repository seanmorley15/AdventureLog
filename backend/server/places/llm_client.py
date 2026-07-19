"""Anthropic client for the `places` ranking pipeline (P5b).

Provider/model/budget decision: docs/hub/20-decisoes/003b-llm-provider.md
(ADR 003b — Claude Haiku 4.5, chave própria do Caio).

This module is a thin, stateless wrapper: it sends the caller-provided
candidate payload + restrictions to the model and returns whatever
`{"suggestions": [...]}` the model produces, unvalidated. It does NOT decide
which suggestions are trustworthy — that guard-rail (I1: every returned id
must exist in the original candidate list) lives in `places/ranking.py`,
kept separate so it can be tested independently of the LLM call itself.

Invariant I1 (blueprint): this module must never be given, and must never be
asked to produce, a geospatial fact (distance, coordinate, address-as-truth).
Callers are responsible for stripping latitude/longitude/distance_km from the
candidate payload before it reaches this module.
"""
from __future__ import annotations

import json

import anthropic
from django.conf import settings

from .exceptions import LLMUnavailableError

DEFAULT_MAX_TOKENS = 1500

SYSTEM_PROMPT = (
    "Você ranqueia lugares para um roteiro de viagem. Você recebe uma lista de "
    "candidatos (cada um com um \"id\" opaco) e as restrições do usuário. "
    "Responda APENAS com IDs que aparecem literalmente na lista de candidatos — "
    "nunca invente um id, nome ou lugar novo. Nunca mencione distância, tempo de "
    "viagem, endereço completo ou coordenadas — essas informações não estão "
    "disponíveis para você e são calculadas por outro sistema. Baseie a "
    "justificativa apenas nos campos fornecidos (nome, categoria, cozinha, "
    "acessibilidade, taxa, horário de funcionamento, descrição). Se nenhum "
    "candidato atender às restrições, devolva uma lista vazia."
)

SUGGESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "justification": {"type": "string"},
                },
                "required": ["id", "justification"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["suggestions"],
    "additionalProperties": False,
}


def is_configured() -> bool:
    """Whether an LLM_API_KEY is set — callers use this to degrade gracefully
    (I4/I7) instead of calling out and hitting an auth error."""
    return bool(getattr(settings, "LLM_API_KEY", ""))


def rank_candidates(candidates_payload: list[dict], restrictions: str) -> list[dict]:
    """Send sanitized candidates + restrictions to the LLM, return raw suggestions.

    Args:
        candidates_payload: list of dicts with an "id" key plus only
            non-geospatial fields (name, category, tags, description). The
            caller MUST have already stripped latitude/longitude/distance_km.
        restrictions: free-text restrictions from the user (diet, budget,
            accessibility, etc.).

    Returns:
        Raw list of {"id": str, "justification": str} dicts, as returned by
        the model — NOT yet validated against the real candidate list. The
        caller (places/ranking.py) must run the I1 guard-rail before trusting
        any id in this list.

    Raises:
        LLMUnavailableError: LLM_API_KEY unset, the API call failed, timed
            out, or the response could not be parsed as the expected schema.
    """
    if not is_configured():
        raise LLMUnavailableError("LLM_API_KEY não está configurada — sugestões indisponíveis.")

    client = anthropic.Anthropic(api_key=settings.LLM_API_KEY)
    user_content = (
        f"Restrições do usuário: {restrictions or '(nenhuma restrição informada)'}\n\n"
        f"Candidatos (JSON):\n{json.dumps(candidates_payload, ensure_ascii=False)}"
    )

    try:
        response = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=DEFAULT_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": SUGGESTION_SCHEMA}},
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIError as exc:
        raise LLMUnavailableError(f"Falha ao chamar o provedor LLM: {exc}") from exc

    text_block = next((block.text for block in response.content if block.type == "text"), None)
    if text_block is None:
        raise LLMUnavailableError("Resposta do LLM não trouxe bloco de texto com o resultado.")

    try:
        parsed = json.loads(text_block)
    except ValueError as exc:
        raise LLMUnavailableError(f"Resposta do LLM não é JSON válido: {exc}") from exc

    suggestions = parsed.get("suggestions")
    if not isinstance(suggestions, list):
        raise LLMUnavailableError("Resposta do LLM não trouxe a lista 'suggestions' esperada.")

    return suggestions
