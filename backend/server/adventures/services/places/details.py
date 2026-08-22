from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.conf import settings

from adventures.providers.places.google import fetch_place_details
from adventures.providers.places.wikipedia import fetch_summary


@dataclass
class PlaceDetails:
    description: Optional[str]
    name: Optional[str]
    formatted_address: Optional[str]
    types: List[str]
    rating: Optional[float]
    review_count: Optional[int]
    website: Optional[str]
    phone_number: Optional[str]
    google_maps_url: Optional[str]
    source: Optional[str]
    provider_used: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "name": self.name,
            "formatted_address": self.formatted_address,
            "types": self.types,
            "rating": self.rating,
            "review_count": self.review_count,
            "website": self.website,
            "phone_number": self.phone_number,
            "google_maps_url": self.google_maps_url,
            "source": self.source,
            "provider_used": self.provider_used,
        }


def _compose_place_description(editorial_summary: Optional[str], review_snippets: List[str]) -> Optional[str]:
    parts: List[str] = []

    summary = (editorial_summary or "").strip()
    if summary:
        parts.append(f"### About\n\n{summary}")

    cleaned_reviews = []
    for snippet in review_snippets:
        text = (snippet or "").strip()
        if len(text) >= 40:
            cleaned_reviews.append(text)
        if len(cleaned_reviews) >= 2:
            break

    if cleaned_reviews:
        review_block = "### Visitor Highlights\n\n" + "\n".join(f"- {text}" for text in cleaned_reviews)
        parts.append(review_block)

    return "\n\n".join(parts).strip() or None


def get_place_details(
    place_id: str,
    fallback_query: Optional[str] = None,
    language: str = "en",
) -> Dict[str, Any]:
    if not place_id:
        return {"error": "place_id is required"}

    details = PlaceDetails(
        description=None,
        name=None,
        formatted_address=None,
        types=[],
        rating=None,
        review_count=None,
        website=None,
        phone_number=None,
        google_maps_url=None,
        source=None,
        provider_used=None,
    )

    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
    if api_key:
        google_payload = fetch_place_details(place_id, api_key)
        if not google_payload.error:
            place = google_payload.data or {}
            details.name = (place.get("displayName") or {}).get("text")
            details.formatted_address = place.get("formattedAddress")
            details.types = place.get("types") or []
            details.rating = place.get("rating")
            details.review_count = place.get("userRatingCount")
            details.website = place.get("websiteUri")
            details.phone_number = (
                place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber")
            )
            details.google_maps_url = place.get("googleMapsUri")

            editorial_summary = (place.get("editorialSummary") or {}).get("text")
            reviews = place.get("reviews") or []
            review_snippets = [((review.get("text") or {}).get("text")) for review in reviews]
            details.description = _compose_place_description(editorial_summary, review_snippets)
            if details.description:
                details.source = "google"
                details.provider_used = "google"

    description_text = (details.description or "").strip()
    if len(description_text) < 220:
        wiki_payload = fetch_summary(fallback_query or details.name or "", language=language)
        wikipedia_summary = wiki_payload.data if not wiki_payload.error else None
        if wikipedia_summary:
            if description_text:
                details.description = (
                    f"{description_text}\n\n### Background\n\n{wikipedia_summary}"
                )
                details.source = "google+wikipedia"
                details.provider_used = "google+wikipedia"
            else:
                details.description = f"### Background\n\n{wikipedia_summary}"
                details.source = "wikipedia"
                details.provider_used = "wikipedia"

    if not details.description:
        return {"error": "Unable to enrich place description"}

    return details.to_dict()
