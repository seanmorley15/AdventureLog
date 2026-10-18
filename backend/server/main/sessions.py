"""
Cached database sessions with a short cache lifetime.

Django's ``cached_db`` keeps a session in the cache for its whole life (two weeks
here). Sessions deleted straight from the database, for example from the admin,
would keep working until then. Capping the cached copy to a few minutes keeps the
saving (no database read on most requests) and keeps revocation prompt. The database
stays the source of truth: if the cache is cold or down, the session loads from it.
"""
from django.conf import settings
from django.contrib.sessions.backends.cached_db import SessionStore as CachedDBSessionStore
from django.contrib.sessions.backends.db import SessionStore as DBSessionStore


def _cache_ttl(expiry_age: int) -> int:
    return max(1, min(int(expiry_age), int(getattr(settings, 'SESSION_CACHE_SECONDS', 300))))


class SessionStore(CachedDBSessionStore):
    def load(self):
        try:
            data = self._cache.get(self.cache_key)
        except Exception:
            data = None

        if data is None:
            session = self._get_session_from_db()
            if session:
                data = self.decode(session.session_data)
                try:
                    self._cache.set(
                        self.cache_key, data, _cache_ttl(self.get_expiry_age(expiry=session.expire_date))
                    )
                except Exception:
                    pass
            else:
                data = {}
        return data

    def save(self, must_create=False):
        # Save to the database only; the base class would also cache for the full session
        # lifetime, which is exactly what this store avoids.
        DBSessionStore.save(self, must_create)
        try:
            self._cache.set(self.cache_key, self._session, _cache_ttl(self.get_expiry_age()))
        except Exception:
            pass
