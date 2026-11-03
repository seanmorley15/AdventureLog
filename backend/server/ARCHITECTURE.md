# Backend architecture

The backend is a Django REST Framework API (`backend/server/`). This page says where things live, which way
dependencies point, and how to find your way from a URL to the code and its tests.

## The apps

| App | What it owns |
|---|---|
| `core` | Helpers with no knowledge of any app: geo and date maths, parsing, caching, pagination, the outbound HTTP rules (`net.py`), base serializers, the API's error handling (`errors.py`, `exceptions.py`), its schema generation (`openapi.py`) and routers (`routers.py`), shared test helpers (`testing.py`). |
| `worldtravel` | Countries, regions, cities and which of them a user has visited. |
| `adventures` | The product: places, collections, trips and their day plan, transport, lodging, notes, media, comments, sharing, backups. |
| `users` | Accounts, sign-in and API keys, public profiles, invitations. |
| `integrations` | Immich, Strava, Wanderer and Endurain. |
| `billing`, `cloud` | Stripe and hosted-mode access. Only active in cloud deployments. |
| `main` | The project: settings, root URLs, sessions. |

Dependencies point **down** this list: `main` -> `cloud`/`billing` -> `users`/`integrations` -> `adventures` ->
`worldtravel` -> `core`. `.importlinter` enforces it in CI (`lint-imports`). There are two deliberate
exceptions, both listed there: `adventures` reaches `integrations` only through `integrations/facade.py`,
and a place embeds its owner's profile from `users.serializers`.

## Inside `adventures`

```
urls.py            routes, one router entry per resource
views/             thin: read the request, check permission, call a service, return a response
serializers/       how records look over the API, grouped by area
permissions.py     DRF permission classes, built on access/
access/            who may read or change what (collection roles, guest links, file access)
services/          the work: anything that touches several models, files, or other servers
providers/         one module per outside service we call (Google, OpenStreetMap, Wikipedia, ...)
models/            the models, grouped by area (a package; import from adventures.models)
utils/             small pure helpers with no database writes and no HTTP
admin/             Django admin, one module per area
management/        management commands (snake_case names)
```

**Where does new code go?**

- A *view* should only translate between HTTP and a function call. If it has a loop over records, it belongs in a service.
- A *service* raises a domain error (`DayPlanError`, `QuickAddError`, `BackupError`, `IntegrationError`, all
  `core.errors.ServiceError`). `core.exceptions.api_exception_handler` turns it into the API's error body and
  status. Services do not import DRF.
- A *provider* only talks to one outside service and returns data (`core.results.ProviderResult`). No database.
- A *util* has no side effects.

The larger features are packages:

| Package | Purpose |
|---|---|
| `services/day_plan/` | The day-by-day trip planner. Layered from `errors`, `constants`, `dates` up through `registry`, `ordering`, `spans`, then `conversion`, `days`, `placement`, `visits`. |
| `services/backup/` | The whole-account backup and the single-collection archive. One exporter and one restorer serve both. |
| `services/exports/` | The printable PDF and the share image. |
| `services/geocoding/` | Reverse geocoding: provider choice, naming a place, matching it to a region and city. |
| `services/quick_add.py` | Creating a place or lodging from a map pin. |

## Tracing an endpoint

The API's conventions, its documentation, and how to add an endpoint are in [API.md](API.md).

Take `POST /api/collections/<id>/duplicate/`:

1. `main/api_urls.py` mounts `adventures.urls`, which registers `collections` -> `CollectionViewSet`.
2. `adventures/views/collections/viewset.py` -> `duplicate`. Sharing actions live in `sharing.py`, downloads in `exports.py`.
3. `adventures/services/collections/duplicate.py` -> `duplicate_collection`.
4. Tests: `adventures/tests/collections/test_collection_duplicate.py`.

Routes that live inside one collection are nested viewsets: `POST /api/collections/<id>/days/` is
`CollectionDayViewSet.create` in `adventures/views/itineraries.py`, registered with the prefix
`collections/(?P<collection_id>...)/days`.

Views are named after their resource (`views/trails.py` -> `TrailViewSet`), and tests mirror the area of the code
they cover.

## Rules that are easy to break

**Calling other servers.** Never use bare `requests` for an address a user typed.

- `core.net.public_session()` for a URL anyone can supply, such as importing a photo from a link. It refuses
  anything but the public internet, and checks the address it actually connects to, so DNS tricks fail.
- `core.net.self_hosted_session()` for a server the user runs (Immich, Wanderer, Endurain). LAN addresses are
  fine; cloud-metadata and link-local addresses never are.
- `integrations/services/server_urls.py` cleans up and validates those server URLs when they are saved.

Calls to a fixed vendor (Google, OpenStreetMap, Wikipedia, Strava) can use plain `requests`.

**The day plan runs inside migrations.** `services/day_plan/registry.py` fetches models with `apps.get_model` so data
migrations can run the engine against historical models. Keep the package `__init__` free of imports of
`adventures.models`; `files.py` and `legacy.py` do import them, which is why they are imported by path.

**The backup format is a promise.** A file written today must still import tomorrow. To add a field, add it to
`exporter.py` and `restorer.py` (tolerate it being absent), then regenerate the golden files with
`REGEN_GOLDEN=1` and read the diff. Bump `BACKUP_SCHEMA` (`utils/collection_type.py`) only when old files need
different handling.

**Account details are private.** `PRIVATE_USER_FIELDS` in `users/serializers.py` are for the signed-in user only. Use
`without_private_fields` whenever someone else's account is shown, as a place does for its owner.

## Tests

```
adventures/tests/   access/  backup/  collections/  day_plan/  geocoding/  locations/
                    media/  providers/  search/  stats/
core/tests/         integrations/tests/ (immich, strava, wanderer, endurain)
users/tests/        worldtravel/tests/   main/tests/   billing/tests/   cloud/tests/
```

Shared setup is in plain modules, never imported from another test file: `core/testing.py` (`make_user`),
`adventures/tests/factories.py` (`build_rich_account`: one account that touches every record type),
`adventures/tests/base.py` and `adventures/tests/day_plan/base.py`.

```
DJANGO_SETTINGS_MODULE=main.test_settings python manage.py test                       # everything
DJANGO_SETTINGS_MODULE=main.test_settings python manage.py test adventures.tests.backup  # one area
```

Add `--parallel 4` to go faster; install `tblib` too, or a failure inside a worker shows no traceback.

## Checks that run in CI

- `python manage.py test` - includes `core/tests/test_references.py`, which resolves every import, every
  `mock.patch` target and every dotted path in the settings. Write patch targets out in full so it can read them.
- `lint-imports` - the dependency rules above.
- `flake8` (config in `.flake8`) - unused and undefined names.
- `python manage.py makemigrations --check` - a refactor must not change the schema.
- `python manage.py spectacular --file openapi/schema.yaml --validate --fail-on-warn`, then `git diff --exit-code` -
  the API documents every endpoint and the committed schema is current (see [API.md](API.md)).
