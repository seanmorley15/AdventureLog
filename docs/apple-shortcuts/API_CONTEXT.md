# AdventureLog — External Client API Context

**Purpose:** a reusable context dump of the AdventureLog codebase as it relates to
building an external, non-browser client (Apple Shortcuts, scripts, mobile
automations) that authenticates with an API key and creates locations, visits and
categories.

**How to use this in a new chat session:** attach this file with `#File` and say
something like "use this as the codebase context, don't re-analyse the repo."
Everything below is written so it can be trusted without re-reading source, but
every claim carries a `file:line` reference so it can be spot-checked cheaply.

**Scope warning — there are two files named `API_CONTEXT.md`.** This one covers
only the slice an external client touches: API keys, locations, visits and
categories. It carries more detail on those four than anything else, but it omits
collections and sharing, permissions, the frontend, the other Django apps,
integrations and deployment.

- For the **rest of the HTTP surface** — collections, trip content, itineraries,
  media, stats, search, worldtravel, integrations, billing — see
  **`docs/architecture/API_CONTEXT.md`** (project-wide contract reference).
- For **how the system is built** — data model, permissions, frontend,
  deployment, CI — see **`docs/architecture/ARCHITECTURE.md`**.

**Analysed at:** 2026-08-09, against the working tree at
`/Users/lefteris.agrianitis/AdventureLog`.

**Confidence legend used throughout:**

- `[verified]` — read directly from the file at the cited line.
- `[inferred]` — deduced from reading code, not executed or tested.

Nothing here was executed. `[verified]` means "I read that line," not "I observed
that behaviour at runtime."

**Audit pass, 2026-08-09.** Every `file:line` reference in this document was
re-checked against the tree after the first draft. One substantive error and
~25 line-number drifts were corrected — see §12 for the list.

---

## 0. Which URL an external client should use `[verified at runtime 2026-08-09]`

Tested against a running Standard ("aio") stack on `http://localhost:8015`:

- **API keys work through the published port.** `X-API-Key` → 200. The request is
  proxied by SvelteKit rather than hitting Django directly, and the key survives
  that hop intact.
- **Omit the trailing slash on that port.** `/api/categories` → 200, but
  `/api/categories/` → **308** to the slashless form (SvelteKit normalizes, then
  its proxy re-adds the slash for Django). Against Django directly the slash *is*
  required. Following redirects makes both work.
- **`/docs/` and `/csrf/` are 404 on that port** — they are Django-only routes and
  nginx does not forward them.
- Each proxied call costs an extra backend round-trip, because the proxy fetches
  `GET /csrf/` per request even when the token is irrelevant to API-key auth.

Unauthenticated status codes are not uniform, which matters for error handling:
`GET /api/categories` → **401**, `GET /api/visits` → **403**, and
`GET /api/locations` → **200 with an empty page** (its permission class allows
anonymous safe methods and the queryset resolves to none). Branch on status code,
and do not treat 200 as proof of authentication.

---

## 1. Request routing overview

| Layer | Location | Notes |
| --- | --- | --- |
| App API root | `backend/server/main/urls.py:17` | `path('api/', include('adventures.urls'))` |
| Router | `backend/server/adventures/urls.py:7-32` | DRF `DefaultRouter`, so **trailing slashes are required** |
| Auth endpoints | `backend/server/main/urls.py:24-42` | **There is no `users/urls.py`.** The custom `/auth/...` DRF views are wired directly into the root urlconf, one `path()` per view, alongside `path("auth/", include("allauth.headless.urls"))` at `:19`. |
| Swagger UI | `backend/server/main/urls.py:10-15` | `drf-yasg` schema view, exposed at `GET /docs/` near the end of `urlpatterns`. Not `drf-spectacular`. |

Schema class is `rest_framework.schemas.openapi.AutoSchema`
(`main/settings.py:396`). The `adventures` ViewSets carry almost no
`@swagger_auto_schema` decoration, so `/docs/` output for locations/visits/
categories is auto-derived and thin — do not treat it as an accurate contract.

Registered router prefixes (all under `/api/`) `[verified: adventures/urls.py:8-32]`:

```
locations  collections  stats     generate      tags        transportations
notes      checklists   images    reverse-geocode  places    sunrise-sunset
categories ics-calendar search    attachments   lodging     recommendations
backup     trails       activities  visits      calendar    itineraries
itinerary-days
```

---

## 2. API key authentication

### Model — `backend/server/users/models.py:76-151` `[verified]`

```python
class APIKey(models.Model):
    _KEY_HASH_ITERATIONS = 600000
    _KEY_HASH_SALT_NAMESPACE = "users.APIKey"
    id, user (FK CustomUser, related_name='api_keys'), name,
    key_prefix (12 chars), key_hash (unique), created_at, last_used_at
```

- Token format: `f"al_{secrets.token_urlsafe(32)}"` → keys literally start with `al_` (`models.py:126`).
- Hashing: PBKDF2-HMAC-SHA256, 600,000 iterations, salt `"users.APIKey:<SECRET_KEY>"` (`models.py:108-117`).
- `APIKey.authenticate(raw_key)` re-derives the hash, looks up by `key_hash`, bumps `last_used_at` via a plain `.update()` (so no signals fire), returns the instance or `None` (`models.py:138-151`).
- **No expiry field. No scopes. No per-key permission model.** A key grants the
  full permissions of its owning user. The string "Invalid or expired API key"
  is misleading — nothing expires.
- **Rotating `SECRET_KEY` invalidates every existing API key**, because the
  secret is part of the hash salt. Worth knowing before advising anyone.

### DRF auth class — `backend/server/users/authentication.py:19-52` `[verified]`

Accepted headers:

```http
X-API-Key: al_...                  # preferred, checked first
Authorization: Api-Key al_...      # prefix match is case-insensitive
```

- No header → returns `None`, so `SessionAuthentication` still gets a turn.
- Header present but invalid → `AuthenticationFailed` → 401 with `WWW-Authenticate: Api-Key`.
- Success → returns `(api_key.user, api_key)`, so `request.user` is the owner and
  `request.auth` is the `APIKey` row.

### Registration — `backend/server/main/settings.py:392-396` `[verified]`

```python
'DEFAULT_AUTHENTICATION_CLASSES': (
    'users.authentication.APIKeyAuthentication',   # first
    'rest_framework.authentication.SessionAuthentication',
),
```

Applies globally to every DRF view, including all ViewSets below.

### CSRF — writes work with only the key `[verified]`

Two independent reasons:

1. DRF enforces CSRF only inside `SessionAuthentication`, which is never reached
   when the API key authenticates first.
2. `DisableCSRFForAPIKeyMiddleware` (`adventures/middleware.py:41-61`, registered
   at `settings.py:99`) sets `_dont_enforce_csrf_checks` when `X-API-Key` or
   `Authorization: Api-Key` is present — **but deliberately skips that bypass if
   a Django session cookie is also present** (`middleware.py:52-54`).

Shortcuts and curl send no cookies, so POST/PATCH/DELETE work with the header alone.

### Throttling `[verified]`

- `DEFAULT_THROTTLE_CLASSES = ['rest_framework.throttling.UserRateThrottle']`
  **only when** `ENABLE_RATE_LIMITS=true` (`settings.py:326`, default **false**),
  see `settings.py:397-400`.
- Relevant per-view throttle: `ExternalGeocodeThrottle`
  (`adventures/throttling.py:20`, scope `external_geocode`), default
  `120/minute` via `RATE_LIMIT_EXTERNAL_GEOCODE` (`settings.py:333`). Applied to
  `locations/quick-add/`, `places/search/`, `places/reverse/` and the
  `reverse-geocode` read actions.

### Key lifecycle endpoints — `backend/server/users/views.py` `[verified]`

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/auth/api-keys/` | `views.py:257-312`; raw key injected as `response_data["key"]` at `:310`, returned exactly once |
| GET | `/auth/api-keys/` | list (prefix only, never the raw key) |
| DELETE | `/auth/api-keys/<uuid>/` | `views.py:314+` |
| POST/GET/DELETE | `/auth/mobile-qr/` | `MobileQRCodeView`, `views.py:334+`; mints a key named `Mobile App - <Month DD, YYYY>` and embeds it in a QR payload, raw key at `:448` |

All require `IsAuthenticated`, which means **an API key can mint another API key**.

UI for humans: Settings → Security (`/settings?tab=security`).

### CLOUD_MODE note `[verified]`

`backend/server/cloud/middleware.py:25-32` independently re-resolves the key via
`APIKey.authenticate` to gate on subscription status. Irrelevant for
self-hosted, relevant if targeting the hosted product.

---

## 3. Locations

### Model — `backend/server/adventures/models.py:157-255` `[verified]`

Writable-ish fields: `name` (CharField 200, the only genuinely required one),
`location` (free-text place label, CharField 200), `tags` (ArrayField of
CharField), `description`, `rating` (Float), `price` / `price_currency`
(MoneyField), `link` (URLField), `is_public` (bool, default False), `coordinates`
(`gis_models.PointField(srid=4326)`), `category` (FK, nullable), `collections` (M2M).

Server-derived, read-only via the API: `city`, `region`, `country` (FKs).

**There is no `is_visited` column.** `Location.is_visited_status()`
(`models.py:183`) derives it from related `Visit.start_date` via
`adventures/utils/get_is_visited.py:16`. The serializer exposes it as a
read-only `SerializerMethodField`.

`Location.save()` (`models.py:212-244`) does three notable things:

1. Auto-creates/attaches a `general` category (`display_name: 'General'`,
   `icon: '🌍'`) when none is set.
2. Calls `super().save()` **then** `self.clean()`, so a `ValidationError` leaves
   the invalid row already persisted.
3. If `coordinates` are set, spawns a **daemon thread** running
   `background_geocode_and_assign` (see §7).

### Serializer — `LocationSerializer`, `adventures/serializers.py:517-729` `[verified]`

```python
class LocationSerializer(CoordinateSerializerMixin, CustomModelSerializer):
    images      = SerializerMethodField()
    visits      = VisitSerializer(many=True, read_only=False, required=False)   # :519  ⚠ see gotcha
    attachments = AttachmentSerializer(many=True, read_only=True)
    category    = CategorySerializer(read_only=False, required=False)           # :521  nested object, NOT an id
    is_visited  = SerializerMethodField()
    country / region / city = read_only
    collections = PrimaryKeyRelatedField(many=True, required=False)
    trails      = TrailSerializer(many=True, read_only=True, required=False)
```

Fields list at `serializers.py:536-541`. Read-only:
`id, created_at, updated_at, user, is_visited`.

`latitude` / `longitude` come from `CoordinateSerializerMixin`
(`adventures/utils/serializer_geo_fields.py:22-45`) as writable
`FloatField(required=False, allow_null=True)`, converted to the `coordinates`
Point in `_pop_lat_lon` (`:47-64`) and echoed back in `to_representation`
(`:73-80`).

- Sending only one of lat/lon → `'Valid latitude and longitude are required together.'`
- **No -90/90 or -180/180 range check on this path.** Range coercion exists only
  in `quick-add`, via `coerce_coordinate`.

### `POST /api/locations/`

ViewSet: `LocationViewSet`, `adventures/views/location_view.py:54-63` `[verified]`

```python
serializer_class   = LocationSerializer
permission_classes = [IsOwnerOrSharedWithFullAccess]   # adventures/permissions.py:238-255
pagination_class   = StandardResultsSetPagination
```

`perform_create` (`location_view.py:142-157`) validates collection permissions
then forces `user=request.user`.

Minimum body:

```json
{ "name": "Blue Lagoon" }
```

Practical body:

```json
{
  "name": "Blue Lagoon",
  "latitude": 63.88,
  "longitude": -22.45,
  "description": "Geothermal spa",
  "location": "Grindavík, Iceland",
  "tags": ["swim"],
  "category": { "name": "nature", "display_name": "Nature", "icon": "🏞" }
}
```

Response: `201` with the full serialized location, including `id` (UUID),
`latitude`/`longitude`, resolved `category`, `is_visited: false`, `visits: []`,
`images`, `collections`, and a **nested full `user` object**.
`city`/`region`/`country` are usually still `null` in this response because
geocoding runs on a background thread.

### ⚠ Gotcha: nested `visits` on POST cannot be used `[verified at runtime 2026-08-09]`

An earlier revision of this file claimed a flat 500. Both outcomes were then
observed against a live stack:

| Payload | Result |
| --- | --- |
| `visits: [{"start_date": "..."}]` | **400** `{"visits":[{"location":["This field is required."]}]}` |
| `visits: [{"start_date": "...", "location": "<existing uuid>"}]` | **500** |

`visits` is declared writable (`serializers.py:519`), but `VisitSerializer.location`
is `required=True` (confirmed by introspecting the serializer's fields), so nested
validation fails before `LocationSerializer.create` runs — hence the 400 naming a
field the client cannot know when creating a *new* location. If you do satisfy
`location`, `create` (`serializers.py:674-692`) never pops `visits` before
`Location.objects.create(**validated_data)`, the value hits the reverse
`ReverseManyToOneDescriptor` (`TypeError: Direct assignment to the reverse side of
a related set is prohibited`), and you get the 500.

**Net: create the location first, then POST `/api/visits/`.**

Nested visits are only honoured in `update` (`serializers.py:694-729`, the
replacement itself at `:724-728`), where they **delete and replace all existing
visits** — which also destroys any `Activity` rows cascading off those visits.

No test covers this path. The frontend sidesteps it entirely by posting to
`/api/visits/` separately (`frontend/src/lib/components/locations/LocationVisits.svelte:256,279,785`).

### `POST /api/locations/quick-add/` — the external-client-friendly alternative

`location_view.py:196-316` (`def quick_add` at `:202`), throttled by
`ExternalGeocodeThrottle` `[verified]`.

Accepts / does, in one call:

- `name` (required), `latitude` + `longitude` (required, **range-validated** via `coerce_coordinate`)
- `category` as **either a UUID string or an object** (`_normalize_quick_add_category`, `location_view.py:675-718`)
- server-side reverse geocoding, result merged onto the location
- `place_id` → enriched server-side through `extract_google_place_details`
  (`adventures/views/quick_add_utils.py:152-166`) into description / rating /
  review_count / website / phone / `google_maps_url`
- `collection_id` + `itinerary_date` → creates a collection itinerary item
- `photos` (list of remote URLs) → imported as `ContentImage` with
  `Source.GOOGLE`
- `tags` / `types`, `is_public`, `rating`, `description`, `link`

Returns `201` with the serialized location, plus optional
`quick_add_itinerary_item` and `quick_add_image_import` keys.

It still does **not** accept nested visits.

---

## 4. Visits

### Model — `adventures/models.py:128-155` `[verified]`

`id` (UUID), `location` (FK, `related_name='visits'`), `start_date` /
`end_date` (`DateTimeField`, both nullable), `timezone` (CharField with
`TIMEZONES` choices), `notes` (Text), `created_at`, `updated_at`, plus generic
image/attachment relations.

### Serializer — `VisitSerializer`, `adventures/serializers.py:461-491` `[verified]`

Fields: `id, start_date, end_date, timezone, notes, activities, location,
created_at, updated_at`. Read-only: `id, created_at, updated_at`.

- `validate` coerces both dates through `ensure_aware_utc`, then applies
  `normalize_all_day_visit_dates`.
- `create` defaults `end_date` to `start_date` when omitted (`:487-491`).

### `POST /api/visits/` — canonical external flow

```json
{
  "location": "<location-uuid>",
  "start_date": "2026-01-05T14:00:00Z",
  "end_date": "2026-01-05T18:00:00Z",
  "timezone": "Europe/Athens",
  "notes": "..."
}
```

`end_date`, `timezone`, `notes` are all optional. `timezone` must be a valid
tz database name.

`VisitViewSet` — `adventures/views/visit_view.py:9-71` `[verified]`:

- `permission_classes = [IsOwnerOrSharedWithFullAccess]`
- queryset limited to visits on locations you own, or in collections you own /
  are shared with
- `perform_create` re-checks object permission against the **location**, saves,
  then calls `background_geocode_and_assign(str(location.id))`
- `perform_update` refuses to move a visit to a different location
  (`PermissionDenied`)
- detail routes: `PATCH` / `DELETE /api/visits/<uuid>/`

---

## 5. Categories

### Model — `adventures/models.py:549-568` `[verified]`

`id` (UUID), `user` (FK), `name` (lowercased by convention), `display_name`,
`icon` (default `🌍`). Categories are **per-user**, with a real DB constraint:
`Meta.unique_together = ['name', 'user']`. `clean()` lowercases and strips `name`.

### ViewSet — `adventures/views/category_view.py:9-39`, `permission_classes = [IsAuthenticated]` `[verified]`

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/categories/` | only `request.user`'s categories; custom `list` returns the whole set — **not paginated** |
| POST | `/api/categories/` | `CategorySerializer.create` forces lowercase `name` (`serializers.py:177-180`) |
| DELETE | `/api/categories/<uuid>/` | blocked for `general`; reassigns affected locations to `general`, creating it if needed |

Serializer fields (`serializers.py:167-192`): `id, name, display_name, icon,
num_locations`. `num_locations` is a `SerializerMethodField` doing a `COUNT` per
row — N+1 by design, fine at typical category counts.

### Auto-creation on write — two paths `[verified]`

1. `Location.save()` attaches `general` when `category` is null.
2. `LocationSerializer.validate_category` (`serializers.py:634-644`) lowercases
   the name and returns an existing match; `get_or_create_category`
   (`serializers.py:646-669`) does
   `Category.objects.get_or_create(user, name, defaults={display_name, icon})`.

So a client can send a category **name** it has never used and the server creates
it on first use — no need to pre-fetch the list.

⚠ On **update**, category changes are silently ignored for non-owners — the guard
is `if category_data and instance.user == user:` (`serializers.py:706`), with no
`else` and no error. A shared user's PATCH returns 200 with the old category.

⚠ `LocationSerializer` does **not** accept a bare UUID or `{"id": ...}` for
`category`. Only `quick-add` normalizes an id.

---

## 6. Filtering, search, and the absence of geo queries

`LocationViewSet` has **no `filter_backends`, no `search_fields`, and no
`list()` override** `[verified by grep]`. Consequences:

| Endpoint | Behaviour |
| --- | --- |
| `GET /api/locations/` | default `ModelViewSet.list` over `get_queryset()` → `Location.objects.retrieve_locations(user, include_owned=True, include_shared=True).order_by('-updated_at')` (`location_view.py:65-84`). **Only `?page` and `?page_size` are honoured** — `order_by` / `order_direction` / `include_collections` are ignored here because `apply_sorting` is never called from `list`. |
| `GET /api/locations/filtered/` | `location_view.py:317-348`. `types=` must be existing category **names** for the user (or `all`), else 400. `is_visited=true\|false` via `_apply_visit_filtering` (`location_view.py:761-781`, `visits__start_date__lte=today`). Supports `order_by` (`name\|type\|date\|rating\|updated_at`), `order_direction`, `include_collections`, pagination. |
| `GET /api/locations/all/` | unpaginated full dump; `include_collections`, `nested`, `allowed_nested_fields`. |
| `GET /api/locations/pins/` | action at `location_view.py:569`, `MapPinSerializer` at `serializers.py:731`: `id, name, latitude, longitude, is_visited, category` for every owned location. **The only cheap bulk coordinate feed.** |
| `GET /api/search/?q=&types=&limit=&offset=` | separate endpoint, `adventures/views/global_search_view.py:13-58`, `IsAuthenticated`. Returns `{query, total, limit, offset, results, facets}` from `adventures/services/search/global_search.py`. Substring / `icontains` based. |

Pagination: `StandardResultsSetPagination` (`adventures/utils/pagination.py`) —
`page_size = 25`, `page_size_query_param = 'page_size'`, `max_page_size = 1000`.

### No geographic filtering exists anywhere `[verified by grep]`

A repo-wide search for `dwithin`, `distance_lte`, `bbox`, `Distance(`,
`coordinates__` returns only `coordinates__isnull` filters
(`views/location_image_view.py:143`, plus a backfill management command) and
Pillow text bounding boxes.

There is no radius, bounding-box, or nearest-neighbour query parameter on any
locations route — **despite `coordinates` being a real PostGIS `PointField`,
which means `dwithin` is available and cheap to add.**

Therefore "nearby duplicate detection" today must be client-side: pull
`/api/locations/pins/` and compute distances locally, or name-match via
`/api/search/`.

---

## 7. Geocoding and place lookup — already server-side

### Proxy endpoints (server's Google key, OSM fallback)

`PlacesAPI` — `adventures/views/places_api_view.py:12`, `IsAuthenticated` `[verified]`:

| Path | Notes |
| --- | --- |
| `GET /api/places/search/?query=&include_meta=` | `search_places()`; throttled |
| `GET /api/places/place_details/?place_id=&name=&language=` | `get_place_details()` |
| `GET /api/places/reverse/?lat=&lon=` | `reverse_geocode()`; throttled |

`ReverseGeocodeViewSet` — `adventures/views/reverse_geocode_view.py:13+`, `IsAuthenticated` `[verified]`:

| Path | Notes |
| --- | --- |
| `GET /api/reverse-geocode/reverse_geocode/?lat=&lon=` | returns `region_id`, `city_id`, `country_id`, `display_name`, visited flags (`adventures/utils/geocoding_utils.py:~400-420`); throttled |
| `GET /api/reverse-geocode/search/?query=&include_meta=` | forward geocode / place search |
| `GET /api/reverse-geocode/place_details/?place_id=` | place details |
| `POST /api/reverse-geocode/mark_visited_region/` | bulk-creates `VisitedRegion`/`VisitedCity` from stored `location.region`/`location.city` for visited locations; returns counts and names |

### Provider configuration `[verified]`

`GOOGLE_MAPS_API_KEY = getenv('GOOGLE_MAPS_API_KEY', '')`
(`main/settings.py:473`). Consumed by:

- `adventures/services/places/search.py:306` — Google attempted first, **OSM fallback** when unset
- `adventures/services/places/details.py:84`
- `adventures/services/geocoding/reverse.py:65`
- `adventures/services/recommendations/search.py:51,232`
- `adventures/geocoding.py:37,68` — `reverse_geocode_google` returns
  `{"error": "Geocoding service unavailable..."}` when no key

Exposure to the frontend: `integrations/views/integration_view.py:17` reports
`google_map_integration = settings.GOOGLE_MAPS_API_KEY != ''`.

**Implication for any external client:** it does not need its own Google API
key. `/api/places/search/` and `/api/reverse-geocode/` already do place lookup
with the server's key, and degrade to OpenStreetMap rather than failing.

### No Google Maps URL resolver exists `[verified by grep]`

Nothing in the backend parses `maps.app.goo.gl`, `goo.gl/maps`, or
`google.com/maps` **inbound**. The only matches are outbound link *construction*
in the frontend (`routes/locations/[id]/+page.svelte:271`,
`lib/components/shared/ExternalMapLinks.svelte:20`). Resolving a shared Maps
link is entirely the client's problem today.

### Background assignment — ordering matters `[verified]`

`background_geocode_and_assign` (`adventures/models.py:24-62`):

1. Reverse-geocodes the location's coordinates.
2. Assigns `region`, `city`, `country`.
3. **Only if `location.is_visited_status()` is already true**, `get_or_create`s
   `VisitedRegion` / `VisitedCity`.

Two consequences for an external client:

1. Immediately after `POST /api/locations/`, the location has no visits, so
   region/city get attached but **not** marked visited — and the response body
   typically still shows `city`/`region`/`country` as `null` because the thread
   is asynchronous.
2. The subsequent `POST /api/visits/` re-runs `background_geocode_and_assign`
   from `VisitViewSet.perform_create`, and *that* pass creates the visited
   region/city records.

**Correct order: create location → create visit.**

---

## 8. Documentation infrastructure

| Thing | Location |
| --- | --- |
| Public docs site | `documentation/` (VitePress) |
| Page tree | `documentation/docs/{intro,install,configuration,guides,usage,troubleshooting,changelogs}` |
| Sidebar config | `documentation/.vitepress/config.mts` — "API Keys" entry at `:299`, Guides block at `:364-372` |
| Per-page SEO metadata | `documentation/.vitepress/seo.ts` — `api_keys.md` at `:184-189`, `guides/admin_panel.md` at `:209+` |
| Existing API key page | `documentation/docs/configuration/api_keys.md` |
| Existing guides | `guides/admin_panel.md`, `guides/invite_user.md`, `guides/v0-7-1_migration.md` |
| Internal dev docs | root `docs/` — partly gitignored (`.gitignore` lists `docs/cursor-prompts/`, `docs/FIX_PACKAGE_PLAN.md`, `docs/GITHUB_COMMENTS.md`) |

### Known documentation defect

`documentation/docs/configuration/api_keys.md:63` (Security Notes) claims raw keys
are stored as "only a SHA-256 hash". The implementation is PBKDF2-HMAC-SHA256 at
600,000 iterations (`users/models.py:108-117`). Stale.

---

## 9. Testing and CI reality

- Backend tests live in `backend/server/adventures/tests/` (e.g.
  `test_geocoding_provider_selection.py` uses
  `@override_settings(GOOGLE_MAPS_API_KEY="test-key")` with patched providers).
- `.github/workflows/backend-test.yml` **never runs the test suite** `[verified]`.
  It installs deps, starts the PostGIS compose stack
  (`docker/docker-compose.database.yml`), runs `migrate`, backgrounds
  `runserver`, and then just `curl`s `http://localhost:8000/`. That is a boot
  smoke test only.
- Practical consequence: any regression in serializers or viewsets will not be
  caught by CI. New behaviour needs tests **plus** a CI step that actually runs
  them, or it is unprotected.
- Local testing needs PostGIS + GDAL (`python3-gdal`), so a plain `manage.py
  test` on a bare machine will fail on the GIS backend.

---

## 10. Quick reference — full external client flow

```bash
BASE=https://adventure-api.example.com
KEY=al_xxxxxxxxxxxx

# 1. list categories (optional; names are get-or-created on write anyway)
curl -s "$BASE/api/categories/" -H "X-API-Key: $KEY"

# 2. create a location
curl -s -X POST "$BASE/api/locations/" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"name":"Blue Lagoon","latitude":63.88,"longitude":-22.45,
       "category":{"name":"nature","display_name":"Nature","icon":"🏞"}}'
# -> 201, read .id

# 2b. or one-shot with server-side geocoding + Google enrichment
curl -s -X POST "$BASE/api/locations/quick-add/" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"name":"Blue Lagoon","latitude":63.88,"longitude":-22.45,
       "category":"<category-uuid>"}'

# 3. log the visit (this is what marks region/city visited)
curl -s -X POST "$BASE/api/visits/" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"location":"<location-uuid>","start_date":"2026-01-05T14:00:00Z",
       "timezone":"Europe/Athens"}'

# helpers
curl -s "$BASE/api/places/search/?query=blue+lagoon" -H "X-API-Key: $KEY"
curl -s "$BASE/api/reverse-geocode/reverse_geocode/?lat=63.88&lon=-22.45" -H "X-API-Key: $KEY"
curl -s "$BASE/api/locations/pins/" -H "X-API-Key: $KEY"   # bulk coords, client-side dedupe
```

---

## 11. Summary of gaps found

| # | Gap | Evidence | Severity |
| --- | --- | --- | --- |
| 1 | Nested `visits` on `POST /api/locations/` raises → 500 | `serializers.py:519` vs `:674-692` | bug, blocks single-call create |
| 2 | No radius / bbox / nearest filtering on locations | grep: no `dwithin`/`distance_lte`/`bbox` | missing feature; PostGIS already available |
| 3 | `LocationSerializer` won't accept a category id | `serializers.py:634-644` vs `location_view.py:675` | inconsistency with `quick-add` |
| 4 | No lat/lon range validation on plain create | only `quick-add` uses `coerce_coordinate` | data-quality risk |
| 5 | No inbound Google/Apple Maps URL resolver | grep: outbound construction only | missing feature |
| 6 | `api_keys.md` says SHA-256, code is PBKDF2 | `api_keys.md` vs `users/models.py:108-117` | doc defect |
| 7 | API keys have no scopes and no expiry | `users/models.py:76-151` | security posture, out of scope here |
| 8 | Backend test suite is never run in CI | `.github/workflows/backend-test.yml` | process gap |
| 9 | `order_by` silently ignored on `GET /api/locations/` | `apply_sorting` not called from `list` | surprising behaviour |

---

## 12. Audit log

Every `file:line` reference above was re-verified against the working tree on
2026-08-09, after the first draft. Results:

### One substantive error

**"Auth endpoints — `backend/server/users/urls.py`" was wrong: that file does not
exist.** The `users` app has no urlconf at all. The custom `/auth/...` DRF views
(`api-keys/`, `mobile-qr/`, `current-user/`, `social-providers/`,
`is-registration-disabled/`, `users/`, `user/<username>/`, `update-user/`,
`user-metadata/`, `user-media-usage/`, `disable-password/`) are each wired
directly into `main/urls.py:24-42`, sharing the `/auth/` prefix with
`allauth.headless.urls` (mounted at `:19`) without being part of it. Corrected in
§1.

### Line-number drift corrected

| Reference | Was | Actual |
| --- | --- | --- |
| `main/urls.py` — api include | `:18` | `:17` |
| `main/urls.py` — schema view | `:7-16` | `:10-15` |
| `adventures/urls.py` — router block | `:7-35` / `:8-34` | `:7-32` / `:8-32` |
| `main/settings.py` — `DEFAULT_SCHEMA_CLASS` | `:397` | `:396` |
| `users/models.py` — `APIKey` | `:76-152` | `:76-151` |
| `users/models.py` — `authenticate()` | `:139-152` | `:138-151` |
| `users/authentication.py` — class | `:20-52` | `:19-52` |
| `adventures/middleware.py` — API-key CSRF class | `:41-62` | `:41-61` (file is 61 lines) |
| `adventures/throttling.py` — `ExternalGeocodeThrottle` | `:21` | `:20` |
| `users/views.py` — `MobileQRCodeView` | `:~418-450` | `:334+` (raw key at `:448`) |
| `cloud/middleware.py` — key re-resolution | `:24-35` | `:25-32` |
| `adventures/models.py` — `Location` | `:157-256` | `:157-255` |
| `adventures/models.py` — `is_visited_status` | `:~182` | `:183` |
| `adventures/models.py` — `Location.save` | `:~212-245` | `:212-244` |
| `adventures/models.py` — `Category` | `:549-569` | `:549-568` |
| `adventures/serializers.py` — `LocationSerializer` | `:517-731` | `:517-729` |
| `adventures/serializers.py` — `create()` | `:675-693` | `:674-692` |
| `adventures/serializers.py` — non-owner category guard | `:704-710` | `:706` |
| `adventures/serializers.py` — `MapPinSerializer` | `:733-744` | `:731` |
| `adventures/utils/serializer_geo_fields.py` — `to_representation` | `:74-80` | `:73-80` |
| `adventures/views/location_view.py` — `get_queryset` | `:66-84` | `:65-84` |
| `adventures/views/location_view.py` — `perform_create` | `:~141-157` | `:142-157` |
| `adventures/views/location_view.py` — `quick_add` | `:~187-320` | `:196-316` (def at `:202`) |
| `adventures/views/location_view.py` — `filtered` | `:~322-350` | `:317-348` |
| `adventures/views/location_view.py` — `_apply_visit_filtering` | `:762-784` | `:761-781` |
| `adventures/views/visit_view.py` — class | `:9-72` | `:9-71` |
| `adventures/views/category_view.py` — class | `:9-45` | `:9-39` (file is 39 lines) |
| `adventures/views/global_search_view.py` — class | `:14-58` | `:13-58` |
| `adventures/permissions.py` — `has_permission` | `:~236-250` | `:238-255` |
| `documentation/.../api_keys.md` — SHA-256 claim | `:64` | `:63` |

### One claim strengthened

`Category` uniqueness was described as "effectively `(user, name)` enforced
through the `get_or_create` call sites." It is stronger than that: there is a real
`Meta.unique_together = ['name', 'user']` DB constraint. Corrected in §5.

Contrast with `worldtravel.VisitedRegion` / `VisitedCity`, which genuinely have
**no** DB constraint — their uniqueness lives only in a `save()` override that
also blocks re-saving an existing row. See `docs/architecture/ARCHITECTURE.md` hazard #21.

### Re-confirmed as written

`models.py:126` (`al_` token format), `models.py:108-117` (PBKDF2 600k
iterations), `settings.py:392-396` (auth class order), `settings.py:326` / `:330`
/ `:333` (rate-limit flags and values), `settings.py:397-400` (throttle classes),
`settings.py:473` (`GOOGLE_MAPS_API_KEY`), `middleware.py:52-54` (session-cookie
guard on the CSRF bypass), `users/views.py:257-312` and `:310` (API key create,
raw key returned once), `users/views.py:314+` (delete), `serializers.py:519`
/ `:521` / `:536-541` / `:634-644` / `:646-669` / `:724-728`,
`serializers.py:461-491` and `:487-491` (VisitSerializer, `end_date` defaulting),
`serializers.py:167-192` and `:177-180` (CategorySerializer),
`serializer_geo_fields.py:22-45` and `:47-64`, `models.py:128-155` (Visit),
`models.py:24-62` (`background_geocode_and_assign`),
`get_is_visited.py:16`, `quick_add_utils.py:152`,
`location_view.py:54-63` and `:569` (pins) and `:675-718`,
`places_api_view.py:12`, `reverse_geocode_view.py:13`,
`location_image_view.py:143` (the only non-migration `coordinates__isnull`),
`integration_view.py:17`, `LocationVisits.svelte:256,279,785`,
`locations/[id]/+page.svelte:271`, `ExternalMapLinks.svelte:20`,
`config.mts:299` and the Guides block, `seo.ts:184` and `:209`, the guides file
list, and the absence of any inbound Google Maps URL parsing.

Also re-confirmed by grep: **no geographic filtering anywhere** — `dwithin`,
`distance_lte`, `Distance(`, `__within` and `__bbcontains` return zero
non-migration hits across the backend. Gap #2 stands.
