# AdventureLog — API Contract Reference (project-wide)

**Purpose:** the complete HTTP contract for the AdventureLog backend — every
endpoint, what you may send, what you get back, and where the contract is
inconsistent. Written for anyone building a client, an integration, or changing
an endpoint.

**How to use this in a new chat session:** attach this file with `#File` and say
"use this as the API contract, don't re-analyse the repo."

## Scope, and how this differs from the other three documents

| Document | Answers |
| --- | --- |
| `docs/architecture/ARCHITECTURE.md` | *How is the system built?* Apps, data model, permissions, frontend, deployment, CI. |
| **`docs/architecture/API_CONTEXT.md`** (this file) | *What is the HTTP contract?* Every endpoint, params, bodies, responses, status codes. |
| `docs/apple-shortcuts/API_CONTEXT.md` | *Deep dive on one slice:* API keys + locations + visits + categories, for an external client. More detail on those four than this file carries. |
| `docs/apple-shortcuts/IMPLEMENTATION_PLAN.md` | A worked feature plan built on that slice. |

Note the name collision: there are two `API_CONTEXT.md` files. This one is
project-wide; the one under `apple-shortcuts/` is the narrow deep dive. For
locations, visits and categories, prefer that file — §4 here only summarises.

**Analysed:** 2026-08-09 against the working tree. Version `v0.13.0`.

**Confidence markers:** `[v]` verified — the cited file/line was read directly.
`[i]` inferred — deduced from code, not executed. **Nothing here was executed;**
no request was ever issued against a running server. `[v]` means "I read that
line," not "I observed that response."

---

## 1. Conventions that apply everywhere

### 1.1 Base paths `[v]` (`main/urls.py`)

| Prefix | Contents |
| --- | --- |
| `/api/` | `adventures.urls` **and** `worldtravel.urls`, both mounted at the same prefix (`urls.py:17-18`) |
| `/api/integrations/` | `integrations.urls` |
| `/api/billing/` | `billing.urls` |
| `/auth/` | allauth headless (`/auth/browser/v1/...`, `/auth/app/v1/...`) **plus** 12 hand-wired DRF views (`urls.py:24-42`) |
| `/accounts/` | classic allauth (social login lives here) |
| `/media/<path>` | `serve_protected_media` — plain Django view, not DRF |
| `/csrf/`, `/health/`, `/public-url/` | plain Django helper views |
| `/docs/` | drf-yasg Swagger UI |

**There is no `users/urls.py`.** The `/auth/...` DRF endpoints are individual
`path()` entries in the root urlconf, sharing the prefix with allauth without
being part of it.

### 1.2 Trailing slashes — depends on which port you hit `[v, runtime]`

**Against Django directly** (Advanced deployment, or `127.0.0.1:8000` inside the
container): all routers are `DefaultRouter()`, so **trailing slashes are
required**. `APPEND_SLASH` redirects a slashless GET but will not preserve a POST
body.

**Against the Standard ("aio") published port the opposite is true.** nginx sends
everything except `/static/`, `/media`, `/admin` and `/accounts` to SvelteKit, so
`/api/...` is handled by the `/api/[...path]` **proxy**, which normalizes away the
trailing slash before re-adding it for Django. Observed on a live stack:

```
GET /api/categories    -> 200
GET /api/categories/   -> 308 Permanent Redirect, location: /api/categories
                          (x-sveltekit-normalize: 1)
```

So: **slashless on the aio port, slashed against Django.** Following redirects
makes both work; a POST with a body must either be slashless or use a client that
re-sends the body on 308 (curl needs `-L` and handles 308 correctly).

Also unreachable on the aio port, because they are Django-only routes that nginx
does not forward: **`/docs/` (Swagger) → 404** and **`/csrf/` → 404**.

One further exception: allauth headless routes under `/auth/browser/` and
`/auth/app/` are genuinely slashless everywhere, which is why the proxy
special-cases them (`frontend/src/lib/server/django-proxy.ts`).

**Cost note:** the proxy calls `GET /csrf/` on the backend for *every* proxied
request, so each `/api/` call through the aio port is two backend round-trips.

### 1.3 Authentication `[v]` (`main/settings.py:392-396`)

```
DEFAULT_AUTHENTICATION_CLASSES = (
    'users.authentication.APIKeyAuthentication',   # tried first
    'rest_framework.authentication.SessionAuthentication',
)
```

Three ways in:

```http
X-API-Key: al_...                 # preferred for scripts
Authorization: Api-Key al_...     # equivalent
Cookie: sessionid=...             # browser session
X-Session-Token: <sessionid>      # header-as-cookie, for native clients
```

API-key writes need no CSRF token. Session writes do (`GET /csrf/` first, then
send `X-CSRFToken`). A key carries its owner's full permissions, with no scopes
and no expiry.

### 1.4 There are no framework-wide defaults `[v]`

`REST_FRAMEWORK` sets only auth classes, schema class, throttles and renderers.
Verified absent: `DEFAULT_PERMISSION_CLASSES`, `DEFAULT_PAGINATION_CLASS`,
`DEFAULT_FILTER_BACKENDS`, `DEFAULT_PARSER_CLASSES`, `EXCEPTION_HANDLER`.

Four consequences that shape the whole contract:

1. **A view without `permission_classes` is effectively `AllowAny`.** Two real
   cases: `GET /api/stats/counts/<username>/` and `GET /api/sunrise-sunset/lookup/`.
2. **Almost nothing paginates.** Only `LocationViewSet`, `CollectionViewSet` and
   the Immich actions set `pagination_class`. Everything else returns a **bare
   JSON array** with no `count`/`next`/`previous`.
3. **`filterset_fields` is dead config.** `note_view.py:16` and
   `checklist_view.py:16` declare it, but there is no `django_filters` install and
   no `filter_backends` anywhere, so `?is_public=`/`?collection=` are silently
   ignored on those routes.
4. **Django `ValidationError` raised inside `Model.save()` becomes a 500, not a
   400** — DRF's default handler only converts `Http404`, Django's
   `PermissionDenied` and `APIException`. This bites on `Trail`, `ContentImage`,
   `VisitedRegion` and `VisitedCity`, all of which validate in `save()`. `[i]`

### 1.5 Pagination `[v]` (`adventures/utils/pagination.py`)

```python
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 1000
```

Envelope: `{count, next, previous, results}`. Params `?page=`, `?page_size=`.
Applies to `GET /api/locations/`, `GET /api/collections/`, the paginated
locations actions, and the Immich search/album actions (which use an identical
class in `integrations/utils.py`).

### 1.6 The `user` field in every response is a UUID string `[v]` (`main/utils.py:20-26`)

```python
class CustomModelSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if hasattr(instance, 'user') and instance.user:
            representation['user'] = get_user_uuid(instance.user)
        return representation
```

So `user` is `str(user.uuid)` — not the integer pk, not the username — on
Transportation, Lodging, Note, Checklist(Item), Collection, Trail, Activity,
ContentImage, Attachment, VisitedRegion, VisitedCity and both itinerary
serializers. It is read-only everywhere.

`LocationSerializer` is the exception: it replaces `user` with a **full nested
user object** (see §4 and hazard H1).

### 1.7 Media URLs are absolute `[v]` (`main/utils.py:11-19`)

```python
def build_media_url(path):
    if settings.USE_S3_MEDIA:  return default_storage.url(path)   # possibly presigned
    return f"{get_public_url()}/media/{path}"                     # PUBLIC_URL based
```

Never relative. Immich-backed images are instead rewritten to
`{PUBLIC_URL}/api/integrations/immich/{integration_id}/get/{immich_id}`.

### 1.8 Error body shapes — five incompatible conventions `[v]`

Counted in `adventures/` alone: **143** `{"error": ...}` sites versus **11**
`{"detail": ...}` sites. Full taxonomy:

| Shape | Where | Note |
| --- | --- | --- |
| `{"error": "<sentence>"}` | most hand-rolled guards across collections, itineraries, quick-add, images, worldtravel | status varies 400/401/403/404/500/503 |
| `{"error": "User is not authenticated"}` with **HTTP 400** | `collections` list/all/archived/shared/invites and friends, `notes/all/` | wrong status class for an auth failure |
| **Empty body, HTTP 403** | `GET /api/transportations/` and `GET /api/lodging/` when anonymous (`Response(status=403)`) | no body at all |
| `{"detail": "<sentence>"}` | all DRF `PermissionDenied` / `NotFound` / throttling; `notes` list refusal; collection ZIP import; `itineraries/auto-generate/` validation | DRF standard plus a few hand-rolled |
| DRF field dict, `{"field": ["msg"]}` | any `serializer.is_valid(raise_exception=True)` | standard |
| `{"non_field_errors": ["..."]}` | `ChecklistSerializer.validate`, itinerary-day unique-together | |
| `{"items": "<string>"}` | `itineraries/reorder/` | value is a bare string, not a list |
| `{"error": "...", "limit_bytes": N, ...}` | quota failures | **413 with scalars** on images, **400 with each value wrapped in a list** on attachments |
| Immich style `{"message", "error": true, "code": "immich.*"}` | all Immich routes | a sixth convention, only here |

**Do not write a client that branches on body shape.** Branch on status code and
treat the body as advisory.

### 1.9 Throttling is off by default `[v]`

Every throttle extends `ConditionalUserRateThrottle`, whose `get_rate()` returns
`None` unless `ENABLE_RATE_LIMITS=true` (default **false**). Scopes and defaults:
`user` 10000/hour, `image_proxy` 60/min, `image_import` 12/min,
`external_geocode` 120/min, `external_recommendations` 30/min,
`external_wikipedia` 60/min, `external_sunrise_sunset` 30/min.
**`endurain_auth` (10/min) is always on.**

### 1.10 CLOUD_MODE `[v]`

With `CLOUD_MODE=false` (default) nothing returns 402 and the billing
checkout/portal routes return `404 {"detail": "Cloud billing is disabled for this
instance."}`. With it true, `CloudAccessMiddleware` intercepts **every** `/api/`
path (except `/api/billing/`) and returns
`402 {"detail": "Subscription required.", "code": "subscription_required"}` for
users without an active or unexpired-trial subscription. `/auth/`, `/csrf/`,
`/health/`, `/public-url/` and `/media/` are never gated — `GET /auth/current-user/`
is the intended way to detect `has_access: false` before touching `/api/`.

---

## 2. Complete endpoint index

`A` = anonymous access possible. `P` = paginated. Bold = non-JSON response.

### `/api/` — adventures

| Method | Path | Notes |
| --- | --- | --- |
| GET POST | `locations/` | P; list is owner-scoped |
| GET PUT PATCH DELETE | `locations/{id}/` | A on GET (public); owner-only DELETE |
| POST | `locations/quick-add/` | one-call create + geocode |
| GET | `locations/filtered/` | P; `types`, `is_visited`, sorting |
| GET | `locations/all/` | unpaginated dump |
| GET | `locations/pins/` | cheap coordinate feed |
| GET | `locations/calendar/` | slim calendar payload |
| GET | `locations/{id}/additional-info/` | A |
| GET | `locations/{id}/share-image/{square\|story\|landscape}/` | A; **PNG** |
| GET POST | `visits/` | permission checked on parent location |
| GET PATCH DELETE | `visits/{id}/` | cannot move to another location |
| GET POST | `categories/` | unpaginated; `general` undeletable |
| GET PUT PATCH DELETE | `categories/{id}/` | |
| GET POST | `collections/` | P; see §5 |
| GET PUT PATCH DELETE | `collections/{id}/` | A on GET; owner-only writes |
| GET | `collections/all/` `archived/` `shared/` `invites/` | bare arrays |
| POST | `collections/{id}/share/{uuid}/` | creates an invite, not a share |
| POST | `collections/{id}/revoke-invite/{uuid}/` | owner only |
| POST | `collections/{id}/accept-invite/` `decline-invite/` | invitee only |
| GET | `collections/{id}/can-share/` | |
| POST | `collections/{id}/unshare/{uuid}/` `leave/` | |
| GET | `collections/{id}/export-pdf/` | A; **PDF** |
| GET | `collections/{id}/share-image/{aspect}/` | A; **PNG** |
| GET | `collections/{id}/export/` | **ZIP** |
| POST | `collections/import/` | multipart **ZIP** |
| POST | `collections/{id}/duplicate/` | owner only |
| GET POST | `transportations/` | anonymous list → empty 403 |
| GET PUT PATCH DELETE | `transportations/{id}/` | |
| GET POST | `lodging/` | anonymous list → empty 403 |
| GET PUT PATCH DELETE | `lodging/{id}/` | |
| POST | `lodging/quick-add/` | |
| GET | `notes/` | **always 403** — use `notes/all/` |
| GET | `notes/all/` | |
| POST | `notes/` · GET PUT PATCH DELETE `notes/{id}/` | |
| GET POST | `checklists/` · GET PUT PATCH DELETE `checklists/{id}/` | nested `items` required on POST |
| GET POST | `images/` · GET PUT PATCH DELETE `images/{id}/` | multipart |
| POST | `images/{id}/image_delete/` `toggle_primary/` | |
| GET | `images/map_pins/` | |
| POST | `images/fetch_from_url/` | **raw image bytes** |
| POST | `images/import_from_urls/` | max 10 URLs |
| GET POST | `attachments/` · GET PUT PATCH DELETE `attachments/{id}/` | multipart |
| GET POST | `activities/` · GET PUT PATCH DELETE `activities/{id}/` | GPX upload |
| GET POST | `trails/` · GET PUT PATCH DELETE `trails/{id}/` | anonymous → 403 |
| GET POST | `itineraries/` · GET PUT PATCH DELETE `itineraries/{id}/` | |
| POST | `itineraries/reorder/` `auto-generate/` | |
| GET POST | `itinerary-days/` · GET PUT PATCH DELETE `itinerary-days/{id}/` | |
| GET | `stats/dashboard/` | |
| GET | `stats/counts/{username}/` | **A** (no permission class) |
| GET | `search/` | `q`, `types`, `limit`≤50, `offset` |
| GET | `calendar/events/` | |
| GET | `ics-calendar/generate/` | **text/calendar** |
| GET | `tags/types/` | bare string array |
| GET | `places/search/` `place_details/` `reverse/` | |
| GET | `reverse-geocode/reverse_geocode/` `search/` `place_details/` | |
| POST | `reverse-geocode/mark_visited_region/` | no body |
| GET | `recommendations/query/` | |
| GET | `sunrise-sunset/lookup/` | **A** (`AllowAny`) |
| GET | `generate/desc/` `generate/img/` | Wikipedia, not AI |
| GET | `backup/export/` | **ZIP** |
| POST | `backup/import/` | multipart; **destructive** |

### `/api/` — worldtravel

| Method | Path | Notes |
| --- | --- | --- |
| GET | `countries/` `countries/{id}/` | unpaginated, ~250 rows; pk is the integer id, not the ISO code |
| GET | `countries/check_point_in_region/` | **broken, always 500** |
| POST | `countries/region_check_all_adventures/` | **broken, always 500** |
| GET | `regions/` `regions/{id}/` | unpaginated, ~5k rows |
| GET POST | `visitedregion/` `visitedcity/` | JSON only (see H7) |
| DELETE | `visitedregion/{region_id}/` `visitedcity/{city_id}/` | **pk is the Region/City id**, not the VisitedX id |
| GET | `{country_code}/regions/` `{country_code}/visits/` | |
| GET | `regions/{region_id}/cities/` `.../cities/visits/` | |
| GET | `globespin/` | random country → region → city |

### `/auth/` — non-allauth

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `is-registration-disabled/` | A | throttle-exempt |
| GET | `users/` | A | array of public profiles |
| GET | `user/{username}/` | A | user + public locations + collections |
| PATCH | `update-user/` | yes | multipart for `profile_pic`; 413 on quota |
| GET | `user-metadata/` | yes | throttle-exempt |
| GET | `user-media-usage/` | yes | |
| GET | `current-user/` | yes | `{user, subscription, has_access, cloud_mode}` |
| GET | `social-providers/` | A | |
| POST DELETE | `disable-password/` | yes | |
| GET POST | `api-keys/` | yes | POST returns raw `key` once |
| DELETE | `api-keys/{uuid}/` | yes | 204 |
| GET POST DELETE | `mobile-qr/` | yes | POST returns `key` + base64 QR |
| GET | `/csrf/` `/health/` `/public-url/` | A | plain Django views |

### `/api/integrations/` and `/api/billing/`

See §12 and §13.

---

## 3. Cheat sheet

```bash
BASE=https://adventurelog.example.com
KEY=al_xxxxxxxxxxxx
H="-H X-API-Key:$KEY -H Content-Type:application/json"

# create a location, then log a visit (this order matters — see §4)
curl -s -X POST "$BASE/api/locations/" $H \
  -d '{"name":"Blue Lagoon","latitude":63.88,"longitude":-22.45,
       "category":{"name":"nature","display_name":"Nature","icon":"🏞"}}'
curl -s -X POST "$BASE/api/visits/" $H \
  -d '{"location":"<uuid>","start_date":"2026-01-05T14:00:00Z","timezone":"Europe/Athens"}'

# a trip
curl -s -X POST "$BASE/api/collections/" $H -d '{"name":"Iceland 2026"}'
curl -s -X PATCH "$BASE/api/locations/<uuid>/" $H -d '{"collections":["<collection-uuid>"]}'

# attach an image (multipart, note content_type is a model NAME string)
curl -s -X POST "$BASE/api/images/" -H "X-API-Key:$KEY" \
  -F content_type=location -F object_id=<uuid> -F image=@photo.jpg

# read
curl -s "$BASE/api/locations/pins/"              -H "X-API-Key:$KEY"
curl -s "$BASE/api/search/?q=lagoon&limit=10"    -H "X-API-Key:$KEY"
curl -s "$BASE/api/stats/dashboard/"             -H "X-API-Key:$KEY"
curl -s "$BASE/api/calendar/events/?start=2026-01-01&end=2026-12-31" -H "X-API-Key:$KEY"
```

---

## 4. Locations, visits, categories — summary

Full treatment is in `docs/apple-shortcuts/API_CONTEXT.md`. The essentials:

**`POST /api/locations/`** `[v]` — minimum body `{"name": "..."}`. Writable:
`name`, `description`, `rating`, `tags[]`, `location` (free-text label),
`is_public`, `link`, `price`/`price_currency`, `latitude` + `longitude` (must be
sent together), `collections[]` (UUIDs), `category` (**nested object**, not an id).
Read-only: `id, created_at, updated_at, user, is_visited`. Server-derived:
`city`, `region`, `country`.

Three traps:
- `category` accepts only a nested object here; only `quick-add` normalizes an id.
- **Do not send nested `visits` on POST** — it is declared writable but never
  popped in `create()`, so it hits the reverse relation and 500s. `[i]`
- The response embeds the owner's **full user object**, including email (H1).

**`POST /api/visits/`** `[v]` — `{"location": "<uuid>", "start_date": "...",
"end_date"?, "timezone"?, "notes"?}`. `end_date` defaults to `start_date`.
Permission is checked against the **location**, so a shared collaborator can
create, edit and delete visits they don't own.

**Ordering matters.** `Location.save()` spawns a background geocode thread; it
only creates `VisitedRegion`/`VisitedCity` when the location already has a visit.
So: create location → create visit. Expect `city`/`region`/`country` to still be
`null` in the create response because the thread is asynchronous.

**`GET /api/categories/`** `[v]` — unpaginated. Per-user, with a real
`unique_together = ['name', 'user']` constraint. Names are lowercased. Writing a
location with an unknown category name creates it, so pre-fetching is optional.

---

## 5. Collections

`CollectionViewSet` `[v]` — `permission_classes = [CollectionShared]`, paginated.
`list`/`all`/`archived`/`shared` use a fully read-only `UltraSlimCollectionSerializer`;
everything else uses `CollectionSerializer`.

### Writable contract `[v]`

```python
fields = ['id','description','user','name','is_public','locations','created_at',
          'start_date','end_date','transportations','notes','updated_at','checklists',
          'is_archived','shared_with','collaborators','link','lodging','status',
          'days_until_start','primary_image','primary_image_id']
read_only_fields = ['id','created_at','updated_at','user','shared_with','status',
                    'days_until_start','primary_image']
```

**A client may send only:** `name` (the sole required field), `description`,
`is_public`, `start_date`, `end_date`, `is_archived`, `link`, `primary_image_id`.

`locations`, `transportations`, `notes`, `checklists`, `lodging`, `collaborators`
are all `SerializerMethodField` — read-only output, never writable. You attach a
location to a collection by PATCHing **the location's** `collections` array, not
the collection.

`primary_image_id` is write-only and validated: `{"primary_image_id": "You can
only choose cover images you own."}` / `"Cover image must come from a location in
this collection."` `validate_link` **silently coerces** a blank or invalid URL to
`null` rather than erroring.

### Queryset scoping is per-action `[v]`

- `update`/`partial_update`/`destroy` → owner only, so a shared member gets **404**, not 403.
- `retrieve`/`export_pdf`/`share_image` → public collections readable **anonymously**.
- `list` and everything else → `owner AND is_archived=False`. Archived collections
  cannot be exported or duplicated.

### Response extras `[v]`

`GET /api/collections/{id}/` injects two keys beyond the serializer:
`itinerary` (array of itinerary items) and `itinerary_days`.

### Query params `[v]`

`order_by` ∈ `name|updated_at|start_date` (anything else → `updated_at`),
`order_direction` ∈ `asc|desc` — note the mapping is inverted, `name&asc`
produces `-lower_name`. `status` ∈ `folder|upcoming|in_progress|completed`, honoured
**only on `list`**. `nested=true` strips the child arrays. `page`, `page_size`.
`exclude_transportations`/`_notes`/`_checklists`/`_lodging` are placed into
serializer context but never read — silently ignored.

### Sharing lifecycle `[v]`

Two hops. `POST /api/collections/{id}/share/{user-uuid}/` creates a
`CollectionInvite` (target must have `public_profile=True`); the invitee then
POSTs `accept-invite/`. All these actions answer `200 {"success": "<sentence>"}`.

`unshare` and `leave` both **remove the departing user's own locations** from the
collection and report the count in the message.

### `PATCH` side effects worth knowing `[v]`

- Flipping `is_public` **true** runs `.update(is_public=True)` across
  `locations`, `transportation_set`, `note_set`, `checklist_set`, `lodging_set` —
  bypassing `save()`, `clean()` and signals, and publishing other members'
  private locations (H2).
- Changing `start_date`/`end_date` **hard-deletes** itinerary items and days
  outside the new range, with no report of what was removed. Trip-wide
  (`is_global`) items survive; nothing is deleted if either bound is null.

### Non-JSON `[v]`

| Route | Content-Type | Disposition |
| --- | --- | --- |
| `{id}/export-pdf/` | `application/pdf` | `attachment` |
| `{id}/share-image/{aspect}/` | `image/png` | `inline`, or `attachment` with `?download=1` |
| `{id}/export/` | `application/zip` | `attachment; filename="collection-<name>.zip"` |

`POST /api/collections/import/` is `multipart/form-data`, requires a ZIP
containing `metadata.json`, and is **non-destructive** (unlike `/api/backup/import/`).

---

## 6. Trip content: transportations, lodging, notes, checklists

All four share a pattern `[v]`: `permission_classes = [IsOwnerOrSharedWithFullAccess]`,
no pagination, `list` returns **only your own rows** (not shared ones), and
`retrieve` widens to `is_public | owner | collection shared`.

### Writable fields, verbatim `[v]`

**Transportation** — required: `type` (enum `car|plane|train|bus|boat|bike|walking|other`)
and `name`.
```python
fields = ['id','user','type','name','description','rating','price','price_currency',
          'link','date','flight_number','from_location','to_location','is_public',
          'collection','created_at','updated_at','end_date','origin_latitude',
          'origin_longitude','destination_latitude','destination_longitude',
          'start_timezone','end_timezone','distance','images','attachments',
          'start_code','end_code','travel_duration_minutes']
read_only_fields = ['id','created_at','updated_at','user','distance','travel_duration_minutes']
```
`images`/`attachments` are method fields — read-only despite not being listed.
The four `*_latitude`/`*_longitude` fields are writable and map onto the
`origin`/`destination` PointFields; send each pair together.

**Lodging** — required: `name`. `type` defaults `other`.
```python
fields = ['id','user','name','description','rating','link','check_in','check_out',
          'reservation_number','price','price_currency','latitude','longitude',
          'location','is_public','collection','created_at','updated_at','type',
          'timezone','images','attachments']
read_only_fields = ['id','created_at','updated_at','user']
```

**Note** — required: `name`. `links` is an array of validated URL strings.
```python
fields = ['id','user','name','content','date','links','is_public','collection',
          'created_at','updated_at']
read_only_fields = ['id','created_at','updated_at','user']
```

**Checklist** — required: `name` **and `items`**.
```python
fields = ['id','user','name','date','is_public','collection','created_at','updated_at','items']
read_only_fields = ['id','created_at','updated_at','user']
# items = ChecklistItemSerializer(many=True, source='checklistitem_set')  ← no required=False
```
Per item you may send only `name` and `is_checked`.

`collection` is a plain `PrimaryKeyRelatedField` on all four — send a collection
**UUID**, not a nested object.

### Behaviours that will surprise you `[v]`

- **`GET /api/notes/` always returns `403 {"detail": "Listing all notes is not
  allowed."}`.** Use `GET /api/notes/all/`.
- **Anonymous `GET /api/transportations/` and `/api/lodging/` return 403 with an
  empty body.**
- **`perform_create` reassigns ownership.** If you pass a `collection`, the row is
  saved with `user=collection.user` — so creating content in someone else's shared
  collection makes *them* the owner.
- **Checklist PATCH without `items` deletes every item** (H5).
- **`PATCH` on content inside someone else's collection raises
  `PermissionDenied("You cannot remove the collection as you are not the owner.")`**
  even when you never mentioned `collection`, because the code cannot distinguish
  "absent" from "explicit null".
- **`PUT` skips all of those guards** — only `partial_update` is overridden.
- Changing a note's or checklist's `date` silently deletes matching itinerary items.

---

## 7. Itineraries

Two viewsets, both `IsOwnerOrSharedWithFullAccess`, both denying anonymous access
entirely (`none()` queryset) `[v]`.

### `itinerary-days` — simple

```python
fields = ['id','collection','date','name','description','created_at','updated_at']
read_only_fields = ['id','created_at','updated_at']
```
Required: `collection` + `date`, unique together. **`update()` pops `collection`
and `date`**, so after creation only `name` and `description` can change.
All three `perform_*` hooks raise `403 {"detail": "You do not have permission to
modify this collection"}` for non-members.

### `itineraries` — the least standard endpoint in the codebase

```python
fields = ['id','collection','content_type','object_id','item','date','is_global',
          'order','start_datetime','end_datetime','created_at','object_name']
read_only_fields = ['id','created_at','start_datetime','end_datetime','item','object_name']
validators = []      # unique-together validators deliberately disabled
```

`content_type` accepts a `ContentType` **integer pk** or one of the strings
`location`, `transportation`, `note`, `lodging`, `visit`, `checklist`. `order` is
effectively **required** (no model default). Exactly one of `date` or
`is_global=true` must be set.

`POST` also accepts behaviour flags — `update_item_date`, `source_visit_id`,
`start_date`, `end_date` — and when `update_item_date` is truthy it **mutates the
referenced object**: creating or moving a `Visit` for locations, rewriting
`date`/`end_date` for transportation, `check_in`/`check_out` for lodging. Success
is `201` plus an injected `updated_object` key for transportation and lodging.

`DELETE /api/itineraries/{id}/` **deletes visits.** For location-type items it
removes *every* `Visit` at that location whose `start_date` falls on the item's
date — not only ones this feature created. Pass `?preserve_visits=true` to skip.

`POST /api/itineraries/reorder/` takes `{"items":[{"id","date","order","is_global"?}]}`
and answers 200 with the updated items. Its errors use the odd
`{"items": "<string>"}` shape.

`POST /api/itineraries/auto-generate/` takes `{"collection_id"}`, works only on a
collection with zero existing items, and answers
`201 {"message": "...", "items": [...]}`.

`update()` pops `collection`, `content_type` and `object_id`, so PATCH can only
change `date`, `is_global`, `order`.

---

## 8. Activities and trails

Both derive permission from the parent **location**, and both reassign ownership
to that location's owner on create `[v]`.

**Activity** — required `visit` + `name`; `sport_type` defaults `General`.
Read-only: `id`, `user`. `gpx_file` needs `multipart/form-data` and comes back as
an absolute media URL. `start_lat`/`start_lng`/`end_lat`/`end_lng` are writable
pairs mapping to PointFields. Durations (`moving_time`, `elapsed_time`,
`rest_time`) serialize as `"HH:MM:SS"`. On create, elevation and coordinate
fields are backfilled from the GPX **only where you left them null**. `visit`
cannot change after creation.

**Trail** — required `location` + `name`, plus a model-level XOR: exactly one of
`link` or `wanderer_id`. Writable: `name`, `location`, `link`, `wanderer_id`,
`wanderer_author_username`, `wanderer_author_domain`.

Two things to expect:
- `GET /api/trails/` **raises `403 {"detail": "You must be authenticated to view
  trails."}` from inside `get_queryset`** — the only prefix here with no public
  read path at all.
- Violating the link/wanderer XOR surfaces as a **500**, because `Trail.save()`
  calls `full_clean()` and Django's `ValidationError` is not translated. `[i]`
- `provider`, `wanderer_data`, `wanderer_link` and `geojson` are method fields
  that make **outbound HTTP calls to Wanderer per object**, so list responses can
  be slow and these keys are `null` without an integration.

---

## 9. Media: images, attachments, protected files

### Attaching to a generic parent `[v]`

Both `/api/images/` and `/api/attachments/` identify their target with two flat
form fields, **not** serializer fields:

```
content_type = location | transportation | note | lodging | visit    ← model NAME string
object_id    = <target uuid>
```

Not a `ContentType` pk, not `app_label.model`. Attachments also accept a legacy
`location=<uuid>` alias. Because these are not serializer fields, **PUT/PATCH can
never retarget an existing image or attachment**.

### Serializers, verbatim `[v]`

```python
# ContentImageSerializer
fields = ['id','image','is_primary','user','immich_id','source','source_url','latitude','longitude']
read_only_fields = ['id','user']

# AttachmentSerializer
fields = ['id','file','extension','name','user','geojson']
read_only_fields = ['id','user']      # only `file` and `name` are writable
```

`source` ∈ `upload|google|wikipedia|url|immich`. Exactly one of `image` or
`immich_id` must be set. `is_primary` is **not** honoured on create — use
`toggle_primary/`.

⚠ `ContentImageSerializer.to_representation` **returns `None`** when an image has
an `immich_id` but its owner has no Immich integration. So list payloads can
contain `null` elements and a detail fetch can return a literal `null` body.

### Routes `[v]`

| Method | Path | Notes |
| --- | --- | --- |
| POST | `images/` | 201; 400/403/404 guards; **413** on quota with scalar keys |
| POST | `images/{id}/image_delete/` | alias for destroy → 204 |
| POST | `images/{id}/toggle_primary/` | 200 `{"success": ...}`; 400 if already primary; one-way |
| GET | `images/map_pins/` | bare array; drops entries with no image or coords |
| POST | `images/fetch_from_url/` | body `{"url"}` → **raw image bytes**; 400/502/504 |
| POST | `images/import_from_urls/` | max 10 URLs; **201** if all succeeded, **200** if partial, 400 if none |
| POST | `attachments/` | 201; quota failure is **400 with list-wrapped values** |

Every uploaded image is transcoded to **WebP at quality 75** with EXIF kept, and
renamed to `images/<uuid4>.<original-ext>` — so the stored key often says `.jpg`
while the bytes are WebP. Attachments accept a permissive ~40-extension allowlist
including archives, video, `.gpx` and `.md`.

### Remote import SSRF guard `[v]` (`services/images/fetch.py`)

http/https only, ports 80/443 only, every resolved IP rejected if private,
loopback, reserved, link-local or multicast, each of ≤3 redirects re-validated,
`Content-Type` must be `image/*`, 20 MB cap via `Content-Length`. Failures are
mapped to generic messages (`"Invalid image URL"`, `"Download timeout"`, …) so
upstream detail is not leaked. The cap is header-only, so a chunked response
without `Content-Length` is not capped. `[i]`

Summary dict: `{created_images, results, created_count, requested_count,
failed_count, failed}`. `results` preserves input order; entries are
`{url, status: "created", id}` or `{url, error, status: "failed"}`.

### `GET /media/<path>` `[v]` (`main/views.py`)

Plain Django view, no DRF, no throttling. Path is normalized (rejects `..`, NUL,
absolute). `profile-pics/`, `achievements/`, `flags/` are served with **no auth**.
`images/`, `attachments/`, `activities/` require passing `checkFilePermission`,
which resolves the file's parent object and allows public / owner / collection
member. The user is resolved from the session **or an API key**.

Three delivery modes: S3 → **302** to a possibly presigned URL; `DEBUG` → real
bytes; production → **200 with an empty `Content-Type` and
`X-Accel-Redirect: /protectedMedia/<path>`** for nginx to fulfil. A client
bypassing nginx therefore sees a 0-byte 200.

Every failure is a bare **403** with Django's HTML error page — never 401, and
never JSON. So an expired session is indistinguishable from a forbidden file.

---

## 10. Read and aggregate endpoints

### `GET /api/stats/dashboard/` `[v]`
`IsAuthenticated`. `?events_days=` default 30, silently clamped to **1–90** (a
non-integer falls back to 30 without a 400). Response has 6 keys:
`stats`, `recent_locations` (≤3), `upcoming_trips` (≤3), `active_trip` or null,
`upcoming_events` (≤10), `invite_count`.

### `GET /api/stats/counts/{username}/` `[v]`
**No permission class** → effectively public. Non-self access requires
`public_profile=True`, otherwise **404 (not 403)**. Returns `build_user_stats`:
`location_count`, `visited_location_count`, `trips_count`,
`visited_city_count`/`total_cities`, `visited_region_count`/`total_regions`,
`visited_country_count`/`total_countries`, `activities_overall`, four flat
`activity_*` aliases, and `activities_by_category`. The `total_*` values are
**global table counts**, not per-user. `record_holders` entries null out
`location_id`/`location_name` unless the requester owns the profile or the
location is public.

### `GET /api/search/` `[v]`
`q` (or `query`) required, min 2 chars, **truncated** at 100. `types` CSV from
11 values: `location, collection, lodging, transportation, note, checklist,
activity, country, region, city, user`. `limit` default 20 clamped to **50**;
`offset` ≥0; `fetch_limit = min(50, offset+limit)`, so you cannot page past 50
fetched hits.

Response: `{query, total, limit, offset, results, facets}`. Every result has the
same shape `{type, id, title, subtitle, url, score, meta}`. Note `total` is the
sum of per-type facet counts, which can exceed what pagination can reach, and
`country` results use the **ISO code as `id`**.

Matching is Postgres FTS (`SearchVector` + prefix `tok:*`) unioned with
`icontains`. **Type priority dominates score** — locations always sort before
collections regardless of relevance.

### `GET /api/calendar/events/` and `GET /api/ics-calendar/generate/` `[v]`
One engine, `services/calendar_events.py`. Types: `visit, transportation,
lodging, collection, note, checklist`.

`?start=`/`?end=` are parsed leniently — **an invalid date silently becomes
unbounded**, and a fully bogus `?types=` falls back to *all* types rather than
none. JSON response is `{"events": [...], "count": N}`, unpaginated. Every event
has 16 keys: `id, type, title, start, end, all_day, timezone, color, icon,
category, location_label, description, url, resource_id, collection_id,
collection_name`.

The ICS variant **accepts no parameters** — it emits the user's entire history,
all six types — and returns `text/calendar` with the fixed filename
`adventurelog.ics`, fully buffered.

⚠ The visit query includes `Q(is_public=True)`, so **public locations belonging to
other users appear in your calendar**.

### `GET /api/tags/types/` `[v]`
Bare array of tag strings, in DB row order, deduped in Python.

---

## 11. External lookup endpoints

### `/api/places/` `[v]`
- `search/?query=&include_meta=` — `include_meta` **changes the top-level type**:
  falsy → a bare array (and a bare `[]` with **status 200** even on provider
  error); truthy → `{provider_used, providers_attempted, results[, error]}`.
  `provider_used` ∈ `google|osm|mixed|null`. Each item has 19 keys
  (`lat, lon, name, display_name, place_id, type, types, category, description,
  website, phone_number, google_maps_url, importance, rating, review_count,
  photos, addresstype, provider, powered_by`).
- `place_details/?place_id=&name=&language=` — 11 keys, `description` is assembled
  Markdown; failure is **502** with the raw error dict. **This action has no
  throttle**, unlike its `reverse-geocode` twin.
- `reverse/?lat=&lon=` — see the payload below; provider errors are flattened to a
  generic `400`.

### `/api/reverse-geocode/` `[v]`
Partially duplicates `PlacesAPI`. `reverse_geocode/?lat=&lon=` returns up to 12
keys: `region_id, region, country, country_id, region_visited, display_name, city,
city_id, city_visited, location_name`, plus `provider_used` and `provider`.
If no `Region` row matches, you get the generic `400` — the common failure when
world-travel data has not been seeded.

`POST mark_visited_region/` takes **no body**. It derives regions/cities from the
`region`/`city` FKs already denormalized on your visited locations (no geocoding),
bulk-creates the missing rows, and answers
`{new_regions, regions, new_cities, cities}` where the two maps contain **only the
newly created** entries. Additive only, never deletes.

### `GET /api/recommendations/query/` `[v]`
`lat`+`lon`, or `location` to geocode. `category` **required**, one of
`lodging|food|tourism`. `sources` ∈ `google|osm|both` (default `both`). `radius`
in metres, **upper-clamped to 50000 but negatives are not rejected**; Overpass is
further capped at 5000 internally.

Response `{count, results, sources_used[, warnings]}`, results sorted by
`quality_score`, capped at 50. The **503** only fires when `sources=osm` *and*
zero results *and* a warning exists — the same Overpass failure under
`sources=both` returns 200 with `warnings`.

### `GET /api/sunrise-sunset/lookup/` `[v]`
**`AllowAny`** with a manual per-location access check. `location_id` and `date`
both required. Success is `{date, sunrise, sunset}`; unavailable is
`404 {"error": "Sunrise/sunset not available for this date"}`. Cached 30 days.

### `/api/generate/` `[v]`
**Wikipedia, not AI** — a repo-wide grep for `openai|anthropic|gemini|llm|ollama`
in the backend returns zero matches. `desc/?name=&lang=` returns the raw MediaWiki
page object with `lang` injected (so `pageid`, `title`, `extract`, `categories`),
cached 7 days. `img/` returns `{"images": [{source, width, height, title, type}]}`,
max 8, **uncached**. Both `404 {"error": "No description found"}` / `"No image found"`
when nothing qualifies.

---

## 12. Backup

### `GET /api/backup/export/` `[v]`
No params. Returns `application/zip`,
`attachment; filename="adventurelog_backup_<username>_<YYYYmmdd_HHMMSS>.zip"`,
**fully buffered in memory** — large accounts will spike RAM.

ZIP layout: `data.json`, `images/<basename>`, `attachments/<basename>`,
`gpx/<basename>`. Files are deduped by **basename**, so two files sharing a
basename collide and the second is silently skipped. Per-file errors are printed,
not raised, so an export can quietly omit media.

`data.json` top-level keys (14): `version, export_date, user_email, user_username,
categories, collections, locations, transportation, notes, checklists, lodging,
visited_cities, visited_regions, itinerary_items`. Cross-references use synthetic
integer `export_id` values, not UUIDs.

### `POST /api/backup/import/` `[v]` — destructive

`multipart/form-data` only. Required: `file` (the ZIP) and `confirm` exactly
`"yes"`. Inside one transaction it calls `_clear_user_data(user)` — deleting
**all** of the caller's activities, trails, checklists, notes, transportation,
lodging, images, attachments, locations (visits cascade), collections, categories,
visited cities and visited regions — and then imports.

Success `200 {"success": true, "message": ..., "summary": {...17 counters...}}`.
**Every failure is a 400**, including internal errors, because a broad
`except Exception` collapses them: `"No file provided"`,
`"Confirmation required to proceed with import"`,
`"Invalid backup file - missing data.json"`, `"Invalid JSON in backup file"`,
`"An internal error occurred during import"`.

There is **no version check** — `version` is written on export and never read on
import.

---

## 13. worldtravel, auth/user, integrations, billing

### worldtravel `[v]`

`countries/` and `regions/` are unpaginated read-only dumps (~250 and ~5k rows).
Serializers exclude `coordinates` and inject read-only `latitude`/`longitude`
derived from it. `CountrySerializer` adds `flag_url`, `num_regions`, `num_visits`
(0 when no request context, e.g. from `globespin`).

`visitedregion/` and `visitedcity/`:
- `POST` body is `{"region": "<id>"}` / `{"city": "<id>"}`. **JSON only** — the view
  does `request.data['user'] = request.user`, which raises on an immutable
  `QueryDict`, so form-encoded requests 500 (H7). `[i]`
- Duplicate `visitedregion` POST → `400 {"error": "Region already visited by user."}`.
  Duplicate `visitedcity` POST has **no pre-check** and hits the model guard →
  **500**. `[i]`
- Creating a `visitedcity` silently **also creates the parent `VisitedRegion`**,
  which is not reported in the response.
- `DELETE` takes the **Region/City id**, not the VisitedX id, while
  retrieve/update take the VisitedX pk.

`countries/check_point_in_region/` and `countries/region_check_all_adventures/`
both query fields that no longer exist (`Region.geometry`, dropped in migration
`0007`; `Location.type`, never existed) → `FieldError` → **500 on every call**.

### auth/user `[v]`

Every user payload is the same serializer (`CustomUserDetailsSerializer`, aliased
as both `PublicUserSerializer` and `UserSerializer`). Effective response keys:
`profile_pic, uuid, public_profile, username, first_name, last_name, date_joined,
is_staff, disable_password, measurement_system, default_currency, map_style,
has_password, shared_collection_count, pending_collection_invite_count`.
`pk` and `email` are popped in `to_representation`.

Writable via `PATCH /auth/update-user/`: `profile_pic` (multipart),
`public_profile`, `username`, `first_name`, `last_name`, `measurement_system`,
`default_currency`, `map_style`. Only `patch` is defined, so other verbs 405.
Quota failure is **413** with scalar keys.

Side effect: setting `public_profile=false` removes you from **every** collection
shared with you and deletes your pending invites, reported as
`left_shared_collections` / `revoked_collection_invites`.

Scrubbing is inconsistent: `PublicUserListView` really does remove
`has_password`/`disable_password` (it mutates the cached inner dicts), while
`PublicUserDetailView` pops from a fresh `ReturnDict`, so **`has_password`
survives in the single-user response**. `[i]`

`GET /auth/user-media-usage/` → `{total_bytes, images_bytes, attachments_bytes,
profile_pics_bytes, images_files, attachments_files, profile_pics_files,
limit_bytes}` (`limit_bytes` is `null` when unlimited).

`GET /auth/current-user/` → `{user, subscription, has_access, cloud_mode}`. Side
effect: it creates the `Subscription` row on first call.

API keys: `POST /auth/api-keys/` with `{"name"}` returns the record plus a
one-time `key`. `POST /auth/mobile-qr/` additionally returns `qr_code` as a
`data:image/png;base64,...` whose payload is
`{"version":1,"server_url","api_key","code_words":["hike","explore"]}`.

### integrations `[v]`

`GET /api/integrations/` capability probe:
```json
{"immich":{"exists":true,"copy_locally":true},"google_maps":true,
 "strava":{"global":true,"user":false},"wanderer":{"exists":false},
 "endurain":{"exists":false}}
```

Secret handling differs per integration and matters:
- **Immich leaks.** `ImmichIntegrationSerializer` uses `fields = '__all__'` and
  pops only `user`, so **`api_key` is returned in plaintext** by list/create/update.
- Wanderer and Endurain strip their secrets via `to_representation`.
- Strava has no serializer, so tokens are never rendered.

Notable routes: Immich `search/`, `albums/`, `albums/{id}/` (paginated), and the
**unauthenticated** image proxy `immich/{integration_id}/get/{imageid}` with
hand-rolled per-image ACL, `Cache-Control: public, max-age=86400`, 5 s upstream
timeout, and Immich-style error bodies. Strava `authorize/` → `callback/` (**302**
to the frontend) → `activities/`. Endurain `connect/` can answer **202** with
`{"mfa_required": true, "mfa_token", ...}`, and `activities/{id}/gpx/` returns
`application/gpx+xml`.

`integrations/urls.py` registers the `immich` prefix **twice**, so resolution
depends on registration order (H10).

### billing `[v]`

`GET /api/billing/subscription/` → `{stripe_subscription_id, status,
trial_ends_at, current_period_ends_at, cancel_at_period_end}`, all read-only;
`status` ∈ `trial|active|canceled|past_due`.

`create-checkout-session/` and `create-portal-session/` answer
`404 {"detail": "Cloud billing is disabled for this instance."}` when
`CLOUD_MODE=false`, `503` when Stripe env vars are missing, `409` when already
active / no customer, `502` on Stripe errors, else `200 {"url"}`.

`POST /api/billing/webhooks/stripe/` has `authentication_classes = []` and is
`@csrf_exempt`; it requires a valid `Stripe-Signature` header and answers with
**empty bodies** (503 unconfigured, 400 bad signature, 200 otherwise).

---

## 14. Contract warts register

Referenced as H*n* above. These are real findings, not style opinions.

| # | Wart | Impact |
| --- | --- | --- |
| H1 | `LocationSerializer` embeds the owner's **full user object incl. email and `is_staff`** on public, unauthenticated reads | data exposure |
| H2 | Making a collection public runs `.update(is_public=True)` over children, publishing **other members' private locations**, bypassing validation and signals | data exposure |
| H3 | `POST /api/backup/import/` wipes all your content, gated only by `confirm=yes`, unversioned, fully buffered, trusts the ZIP | destructive |
| H4 | Nested `visits` on `POST /api/locations/` is declared writable but **unusable**: `VisitSerializer.location` is `required=True`, so the natural payload gets **400** `{"visits":[{"location":["This field is required."]}]}`; supplying a `location` id to satisfy it reaches the unpopped reverse relation and gives **500**. On `update` it deletes and replaces all visits, destroying cascaded activities. `[v, runtime]` | broken field + data loss |
| H5 | **Checklist PATCH without `items` deletes every item**, and item `id` is read-only so every update recreates items with new UUIDs | data loss + unstable ids |
| H6 | `DELETE /api/itineraries/{id}/` deletes *all* visits at that location on that date, not just ones it created | data loss |
| H7 | `visitedregion`/`visitedcity` POST mutates `request.data` → **500 on form-encoded bodies**; duplicate `visitedcity` → 500 instead of 400 | JSON-only, wrong status |
| H8 | Two worldtravel endpoints query dropped fields (`Region.geometry`, `Location.type`) → **always 500** | dead endpoints |
| H9 | `ImmichIntegrationSerializer` returns `api_key` in plaintext | secret exposure |
| H10 | `immich` router prefix registered twice | ambiguous routing |
| H11 | Model-level `ValidationError` (Trail XOR, ContentImage XOR, VisitedX duplicates) surfaces as **500**, not 400 | wrong status |
| H12 | Ownership is silently reassigned to the collection/location owner on create for transportation, lodging, note, checklist, activity, trail | surprising |
| H13 | `PATCH` on content in another user's collection raises "You cannot remove the collection…" even when `collection` was never sent | false rejection |
| H14 | `PUT` bypasses the collection guards and date-cleanup that `PATCH` performs | inconsistent |
| H15 | Non-owner category change on a location is **silently ignored** (200 with the old value) | silent no-op |
| H16 | Six mutually incompatible error body shapes; auth failures returned as **400** in places; two endpoints return an **empty 403** | client complexity |
| H17 | `GET /api/notes/` always 403 — the real list is `notes/all/` | discoverability |
| H18 | `GET /api/trails/` 403s anonymously from inside `get_queryset`, unlike every sibling | inconsistent |
| H19 | `filterset_fields` on notes and checklists is dead — no filter backend installed | silently ignored params |
| H20 | `order_by` is silently ignored on `GET /api/locations/`; `exclude_*` params ignored on collections; invalid calendar `?types=` falls back to **all** types | silently ignored params |
| H21 | Almost nothing paginates; `regions/` returns ~5k rows and `countries/` ~250 in one array | payload size |
| H22 | Quota failure is **413 with scalars** on images but **400 with list-wrapped values** on attachments | inconsistent |
| H23 | `ContentImageSerializer` can serialize to `null`, so arrays contain nulls and a detail fetch can return `null` | client crash risk |
| H24 | `/media/` failures are bare **403 HTML**, never 401, never JSON | poor diagnostics |
| H25 | Production `/media/` returns a **0-byte 200** with `X-Accel-Redirect` if nginx is bypassed | confusing |
| H26 | Calendar visit query includes `is_public=True`, so **strangers' public locations appear in your calendar** | correctness |
| H27 | `search` `total` is a facet sum that can exceed reachable results; type priority overrides relevance | misleading |
| H28 | `/api/stats/counts/{username}/` and `/api/sunrise-sunset/lookup/` have no permission class; private profiles 404 rather than 403 | implicit public surface |
| H29 | `TrailSerializer` makes outbound Wanderer calls **per object** in list responses | latency |
| H30 | `/api/places/place_details/` is unthrottled while the `reverse-geocode` twin is throttled | abuse vector |
| H31 | Collection date change hard-deletes out-of-range itinerary items and days with no report | silent data loss |
| H32 | Collection ZIP export dedupes media by **basename**, silently dropping colliding files | silent data loss |

---

## 15. Coverage and confidence

**Read directly for this document** (`[v]`): `main/urls.py`, `main/utils.py`,
`main/views.py`, `main/settings.py` (REST_FRAMEWORK, throttles, storage),
`adventures/urls.py`, `adventures/permissions.py`,
`adventures/utils/pagination.py`, `adventures/utils/file_permissions.py`,
`adventures/serializers.py` (all serializers cited),
`adventures/views/{collection,itinerary,lodging,location_image,attachment,note,reverse_geocode,import_export}_view.py`,
`adventures/services/images/fetch.py`,
`adventures/services/search/global_search.py`,
`adventures/services/calendar_events.py`, `adventures/services/user_stats.py`,
`users/{views,serializers,media_utils}.py`, `worldtravel/{views,serializers}.py`,
`integrations/{serializers,urls}.py`, `integrations/views/immich_view.py`.

**Mapped via sub-agent exploration** — trust the shape, verify exact line numbers
before depending on them: `transportation_view.py`, `note_view.py`,
`checklist_view.py`, `activity_view.py`, `trail_view.py`, `stats_view.py`,
`recommendations_view.py`, `places_api_view.py`, `generate_description_view.py`,
`sunrise_sunset_view.py`, `tags_view.py`, `calendar_view.py`,
`ics_calendar_view.py`, `strava_view.py`, `wanderer_view.py`,
`endurain_view.py`, `billing/views.py`, `cloud/middleware.py`,
`utils/itinerary.py`, `utils/autogenerate_itinerary.py`.

**Not covered:** the allauth headless route set under `/auth/browser/v1/` and
`/auth/app/v1/` (third-party package, not in this repo — the frontend calls
documented in `ARCHITECTURE.md` §6.3 are the practical subset); internals of
`collection_pdf.py` and `share_image.py` beyond content types; the exact key set
of Strava/Endurain `normalize_activity` output; `SPORT_CATEGORIES` key names;
and the full nested field lists for transportation/notes/checklists/lodging
inside `data.json`.

**Never verified at runtime:** every status code and body in this document was
read from source. No request was issued. The `[i]` markers flag the claims where
that gap matters most — chiefly the 500-level failures (H4, H7, H8, H11), which
are reasoned from DRF's default exception handler and Django ORM semantics rather
than observed.

**Staleness triggers.** Re-verify if any of these change: `main/settings.py`
(`REST_FRAMEWORK`), `main/utils.py`, `adventures/urls.py`,
`adventures/serializers.py`, `adventures/permissions.py`, or any file under
`adventures/views/`.
