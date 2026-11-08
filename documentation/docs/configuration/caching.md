# Caching

AdventureLog caches data that is slow to fetch or compute and the same for everyone.
It does **not** cache API responses that depend on who is asking, such as collections
or locations, so permissions and freshness are never affected by the cache.

## What is cached

| Data | Where | For how long |
| ---- | ----- | ------------ |
| OpenStreetMap lookups: place search, reverse geocoding, recommendations | Cache | 1 day (`OSM_CACHE_TIMEOUT`) |
| Google Maps results and photos | Never cached | See below |
| Wanderer trails and their GPX | Cache | 6 hours; a failed lookup is remembered for 10 minutes |
| GPX files converted to map data | Cache | 7 days; a stored file never changes, so nothing needs clearing |
| Login sessions | Cache, then database | 5 minutes in the cache (`SESSION_CACHE_SECONDS`); the database is the source of truth |

Only successful results are cached. A timeout or provider error is retried on the
next request. Immich and Strava data is never cached.

### Google Maps

Google's [Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies)
allow caching only place IDs and coordinates, so AdventureLog never caches Google
search, details, recommendation or reverse-geocoding results, and Google photos are
sent with `Cache-Control: no-store`. Every Google-backed lookup is a fresh request.
Turn on `ENABLE_RATE_LIMITS` to keep usage in check.

### OpenStreetMap

The public Nominatim and Overpass servers ask clients to cache, so every OpenStreetMap
lookup is kept for one day by default, empty answers included for Overpass. Change it
with `OSM_CACHE_TIMEOUT` (seconds).

## Memcached (default)

The Docker images include memcached and use it automatically. No setup is needed.
If memcached is unavailable, requests keep working and simply skip the cache.

## Using Redis instead

Redis is optional and meant for larger or multi-instance setups. It shares one cache
between several backend containers and has no 1 MB item limit.

1. Run a Redis server, for example by uncommenting the `redis` service in
   `docker/docker-compose.advanced.yml`.
2. Set in your env file:

```bash
CACHE_BACKEND=redis
REDIS_URL=redis://redis:6379/0
# CACHE_KEY_PREFIX=adventurelog   # if the Redis server is shared with other apps
```

3. Restart the backend.

Switch back by removing `CACHE_BACKEND` (or setting it to `memcached`). The bundled
memcached keeps running inside the image either way; it is idle when Redis is used.

## Turning caching off

`CACHE_BACKEND=dummy` disables caching, which is useful when debugging.
Sessions then always load from the database.
