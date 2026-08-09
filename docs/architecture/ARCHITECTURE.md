
# AdventureLog — Architecture Reference

**Purpose:** a durable, reusable map of how this project is structured and how it
works. Written so a fresh session (or a new engineer) can get productive without
re-exploring the repo.

**How to use this in a new chat session:** attach this file with `#File` and say
"use this as the codebase context, don't re-analyse the repo." Then read only the
specific files you intend to change.

**Companion documents:**

- **`docs/architecture/API_CONTEXT.md`** — the project-wide HTTP contract: every endpoint,
  params, request bodies, response shapes, status codes, and a 32-item register of
  contract inconsistencies. Where this file says *how the system is built*, that
  one says *what the wire protocol is*. Sections 3.4 and 3.5 here are only a
  routing index; go there for actual contracts.
- `docs/apple-shortcuts/API_CONTEXT.md` — deep dive on one slice of that surface
  (API keys, locations, visits, categories) for an external client.
- `docs/apple-shortcuts/IMPLEMENTATION_PLAN.md` — worked example of a feature
  plan built on that slice.

**Analysed:** 2026-08-09, against the working tree at
`/Users/lefteris.agrianitis/AdventureLog`. Version `v0.13.0`
(`backend/server/main/settings.py`, `ADVENTURELOG_RELEASE_VERSION`; frontend
`package.json` agrees).

**Confidence markers used throughout:**

- `[v]` verified — the cited file/line was read directly.
- `[i]` inferred — deduced from reading code, not executed or observed at runtime.

**Nothing in this document was executed.** No server was booted, no tests run, no
database queried. `[v]` means "I read that line," not "I observed that behaviour."

---

## 1. System at a glance

AdventureLog is a self-hostable travel journal. Django + DRF backend, SvelteKit
SSR frontend, PostGIS database. Users record **Locations** (places), **Visits**
(dated stays at a place), and group them into **Collections** (trips), with
world-travel reference data (countries/regions/cities) driving "places I've been"
statistics.

### Runtime topology — Standard ("aio") deployment `[v]`

```
browser
  │  host :8015
  ▼
┌──────────────────────── container: adventurelog (target: aio) ─────────────┐
│  nginx :80                                                                 │
│    /static/            → /code/staticfiles/          (alias, from build)    │
│    /protectedMedia/    → /code/media/   (internal; X-Accel-Redirect only)   │
│    /media|/admin|/accounts → django                                         │
│    /                   → frontend                                           │
│                                                                             │
│  supervisord manages:                                                       │
│    gunicorn main.wsgi  127.0.0.1:8000   (--workers ${GUNICORN_WORKERS:-2})   │
│    node /app/start.js  127.0.0.1:3000   (SvelteKit SSR)                      │
│    memcached           127.0.0.1:11211                                      │
│    cron -f                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
  │ db:5432
  ▼
postgis/postgis:16-3.5   (volume postgres_data)
```

Only port 80 is exposed from the container. Media lives on the
`adventurelog_media` volume at `/code/media/`.

**The browser never talks to Django directly.** Every request goes through
SvelteKit, either as an SSR load or through the catch-all proxy at
`/api/[...path]` and `/auth/[...path]`. See section 8.3.

### Advanced deployment `[v]`

`docker/docker-compose.advanced.yml` splits the same code into three containers:
`web` (frontend image, `:8015→3000`), `server` (backend image, `:8016→80`,
nginx + gunicorn), `db`. The frontend reaches the backend at
`PUBLIC_SERVER_URL=http://server:8000`.

---

## 2. Repository layout

```
backend/server/          Django project (see §3)
  main/                  settings, root urls, wsgi, csrf/health/media views
  adventures/            the core domain app — biggest app by far
  worldtravel/           country/region/city reference data + visited tracking
  users/                 CustomUser, APIKey, adapters, auth backend, admin
  integrations/          Immich, Strava, Wanderer, Endurain
  billing/               Stripe Subscription (cloud only)
  cloud/                 CLOUD_MODE gating middleware + /auth/current-user/
  achievements/          scaffolding, NOT in INSTALLED_APPS
  templates/             allauth/mfa/invitations template overrides
frontend/                SvelteKit 2 / Svelte 4 app
docker/                  single Dockerfile (3 targets) + compose variants + nginx/supervisor
docker-compose.yml       Standard deployment (app + db)
documentation/           public VitePress docs site
k8s/                     plain manifests (base/ maintained, legacy/ deprecated)
scripts/                 installer libs, validate-env, backup/restore/deploy
install_adventurelog.sh  interactive installer (v2.0.0)
docs/                    internal dev docs (this file; partly gitignored)
brand/  .devcontainer/  .github/workflows/
```

---

## 3. Backend: apps, settings, routing

### 3.1 `INSTALLED_APPS` `[v]` (`main/settings.py:56-89`)

`allauth_ui`, Django contrib (incl. `sites`, `staticfiles`), `storages`,
`rest_framework`, `rest_framework.authtoken` (installed but unused for auth),
`allauth` + `account` + `mfa` + `headless` + `socialaccount` + providers
`github` and `openid_connect`, `invitations`, `drf_yasg`, `djmoney`,
`corsheaders`, **`adventures`**, **`worldtravel`**, **`users`**,
`billing.apps.BillingConfig`, `cloud.apps.CloudConfig`, `integrations`,
`django.contrib.gis`, `widget_tweaks`, `slippers`.
`INSTALLED_APPS` spans `settings.py:56-89`.
`# 'achievements', # Not done yet` — **commented out** (`settings.py:86`). The app
`# 'achievements', # Not done yet` — **commented out** (`settings.py:86`). The app
has no `migrations/` directory, so its tables do not exist.

`cloud/` and `main/` contain no models.

### 3.2 Key settings `[v]`

| Concern | Value / location |
| --- | --- |
| `AUTH_USER_MODEL` | `users.CustomUser` (`settings.py:284`) |
| DB engine | `django.contrib.gis.db.backends.postgis`, env resolved by a local `env(*keys)` helper accepting `PGDATABASE\|POSTGRES_DB` etc., `sslmode: prefer` |
| Cache | **hardcoded** `PyMemcacheCache` at `127.0.0.1:11211`, TTL 1 day. No env override. |
| `DEBUG` | defaults **true** |
| `ALLOWED_HOSTS` | `['*']` |
| Static | `whitenoise.CompressedManifestStaticFilesStorage`, `STATIC_ROOT=BASE_DIR/staticfiles` |
| Media | `FileSystemStorage` → `S3Boto3Storage` when `MEDIA_STORAGE=s3` |
| DRF auth | `users.authentication.APIKeyAuthentication` **first**, then `SessionAuthentication` (`settings.py:392-396`) |
| DRF schema | `rest_framework.schemas.openapi.AutoSchema`; docs UI is **drf-yasg** at `GET /docs/` |
| Throttling | only when `ENABLE_RATE_LIMITS=true` (default **false**) |
| `ACCOUNT_RATE_LIMITS` | `{...} if ENABLE_RATE_LIMITS else {}` — the empty dict **removes allauth's own defaults** |
| CORS + CSRF | one env var `CSRF_TRUSTED_ORIGINS` feeds **both** `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`; `CORS_ALLOW_CREDENTIALS=True` |
| Session cookie | name `sessionid`, `SameSite=Lax`, `Secure` iff `FRONTEND_URL` starts with `https`, domain derived via `publicsuffix2.get_sld` → `.registrable.domain` (None for IPs/single-label) |
| `SESSION_SAVE_EVERY_REQUEST` | `True` (rolling expiry) |
| Password validators | **none defined anywhere in the repo** |
| Email backend | **console by default**; SMTP only when `EMAIL_BACKEND` != `console` |
| `ACCOUNT_EMAIL_VERIFICATION` | `none` by default |
| Reference data pin | `COUNTRY_REGION_JSON_VERSION = 'v3.1'` |

`requirements.txt` highlights `[v]`: Django 5.2.13, DRF >=3.15.2,<3.16,
**django-allauth 0.63.3** (notably old for Django 5.2), django-invitations 2.1.0,
drf-yasg 1.21.15, whitenoise, django-storages + boto3, pillow + pillow-heif +
django-resized, django-geojson/geojson/gpxpy/geopy/overpy (**no GDAL Python
package** — the system library is used, hence `gdal-bin`/`libgdal-dev` in Docker),
ijson/tqdm/psutil (world data import), pymemcache, django-ical + icalendar,
reportlab (PDF), stripe, django-money, publicsuffix2, qrcode.

### 3.3 Middleware chain `[v]` (`settings.py:95-111`, order matters)

```
whitenoise.WhiteNoiseMiddleware
adventures.middleware.XSessionTokenMiddleware              ← header→session cookie
adventures.middleware.DisableCSRFForSessionTokenMiddleware ← blanket CSRF exempt
adventures.middleware.DisableCSRFForAPIKeyMiddleware       ← CSRF exempt (guarded)
adventures.middleware.DisableCSRFForMobileLoginSignup      ← CSRF exempt (2 paths)
corsheaders.CorsMiddleware
django.contrib.sessions.SessionMiddleware
django.middleware.common.CommonMiddleware
adventures.middleware.OverrideHostMiddleware               ← rewrites HTTP_HOST
django.middleware.csrf.CsrfViewMiddleware
django.contrib.auth.AuthenticationMiddleware
cloud.middleware.CloudAccessMiddleware                     ← subscription gate
django.contrib.messages.MessageMiddleware
django.middleware.clickjacking.XFrameOptionsMiddleware
allauth.account.middleware.AccountMiddleware
```

All five custom classes live in `backend/server/adventures/middleware.py`
(61 lines total) `[v]`:

1. **`OverrideHostMiddleware`** — if `PUBLIC_URL` is set, rewrites `HTTP_HOST`,
   `wsgi.url_scheme`, `HTTP_X_FORWARDED_PROTO`. Placed before
   `CsrfViewMiddleware` so Referer/origin checks and allauth URL building see the
   public host, not the container host.
2. **`XSessionTokenMiddleware`** — copies the `X-Session-Token` header into
   `request.COOKIES['sessionid']`. Runs before `SessionMiddleware`, so a header
   is indistinguishable from a cookie to Django.
3. **`DisableCSRFForSessionTokenMiddleware`** — any request carrying
   `X-Session-Token` gets `_dont_enforce_csrf_checks = True`.
4. **`DisableCSRFForMobileLoginSignup`** — CSRF exempt when `X-Is-Mobile: true`
   **and** path is exactly `/auth/browser/v1/auth/login` or `.../signup`.
5. **`DisableCSRFForAPIKeyMiddleware`** — exempts `X-API-Key` or
   `Authorization: Api-Key`, **but returns early (keeps CSRF on) if a
   `sessionid` cookie is also present**. The only one of the three exemptions
   with a confusion guard.

### 3.4 Complete URL map

Root (`main/urls.py`) `[v]`:

| Prefix | Target |
| --- | --- |
| `api/` | `adventures.urls` **and** `worldtravel.urls` (both mounted at the same prefix) |
| `api/integrations/` | `integrations.urls` |
| `api/billing/` | `billing.urls` |
| `auth/` | `allauth.headless.urls` → both `/auth/browser/v1/...` and `/auth/app/v1/...` |
| `accounts/` | `allauth.urls` (classic, server-rendered; social login lives here) |
| `invitations/` | `django-invitations`, namespace `invitations` |
| `admin/` | Django admin |
| `docs/` | drf-yasg Swagger UI |
| `media/<path>` | `main.views.serve_protected_media` |
| `csrf/`, `health/`, `public-url/` | `main.views` helpers |
| `/` | `home.html` TemplateView |

Custom `/auth/...` DRF views (not allauth) `[v]`:
`is-registration-disabled/`, `users/`, `user/<username>/`, `update-user/`,
`user-metadata/`, `user-media-usage/`, `current-user/`, `social-providers/`,
`disable-password/`, `api-keys/`, `api-keys/<uuid>/`, `mobile-qr/`.

`adventures/urls.py` DRF `DefaultRouter` `[v]` — **trailing slashes required**:

```
locations  collections  stats     generate    tags        transportations
notes      checklists   images    reverse-geocode  places  sunrise-sunset
categories ics-calendar search    attachments lodging     recommendations
backup     trails       activities  visits    calendar    itineraries
itinerary-days
```

`worldtravel/urls.py` `[v]`: `countries/`, `regions/`, `visitedregion/`,
`visitedcity/`, `<country_code>/regions/`, `<country_code>/visits/`,
`regions/<region_id>/cities/`, `regions/<region_id>/cities/visits/`,
`globespin/`.

`integrations/urls.py` `[v]`: `immich`, `strava`, `wanderer`, `endurain`, plus an
empty-prefix `IntegrationView`. **`immich` is registered twice** (once as
`ImmichIntegrationView`, once as `ImmichIntegrationViewSet`, with the
empty-prefix router registered between them) — resolution depends on
registration order. Hazard, see §16.

### 3.5 Viewset index (`adventures/views/`) `[v] paths, [i] some internals`

| Route | Class | Notes |
| --- | --- | --- |
| `locations/` | `LocationViewSet` | `list` honours only pagination; extra actions `quick-add/`, `filtered/`, `all/`, `pins/`, `calendar/`, `<id>/additional-info/`, `<id>/share-image/<aspect>/`. Owner-only `destroy`. |
| `collections/` | `CollectionViewSet` | 1223 lines. Sharing lifecycle, PDF export, PNG share card, ZIP export/import, duplicate. Widest blast radius in the app. |
| `visits/` | `VisitViewSet` | permission checked against the **location**, not the visit. Re-triggers geocoding on write. |
| `categories/` | `CategoryViewSet` | per-user; unpaginated `list`; `general` undeletable. |
| `transportations/` `lodging/` `notes/` `checklists/` | CRUD | `notes.list` deliberately 403s — use `notes/all/`. `lodging/quick-add/` mirrors locations. |
| `images/` | `ContentImageViewSet` | `image_delete/`, `toggle_primary/`, `map_pins/`, `fetch_from_url/`, `import_from_urls/`. |
| `attachments/` | `AttachmentViewSet` | 13-clause generic-FK `Q()` queryset, duplicated in `location_image_view.py`. |
| `activities/` | `ActivityViewSet` | hangs off `Visit`; parses GPX with `gpxpy` on create. |
| `trails/` | `TrailViewSet` | hangs off `Location`; Wanderer linkage restricted to owned locations. |
| `itineraries/` `itinerary-days/` | `ItineraryViewSet`, `ItineraryDayViewSet` | `reorder/` (two-phase to dodge unique constraints), `auto-generate/`. |
| `stats/` | `StatsViewSet` | `dashboard/`, `counts/<username>/`. |
| `search/` | `GlobalSearchView` | `?q=&types=&limit=&offset=`; `icontains`-based. |
| `places/` | `PlacesAPI` | `search/`, `place_details/`, `reverse/` — proxies Google with OSM fallback. |
| `reverse-geocode/` | `ReverseGeocodeViewSet` | `reverse_geocode/`, `search/`, `place_details/`, `mark_visited_region/`. |
| `recommendations/` | `RecommendationsViewSet` | `query/`, radius clamped to 50 km. |
| `calendar/` `ics-calendar/` | two views, one event engine (`services/calendar_events.py`) |
| `generate/` | `GenerateDescription` | **Wikipedia**, not AI. `desc/`, `img/`. |
| `sunrise-sunset/` | `SunriseSunsetAPI` | `AllowAny` + manual access check. |
| `backup/` | `BackupViewSet` | `export/`, `import/` — import is destructive, see §16. |
| `tags/` | `ActivityTypesView` | distinct tag strings across the user's locations. |

---

## 4. Data model

`AUTH_USER_MODEL = users.CustomUser`. PK types are inconsistent by design:
`CustomUser` uses the inherited `BigAutoField` **integer** id (with a separate
unique `uuid` column used in URLs/sharing), `worldtravel.Country` uses
`AutoField`, `Region`/`City` use **string** PKs (`US-CA`), and nearly everything
in `adventures` uses `UUIDField`. `[v]`

### 4.1 ER summary `[v]`

```
CustomUser (int pk; uuid unique; email unique)
 ├─1:N→ Location.user                       (no related_name → location_set)
 ├─1:N→ Collection.user
 ├─M:N← Collection.shared_with              related_name='shared_with'  ← reads backwards
 ├─1:N→ CollectionInvite.invited_user        related_name='collection_invites'
 ├─1:N→ Category, Transportation, Note, Checklist, ChecklistItem, Lodging,
 │       Trail, Activity, ContentImage, ContentAttachment   (all .user)
 ├─1:N→ VisitedRegion.user, VisitedCity.user
 ├─1:N→ APIKey.user                          related_name='api_keys'
 ├─1:N→ StravaToken / WandererIntegration / EndurainIntegration / ImmichIntegration
 └─1:1→ Subscription.user                    related_name='subscription'

Collection (UUID)
 ├─M:N← Location.collections                 related_name='locations'  (Location owns the M2M)
 ├─1:N→ CollectionInvite                     related_name='invites'
 ├─1:N→ CollectionItineraryDay               related_name='itinerary_days'   unique(collection,date)
 ├─1:N→ CollectionItineraryItem              related_name='itinerary_items'  2 partial unique constraints
 ├─1:N→ Transportation / Note / Checklist / Lodging  (.collection FK, nullable)
 └─N:1→ ContentImage (primary_image, SET_NULL, related_name='primary_for_collections')

Location (UUID)  ── the hub
 ├─1:N→ Visit.location                       related_name='visits'
 ├─1:N→ Trail.location                       related_name='trails'
 ├─N:1→ Category (SET_NULL)
 ├─N:1→ City / Region / Country (SET_NULL, worldtravel — server-derived)
 └─GenericRelation→ ContentImage, ContentAttachment

Visit ─1:N→ Activity.visit   related_name='activities'
Trail ─1:N→ Activity.trail   related_name='activities'   (same accessor name, different model)
Checklist ─1:N→ ChecklistItem

Country ─1:N→ Region ─1:N→ City
VisitedRegion(user, region) / VisitedCity(user, city)  ← uniqueness enforced only in save()
```

### 4.2 The core three

**`Location`** (`adventures/models.py:157-255`) `[v]` — `name` (the only truly
required field), free-text `location` label, `tags` (ArrayField), `description`,
`rating`, `price` (MoneyField → shadow `price_currency` column), `link`,
`is_public`, `coordinates` (**PointField srid=4326**), FKs to `category` and
server-derived `city`/`region`/`country`, M2M `collections`.

There is **no `is_visited` column** — `is_visited_status()` derives it from
related `Visit.start_date` (`adventures/utils/get_is_visited.py`).

`Location.save()` does three notable things `[v]`:

1. Auto-creates/attaches a `general` category when none is set.
2. Calls `super().save()` **then** `self.clean()` — so a `ValidationError` leaves
   the invalid row already persisted.
3. If coordinates exist and not `_skip_geocode`, spawns a **daemon
   `threading.Thread`** running `background_geocode_and_assign`. This is the only
   `threading.` call in the backend.

**`Visit`** (`models.py:128-155`) `[v]` — `location` FK, `start_date`/`end_date`
(both nullable `DateTimeField`), `timezone` (choices from
`adventures/utils/timezones.py`), `notes`. `clean()` compares
`start_date > end_date` with **no null guard**, so it raises `TypeError` when
either is None.

**`Category`** (`models.py:549-568`) `[v]` — per-user, `unique_together
['name','user']`, `name` lowercased in `clean()`, `icon` defaults `🌍`.

### 4.3 `background_geocode_and_assign` `[v]` (`models.py:24-62`)

Reloads the Location, reverse-geocodes its point, sets `region`/`city`/`country`,
and — **only if `is_visited_status()` is already true** — `get_or_create`s
`VisitedRegion`/`VisitedCity`. Finishes with
`save(update_fields=[...], _skip_geocode=True)` to break recursion. Exceptions are
swallowed to `print()`.

**Ordering consequence for any client:** create location → create visit. Right
after creating a location it has no visits, so region/city get attached but not
marked visited; the subsequent visit creation re-runs the function and *that*
pass creates the visited rows. Also, `city`/`region`/`country` are usually still
`null` in the create response because the thread is asynchronous.

### 4.4 Generic (ContentType) relations `[v]`

`ContentImage` and `ContentAttachment` both use `content_type` FK +
`object_id` **UUIDField** + `GenericForeignKey`, each with a composite index on
`(content_type, object_id)`. Models declaring the reverse `GenericRelation`:

| Model | images | attachments |
| --- | --- | --- |
| `Location`, `Visit`, `Transportation`, `Note`, `Lodging` | yes | yes |
| `Checklist`, `ChecklistItem`, `Collection` | no | no |

Because `object_id` is a UUID field, only UUID-pk models can be targets —
`worldtravel` models and `CustomUser` cannot.

`CollectionItineraryItem` is the third ContentType consumer (points at Visit /
Transportation / Lodging / Note). It has no reverse `GenericRelation`, which is
why the blanket `post_delete` receiver exists (§4.6).

### 4.5 PostGIS fields — all `srid=4326`, all nullable `[v]`

`Location.coordinates`, `Transportation.origin`/`destination`,
`Lodging.coordinates`, `Activity.start_point`/`end_point`,
`ContentImage.coordinates`, `Country`/`Region`/`City.coordinates`.

Helpers in `adventures/utils/geo.py`: `WGS84_SRID`, `make_point(lon, lat)`,
`point_to_lat_lon(point) -> (y, x)`, `has_coordinates(point)`. Watch the axis
order: `Point(longitude, latitude)`.

All are plain geometry `PointField`, not `geography=True`.

### 4.6 Signals `[v]`

`adventures/signals.py` (registered in `adventures/apps.py.ready()`):

1. **`update_adventure_publicity`** — `m2m_changed` on
   `Location.collections.through`. On `post_add`/`post_remove`/`post_clear`:
   if any attached collection is public, force `is_public=True`; else force it
   back to `False`. Two traps: the handler early-returns unless `instance` is a
   `Location`, so it only fires on the **forward** direction
   (`location.collections.add(...)`, not `collection.locations.set(...)`); and
   the `elif` **silently un-publishes** a location that was intentionally public
   standalone.
2. **`_remove_collection_itinerary_items_on_object_delete`** — `post_delete` with
   **no sender**, i.e. fires on every delete of every model in the project. Does
   a `ContentType` lookup and deletes matching `CollectionItineraryItem` rows.
   This is the GC for GenericForeignKeys, which have no DB-level cascade.

`users/signals.py` `[v]` — three receivers on allauth's `EmailAddress` (not
CustomUser): mirror the primary verified email onto `user.email` on
`post_save`/`post_delete`, and `pre_delete` refuses to delete the last address.

`billing/signals.py` `[v]` — `post_save` on User creation always creates a
`Subscription`: `trial` (+`CLOUD_TRIAL_DAYS`, default 30) in `CLOUD_MODE`,
otherwise `active` with no trial. So self-hosted users all have a permanently
active subscription row.

### 4.7 The one custom manager `[v]` (`adventures/managers.py`, 17 lines)

```python
class LocationManager(models.Manager):
    def retrieve_locations(self, user, include_owned=False, include_shared=False, include_public=False):
        query = Q()
        if include_owned:  query |= Q(user=user)
        if include_shared: query |= Q(collections__shared_with=user) | Q(collections__user=user)
        if include_public: query |= Q(is_public=True)
        return self.filter(query).distinct()
```

`include_shared` deliberately covers both directions: collections shared *with*
you and collections *you own*. `.distinct()` is required because of the M2M join.

**Fail-open footgun:** with all flags false this is `filter(Q())` — the entire
table. `LocationViewSet` avoids it by returning `Location.objects.none()`
explicitly, but any new caller that forgets a flag gets everything.

### 4.8 Migrations `[v]`

| App | Count | Notable |
| --- | --- | --- |
| `adventures` | **64 files**, numbered up to `0076` (the gap is the squash) + 2 orphaned unnumbered helper modules | one squash `0036_rename_adventure_location_squashed_0050_rename_user_id_lodging_user.py` replacing `0036`–`0050` (the `Adventure → Location` rename); `0073_pointfield_geography` converts float lat/lon columns to Points; `0054` moves images/attachments to generic relations; `0012` migrates legacy types to Categories |
| `worldtravel` | 19 | `0019_pointfield_coordinates` backfills Points and drops lat/lon; `0007` **removed `Region.geometry`** (see §16) |
| `users` | 9 | `0003` guards duplicate emails before making `email` unique |
| `integrations` | 9 | `0007` **destructively wipes** existing Wanderer rows |
| `billing` | 1 | backfills a Subscription per existing user |
| `achievements` | 0 (no `migrations/` dir) | app not installed |

`migrate_images.py` and `migrate_visits_categories.py` in
`adventures/migrations/` reference pre-rename models and are effectively dead —
Django won't order them without numeric prefixes.

---

## 5. Permissions, visibility, sharing

This is the highest-risk area to change. All custom permission classes live in
**one file**, `backend/server/adventures/permissions.py` (276 lines) `[v]`.

### 5.1 The classes

| Class | Used by |
| --- | --- |
| `IsOwnerOrReadOnly` | nothing found `[i]` — looks legacy |
| `IsPublicReadOnly` | nothing found `[i]` — looks legacy |
| `CollectionShared` | `CollectionViewSet` only |
| `IsOwnerOrSharedWithFullAccess` | Location, Visit, Trail, Activity, Note, Checklist, Transportation, Lodging, Itinerary, ItineraryDay |
| `ContentImagePermission` (subclass) | `ContentImageViewSet`, `AttachmentViewSet` |

Both workhorse classes share the same view-level gate `[v]`:

```python
def has_permission(self, request, view):
    return (request.user and request.user.is_authenticated) or \
           request.method in permissions.SAFE_METHODS
```

### 5.2 `IsOwnerOrSharedWithFullAccess.has_object_permission` — exact order `[v]`

**Step 0, object substitution.** Before any check, the object under test is
replaced by an ancestor:

```python
if type(obj).__name__ == 'Trail':                    obj = obj.location
if type(obj).__name__ == 'Activity':                 obj = obj.visit.location
if type(obj).__name__ == 'Visit':                    obj = obj.location
if type(obj).__name__ == 'CollectionItineraryItem':  obj = <resolved GFK target>
```

So a Visit's / Trail's / Activity's own `user` field is **never consulted**.
Permission is entirely inherited from the parent Location. `type(obj).__name__`
is an exact string match, so subclasses would slip past. Two stray `print()`
calls sit in this block (Visit and CollectionItineraryItem branches).

Then:

1. anonymous → `is_safe_method and getattr(obj, 'is_public', False)`
2. `_is_owner` → `hasattr(obj,'user') and obj.user == user` → **True**
3. `_has_collection_access` → shared-with **or owner** of any collection
   containing the object (handles both `obj.collections` M2M and `obj.collection`
   FK) → **True**
4. `_has_direct_sharing_access` → `obj.shared_with` contains user → **True**
5. safe method and `is_public` → True
6. else False

**Steps 2–4 never consult `request.method`.** That is what "full access" means:
being in one collection's `shared_with` grants GET *and* PUT/PATCH/DELETE on
every Location in it, plus its Visits, Trails, Activities, images and
attachments. The only reason a shared user can't delete a Location outright is a
hand-rolled check in the viewset (`location_view.py`, `"Only the owner can
delete this location."`), not the permission class.

The relation is also reflexive: if a collection owner adds someone else's
location to their collection, step 3's `collections.filter(user=user)` hands the
collection owner full write/delete on a location they don't own.

### 5.3 `CollectionShared` — the Collection row itself is read-only when shared `[v]`

```python
if obj.__class__.__name__ == 'Collection':
    if obj.user == user: return True
    if request.method in permissions.SAFE_METHODS:
        return obj.shared_with.filter(id=user.id).exists() or getattr(obj,'is_public',False)
    return False
```

That unconditional `return` makes the later generic `shared_with` branch dead
code for Collections. An invite escape hatch runs *before* this branch, so an
invitee can POST `accept_invite`/`decline_invite` on a collection they otherwise
cannot touch.

### 5.4 `ContentImagePermission` `[v]`

Stricter than its parent: anonymous is **always** denied, then the check is
re-targeted onto the GFK parent. Consequences: images on public locations are
unreachable via `/api/images/` when logged out (they're only visible through URLs
embedded in the location payload), and an orphaned image whose `content_object`
resolves to `None` is inaccessible to everyone including its owner.

### 5.5 Sharing lifecycle `[v]` (`adventures/views/collection_view.py`)

Two hops, mediated by `CollectionInvite`:

1. `POST /api/collections/<id>/share/<uuid>/` — looks up
   `User.objects.get(uuid=uuid, public_profile=True)` (**only public profiles are
   invitable**), rejects self / already-shared / already-invited, then creates a
   `CollectionInvite`. It does *not* share directly.
2. `POST /api/collections/<id>/accept-invite/` — `shared_with.add(request.user)`
   and delete the invite.

Other actions: `invites/`, `revoke-invite/<uuid>/` (explicit owner check),
`decline-invite/`, `can-share/`, `unshare/<uuid>/`, `leave/` (blocks the owner),
`shared/`. `unshare` and `leave` both remove the departing user's own locations
from the collection.

What a shared member can do: read the collection; create locations, notes,
checklists, transportation, lodging in it; edit and delete other members'
Visits/Trails/Activities; add and reorder itinerary items. What they cannot:
PATCH/DELETE the Collection row, change its `is_public`, delete a Location they
don't own, duplicate the collection, or revoke others' invites. Category changes
are **silently ignored** rather than refused (§16).

### 5.6 `is_public` propagation — three independent paths `[v]`

Models with `is_public`: `Location`, `Collection`, `Transportation`, `Note`,
`Checklist`, `Lodging`. `Visit`, `Trail`, `Activity`, `ContentImage`,
`ContentAttachment`, `Category`, `ChecklistItem`, itinerary models have none —
their visibility is purely inherited.

- **Path A — the `m2m_changed` signal** (§4.6). Forward direction only; force-demotes.
- **Path B — the collection update cascade** (`collection_view.py`, `update()`).
  On `is_public` → True it runs `locations.filter(is_public=False).update(is_public=True)`
  and the same for `transportation_set`, `note_set`, `checklist_set`,
  `lodging_set`. This is queryset `.update()`, bypassing `save()`, `clean()` and
  signals — **so making a shared collection public publishes other members'
  private locations**, with no validation error and no notification. Going
  private demotes Locations only if they belong to no other public collection,
  but demotes the FK-attached models unconditionally.
- **Path C — model `clean()` invariants.** Every child model refuses to be
  private inside a public collection. But `Location.save()` validates *after*
  writing (§4.2).

Publicity change on a collection is owner-gated in three places: the per-action
queryset, `CollectionShared`, and an explicit check in `update()` returning
`"Only the collection owner can change publicity."`

### 5.7 Unauthenticated surface `[v]`

- `GET /api/locations/<id>/`, `/additional-info/`, `/share-image/<aspect>/` for
  public locations (`public_allowed_actions = {'retrieve','additional_info','share_image'}`).
- `GET /api/collections/<id>/`, `/export-pdf/`, `/share-image/<aspect>/` for
  public collections.
- `GET /api/notes/<id>/`, `/api/checklists/<id>/` for public rows, retrieve only.
- `GET /auth/users/`, `/auth/user/<username>/` — `permission_classes = []`.
- `SunriseSunsetAPI` (`AllowAny`), and the Immich image proxy action
  (`permission_classes=[]`, with hand-rolled per-image ACL).

**Data exposure to note:** `LocationSerializer.to_representation` embeds the full
`CustomUserDetailsSerializer` output for the owner when not nested. That
serializer includes `EMAIL_FIELD`, `first_name`, `last_name`, `date_joined`,
`is_staff`, `disable_password`. The public-user endpoints manually null out email
and pop the password flags; the location path does not. So an anonymous
`GET /api/locations/<public-id>/` returns the owner's email address `[i — read
from serializer code, not observed in a response]`. By contrast
`CollectionSerializer` reduces `shared_with` to bare UUIDs and
`_serialize_collaborator` omits email.

### 5.8 Staff `[v]`

No custom role flags exist. `CustomUser` adds only profile fields. `is_staff`
unlocks the Django admin and nothing else — **no DRF permission class anywhere
consults `is_staff`, `is_superuser`, or `IsAdminUser`**. Staff see only their own
data through the REST API. `SessionAdmin` does display decoded session data,
which is worth knowing.

---

## 6. Authentication and user management

### 6.1 Three authentication paths `[v]`

| Path | Mechanism | CSRF |
| --- | --- | --- |
| Browser (SvelteKit) | allauth headless session cookie `sessionid`, proxied server-side | token fetched per request from `/csrf/` |
| API key | `X-API-Key: al_...` or `Authorization: Api-Key al_...`, `APIKeyAuthentication` first in DRF | exempt, unless a session cookie is also present |
| Native/mobile | `X-Is-Mobile` to bootstrap login without CSRF, then `X-Session-Token` header as the session | exempt |

### 6.2 API keys `[v]` (`users/models.py:76-151`, `users/authentication.py`)

`al_{secrets.token_urlsafe(32)}`; only a **PBKDF2-HMAC-SHA256** hash at 600,000
iterations is stored, salted with `"users.APIKey:<SECRET_KEY>"`. `key_prefix`
(12 chars) for display, `last_used_at` bumped via `.update()` (no signals).

- **No scopes. No expiry.** A key carries the full permissions of its owner. The
  "Invalid or expired API key" message is misleading.
- **Rotating `SECRET_KEY` invalidates every key**, because it's in the salt.
- A key can mint another key (`/auth/api-keys/` requires only `IsAuthenticated`).
- `serve_protected_media` also accepts API-key auth, so a paired client can fetch
  protected images with just the key.

Lifecycle endpoints: `GET|POST /auth/api-keys/` (raw key returned exactly once as
`response_data["key"]`), `DELETE /auth/api-keys/<uuid>/`, and
`GET|POST|DELETE /auth/mobile-qr/` which mints a key named
`Mobile App - <Month DD, YYYY>` and returns a base64 PNG QR containing
`{version, server_url, api_key, code_words}`. The `"Mobile App -"` name prefix is
the only marker, so one mobile key per user by convention.

### 6.3 allauth `[v]`

Headless mounted at `auth/`, classic at `accounts/`. Endpoints the frontend
actually calls:

```
POST   /auth/browser/v1/auth/login                      (401 ⇒ MFA required)
POST   /auth/browser/v1/auth/2fa/authenticate
POST   /auth/browser/v1/auth/signup
DELETE /auth/browser/v1/auth/session                    (logout)
POST   /auth/browser/v1/auth/password/request|reset
POST   /auth/browser/v1/auth/email/verify
*      /auth/browser/v1/account/email                   (list/add/remove/primary/resend)
POST   /auth/browser/v1/account/password/change
GET    /auth/browser/v1/account/authenticators
*      /auth/browser/v1/account/authenticators/totp
GET    /auth/browser/v1/account/authenticators/recovery-codes
GET    /csrf/
GET    /auth/current-user/                              ← NOT allauth; cloud/views.CurrentUserView
```

Session hydration uses `/auth/current-user/`, which returns
`{user, subscription, has_access, cloud_mode}` — not the headless session
endpoint. `HEADLESS_FRONTEND_URLS` maps email-confirm / password-reset / signup /
social-error keys to `{FRONTEND_URL}/...` paths.

**MFA** is `allauth.mfa` with **no `MFA_*` settings**, so allauth defaults apply
(TOTP + recovery codes). The model is allauth's own `Authenticator`. Admin login
is wrapped in `secure_admin_login`, so staff login is MFA-aware.

**Social**: GitHub and generic OIDC only. Configuration is **entirely
admin-managed `SocialApp` rows** — no env bootstrapping.
`GET /auth/social-providers/` returns `{provider, url, name, usage_required}`.
`SOCIALACCOUNT_LOGIN_ON_GET=True`, and `SOCIALACCOUNT_EMAIL_AUTHENTICATION` +
`..._AUTO_CONNECT` auto-link a social identity to an existing account by matching
email — which trusts the provider's email claim. `AUTHENTICATION_BACKENDS` has
exactly one entry, `users.backends.NoPasswordAuthBackend`, which delegates to
allauth's backend and refuses password auth when `FORCE_SOCIALACCOUNT_LOGIN` or
the user's `disable_password` is set.

**Invites**: django-invitations, at `/invitations/...`. `UseAdminInviteForm`
deliberately clears all fields, so **only staff can invite, via the Django
admin**. `CustomAccountAdapter.is_open_for_signup` allows signup when
`DISABLE_REGISTRATION` is false, **or** the session carries
`account_verified_email` (set by accepting an invite), **or** the view is
`invitations:accept-invite`. Note `GET /auth/is-registration-disabled/` has no
notion of an invite session, so the frontend can show "registration disabled"
while an invited signup would in fact succeed.

### 6.4 `CustomUser` `[v]`

`AbstractUser` plus: `email` (unique override), `profile_pic`
(WebP `ResizedImageField`), `uuid` (unique, non-editable — used in URLs and
sharing), `public_profile`, `disable_password`, `measurement_system`,
`default_currency` (20 choices), `map_style` (25 choices).

`uuid` is **not** the PK; all FKs point at the integer `id`. Flipping
`public_profile` off has a side effect: the serializer removes the user from every
`Collection.shared_with` and deletes their pending invites.

---

## 7. Frontend (`frontend/`)

### 7.1 Stack `[v]`

SvelteKit `^2.49.5` with **Svelte pinned at `4.2.19`** — stores and `$:`
reactivity, **not runes**. Adapter is conditional: `adapter-vercel` when
`process.env.VERCEL` is set, otherwise `adapter-node`. Tailwind 3 + **daisyUI 4**
+ typography. `unplugin-icons` with `@iconify-json/mdi` powers
`import X from '~icons/mdi/...'`. Node 22 (`engines: ">=22 <26"`), pnpm 10.32.1.

**There is no test runner.** Scripts are `dev`, `build`, `preview`, `check`
(`svelte-check`), `lint` (`prettier --check`), `format`. No vitest/playwright/jest
anywhere.

Notable deps: `svelte-maplibre`, `svelte-i18n`, `luxon`, `marked` + `dompurify`,
`@event-calendar/*`, `svelte-dnd-action`, `psl`, `qrcode`, `gsap`.

### 7.2 Routing `[v]`

61 files under `frontend/src/routes/`, of which 28 are `+page.server.ts`.
**There are zero `+page.ts` universal loads in the repo** — data always arrives
via SSR-only loads. Those loads return a non-idiomatic `{ props: {...} }` wrapper,
so pages read `data.props.x`.

Groups: `locations/`, `collections/`, `lodging/[id]`, `transportations/[id]`,
`map/`, `calendar/`, `dashboard/`, `search/`, `worldtravel/` (→ region → city),
`users/`, `user/[uuid]`, `profile/[uuid]`, `invites/`, `admin/`, `login/`,
`signup/`, `settings/`, `subscribe/`, password-reset and verify-email flows.
`adventures/` and `adventures/[id]/` are 301 redirects to `/locations` — leftovers
from the rename.

Server-only endpoints: `api/[...path]`, `auth/[...path]`, `immich/[key]`,
`activities/`, `health/`.

### 7.3 The backend contract — `frontend/src/lib/server/django-proxy.ts` `[v]`

This single file is the whole contract. Two routes into Django:

**(a) Browser → SvelteKit proxy → Django.** Components fetch relative URLs
(`fetch('/api/...')`, ~124 occurrences). `api/[...path]/+server.ts` and
`auth/[...path]/+server.ts` are 13-line wrappers over `proxyToDjango`, which:

- resolves the backend from **`process.env['PUBLIC_SERVER_URL']`** (default
  `http://localhost:8000`) — read via `process.env`, so it is a runtime variable
  server-side and never reaches the browser despite the `PUBLIC_` prefix;
- calls `fetchCSRFToken()` → `GET ${endpoint}/csrf/` **on every proxied
  request**, 400-ing if it fails (a real per-request round trip);
- normalizes trailing slashes, **skipping** them for allauth headless prefixes
  `browser/` and `app/`;
- appends `format=json` for api GET/PATCH/PUT/DELETE;
- strips hop-by-hop headers (undici rejects them);
- deletes any inbound `csrftoken` cookie, then sends `X-CSRFToken` plus
  `Cookie: csrftoken=…[; sessionid=…]`;
- **deletes `set-cookie` from the response**, so Django can never set a cookie on
  the browser directly;
- returns 499 on client abort.

**(b) SvelteKit server load → Django directly**, using `backendApiUrl()` and a
manual `Cookie: sessionid=…` header, adding `X-CSRFToken` + `Referer` for writes.

### 7.4 `frontend/src/hooks.server.ts` `[v]`

`sequence(authHook, themeHook, i18nHook)`.

`authHook` deletes the `csrftoken` cookie on every request, short-circuits for
`/immich/` (high volume), and otherwise **validates the session on every request**
via `GET /auth/current-user/` with the raw inbound cookie header. On 429 or 5xx it
deliberately **preserves** the session cookie to avoid a logout loop; on any other
failure it deletes `sessionid`. On success it populates
`locals.{user, subscription, hasAccess, cloudMode}` and re-sets a rolling
`sessionid` from the response `Set-Cookie` (Django has
`SESSION_SAVE_EVERY_REQUEST=True`).

`themeHook` validates `?theme=`/`colortheme` cookie against the `themes` list and
rewrites `data-theme=""` in the HTML server-side — hence no theme flash.
`i18nHook` copies the `locale` cookie into locals.

### 7.5 Auth, guards, paywall `[v]`

Login posts to allauth headless; **HTTP 401 means MFA required**, and the retry
posts the TOTP code with the interim sessionid. Session cookies are set by the
SvelteKit server, with the cookie domain derived using **`psl`** (skipped for IPs,
localhost, and single-label hosts) — mirroring the `publicsuffix2` logic in
Django settings.

**Route guards are per-route, not centralized:** each protected
`+page.server.ts` begins with `if (!event.locals.user) return redirect(302,
'/login')`, repeated in ~15 files. There is no hook-level gate, so a new
protected route must remember that line.

Paywall guard lives in `+layout.server.ts`: when `cloudMode && user &&
!hasAccess` and the path isn't allow-listed, redirect to `/subscribe`.

Logout is a form action on the root route (`/?/logout`) that DELETEs the headless
session, recomputes the psl cookie domain, deletes `sessionid`, and redirects.

### 7.6 Shared code, i18n, theming, maps `[v]`

- `src/lib/index.ts` is a ~36 KB barrel and de facto util grab bag: `themes`,
  `getBasemapUrl`, `basemapOptions`, `getIsDarkMode`, date-grouping helpers,
  legacy `ADVENTURE_TYPES` + icon maps, `debounce`, `copyToClipboard`.
- `src/lib/types.ts` (~18 KB) is **hand-written** — no OpenAPI codegen, no
  generated client. The contract is mirrored manually.
- Components: 34 flat top-level plus domain folders (`cards/`, `map/`,
  `locations/`, `collections/`, `lodging/`, `calendar/`, `search/`, `settings/`,
  `shared/`, `transportation/`).
- Stores are minimal (`search/palette.ts`, `toasts.ts`). State rides on server
  load data and props.
- **i18n**: `svelte-i18n`, 25 locale JSON files on disk but only **22
  `register()` calls** in `+layout.svelte`. `pt.json`, `ta.json` are listed in
  the `locales` array but never registered; `sq.json` appears in neither. `init()`
  runs **only in the browser**, gated by `waitLocale()`, so **SSR emits no
  translated strings**.
- **Theming**: daisyUI themes declared in `tailwind.config.js` (8 stock + 5
  custom); the user-facing picker in `lib/index.ts` exposes 9, so `retro` and
  `emerald` are compiled but unselectable. Dark mode is not Tailwind's `dark:`
  strategy — `getIsDarkMode()` reads `data-theme`.
- **There are no `.css` files at all.** Global styling is one Tailwind import plus
  a small `<style>` block with `:global()` overflow rules.
- **Maps**: MapLibre GL via `svelte-maplibre` (no Leaflet). Tile styles are
  returned as MapLibre style objects from `getBasemapUrl()` — CARTO raster, Esri
  imagery/topo, AWS terrarium DEM for 3D terrain, and a MapTiler variant still
  carrying the **public demo key placeholder**. Pins come from
  `/api/locations/pins/` via `map/+page.server.ts`.

### 7.7 Build `[v]`

`pnpm build` → `frontend/build/`, entry `build/index.js`. `frontend/start.js`
maps `SITE_URL`→`ORIGIN`, filters one known undici `ERR_ASSERTION` on client
disconnect, then imports the build. In Docker the build stage runs
`rm -f .env && pnpm run build` so a stray local `.env` can't leak into the image.

---

## 8. Service layer: geocoding, places, and friends

Three layers plus a legacy shim `[v]`:

1. **Providers** (`adventures/providers/`) — thin HTTP wrappers returning
   `ProviderResult(data|error)`. `geocoding/{google,osm}`,
   `places/{google,osm,wikipedia}`, `recommendations/{google,osm}`,
   `sun/sunrisesunset`. They know nothing about models or requests.
2. **Services** (`adventures/services/`) — provider selection, normalization,
   scoring, merging. `geocoding/reverse.py` tries Google first when
   `GOOGLE_MAPS_API_KEY` is set, scores the result, and falls back to / compares
   against OSM, tagging the winner `provider_used`. `places/search.py` does the
   same but also dedupes and can report `mixed`. Also `places/details.py`,
   `recommendations/search.py`, `sunrise_sunset/times.py`, `wikipedia/*`,
   `search/global_search.py`, `calendar_events.py`, `collection_pdf.py`,
   `share_image.py`, `dashboard.py`, `user_stats.py`.
3. **Caching** — `adventures/services/external_cache.py`: `get_or_fetch_cached`
   over the Django cache, TTLs `EXTERNAL_API_CACHE_TIMEOUT` (24 h),
   `SUNRISE_SUNSET_CACHE_TIMEOUT` (30 d), Wikipedia (7 d).
4. **`adventures/geocoding.py`** is an explicit compatibility shim ("preserves old
   import paths during migration") that re-exports the service functions. New
   code should import services directly.

**Key operational point:** because the server proxies Google (with OSM fallback)
through `/api/places/*` and `/api/reverse-geocode/*`, an external client does
**not** need its own Google key.

Throttling of external calls is centralized in `adventures/throttling.py` with
`ConditionalUserRateThrottle` — scopes `image_proxy` 60/min, `image_import`
12/min, `external_geocode` 120/min, `external_recommendations` 30/min,
`external_wikipedia` 60/min, `external_sunrise_sunset` 30/min. All are inert
unless `ENABLE_RATE_LIMITS=true`; only `endurain_auth` (10/min) is always on. `[v]`

**No AI anywhere.** `GET /api/generate/desc/` and `/img/` are Wikipedia lookups.
A repo-wide grep for `openai|anthropic|gemini|llm|ollama` in the backend returns
zero matches `[v]`.

---

## 9. Media, images, storage

- **`ContentImage`** `[v]` — `image` is a `ResizedImageField(force_format="WEBP",
  quality=75, keep_meta=True)`, so **every upload is transcoded to WebP at q75**;
  there is no separate thumbnail pipeline. `PathAndRename` renames every upload to
  `uuid4.<ext>` under `images/`, `attachments/`, `activities/`. `clean()` enforces
  XOR between `image` and `immich_id`, and `save()` calls `full_clean()`, so every
  save is fully validated. `source` ∈ upload/google/wikipedia/url/immich.
- **`ContentAttachment`** — very permissive ~40-extension allowlist including
  archives and video, plus `.gpx` and `.md`.
- **Remote import** `[v]` — `adventures/services/images/fetch.py` has a real SSRF
  guard: http/https only, ports 80/443 only, rejects private/loopback/reserved/
  link-local/multicast resolved IPs, re-validates each of ≤3 redirects, requires
  `Content-Type: image/*`, rejects >20 MB. Downloads run in a bounded
  `ThreadPoolExecutor` (≤5) **inside the request**.
- **EXIF/metadata** — `services/images/metadata.py` extracts GPS from bytes,
  fetches Immich `exifInfo` coordinates, and funnels creation through
  `create_content_image`.
- **Serving** `[v]` — `main.views.serve_protected_media` normalizes the path,
  allows public paths, resolves the user via session **or** API key, checks
  `checkFilePermission`, then: S3 → redirect to a (possibly signed) storage URL;
  `DEBUG` → `django.views.static.serve`; production → empty response with
  `X-Accel-Redirect: /protectedMedia/<path>` for nginx's `internal` location.
- **Quotas** — `MEDIA_STORAGE_LIMIT_MB` / `_BYTES` enforced by
  `users.media_utils.enforce_media_storage_limit`.
- **Dead duplicate**: `adventures/services/media/images.py` is a near-verbatim
  older copy of `services/images/fetch.py` with different return keys and no
  source/EXIF handling. Nothing imports it `[i — grep found no importers]`.

---

## 10. Integrations (`integrations/`)

Four per-user credential models, all storing secrets in **plaintext DB
columns** `[v]`: `ImmichIntegration`, `StravaToken`, `WandererIntegration`,
`EndurainIntegration`.

`GET /api/integrations/` returns a capability probe:
`{immich, google_maps, strava:{global,user}, wanderer, endurain}`. Google Maps and
Strava are gated by global env vars; the other three are per-user only.

| Integration | Flow |
| --- | --- |
| **Immich** | photo search/albums + image proxy. Pages Immich search with `size=1000` accumulating **all pages in memory** before DRF pagination. Proxy action is `permission_classes=[]` with hand-rolled per-image ACL sorting. `ImmichIntegrationSerializer` uses `fields='__all__'` and only pops `user`, so **`api_key` is echoed back**. |
| **Strava** | OAuth (`activity:read_all`), token refresh <300 s before expiry, activity list/detail, normalizes Strava's `"(GMT-05:00) America/New_York"` timezone strings. |
| **Wanderer** | trails; tries `/api/v1/trail` then `/api/v1/trails` to tolerate versions; ETag-aware cache (`wanderer_trail_v3`, 15 min). Links to `adventures.Trail.wanderer_id`. |
| **Endurain** | password login → tokens, MFA challenges cached 300 s, GPX download. `EndurainAuthThrottle` is **always on**. Does SSRF hardening incl. blocking metadata hosts. |

---

## 11. Background processing and scheduled jobs

**There is no Celery, no RQ, no broker, no `transaction.on_commit`** `[v]`.
Deferred work is exactly four things:

1. `Location.save()` → one **unmanaged daemon thread** per save with coordinates,
   doing outbound HTTP. No retries, no visibility, work lost if the worker
   recycles. Amplified by the `bulk-adventure-geocode` command, which triggers a
   save per location.
2. `services/images/fetch.py` → bounded `ThreadPoolExecutor(≤5)` inside the request.
3. The dead duplicate in `services/media/images.py` → same pattern.
4. **system cron inside the container**.

### Cron `[v]`

`backend/cron/adventurelog` → `/etc/cron.d/adventurelog` (0644), `CRON_TZ=UTC`.
**Exactly one active job:**

```
0 0 * * * root /code/scripts/run-cron-job.sh sync_visited_regions sync_visited_regions
```

`write-cron-env.sh` (run at startup) dumps the whole environment to
`/etc/adventurelog/cron.env` at mode **0644** — including `POSTGRES_PASSWORD`,
`SECRET_KEY`, AWS keys. `run-cron-job.sh` sources it, takes a non-blocking
`flock` (skipping silently if the previous run is still going), tees to
`/var/log/adventurelog/<job>.log` and `/proc/1/fd/1`, and propagates the real
exit code.

### Management commands `[v]`

`adventures/`: `activity_elevation_fix`, `backfill_image_coordinates`,
`image_cleanup` (interactive unless `--dry-run`), `sync_visited_regions`,
`travel-seed`.
`worldtravel/`: `download-countries`, `bulk-adventure-geocode`.
`achievements/`: `achievement-seed` (app not installed).

`download-countries` downloads the pinned `countries+states+cities.json`, streams
it with `ijson` into a **temporary SQLite DB**, bulk-creates in batches with
`ignore_conflicts=True`, prunes obsolete rows, and fetches flags from flagcdn.
It runs **on every container boot** and wants ~2 GB RAM; `SKIP_WORLD_DATA=1` is
the escape hatch. `[v]`

---

## 12. Deployment and infrastructure

### 12.1 One Dockerfile, three targets `[v]` (`docker/Dockerfile`)

Stages: `node-runtime` (donor for the node binary) → `frontend-build`
(Chainguard node dev, pnpm frozen lockfile, `rm -f .env && build`, `prune --prod`)
→ `backend-builder` (`python:3.13-slim` + gdal dev) → `backend-runtime`
(`python:3.13-slim` + postgresql-client, gdal-bin, nginx, memcached, supervisor,
cron, fonts-noto-core; **`collectstatic` runs here, at build time**).

Targets: `frontend` (:3000, healthcheck `/health`), `backend` (:80/:8000,
healthcheck `/health/`), `aio` (:80, healthcheck `/health`).

There is **no `backend/Dockerfile` or `frontend/Dockerfile`** anywhere, which is
why `docker/docker-compose.dev.yml` — whose build contexts are `../frontend/` and
`../backend/` — cannot build as written.

### 12.2 Startup sequence `[v]`

`backend/entrypoint.sh` is 13 lines; the logic is in
`docker/shared/entrypoint-common.sh`. The AIO variant sources
`docker/aio/env-setup.sh` first.

```
wait_for_postgres          loop psql '\q' until success
run_migrations             manage.py migrate
create_superuser_if_needed only if DJANGO_ADMIN_USERNAME/PASSWORD/EMAIL all set;
                           creates the user AND a verified primary allauth EmailAddress;
                           create-only, so changing the env later does nothing
run_download_countries     unless SKIP_WORLD_DATA=1 — every boot
finalize_startup           print banner, write /etc/adventurelog/cron.env
exec supervisord
```

No `collectstatic` at runtime (baked into the image), and no `createsuperuser`
management command — it's a shell heredoc using `DJANGO_ADMIN_*`, not
`DJANGO_SUPERUSER_*`.

`docker/aio/env-setup.sh` derives `ORIGIN`, `FRONTEND_URL`, `PUBLIC_URL`,
`CSRF_TRUSTED_ORIGINS` from `SITE_URL`; sets `PUBLIC_SERVER_URL=http://127.0.0.1:8000`,
`DEBUG=False`, `PORT=3000`, `PGHOST=db`; hard-fails without `POSTGRES_PASSWORD`;
and **generates a random `SECRET_KEY` when unset**. `[v]`

### 12.2b `postgis/postgis:16-3.5` is amd64-only — the stack does not start on arm64 `[v, runtime]`

Found by running the Standard stack on an Apple Silicon Mac (podman, arm64):

```
Image postgis/postgis:16-3.5 Error no image found in image index for
  architecture "arm64", variant "v8", OS "linux"
```

Verified with `podman manifest inspect`: `postgis/postgis:16-3.5` publishes
**`linux/amd64` only**. The AdventureLog image itself is fine — it ships both
`linux/amd64` and `linux/arm64`, as `_build-image.yml` claims.

Nothing in the repo or in `documentation/` mentions this, so **every Apple Silicon
user hits it on first `compose up`** with an error that names no fix. Two working
remedies, both verified on that machine:

| Remedy | Trade-off |
| --- | --- |
| Point `db` at a multi-arch rebuild — `imresamu/postgis:16-3.5` or `ghcr.io/baosystems/postgis:16-3.5`, both confirmed `linux/amd64, linux/arm64` | native speed; a non-official image |
| Add `platform: linux/amd64` to the `db` service and let it emulate (`podman run --platform linux/amd64` confirmed working) | keeps the official image; Postgres under qemu is markedly slower |

Worth fixing upstream, either by switching the pinned image or documenting the
override in the install guide.

### 12.3 Compose variants `[v]`

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Standard: `app` (aio) + `db`. Requires `.env`. |
| `docker/docker-compose.advanced.yml` | 3 services from `../.env.advanced` |
| `docker/docker-compose.database.yml` | postgis only on `127.0.0.1:5432`, password `changeme123` — **this is what CI uses** |
| `docker/docker-compose.dev.yml` | hot reload; `vite dev` + `runserver`; broken build contexts |
| `docker/docker-compose.traefik.yaml` | Traefik 2.11 + Let's Encrypt; path-based split |
| `docker/docker-bake.hcl` | builds all three targets, tags `*:local` |

### 12.4 k8s and installer `[v]`

`k8s/base/adventurelog.yaml` + `kustomization.yaml`: Secret (placeholder values),
two 10 Gi RWO PVCs, a postgis StatefulSet, the aio Deployment (replicas **1**),
Services, and a plain Ingress. No Helm, no overlays, no resource limits, no
liveness probes, no TLS on the Ingress. Scaling out needs S3 because the media
PVC is RWO. `k8s/legacy/` is marked DEPRECATED.

`install_adventurelog.sh` (v2.0.0) is a 7-step wizard sourcing
`scripts/install/lib/*.sh` (locally or curled from GitHub). It prompts for site
URL, host port, Postgres password, admin credentials, then optional features
(auth, SMTP, S3, Google Maps, Strava, Umami, performance, debug), runs
`scripts/validate-env.sh`, then `compose pull` + `up -d --wait`, then polls
`${SITE_URL}/health` for up to ~10 minutes. `validate-env.sh` is the enforcement
point: errors on missing `POSTGRES_PASSWORD`, S3 without AWS vars, SMTP without
host/user/password; warns on `changeme123`, `admin/admin`, non-http `SITE_URL`,
`DEBUG=True`.

### 12.5 Health endpoints, and what is actually reachable on the aio port

**Corrected 2026-08-09 by testing a running Standard stack.** The earlier claim
that "`/health/` (with slash) → Django `health_check`" was wrong for the aio image.

nginx-aio routes only `/static/`, and `^/(media|admin|accounts)(/|$)`, to Django.
**Everything else goes to the SvelteKit frontend**, so on the published port `[v, runtime]`:

| Path | Observed | Served by |
| --- | --- | --- |
| `/health` | 200 `{"ok":true,"backend":"reachable"}` | SvelteKit route |
| `/health/` | **308 → `/health`** (`x-sveltekit-normalize: 1`) | SvelteKit, **not Django** |
| `/admin/` | 302 | Django |
| `/accounts/login/` | 200 | Django (allauth) |
| `/api/locations` | 200 | **SvelteKit `/api/[...path]` proxy → Django** |
| `/api/locations/` | 308 → `/api/locations` | SvelteKit normalize, then proxy |
| `/docs/` | **404** | nobody — Swagger is Django-only, unreachable here |
| `/csrf/` | **404** | nobody — same |

Two things this means in practice:

1. **Django's `/health/` is not reachable through the aio published port at all.**
   It exists and does `connection.ensure_connection()` with a 503 on DB failure,
   but only the separately-published `backend` image (whose nginx sends `/` to
   Django) can serve it. So the Standard deployment's compose healthcheck and the
   k8s readiness probe validate the Node process and its ability to reach the
   backend — not the database directly.
2. **`/api/` traffic goes through the SvelteKit proxy**, not straight to Django.
   API keys pass through fine (verified: `X-API-Key` → 200), but every proxied
   request triggers a `GET /csrf/` on the backend first, and the trailing-slash
   form costs a 308. See `docs/architecture/API_CONTEXT.md` §1.2.

---

## 13. Environment variables

Canonical list: `documentation/docs/configuration/environment_variables.md`.
Three templates exist and differ by deployment shape `[v]`:

| Template | Required |
| --- | --- |
| `.env.example` (Standard) | **`POSTGRES_PASSWORD` only** — everything else derived from `SITE_URL` |
| `.env.advanced.example` | `PUBLIC_SERVER_URL`, `ORIGIN`, `FRONTEND_URL`, `PGHOST`, `POSTGRES_*`, `SECRET_KEY`, `PUBLIC_URL`, `CSRF_TRUSTED_ORIGINS` |
| `backend/server/.env.example` (bare metal) | `PG*`, `SECRET_KEY` |

Grouped by concern: URLs/origins (`SITE_URL`, `HOST_PORT`, `PUBLIC_URL`,
`FRONTEND_URL`, `PUBLIC_SERVER_URL`, `ORIGIN`, `CSRF_TRUSTED_ORIGINS`,
`BODY_SIZE_LIMIT`), database (`PGHOST`/`POSTGRES_*`), Django core (`SECRET_KEY`,
`DEBUG`, `GUNICORN_WORKERS`), admin bootstrap (`DJANGO_ADMIN_*`), auth flags
(`DISABLE_REGISTRATION`(+`_MESSAGE`), `SOCIALACCOUNT_ALLOW_SIGNUP`,
`FORCE_SOCIALACCOUNT_LOGIN`, `ACCOUNT_EMAIL_VERIFICATION`), rate limits
(`ENABLE_RATE_LIMITS`, `RATE_LIMIT_*`), email (`EMAIL_*`, `DEFAULT_FROM_EMAIL`),
storage (`MEDIA_STORAGE`, `AWS_*`, `MEDIA_STORAGE_LIMIT_*`), external APIs
(`GOOGLE_MAPS_API_KEY`, `STRAVA_CLIENT_*`, `PUBLIC_UMAMI_*`), cloud
(`CLOUD_MODE`, `CLOUD_TRIAL_DAYS`, `STRIPE_*`), ops (`SKIP_WORLD_DATA`,
`COMPOSE_FILE`, `BACKUP_DIR`, `ADVENTURELOG_REF`).

**`.env.example` never sets `SECRET_KEY`** — it appears only inside a comment at
`.env.example:10` claiming it is "derived at startup" — and
`docker/aio/env-setup.sh:30-31` generates a random `secrets.token_urlsafe(50)`
whenever it is unset. So the Standard image **rotates `SECRET_KEY` on every
restart**, logging everyone out and invalidating every API key (the key is part of
the PBKDF2 salt, §6.2). `.env.advanced.example:24` does set it
(`SECRET_KEY=changeme123`), so Advanced deployments are unaffected. This is the
single most consequential default in the project. `[v]`

---

## 14. CI/CD and the testing reality

Twelve workflows in `.github/workflows/` `[v]`:

| Workflow | What it actually does |
| --- | --- |
| `backend-test.yml` | **Runs no tests.** setup-python 3.13 → `apt install python3-gdal` → start `docker-compose.database.yml` → `pip install -r requirements.txt` → `manage.py migrate` → `runserver &` → `curl http://localhost:8000/`. A boot smoke test. |
| `frontend-test.yml` | **Runs no tests** (there are none). `pnpm lint` (prettier), `pnpm check` (svelte-check), `pnpm build`. Job name "Frontend Quality Checks" is accurate. |
| `_build-image.yml` | reusable; buildx multi-arch `linux/amd64,linux/arm64`, pushes to GHCR + Docker Hub, gha + registry cache |
| `_build-images.yml` | reusable fan-out to frontend/backend/aio with `dorny/paths-filter` |
| `images-beta` / `images-latest` / `images-release` | `development`→`beta`, `main`→`latest`, release→tag + move `latest` |
| `compose-smoke-test.yml` | builds `--target aio`, `compose up -d --wait`, curls `:8015/health` 60×. **The closest thing to an end-to-end test.** |
| `installer-smoke-test.yml` | shellcheck + `--dry-run` wizard + `validate-env.sh` fixtures |
| `trivy_security_scans.yml` | filesystem + all three images, CRITICAL/HIGH gating, weekly cron |
| `adventurelog-bot.yml`, `sync-project-status.yml` | PR issue-link validation; label→Project field sync |

**~20 Django test modules exist and never run in CI** — e.g.
`adventures/tests/test_protected_media.py`, `test_collection_sharing.py`,
`test_dashboard.py`, `test_collection_pdf.py`, `test_global_search.py`,
`worldtravel/tests/test_serializers.py`, `integrations/tests/test_immich_view.py`,
`integrations/tests/test_endurain_services.py`. `[v]`

Adding `python manage.py test` to `backend-test.yml` is arguably the
highest-value change available in this repo. Expect it to surface pre-existing
failures, so it belongs in its own PR.

Local test runs need PostGIS **and** GDAL (`python3-gdal`); a bare
`manage.py test` fails on the GIS backend.

---

## 15. Hazard register

Ordered roughly by blast radius. Each is a real finding, not a style opinion.

| # | Hazard | Where |
| --- | --- | --- |
| 1 | `SECRET_KEY` regenerated on every restart in Standard deployment → all sessions and **all API keys** invalidated. `.env.example:10` mentions it only in a comment ("SECRET_KEY, CSRF, and backend URLs are derived at startup"), framing rotation as intended; `env-setup.sh:30-31` generates a fresh `token_urlsafe(50)` whenever it is unset. `.env.advanced.example:24` does set it. | `.env.example` + `docker/aio/env-setup.sh` |
| 2 | `Location.save()` spawns an unmanaged daemon thread doing outbound HTTP per write; no retries, no visibility. `bulk-adventure-geocode` multiplies it | `adventures/models.py` |
| 3 | Sharing grants **delete**, not just write, on Visits/Trails/Activities/images; and permission is checked on the substituted ancestor, never the object's own `user` | `adventures/permissions.py` |
| 4 | Owner making a collection public flips **other members' private locations** public via queryset `.update()`, bypassing `save()`/`clean()`/signals | `collection_view.py` `update()` |
| 5 | `LocationSerializer` embeds the full owner user object incl. **email** and `is_staff` on public, unauthenticated reads | `serializers.py` `to_representation` |
| 6 | `POST /api/backup/import/` calls `_clear_user_data` — deletes all the caller's content before importing; gated only by `confirm=yes`, unversioned, fully buffered, trusts ZIP contents | `import_export_view.py` |
| 7 | **No password validators at all**, and `ACCOUNT_RATE_LIMITS = {}` by default removes allauth's own throttling defaults | `main/settings.py` |
| 8 | `CACHES` hardcoded to `127.0.0.1:11211` with no env override, while caching is load-bearing for geocoding, Wikipedia, sunset and Endurain MFA | `main/settings.py` |
| 9 | `/etc/adventurelog/cron.env` is a 0644 dump of the entire environment, secrets included | `write-cron-env.sh` |
| 10 | Two guaranteed-500 endpoints query `Region.geometry`, dropped in migration `0007` (and one also filters `Location.type`, which no longer exists) | `worldtravel/views.py` `check_point_in_region`, `region_check_all_adventures` |
| 11 | `integrations/urls.py` registers `immich` **twice** with an empty-prefix router between them | `integrations/urls.py` |
| 12 | Immich image proxy is `permission_classes=[]` with hand-rolled per-image ACL sorting; `ImmichIntegrationSerializer` echoes `api_key` | `immich_view.py`, `integrations/serializers.py` |
| 13 | Nested `visits` on `POST /api/locations/` is declared writable but never popped in `create()` → 500 `[i]` | `serializers.py` |
| 14 | `LocationSerializer.update` **deletes and replaces all visits** when `visits` is provided, losing cascaded Activities | `serializers.py` |
| 15 | Category change by a non-owner is **silently ignored** (200 with the old value) rather than refused | `serializers.py` |
| 16 | `retrieve_locations()` with no flags returns the entire table (fail-open) | `managers.py` |
| 17 | `Location.save()` validates **after** `super().save()`, so invalid rows persist when `ValidationError` raises | `adventures/models.py` |
| 18 | Project-wide sender-less `post_delete` receiver runs a ContentType lookup + up to 2 queries on **every** delete of **every** model | `adventures/signals.py` |
| 19 | `m2m_changed` publicity signal fires forward-only and force-demotes intentionally-public standalone locations | `adventures/signals.py` |
| 20 | `Visit.clean()` raises `TypeError` when either date is None; `ChecklistItem.clean()` public check is a tautology | `adventures/models.py` |
| 21 | `VisitedRegion`/`VisitedCity` enforce uniqueness only in `save()` — no DB constraint, and existing rows cannot be re-saved | `worldtravel/models.py` |
| 22 | No geographic filtering anywhere despite real PostGIS PointFields (no `dwithin`/`bbox`/`distance_lte`) | backend-wide |
| 23 | `GET /api/locations/` silently ignores `order_by` (`apply_sorting` isn't called from `list`) | `location_view.py` |
| 24 | Frontend proxy fetches `/csrf/` on **every** proxied request | `django-proxy.ts` |
| 25 | Auth guards duplicated across ~15 `+page.server.ts` files; no hook-level gate | `frontend/src/routes/**` |
| 26 | `src/service-worker/indes.ts` is misspelled → never registered or built | `frontend/src/service-worker/` |
| 27 | `pt.json`, `ta.json`, `sq.json` locales exist but are not registered; SSR renders no translations at all | `+layout.svelte` |
| 28 | `docker/docker-compose.dev.yml` cannot build — build contexts have no Dockerfile | `docker/` |
| 28b | `postgis/postgis:16-3.5` is **amd64-only**, so the Standard stack fails to start on Apple Silicon with an error naming no fix. Undocumented. See §12.2b `[v, runtime]` | `docker-compose.yml` |
| 29 | On the aio port, **both** `/health` and `/health/` hit the frontend (the latter 308s to the former). Django's DB-checking `/health/` is unreachable there, as are `/docs/` and `/csrf/`. Probes validate Node, not Postgres. `[v, runtime]` | nginx + compose + k8s |
| 30 | `collectstatic` is build-time, so a bind-mounted `/code` (dev compose) has no `staticfiles/` | `docker/Dockerfile` |
| 31 | Dead duplicate image-import module diverging from the live one | `services/media/images.py` |
| 32 | `achievements` app is scaffolding: no migrations, not installed, nothing computes achievements | `achievements/` |
| 33 | API keys have no scopes and no expiry; a phone-paired key has full account power forever | `users/models.py` |
| 34 | `default_user = 1` used as a literal FK default on 13 fields (11 in `adventures`, 2 in `worldtravel`) — a raw PK, not a callable | `adventures/models.py:124`, `worldtravel/models.py` |
| 35 | Debug `print()` calls in the permission hot path and the geocode thread | `permissions.py`, `models.py` |
| 36 | `django-allauth 0.63.3` pinned against Django 5.2.13 — a notable version gap | `requirements.txt` |
| 37 | Session cookie is shared across the whole registrable domain (`.example.com`); `SESSION_COOKIE_SECURE` derives from the **frontend** URL scheme only | `main/settings.py` |
| 38 | MapTiler basemap style still contains the public demo key placeholder | `frontend/src/lib/index.ts` |

---

## 16. Where to change what

| Task | Start here |
| --- | --- |
| Add/modify a REST endpoint | `adventures/urls.py` (router) → `adventures/views/<x>_view.py` → `adventures/serializers.py` |
| Change access control | `adventures/permissions.py`, then the per-viewset `get_queryset`, then the hand-rolled checks in `collection_view.py` / `location_view.py`. Assume all three matter. |
| Change what a shared user can do | `IsOwnerOrSharedWithFullAccess` + `collection_view.py` sharing actions |
| Add a field to Location/Visit/Collection | `adventures/models.py` → migration → `serializers.py` → `frontend/src/lib/types.ts` (hand-written!) → the relevant Svelte components |
| Change publicity behaviour | `adventures/signals.py` **and** `collection_view.py.update()` — two independent paths |
| Add an external data provider | `adventures/providers/<domain>/` then wire selection in `adventures/services/<domain>/` |
| Add a scheduled job | `backend/cron/adventurelog` + a management command; follow the `run-cron-job.sh <name> <command>` pattern |
| Add an integration | `integrations/models.py`, `integrations/views/`, `integrations/<x>_services.py`, `integrations/urls.py`, then `IntegrationView.list` capability probe, then `frontend/src/lib/components/settings/` |
| Change auth flow | `main/settings.py` (allauth block), `users/adapters.py`, `users/backends.py`, `adventures/middleware.py`, and on the frontend `login/+page.server.ts` + `hooks.server.ts` |
| Add a frontend page | `frontend/src/routes/<x>/+page.server.ts` (remember the `!locals.user` guard and the `{props:{...}}` wrapper) + `+page.svelte` |
| Change the backend contract | `frontend/src/lib/server/django-proxy.ts` — one file |
| Add an env var | `main/settings.py` + all three `.env*.example` + `docker/aio/env-setup.sh` + `scripts/validate-env.sh` + `documentation/docs/configuration/environment_variables.md` |
| Change the container | `docker/Dockerfile`, `docker/shared/{nginx-*,supervisord-*}.conf`, `docker/shared/entrypoint-common.sh` |
| Write user docs | `documentation/docs/**` + sidebar in `documentation/.vitepress/config.mts` + `seo.ts` entry |

---

## 17. Coverage and confidence

**Directly read for this document** (`[v]` claims): `main/settings.py` (all
relevant blocks), `main/urls.py`, `adventures/models.py` (full),
`adventures/permissions.py` (full), `adventures/managers.py`,
`adventures/signals.py`, `adventures/middleware.py`, `adventures/urls.py`,
`adventures/serializers.py` (Location/Visit/Category/MapPin sections),
`adventures/views/location_view.py`, `views/visit_view.py`,
`views/collection_view.py` (queryset, sharing, publicity cascade),
`views/places_api_view.py`, `views/quick_add_utils.py` (partial),
`worldtravel/models.py`, `worldtravel/views.py`, `users/models.py`,
`users/authentication.py`, `users/views.py` (public profile, social providers,
API keys, mobile QR), `integrations/models.py`, `integrations/urls.py`,
`requirements.txt`, `docker-compose.yml`, `docker/Dockerfile`,
`docker/shared/entrypoint-common.sh`, `docker/shared/nginx-aio.conf`,
`.github/workflows/backend-test.yml`, `frontend/package.json`,
`frontend/src/lib/server/django-proxy.ts`, `frontend/src/hooks.server.ts`,
`frontend/src/routes/+layout.svelte`, `frontend/src/routes/+page.server.ts`,
`documentation/docs/configuration/api_keys.md`.

**Mapped via sub-agent exploration rather than my own read** — trust but verify
before relying on exact line numbers: internals of `collection_pdf.py`,
`share_image.py`, `import_export_view.py`, `immich_view.py`, `strava_view.py`,
`endurain_services.py`, `wanderer_services.py`, `itinerary_view.py`,
`global_search.py`, `download-countries.py`, the frontend route inventory and
component tree, `k8s/`, the installer libs, and the ten workflows other than
`backend-test.yml`.

**Not covered at all:** the contents and pass/fail state of the ~20 backend test
modules; per-locale translation completeness; `brand/`; `.devcontainer/`;
`scripts/backup.sh` / `restore.sh` / `deploy.sh` internals; the `templates/`
allauth overrides; migration-by-migration history beyond the notable ones; and
anything about actual runtime behaviour, performance, or production data.

**Audit pass, 2026-08-09.** After the first draft, every counted or line-numbered
claim in this document was re-checked against the tree. Nine were wrong and have
been corrected: `adventures` migration count (66→64 files, numbered to `0076`
with a gap from the squash), workflow count (13→12), frontend route file count
(62→61, of which 28 are `+page.server.ts`), relative-fetch occurrences
(~117→~124), `permissions.py` length (278→276), `background_geocode_and_assign`
start line (26→24), `INSTALLED_APPS` range (56-90→56-89), `MIDDLEWARE` range
(95-112→95-111), and `default_user` usage ("~12 models"→13 fields).

Re-confirmed as written during the same pass: no geographic filtering anywhere
(`dwithin`/`distance_lte`/`Distance(`/`__within` all return zero non-migration
hits); exactly one `threading.Thread` plus two `ThreadPoolExecutor` uses and no
Celery; zero `.css` files; zero `+page.ts` files; 25 locale files against 22
`register()` calls; 15 files carrying the `/login` redirect guard;
`service-worker/indes.ts` misspelling; two MapTiler demo-key occurrences; one
active cron job; three `k8s/` files; 20 backend test modules; only one Dockerfile
in the repo and `docker-compose.dev.yml` pointing at build contexts without one;
`ImmichIntegrationSerializer` using `fields = '__all__'` and popping only `user`
(so `api_key` is echoed); `SessionAdmin` exposing decoded session data; no
`IsAdminUser` and no permission class consulting `is_staff`; no
`AUTH_PASSWORD_VALIDATORS` or `PASSWORD_HASHERS` anywhere; and `health_check`
calling `connection.ensure_connection()` with a 503 on failure.

**Staleness triggers.** Re-verify this document if any of these change: `main/settings.py`,
`adventures/models.py`, `adventures/permissions.py`, `adventures/urls.py`,
`frontend/src/lib/server/django-proxy.ts`, `frontend/src/hooks.server.ts`,
`docker/Dockerfile`, or `docker-compose.yml`. Those eight files anchor most of
what is written above.
