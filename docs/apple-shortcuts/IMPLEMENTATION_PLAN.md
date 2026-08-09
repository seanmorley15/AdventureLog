# Apple Shortcuts Integration — Implementation Plan

**Feature:** let iPhone users log locations and visits in the moment via Apple
Shortcuts calling the AdventureLog REST API, with an offline queue for failures.

**Companion documents:**

- `docs/apple-shortcuts/API_CONTEXT.md` holds the API analysis this plan is built
  on. Read it first, or attach it to a fresh session.
- `docs/architecture/API_CONTEXT.md` is the project-wide HTTP contract — check it before
  assuming an endpoint behaves like the ones in this plan.
- `docs/architecture/ARCHITECTURE.md` is the whole-project reference — useful for the sections
  of this plan that touch permissions, deployment, or CI.

**Status:** not started. This is a plan, no code has been written.

---

## 1. Framing

The API already supports every one of the seven proposed shortcuts. Nothing in
the backend blocks the happy path. That reframes the work:

- **Most of the effort is documentation and distribution**, not code.
- **The backend changes are optional but high-leverage** — each one removes a
  limitation the feature request itself lists as known.
- **One backend item is a genuine bug** (nested visits on create) and should land
  regardless of whether the Shortcuts feature ships.

Three premises in the original request should be revisited before building:

1. **On a default self-hosted install, API keys do not survive a restart.** This
   is a hard blocker for the whole feature and it is not the shortcut author's
   fault. See A0 — it moved to the front of workstream A.
2. **The Google Cloud / Places API key prerequisite is avoidable.** AdventureLog
   already proxies place search, place details and reverse geocoding using the
   server's `GOOGLE_MAPS_API_KEY`, and falls back to OpenStreetMap when it is
   unset. Using those endpoints drops the prerequisites from three credentials to
   one and makes the shortcuts work on instances with no Google key at all.
3. **Seven iCloud share links are not a maintainable deliverable.** They are
   unversioned, unreviewable, and break silently. See §5.

There is also an existing pairing mechanism the request does not mention —
`/auth/mobile-qr/` already mints an `al_` key and packages it with the server URL
into a QR code. See D5.

---

## 2. Workstreams

| ID | Workstream | Depends on | Ships independently? |
| --- | --- | --- | --- |
| A | Backend fixes and small features | — | yes |
| B | Documentation guide | A (for accuracy) | yes |
| C | Shortcut authoring / rework | A, decision D1 | no |
| D | Distribution and ownership decisions | — | blocking for C |

Recommended order: **D → A → B → C.** Settle the distribution question first;
it changes how much of C is worth doing.

---

## 3. Workstream A — backend

### A0. `SECRET_KEY` rotation silently invalidates every API key — **blocker**

This was originally filed under "do not do" as a documentation concern. That was
wrong, and it is the most consequential item in this plan.

**Problem.** `APIKey._hash_raw_key` salts its PBKDF2 hash with
`f"users.APIKey:{settings.SECRET_KEY}"` (`backend/server/users/models.py:108-117`),
so every stored key hash is bound to `SECRET_KEY`. Meanwhile:

- `.env.example` (the Standard deployment template) **never sets `SECRET_KEY`** —
  it appears only inside a comment at `:10` claiming it is "derived at startup".
- `docker/aio/env-setup.sh:30-31` generates a fresh
  `secrets.token_urlsafe(50)` whenever it is unset.

So on the **default** Standard install, every `docker compose restart` /
`up -d` / image pull mints a new `SECRET_KEY`, which invalidates every session
**and every API key**. A user's Shortcuts stop working with a bare `401`, with no
indication why, and the fix ("generate a new key and paste it into Variables
again") is not discoverable. `.env.advanced.example:24` does set it, so Advanced
deployments are unaffected. `[v]`

**Why this outranks everything else here:** the entire feature is an API-key
client. Shipping it against a deployment default that expires keys on restart
generates support load that looks like a Shortcuts bug and is not one.

**Options, roughly in order of preference:**

1. Have `env-setup.sh` **persist** a generated `SECRET_KEY` (write it back to the
   mounted env file or a volume) instead of regenerating per boot. Cleanest fix,
   touches deployment only.
2. Set `SECRET_KEY` in `.env.example` with a clear "change me" placeholder and make
   `scripts/validate-env.sh` error when it is missing or still the placeholder.
   The installer already prompts for a Postgres password, so it can prompt here too.
3. **Decouple key hashing from `SECRET_KEY`** — use a dedicated, persisted salt, or
   a per-row random salt stored alongside the hash. Most correct, but it is a
   migration on `users.APIKey` and needs its own discussion.
4. Documentation only: warn in the guide and in `api_keys.md`. Cheapest, and the
   worst outcome — it leaves the default broken.

**Recommendation:** (1) or (2) before the Shortcuts guide ships publicly. At
minimum, the guide must not be published without (4).

**Files:** `docker/aio/env-setup.sh`, `.env.example`, `scripts/validate-env.sh`,
and `documentation/docs/configuration/api_keys.md`.

**Acceptance:** restart the Standard stack twice and confirm a previously issued
`al_` key still authenticates.

---

### A1. Nested `visits` on `POST /api/locations/` is unusable — **recommended**

**Corrected 2026-08-09 by running it against a live stack.** The first draft called
this a straight 500 and "a genuine bug that should land regardless." The real
behaviour is worse-shaped than that, and the severity is lower. Both outcomes
observed, not inferred:

| Payload | Result |
| --- | --- |
| `visits: [{start_date: ...}]` — the natural thing a client sends | **400** `{"visits":[{"location":["This field is required."]}]}` |
| `visits: [{start_date: ..., location: "<some existing uuid>"}]` | **500** |

**Why.** `VisitSerializer.location` is `required=True` (verified by introspecting
the serializer's fields on the running container), so nested validation fails
before `create()` is ever reached — hence the 400. The `TypeError: Direct
assignment to the reverse side of a related set is prohibited` path described in
the first draft is real, but only reachable once you satisfy `location` with an
id, which is nonsensical when the point is to create a *new* location.

So the field is **declared writable and cannot be used at all**: the sane payload
is rejected with a misleading error naming a field the client cannot possibly
know, and the payload that satisfies the validator crashes.

**Revised severity.** This is a broken writable field, not a crash bug in the
common path. It no longer "should land regardless" on 500 grounds — but the 400 is
actively misleading and the 500 is still reachable, so it is worth fixing.

**Change.** Two parts now, because of the `location`-required finding:

1. Make `location` **not required in the nested context** — either declare
   `visits` with a nested-specific serializer where `location` is `read_only`, or
   pass `required=False` for that field when nested. Without this, the 400 stands
   and popping `visits` in `create()` changes nothing.
2. In `LocationSerializer.create`, pop `visits` alongside `category` and
   `collections`, then create the `Visit` rows with `location=<the new location>`
   after it is saved. Delegate to `VisitSerializer` so `ensure_aware_utc` and the
   `end_date` defaulting at `serializers.py:487-491` are applied consistently
   rather than reimplemented.

Also decide what happens if a client supplies a *conflicting* `location` inside a
nested visit. Silently overwriting it with the new location is probably right;
whatever you choose, it must not reach `Location.objects.create()` unpopped, which
is what produces the current 500.

**Also.** After creating visits, call
`background_geocode_and_assign(str(location.id))` the way
`VisitViewSet.perform_create` does (`adventures/views/visit_view.py:38-50`, the
call itself at `:50`).
Without it, the location will have a visit but no `VisitedRegion` /
`VisitedCity`, because `Location.save()`'s own background pass ran before any
visit existed (`adventures/models.py:24-62`).

**Decide.** `update()` currently deletes and replaces all visits when `visits` is
provided (`serializers.py:694-729`, the replacement at `:724-728`). That is worse
than it first looks: `Activity` rows cascade off `Visit`, so a PATCH carrying a
`visits` array **also destroys every activity attached to those visits** — GPX
files, Strava imports, the lot. Either keep it and document it loudly, or leave
`update` alone and only change `create`. Recommendation: only change `create` in
this pass; changing `update` semantics is a separate, breaking discussion, and
the activity cascade should be raised in it.

**Files:** `backend/server/adventures/serializers.py`

**Acceptance:**
- `POST /api/locations/` with `visits: [{start_date: ...}]` and **no** nested
  `location` returns 201 (today: 400), and the response `visits` array is
  populated with real ids.
- `POST` with a nested `location` id returns 201 or 400 — **never 500**.
- `is_visited` in that same response is `true` when the visit `start_date` is in
  the past.
- A `VisitedRegion` row exists for the location's region afterwards. Note this
  requires the worldtravel tables to be populated; with `SKIP_WORLD_DATA=1` they
  are empty and no region can ever resolve, so test with the dataset loaded.
- Existing behaviour with no `visits` key is unchanged.

**Removes:** the "visit logging requires a location ID" limitation for the
create-time case, and collapses two shortcut network calls into one.

---

### A2. Radius filtering on locations — **recommended**

**Problem.** No geographic filtering exists anywhere in the backend (verified by
grep for `dwithin`, `distance_lte`, `bbox`, `Distance(`). `Location.coordinates`
is a real PostGIS `PointField(srid=4326)`, so this is cheap to add.

**Change.** Add `?lat=`, `?lon=`, `?radius_km=` to a locations list route using
`django.contrib.gis.db.models.functions.Distance` or a `dwithin` lookup.

**Prefer a new `@action(detail=False)` named `nearby`** over bolting the params
onto `filtered/`. The earlier draft of this plan suggested `filtered/` because it
already parses params and paginates, but that route **requires `types=`** to be
either `all` or a list of existing category names for the caller, returning
`400 {"error": "Invalid category or no types provided"}` otherwise
(`location_view.py:317-335`). A duplicate-detection client would have to pass a
meaningless `types=all` on every call. Bare `list` is also a poor host: it ignores
every query param except pagination, so adding some there would be inconsistent.

**Validate** all three params, cap `radius_km` (suggest 50 km) to prevent
full-table distance scans, and return 400 on malformed input. Reuse
`coerce_coordinate` from the quick-add utils for range checking.

**Files:** `backend/server/adventures/views/location_view.py`, plus a test.

**Acceptance:**
- A location 1 km away is returned for `radius_km=5`; one 100 km away is not.
- Missing or non-numeric params → 400, not 500.
- `radius_km` above the cap → 400 or silently clamped, documented either way.

**Removes:** the "no duplicate detection" limitation. Until this lands, the
client-side workaround is `GET /api/locations/pins/` (`id, name, latitude,
longitude, is_visited, category`, unpaginated) plus local distance math — which
is painful to express in Shortcuts, so A2 has real user value here.

---

### A3. Accept a category id on `POST /api/locations/` — **optional**

`LocationSerializer.validate_category` (`serializers.py:634-644`) only accepts a
nested object with a `name`. `quick-add` already normalizes an id **or** an
object via `_normalize_quick_add_category`
(`adventures/views/location_view.py:675-718`). Align them so a client can send
`{"category": "<uuid>"}` or `{"category": {"id": "<uuid>"}}`.

Skip this if the shortcuts target `quick-add` instead. Keep the get-or-create by
name behaviour intact either way — it is what lets a shortcut send a brand-new
category name without a round trip.

**Acceptance:** all three forms (uuid string, `{"id": ...}`, `{"name": ...}`)
resolve correctly; an id belonging to another user returns 400, not a leak.

---

### A4. Coordinate range validation on the plain create path — **optional, small**

`CoordinateSerializerMixin` (`adventures/utils/serializer_geo_fields.py:22-45`)
enforces only that latitude and longitude arrive together. There is no -90/90 or
-180/180 check; that lives solely in `quick-add`'s `coerce_coordinate`. Move the
range check into the mixin so every write path benefits.

**Acceptance:** `{"latitude": 999, "longitude": 0}` returns 400 with a field
error.

---

### A5. Inbound Google Maps URL resolution — **optional, larger**

Nothing in the backend parses inbound `maps.app.goo.gl` / `goo.gl/maps` /
`google.com/maps` URLs (verified by grep; the only matches construct outbound
links in the frontend). A server-side resolver would let the shortcut pass a
shared link straight through and get a location back.

**Caveats before committing to this:**
- It means the server follows arbitrary user-supplied redirects. Needs SSRF
  protection: allowlist hostnames, cap redirects, block private address ranges.
- Google's short-link and URL formats are undocumented and change. This is
  ongoing maintenance.
- Apple Maps links would be a separate parser.

**Recommendation:** defer. Keep URL decoding in the shortcut for v1, where
breakage is the shortcut author's problem rather than a server CVE.

---

### A6. Do not do

- **API key scopes / expiry.** Real gap (`users/models.py:76-151` has neither),
  but out of scope. Note it separately — and see §9 question 3, since a phone-held
  key with full account power and no TTL is a fair thing to challenge.
- **Reworking the error-body conventions.** The backend uses six mutually
  incompatible shapes and returns some auth failures as `400` (see
  `docs/architecture/API_CONTEXT.md` §1.8 and H16). Tempting to clean up while here; don't —
  it is a breaking change for the frontend and unrelated to this feature. The
  shortcuts should branch on **status code only**, which sidesteps it.

---

## 4. Workstream B — documentation

### B1. New guide page

**File:** `documentation/docs/guides/apple_shortcuts.md`

Sections to cover:

1. **Prerequisites** — an AdventureLog instance, one API key. Explicitly state
   that a personal Google Cloud key is *not* required if the instance has
   `GOOGLE_MAPS_API_KEY` configured, and that place search degrades to
   OpenStreetMap otherwise.
2. **Generating the key** — Settings → Security, shown once, link to
   `configuration/api_keys`.
3. **Header format** — `X-API-Key: al_...` (preferred) or
   `Authorization: Api-Key al_...`.
4. **The endpoints the shortcuts use**, with request/response examples. Copy the
   curl block from `API_CONTEXT.md` §10.
5. **Ordering caveat** — create location, then create visit; `city`/`region`/
   `country` come back `null` on the create response because geocoding is async.
6. **Trailing slashes are mandatory** (DRF `DefaultRouter`).
7. **Rate limits** — `ENABLE_RATE_LIMITS` is off by default; when on,
   `external_geocode` is `120/minute`, so place search and reverse geocode are
   the throttled calls.
8. **Installing the shortcuts** — links, the Variables setup step, the Notes
   document for the offline queue. If D5 = yes, document the QR pairing path too.
9. **Known limitations** — carry over the four from the request, updated for
   whatever A1/A2 actually shipped.
10. **Security note** — the key carries the full permissions of the account, has
    no expiry and cannot be scoped; revoke from Settings → Security if a device
    is lost.
11. **Troubleshooting** — this section is what stops the support load:
    - **Everything returns 401 after a server restart.** If A0 has not shipped,
      explain the `SECRET_KEY` rotation and how to pin it. This will be the single
      most common report.
    - **402 with `{"detail": "Subscription required."}`** — only on the hosted
      product, and only for a lapsed subscription. `GET /auth/current-user/` is the
      way to check `has_access` without touching `/api/`.
    - **404 on a URL that looks right** — a missing trailing slash on a POST.
    - **Do not parse error bodies.** Six different shapes exist and some auth
      failures come back as `400`; branch on status code.
12. **Response size note** — `POST /api/locations/` echoes the full location
    including a nested user object (with your own email) and every image and
    collection. For bulk reads prefer `GET /api/locations/pins/`.

### B2. Register the page

- Sidebar: `documentation/.vitepress/config.mts`, Guides block at `:364-372`,
  alongside `{ text: "Admin Panel", link: "/docs/guides/admin_panel" }`.
- SEO metadata: `documentation/.vitepress/seo.ts`, following the
  `docs/guides/admin_panel.md` entry at `:209+`.

### B3. Cross-link and correct `api_keys.md`

**File:** `documentation/docs/configuration/api_keys.md`

- Add a link to the new guide as a worked example.
- **Fix the stale claim** in Security Notes: it says "only a SHA-256 hash is
  kept". The implementation is PBKDF2-HMAC-SHA256 at 600,000 iterations
  (`backend/server/users/models.py:108-117`).
- Consider adding that rotating `SECRET_KEY` invalidates all existing keys.

### B4. Optional: `swagger_auto_schema` on the three ViewSets

`/docs/` is `drf-yasg` with auto-derived schemas and no decoration on
`LocationViewSet` / `VisitViewSet` / `CategoryViewSet`, so its output is thin and
misleading for external integrators. Decorating just the create actions would
make the API self-documenting for the next person building a client. Nice-to-have,
not blocking.

---

## 5. Workstream D — decisions needed before C

These are maintainer calls, not code. **C is blocked until D1 and D2 are
answered.**

**D1. Where do the shortcuts live?**
Options:
- (a) Docs page links to iCloud share URLs, with a version column.
- (b) Exported files committed to a `contrib/apple-shortcuts/` folder, docs link
  to the repo.
- (c) Both — repo as the source of truth, iCloud links as the convenient install
  path.

Recommendation: (c). iCloud links rot and cannot be diffed or reviewed; a
committed copy gives provenance and a rollback point.

**D2. Who maintains them?**
Nothing in CI can exercise an Apple Shortcut. When the API changes, these break
silently and the first signal is a user issue. Decide whether this ships as
first-party (maintainers own it) or community-contributed (docs page carries a
"community maintained, may lag" banner and names the author).

**D3. Do the shortcuts target `/api/locations/` or `/api/locations/quick-add/`?**
`quick-add` does reverse geocoding, category id-or-name normalization,
range-validated coordinates, optional collection/itinerary assignment and remote
photo import server-side — significantly less logic in the shortcut. Its cost is
the `ExternalGeocodeThrottle` (120/minute) and a different response shape.
Recommendation: `quick-add`, unless A1 lands and single-call location+visit via
plain create turns out to be simpler.

**D4. Does the Google API key prerequisite stay?**
Recommendation: drop it, use `/api/places/search/` and
`/api/reverse-geocode/reverse_geocode/`. Cost: rework of the Upload from Google
Maps shortcut, since the proxy response shape differs from raw Places API (New).
Note `/api/places/search/` changes its top-level type based on `include_meta` — a
bare array without it, an object with it — and returns a bare `[]` with **status
200** when the provider errors. Pass `include_meta=true` so failures are
detectable.

**D5. Should setup use the existing QR pairing flow instead of pasted credentials?**
`/auth/mobile-qr/` already exists and is purpose-built for exactly this: `POST`
mints an `al_` key named `Mobile App - <date>` and returns a base64 PNG whose
payload is `{"version": 1, "server_url", "api_key", "code_words": ["hike","explore"]}`
(`users/views.py:334+`). One scan would replace "paste your base URL and API key
into Variables."

Constraints to weigh:
- **One key per user by convention.** `POST` refuses with
  `400 {"detail": "Mobile API key already exists. Please delete the existing one first."}`
  when a key whose name starts with `"Mobile App -"` exists. So Shortcuts would be
  competing with the native mobile app for the same slot.
- Shortcuts can scan a QR, but decoding this payload adds parsing logic that
  pasting two strings does not.
- It does nothing about A0 — a rotated `SECRET_KEY` invalidates the QR-minted key
  just the same.

Recommendation: keep manual paste for v1 and note the QR flow as a future
convenience, unless the maintainers want Shortcuts to share the mobile-app slot.
Worth asking, because it affects whether that "one key" convention should become a
real constraint or be relaxed.

---

## 6. Workstream C — shortcut work

Only meaningful after D.

**Two constraints that apply to every shortcut:**

1. **Branch on HTTP status code, never on the error body.** The backend uses six
   incompatible error shapes, returns some auth failures as `400`, and answers two
   endpoints with an empty `403` body. Status codes are the only reliable signal.
2. **Distinguish "offline" from "rejected" in the Log shortcut.** A network failure
   and a `400`/`401`/`403` need different handling — the first belongs in the
   offline queue for replay, the second will fail identically forever and should
   surface to the user instead. Queueing a rejected payload guarantees the Manual
   Upload shortcut replays it into the same rejection.

Sketch of what changes per shortcut:

| Shortcut | Change implied by this plan |
| --- | --- |
| Variables | Drop the Google Maps API key field if D4 = drop. Keep base URL + AdventureLog key. |
| Select Category | `GET /api/categories/` is unpaginated, so no paging logic needed. Can also be skipped entirely — a name is get-or-created on write. |
| Upload from Current Location | Single call to `quick-add` (or plain create with nested `visits` if A1 lands). |
| Upload from Google Maps | If D4 = drop, replace direct Places API calls with `GET /api/places/search/`. URL decoding stays client-side unless A5 ships. |
| Upload Visit | Unchanged: `POST /api/visits/` with `location`, `start_date`, optional `end_date`/`timezone`/`notes`. Becomes optional if A1 lands and the visit is created inline. |
| Log | Unchanged. Append-to-Notes offline queue. |
| Manual Upload | Unchanged. Replays from the log. |

---

## 7. Verification

### A7. Know which URL the shortcuts actually talk to — **no code, but affects C and B**

Discovered by testing the running Standard ("aio") stack. On the single published
port, nginx routes only `/static/`, `/media`, `/admin` and `/accounts` to Django.
**Everything else — including `/api/` — goes to the SvelteKit frontend**, which
serves `/api/[...path]` as a *proxy* to Django (`frontend/src/lib/server/django-proxy.ts`).

Observed consequences, all against `http://localhost:8015`:

| Request | Result | Why |
| --- | --- | --- |
| `GET /api/categories` + `X-API-Key` | **200** | API keys pass through the proxy fine |
| `GET /api/categories/` (trailing slash) | **308** → `/api/categories` | SvelteKit normalizes, *then* the proxy re-adds the slash for Django |
| `GET /docs/` | **404** | Swagger is Django-only, unreachable on this port |
| `GET /csrf/` | **404** | same |
| `GET /health/` | **308** → `/health` | the SvelteKit health route, not Django's |

Three things follow for this feature:

1. **Tell users to omit the trailing slash** in the shortcuts, or enable redirect
   following. `docs/architecture/API_CONTEXT.md` says slashes are mandatory — true
   against Django directly, but through the published port the slashless form is
   the one that avoids a 308. Shortcuts' "Get Contents of URL" does follow
   redirects, so this is a latency and confusion issue rather than a hard failure.
2. **Every API call pays a CSRF round-trip.** The proxy calls `GET /csrf/` on the
   backend for *every* proxied request. Harmless for correctness with API-key auth
   (the token is ignored), but it doubles the backend round-trips per shortcut
   action. Worth knowing before blaming the network on a slow phone.
3. **Advanced deployments differ.** There the backend is published separately, so
   `/api/` hits Django directly and `/docs/` works. The guide should not assume one
   topology — ask users for their AdventureLog URL and let both work.

---

### Reproduce A1 first

```bash
BASE=http://localhost:8015           # Standard/aio stack; note: no trailing slash on the path
KEY=al_...                           # Settings -> Security, or mint one via manage.py shell

# (a) the natural payload -> 400 today
curl -s -L -X POST "$BASE/api/locations" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"name":"probe A","latitude":63.88,"longitude":-22.45,
       "visits":[{"start_date":"2026-01-05T14:00:00Z"}]}'
# observed: {"visits":[{"location":["This field is required."]}]}

# (b) satisfying `location` with an existing id -> 500 today
curl -s -L -o /dev/null -w '%{http_code}\n' -X POST "$BASE/api/locations" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"name":"probe B","latitude":63.88,"longitude":-22.45,
       "visits":[{"start_date":"2026-01-05T14:00:00Z","location":"<existing-uuid>"}]}'
# observed: 500
```

Both were observed on a live stack on 2026-08-09. If (a) returns 201 the fix has
already landed; if (b) returns anything other than 500, re-read
`serializers.py:674-692` before changing anything.

### Reproduce A0 second

```bash
# with the Standard stack running and a key issued
docker compose restart app
curl -i "$BASE/api/categories/" -H "X-API-Key: $KEY"
```

Expected on a default `.env` (no `SECRET_KEY` set): **401**. If it still returns
200, check whether `SECRET_KEY` is set in the environment — A0 only bites when it
is absent and therefore regenerated.

### After each change

```bash
# happy path, end to end
curl -s "$BASE/api/categories/" -H "X-API-Key: $KEY"
curl -s -X POST "$BASE/api/locations/" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"Blue Lagoon","latitude":63.88,"longitude":-22.45,
       "category":{"name":"nature","display_name":"Nature","icon":"🏞"}}'
curl -s -X POST "$BASE/api/visits/" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"location":"<id>","start_date":"2026-01-05T14:00:00Z","timezone":"Europe/Athens"}'

# then confirm: is_visited flipped true, and a VisitedRegion row exists
```

### Automated tests

Add to `backend/server/adventures/tests/`:

- `POST /api/locations/` with nested `visits` → 201, visits present, region visited.
- `POST /api/locations/` without `visits` → unchanged behaviour (regression guard).
- Radius filter: inside / outside / bad params.
- Category resolution by id, by `{"id":...}`, by name, and another user's id → 400.
- Coordinate range rejection.

### CI gap — read this before claiming coverage

`.github/workflows/backend-test.yml` **does not run the test suite.** It installs
deps, starts the PostGIS compose stack, migrates, backgrounds `runserver`, and
curls `/`. That is a boot smoke test.

So any test written above is unprotected until a step is added that actually
invokes `manage.py test`. Adding that step is arguably the highest-value item in
this whole plan, and it is a separate PR — turning it on repo-wide may surface
pre-existing failures, which should not be tangled up with this feature.

Local runs need PostGIS and GDAL (`python3-gdal`); a bare `manage.py test`
without them fails on the GIS backend.

---

## 8. Suggested PR breakdown

| PR | Contents | Risk |
| --- | --- | --- |
| 0 | **A0 `SECRET_KEY` persistence** + `validate-env.sh` guard + docs | touches deployment defaults; needs maintainer buy-in on which option |
| 1 | A1 nested visits fix + tests | low, but touches a shared serializer used by the frontend |
| 2 | A2 `nearby` radius action + tests | low, additive |
| 3 | A3 + A4 category id and coordinate validation + tests | low, additive |
| 4 | B1–B3 documentation | none |
| 5 | CI: actually run the backend test suite | may surface unrelated pre-existing failures |
| 6 | C shortcuts + `contrib/` folder, per D1 | no code risk, ongoing maintenance cost |

**PR 0 gates the public release of PR 4** — publishing a guide that tells people to
paste an API key, on a deployment whose default silently invalidates it, is worse
than publishing nothing.

PRs 0–4 are independently useful even if the Shortcuts feature is never merged;
PR 0 fixes a bug affecting every API-key and session user, not just Shortcuts.

---

## 9. Open questions to take to the maintainers

1. **A0 first: which fix for `SECRET_KEY`?** Persist a generated value, require it
   in `.env.example` + `validate-env.sh`, or decouple key hashing from it
   altogether. This is the one question that blocks a public guide.
2. D1–D5 above, with D5 (reuse `/auth/mobile-qr/`, and whether the one-key
   `"Mobile App -"` convention should be relaxed) being new.
3. Should `LocationSerializer.update`'s delete-and-replace visits behaviour be
   changed, or documented as-is? Note it also destroys `Activity` rows cascading
   off those visits, which may make this a bug rather than a design choice.
4. Is there appetite for API key scopes / expiry as a follow-up? An automation
   key on a phone currently has full account power and no TTL.
5. Should `GET /api/locations/` start honouring `order_by` (it silently ignores
   it today because `apply_sorting` is not called from `list`), or is that
   intentional?

---

## 10. Revision note

Revised 2026-08-09 after the project-wide audits that produced
`docs/architecture/ARCHITECTURE.md` and `docs/architecture/API_CONTEXT.md`. Changes from the first draft:

- **A0 added** and promoted to blocker. `SECRET_KEY` rotation was previously a
  footnote under "do not do"; the deployment audit showed the Standard install
  regenerates it on every boot, so it invalidates API keys by default.
- **A1 premise corrected by live testing** — it is a 400 (`location` required in
  the nested serializer), not the 500 the first draft claimed; the 500 needs a
  pathological payload. Severity and fix both revised.
- **A7 added** — on the Standard stack `/api/` is served by the SvelteKit *proxy*,
  not Django, which changes trailing-slash guidance and adds a CSRF round-trip per
  call. `/docs/` and `/csrf/` are unreachable on that port.
- **A2 redirected** from `filtered/` to a new `nearby` action, because `filtered/`
  hard-requires a valid `types=` parameter.
- **A1** now notes that the `update` path destroys cascaded `Activity` rows, not
  just visits.
- **D5 added** — `/auth/mobile-qr/` already implements QR-based key pairing.
- **Workstream C** gained the status-code-only and offline-vs-rejected constraints.
- **B1** gained a troubleshooting section and a response-size note.
- **PR 0 added** and made a gate on releasing the guide.
- Line references corrected: `serializers.py:675-693`→`:674-692`,
  `:723-728`→`:694-729` (replacement at `:724-728`),
  `visit_view.py:47-50`→`:38-50`, `users/models.py:76-152`→`:76-151`.
