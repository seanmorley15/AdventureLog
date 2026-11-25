"""
Who travelled on a visit.

Every visit lists its travelers. A visit with no travelers counts for the
owner of its location, so existing data and newly created visits keep working
without any extra input.
"""


def ensure_default_traveler(visit):
    """Add the location owner as a traveler when the visit has none."""
    if not visit.travelers.exists():
        visit.travelers.add(visit.location.user_id)
