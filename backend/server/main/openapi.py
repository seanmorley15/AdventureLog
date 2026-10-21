"""The title, introduction, and tag list of the OpenAPI document (``SPECTACULAR_SETTINGS``)."""

TITLE = 'AdventureLog API'

VERSION = '1.0.0'

DESCRIPTION = """
The AdventureLog API is what the AdventureLog web app itself uses. Everything here is
available to your own scripts and integrations.

## Base URL

Every endpoint lives under `/api/` on your AdventureLog domain, for example
`https://adventurelog.example.com/api/locations/`. Paths end with a slash.

## Authentication

Send **one** of these with each request:

| Method | How | Notes |
|---|---|---|
| API key | `X-API-Key: al_…` | Create keys in **Settings → Security**. Best for scripts. |
| API key | `Authorization: Api-Key al_…` | The same key in the standard header. |
| Session | the `sessionid` cookie set by `POST /api/auth/browser/v1/auth/login` | Used by the web app. Requests that change data must also send `X-CSRFToken` with the token from `GET /api/auth/csrf/`. |

```bash
curl https://adventurelog.example.com/api/locations/ -H "X-API-Key: al_your_key"
```

An invalid key is rejected with `401` and is not combined with a session. Endpoints marked
with no lock in this page work without signing in; most of them show more when you are
signed in (for example a public collection versus your own).

In the interactive docs, click **Authorize** and paste an API key, or sign in to the web app
in the same browser.

## Errors

Every error is JSON with the same shape:

```json
{"detail": "Location not found.", "code": "not_found"}
```

Validation errors (`400`) add `fields`, with the messages for each input:

```json
{"detail": "name: This field is required.", "code": "validation_error",
 "fields": {"name": ["This field is required."]}}
```

`detail` is safe to show to people. `code` is stable and meant for programs. Some errors add
context next to them, for example the storage numbers on `413 media_quota_exceeded`.

| Status | Meaning |
|---|---|
| 400 | The request was not valid (`validation_error`, or a specific code). |
| 401 | Not signed in (`not_authenticated`) or a bad API key (`authentication_failed`). |
| 402 | Hosted (cloud) servers only: the account needs a subscription (`subscription_required`). |
| 403 | You can see the resource but may not do this (`permission_denied`). |
| 404 | It does not exist, or you cannot see it (`not_found`). |
| 409 | It conflicts with the current state, e.g. it already exists (`conflict`). |
| 413 | The upload would exceed your media storage (`media_quota_exceeded`). |
| 429 | Too many requests (`throttled`). Servers can turn on rate limits. |
| 502 / 503 / 504 | An outside service (a map provider, Immich, Strava…) failed, is not set up, or timed out. |

## Lists and pagination

Lists that can grow without bound are paged with `?page=` and `?page_size=` (at most 1000)
and return

```json
{"count": 120, "next": "…?page=2", "previous": null, "results": [ … ]}
```

Search and picker endpoints take `?limit=` and `?offset=` and return `{"count", "results"}`.
Lists that belong to one parent (the days of a trip, a collection's comments) are returned
whole, as an array.

Sort with `?ordering=field` (ascending) or `?ordering=-field` (descending) where an
endpoint lists the fields it accepts. Booleans in query strings are `true` or `false`.

## Collections, trips and the day plan

A **collection** groups places and plans. A collection of type `trip` has a **day plan**:
numbered days (`/api/collections/{id}/days/`) and **itinerary items** that place a location,
lodging, transportation, note or checklist on a day, in the trip-wide list, or in Ideas
(`/api/collections/{id}/itinerary-items/`). Collections can be shared with other users
(roles `editor` and `viewer`) and through guest links.

## Uploads and downloads

Uploads use `multipart/form-data` (images, attachments, GPX files, backups). Downloads
(PDF, PNG share cards, zip archives, iCalendar, GPX) return the file with a
`Content-Disposition` header.

## Sign-in endpoints

`/api/auth/browser/v1/…` and `/api/auth/app/v1/…` are provided by django-allauth's headless
API and answer in its own format (`{"status", "data", "meta"}` or `{"status", "errors"}`).
The **Authentication** section documents the ones the web app uses.
"""

TAGS = [
    {'name': 'Authentication', 'description': 'Sign in and out, sign up, passwords, two-factor authentication, '
     'and what the sign-in screens need to know first.'},
    {'name': 'Account', 'description': 'The signed-in user: profile, settings, API keys, storage, deletion.'},
    {'name': 'Users', 'description': 'Public profiles of other users.'},
    {'name': 'Locations', 'description': 'Places you have been or want to go.'},
    {'name': 'Visits', 'description': 'Dated visits to a location.'},
    {'name': 'Activities', 'description': 'Recorded activities (a hike, a ride) with optional GPX tracks.'},
    {'name': 'Trails', 'description': 'Links to trails, optionally from a Wanderer server.'},
    {'name': 'Categories & tags', 'description': 'Your location categories and the tags used on your locations.'},
    {'name': 'Collections', 'description': 'Folders and trips that group places and plans.'},
    {'name': 'Sharing', 'description': 'Invites, members and their roles, and guest links for a collection.'},
    {'name': 'Comments', 'description': "Discussion on a collection's plan or story, and your comment inbox."},
    {'name': 'Day plan', 'description': 'The days of a trip and the items placed on them.'},
    {'name': 'Trip items', 'description': 'Lodging, transportation, notes and checklists.'},
    {'name': 'Media', 'description': 'Images and file attachments on any record.'},
    {'name': 'Places', 'description': 'Search, geocoding, descriptions and recommendations from map providers.'},
    {'name': 'Calendar', 'description': 'Your visits, stays and trips as calendar events or an iCalendar file.'},
    {'name': 'Search', 'description': 'Search across everything you can see.'},
    {'name': 'Dashboard', 'description': 'The home screen summary.'},
    {'name': 'Backup', 'description': 'Export and restore your whole account.'},
    {'name': 'World travel', 'description': 'Countries, regions and cities, and which of them you have visited.'},
    {'name': 'Integrations', 'description': 'Immich, Strava, Wanderer and Endurain.'},
    {'name': 'Billing', 'description': 'Subscriptions on hosted (cloud) servers.'},
    {'name': 'Server', 'description': 'Information about this server.'},
]
