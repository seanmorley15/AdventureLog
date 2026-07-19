from django.db import models


class OverpassCacheEntry(models.Model):
    """Cached Overpass API response for a normalized (category, lat, lon, radius) query.

    `query_key` is a sha256 hex digest of the normalized query (see
    `places/services.py::normalize_query_key`) so an identical search never
    hits Overpass twice within the TTL window (5a.3 DoD).
    """

    query_key = models.CharField(max_length=64, unique=True, db_index=True)
    payload = models.JSONField()
    fetched_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    def __str__(self):
        return f"OverpassCacheEntry({self.query_key[:12]}..., expires_at={self.expires_at})"
