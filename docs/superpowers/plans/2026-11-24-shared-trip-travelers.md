# Travelers on Visits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each visit records who was there, so a shared trip counts as visited for every traveler on their own account.

**Architecture:**
- A `Visit.travelers` many-to-many field replaces "the location owner" as the person a visit counts for.
- One new service module, `adventures/services/travelers.py`, owns every rule: who can be a traveler, whose view "visited" is computed from, and detaching versus deleting.
- Views, serializers and stats call into that module.
- The frontend adds a traveler checklist to Log visit, "I was there too", an "Add to this trip's visits" action, and a keep-copies option when leaving.

**Tech Stack:** Django 5 + DRF + drf-spectacular, PostgreSQL/PostGIS; SvelteKit 2 / Svelte 5, daisyUI 5, svelte-i18n.

**Spec:** `docs/superpowers/specs/2026-11-24-shared-trip-travelers-design.md`

## Global Constraints

- Branch `feature/trip-travelers`. Commit messages have **no** `Co-Authored-By` trailer.
- **Test command (backend), called `$T` below:** from `backend/server`, with Postgres up (`docker compose -f docker/docker-compose.database.yml up -d` from the repo root) and the env vars from `.github/workflows/backend-test.yml`, run `python manage.py test <dotted.path> --verbosity=1`. Run heavy jobs one at a time, because running them in parallel crashes WSL.
- New backend tests go in `backend/server/adventures/tests/travelers/` (with `__init__.py`).
  - Build fixtures on `adventures/tests/base.py::AudienceTestBase`. It provides owner, editor, viewer, stranger, a trip with dates 2026-06-01..03, the location `self.hut` in the trip, and `self.stop` on day 1.
  - Use `as_user(user)` to sign in as someone.
- Pre-commit hook: it `git add -u`s everything under `frontend/`. Keep unrelated frontend changes out of the tree when committing.
- Frontend gate: `cd frontend && npm run format && npm run check`. New strings go in `frontend/src/locales/en.json` only.
- OpenAPI: regenerate `backend/server/openapi/schema.yaml` with a **Python 3.13** env (the local `.venv` is 3.12 and produces a schema CI rejects), then regenerate `frontend/src/lib/api/schema.d.ts` with the project's existing script.
- Terminology: in UI copy, saved items are "locations" and "visits". "Place" is used only for search results.
- Travelers are never serialized to anonymous users, guest links, or anyone who isn't the owner, a member of a collection holding the location, or a traveler on the visit.

## Review Focus

1. **Visits created by older code paths** (backup restore, importers, `activities` log-visit, `copy_location`, Immich/Strava flows) don't pass travelers, and must still count for the location owner. *Test in Task 1:* `test_visit_created_without_travelers_counts_for_owner`.
2. **An editor saves a location with its visit list** (`LocationSerializer._sync_visits`). The visits left out must detach the editor rather than delete visits other people are on. *Test in Task 5:* `test_saving_location_without_shared_visit_detaches_only_editor`.
3. **A former member is still a traveler on a place after the owner unlinks it from the collection.** It must not appear in their list or map. *Test in Task 3:* `test_traveled_place_outside_membership_not_listed`.
4. **The same person is sent twice in `traveler_uuids`, or the clicker is sent explicitly.** There's no duplicate row and no error. *Test in Task 6:* `test_log_visit_dedupes_travelers`.
5. **A collection with no dates gets "Add to this trip's visits".** Only day-plan-logged visits are touched, not an older solo visit to the same location. *Test in Task 7:* `test_add_travelers_undated_trip_only_logged_visits`.

---

### Task 1: `Visit.travelers` field, backfill, and owner default

**Files:**
- Modify: `backend/server/adventures/models/location.py` (Visit, line 50)
- Create: `backend/server/adventures/migrations/0092_visit_travelers.py`
- Create: `backend/server/adventures/services/travelers.py`
- Modify: `backend/server/adventures/signals.py`
- Test: `backend/server/adventures/tests/travelers/test_model.py`

**Interfaces:**
- Produces:
  - `Visit.travelers: ManyToManyField(User, related_name='visits_traveled', blank=True)`
  - `travelers.ensure_default_traveler(visit: Visit) -> None`: adds `visit.location.user` when the visit has no travelers
  - migration function `backfill_travelers(apps, schema_editor)`

- [ ] **Step 1: Write the failing tests**
  - `test_backfill_sets_location_owner`: create a Visit, clear its travelers, import the migration module with `importlib.import_module('adventures.migrations.0092_visit_travelers')`, and call `backfill_travelers(django.apps.apps, None)`. Assert `list(visit.travelers.all()) == [location.user]`.
  - `test_visit_created_without_travelers_counts_for_owner`: `Visit.objects.create(location=self.hut, start_date=...)`. Assert the travelers are `[self.owner]`.
  - `test_explicit_travelers_replace_default`: create the visit, then `visit.travelers.set([self.editor])`. Assert the travelers are `[self.editor]`.
- [ ] **Step 2: Run** `$T adventures.tests.travelers.test_model`. Expected: errors with `Visit has no field travelers`.
- [ ] **Step 3: Implement**
  - Add the field.
  - `makemigrations adventures --name visit_travelers`, then append a `RunPython(backfill_travelers, migrations.RunPython.noop)`. The backfill uses a bulk `through` insert: one row per visit with `user_id=location.user_id`.
  - `ensure_default_traveler`, called from a `post_save(sender=Visit, created=True)` receiver in `signals.py`.
- [ ] **Step 4: Run** `$T adventures.tests.travelers.test_model`, then `python manage.py makemigrations --check --dry-run`. Expected: tests PASS, and "No changes detected".
- [ ] **Step 5: Commit** `git commit -m "Add travelers to visits, backfilled with the location owner"`

### Task 2: Per-person "visited" rules

**Files:**
- Modify: `backend/server/adventures/utils/get_is_visited.py`
- Modify: `backend/server/adventures/services/travelers.py`
- Modify: `backend/server/adventures/models/location.py` (`is_visited_status`)
- Test: `backend/server/adventures/tests/travelers/test_visited.py`

**Interfaces:**
- Consumes: `Visit.travelers`
- Produces:
  - `is_location_visited(location, user=None) -> bool`: `user=None` means `location.user`. Same date rules as today, plus "user in the visit's travelers". Uses `visit.travelers.all()` so prefetching works.
  - `Location.is_visited_status(user=None) -> bool`
  - `travelers.visited_by(user, now=None) -> Exists`: a subquery for `Location.annotate(...)`, past visit with that user among the travelers
  - `travelers.perspective_user(request, location) -> User`:
    - returns `request.user` if authenticated and they are the owner, `is_member` of any of the location's collections, or a traveler on any of its visits
    - otherwise returns `location.user`
  - `travelers.where_ive_been_q(user) -> Q`: `Q(user=user) | (Q(visits__travelers=user) & (Q(collections__shared_with=user) | Q(collections__user=user)))`. Callers add `.distinct()`.

- [ ] **Step 1: Write the failing tests**
  - `test_visited_only_for_travelers`: a past visit with travelers `[editor]`. `is_location_visited(hut, editor)` is True, and `is_location_visited(hut, owner)` is False.
  - `test_future_visit_not_visited`
  - `test_perspective_member_sees_own`
  - `test_perspective_stranger_sees_owner`
  - `test_visited_by_annotation_matches_python`
  - `test_where_ive_been_includes_traveled_while_member`
- [ ] **Step 2: Run** `$T adventures.tests.travelers.test_visited`. Expected: FAIL.
- [ ] **Step 3: Implement** the signatures above.
- [ ] **Step 4: Run** the same module. Expected: PASS. Also run `$T adventures.tests.locations` and expect PASS, since the owner default keeps old behavior.
- [ ] **Step 5: Commit** `git commit -m "Work out visited status per person"`

### Task 3: Lists, map, stats, dashboard and calendar count traveled locations

**Files:**
- Modify:
  - `backend/server/adventures/views/locations.py` (`list` ~163, `pins` ~392)
  - `backend/server/adventures/serializers/location.py` (`get_is_visited` at ~87, ~299, ~398)
  - `backend/server/adventures/services/dashboard.py:46`
  - `backend/server/adventures/services/user_stats.py:18`
  - `backend/server/adventures/services/calendar_events.py:184`
  - `backend/server/adventures/services/visited_regions.py:16`
  - `backend/server/adventures/services/geocoding/assignment.py:31-49`
  - `backend/server/adventures/utils/query_optimization.py` (prefetch `visits__travelers`)
  - `backend/server/adventures/services/exports/pdf/data.py:307`: `is_visited_status(exporting_user)`. Thread the exporting user through from the export view.
- Test: `backend/server/adventures/tests/travelers/test_counting.py`

**Interfaces:**
- Consumes:
  - `visited_by`
  - `where_ive_been_q`
  - `perspective_user`
  - `is_location_visited(location, user)`
- Produces:
  - `travelers.mark_regions_for_travelers(location) -> None`: for each traveler on a past visit, `mark_regions_visited(user_id, [region_id])` and `mark_cities_visited(user_id, [city_id])`
  - `LocationListSerializer` and `MapPinSerializer` `is_visited` are computed with `perspective_user(request, obj)`. In `list`, the annotation is `annotated_is_visited=visited_by(request.user)`.

- [ ] **Step 1: Write the failing tests.** Setup: a past visit on `hut` with travelers `[owner, editor]`.
  - `test_editor_list_includes_hut_visited`: GET `/api/locations/` as the editor. `hut` is present, its `is_visited` is True, and `visited_count == 1`.
  - `test_editor_pins_include_hut`
  - `test_editor_stats_count_hut`: `UserStatsService().get_visited_locations_count(editor) == 1`.
  - `test_editor_dashboard_recent_has_hut`
  - `test_editor_calendar_has_visit_event`
  - `test_geocode_marks_region_for_each_traveler`: the location has a region, and `VisitedRegion` exists for both owner and editor.
  - `test_sync_visited_regions_uses_traveled`
  - `test_traveled_place_outside_membership_not_listed`: remove `hut` from the trip. The editor's list doesn't include it.
  - `test_category_filter_includes_traveled_by_name`
  - `test_public_profile_unchanged`: `users/views/public.py` still lists only owned public locations.
  - `test_pdf_marks_visited_for_exporter`: the editor exports the trip, and `hut` is marked visited in the PDF data.
- [ ] **Step 2: Run** `$T adventures.tests.travelers.test_counting`. Expected: FAIL.
- [ ] **Step 3: Implement**
  - Swap `Location.objects.filter(user=...)` for `filter(where_ive_been_q(user)).distinct()` in `list`, `pins`, dashboard and calendar.
  - Stats count `Visit.objects.filter(travelers=user, start_date__lt=cutoff)`.
  - `geocode_and_assign_location` calls `mark_regions_for_travelers` instead of marking for `location.user_id`.
  - The category filter becomes `Q(category__name__in=names) & (Q(category__user=request.user) | ~Q(user=request.user))`.
- [ ] **Step 4: Run** the module, then `$T adventures.tests.stats adventures.tests.collections adventures.tests.locations`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Count traveled locations in lists, map, stats and regions"`

### Task 4: Visit API: travelers field, candidates, join and leave

**Files:**
- Modify:
  - `backend/server/adventures/serializers/activity.py:400` (VisitSerializer, LocationVisitSerializer)
  - `backend/server/adventures/views/visits.py`
  - `backend/server/adventures/views/locations.py` (new action)
  - `backend/server/adventures/services/travelers.py`
- Test: `backend/server/adventures/tests/travelers/test_visit_api.py`

**Interfaces:**
- Produces:
  - `travelers.candidates(location) -> QuerySet[User]`: owner ∪ `shared_with` of each collection holding the location
  - `travelers.can_see_travelers(request, visit) -> bool`: owner, a member of a holding collection, or a traveler; never a guest link or anonymous
  - `travelers.set_travelers(visit, users, actor) -> None`:
    - raises `ValidationError` if anyone added isn't a candidate
    - keeps existing travelers who are no longer candidates (only they can remove themselves)
    - then calls `mark_regions_for_travelers`
  - `travelers.join(visit, user)` and `travelers.leave(visit, user) -> bool`: `leave` returns True when the visit was deleted because it had no travelers left
  - Visit JSON: read `travelers: [{uuid, username, first_name, last_name, profile_pic}]`, omitted when `can_see_travelers` is False. Write-only `traveler_uuids: list[uuid]`.
  - `GET /api/locations/<id>/traveler-candidates/` returns that same user shape
  - `POST /api/visits/<id>/join/` and `POST /api/visits/<id>/leave/` return 200 with the visit, or 204 when leaving deleted it

- [ ] **Step 1: Write the failing tests**
  - `test_create_visit_defaults_to_requester`: the editor POSTs a visit with no `traveler_uuids`, and the travelers are `[editor]`.
  - `test_editor_sets_candidates`
  - `test_non_candidate_rejected_400`: the stranger's uuid is refused.
  - `test_viewer_cannot_set_travelers_403`
  - `test_viewer_join_and_leave`
  - `test_stranger_join_404`
  - `test_editor_cannot_remove_former_member`: the editor leaves the trip and stays a traveler. The owner's PATCH without them keeps them on the visit.
  - `test_travelers_hidden_from_guest_link_and_public`
  - `test_candidates_endpoint_lists_owner_and_members`
  - `test_last_traveler_leave_deletes_visit`
- [ ] **Step 2: Run** `$T adventures.tests.travelers.test_visit_api`. Expected: FAIL.
- [ ] **Step 3: Implement**
  - In `perform_create` and `perform_update`, call `set_travelers` with `traveler_uuids`, or `[request.user]` on create when none are given.
  - The `join` and `leave` actions are allowed for members and travelers. Use `get_queryset`, extended with `Q(travelers=user)`.
  - Add `traveler-candidates` as a detail action on `LocationViewSet`, gated by `can_read_location`.
- [ ] **Step 4: Run** the module. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Let visits name their travelers"`

### Task 5: Deleting a shared visit only removes you

**Files:**
- Modify:
  - `backend/server/adventures/views/visits.py` (`perform_destroy`)
  - `backend/server/adventures/serializers/location.py:362` (`_sync_visits`)
  - `backend/server/adventures/views/itineraries.py:339` (stop delete with `confirm_delete_visits`)
  - `backend/server/adventures/services/travelers.py`
- Test: `backend/server/adventures/tests/travelers/test_delete.py`

**Interfaces:**
- Produces:
  - `travelers.remove_or_delete(visit, user, for_everyone=False) -> str`. It returns `'deleted'` or `'detached'`:
    - `for_everyone=True` is allowed only for `visit.location.user`, and raises `PermissionDenied` otherwise
    - if other travelers remain, it removes `user`
    - otherwise it deletes the visit
  - `DELETE /api/visits/<id>/?for_everyone=1`
  - `_sync_visits(location, visits_data, user)` gains `user`, and routes left-out visits through `remove_or_delete`

- [ ] **Step 1: Write the failing tests**
  - `test_editor_delete_shared_visit_detaches`: travelers `[owner, editor]`. The editor DELETEs, gets 204, the visit still exists, and its travelers are `[owner]`.
  - `test_owner_delete_for_everyone`
  - `test_editor_for_everyone_forbidden_403`
  - `test_delete_sole_traveler_deletes`
  - `test_saving_location_without_shared_visit_detaches_only_editor`
  - `test_stop_delete_confirm_visits_detaches_when_shared`
- [ ] **Step 2: Run** `$T adventures.tests.travelers.test_delete`. Expected: FAIL.
- [ ] **Step 3: Implement** by routing all three paths through `remove_or_delete` with `request.user`.
- [ ] **Step 4: Run** the module, plus `$T adventures.tests.day_plan`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Deleting a shared visit only removes you from it"`

### Task 6: Log visit with travelers, and "I was there too"

**Files:**
- Modify:
  - `backend/server/adventures/services/day_plan/visits.py` (`log_visited` :31, `log_day` :74)
  - `backend/server/adventures/views/itineraries.py` (`log_visit` :359, day `log_visit` :482)
  - the `LogVisitSerializer` definition (find it with `grep -rn "class LogVisitSerializer"`)
- Test: `backend/server/adventures/tests/travelers/test_log_visit.py`

**Interfaces:**
- Consumes: `set_travelers` and `candidates`
- Produces:
  - `log_visited(item, visit_date=None, travelers=None, actor=None) -> tuple[Visit, bool]`. `travelers` is a list of users. The final set is `{actor} ∪ travelers`.
  - On an already-logged item, the given people are added to the existing visit and `(visit, False)` is returned.
  - `log_day(collection, day, visit_date=None, travelers=None, actor=None)` passes the same list to each stop.
  - `LogVisitSerializer` gains an optional `traveler_uuids: list[uuid]`.
  - `POST .../itinerary-items/<id>/log-visit/` stays editor-only.

- [ ] **Step 1: Write the failing tests**
  - `test_log_visit_credits_clicker_and_ticked`: the editor logs with `traveler_uuids=[owner]`, and the travelers are `{editor, owner}`.
  - `test_log_visit_alone_credits_only_clicker`
  - `test_log_visit_non_collaborator_400`
  - `test_logged_stop_adds_clicker`: the owner logs, then the editor logs. The response is 200 with the same visit id, and the travelers are `{owner, editor}`.
  - `test_log_day_applies_travelers_to_each_stop`
  - `test_log_visit_dedupes_travelers`: the editor sends `[editor, owner, owner]`, which gives two travelers and no error.
- [ ] **Step 2: Run** `$T adventures.tests.travelers.test_log_visit`. Expected: FAIL.
- [ ] **Step 3: Implement** the signatures above. The views pass `actor=request.user`.
- [ ] **Step 4: Run** the module, plus `$T adventures.tests.day_plan`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Log visits for you and the people with you"`

### Task 7: "Add to this trip's visits"

**Files:**
- Modify:
  - `backend/server/adventures/views/collections/sharing.py`
  - `backend/server/adventures/services/travelers.py`
  - the serializers module used by `sharing.py`
- Test: `backend/server/adventures/tests/travelers/test_add_to_trip.py`

**Interfaces:**
- Produces:
  - `travelers.trip_visits(collection) -> QuerySet[Visit]`, the union of:
    - visits referenced by `CollectionItineraryItem.logged_visit` for this collection, and
    - if `start_date` and `end_date` are set, visits on `collection.locations` whose `start_date` falls within those dates (inclusive, by date)
  - `travelers.add_to_trip(collection, users, dry_run=False) -> dict`. It returns `{'visits': int, 'locations': int}` and records `CollectionActivity` unless it's a dry run.
  - `POST /api/collections/<id>/add-travelers/` with body `{user_uuids: [uuid]}` and query `?dry_run=1`:
    - editors only
    - every uuid must be the owner or a member, otherwise 400
    - returns 200 with the counts above

- [ ] **Step 1: Write the failing tests**
  - `test_add_travelers_dated_trip`: a visit on 2026-06-02 and an older visit on 2025-01-01, both on `hut`. Only the June visit gains the editor, and the response is `{'visits': 1, 'locations': 1}`.
  - `test_add_travelers_undated_trip_only_logged_visits`
  - `test_dry_run_changes_nothing`
  - `test_viewer_forbidden`
  - `test_non_member_uuid_400`
- [ ] **Step 2: Run** `$T adventures.tests.travelers.test_add_to_trip`. Expected: FAIL.
- [ ] **Step 3: Implement** the above, with `@extend_schema(tags=['Sharing'])` like its neighbors.
- [ ] **Step 4: Run** the module. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Add a collaborator to a trip's logged visits"`

### Task 8: Leaving keeps your history as copies

**Files:**
- Modify:
  - `backend/server/adventures/views/collections/sharing.py` (`leave` :318, member DELETE :292)
  - `backend/server/adventures/services/locations/copy.py:43`
  - `backend/server/adventures/views/locations.py:307` (`duplicate`)
  - `backend/server/adventures/services/travelers.py`
- Test: `backend/server/adventures/tests/travelers/test_leave.py`

**Interfaces:**
- Produces:
  - `copy_location(original, user, collection=None, name=None) -> Location`. `name=None` keeps the current "Copy of …" behavior.
  - `travelers.take_my_visits(original, user) -> Location`:
    - copies the location with its original name
    - copies each visit the user travels on, with dates, timezone and notes, and `travelers=[user]`
    - removes the user from the originals with `remove_or_delete`
    - calls `mark_regions_for_travelers(copy)`
  - `travelers.release_member(collection, user, keep_copies: bool) -> int`:
    - acts on the locations in the collection that `user` doesn't own and has a visit on as a traveler
    - takes copies when `keep_copies`, otherwise only detaches
    - returns the number of locations copied
  - `POST /api/collections/<id>/leave/` takes `{keep_copies: bool = true}`, plus `?dry_run=1`, which returns `{'locations': int}`
  - The owner's member DELETE always calls `release_member(..., keep_copies=True)`
  - `POST /api/locations/<id>/duplicate/` takes `take_my_visits: bool`

- [ ] **Step 1: Write the failing tests.** Setup: `hut` has a past visit with travelers `[owner, editor]`.
  - `test_leave_with_copies`: the editor owns a "Hut" (same name) with one visit. The original's travelers are `[owner]`. `get_visited_locations_count(editor) == 1`.
  - `test_leave_without_copies_detaches`: the editor has no copy and isn't on the original. The region credit stays.
  - `test_owner_removal_always_copies`
  - `test_leave_dry_run_count`
  - `test_own_linked_location_untouched`
  - `test_duplicate_take_my_visits`
  - `test_no_access_after_leave`: GET `/api/locations/<hut>/` as the editor returns 404.
- [ ] **Step 2: Run** `$T adventures.tests.travelers.test_leave`. Expected: FAIL.
- [ ] **Step 3: Implement** the above. Run `release_member` before `collection.shared_with.remove(user)`, inside `transaction.atomic`.
- [ ] **Step 4: Run** the module, then the full suite `$T adventures` (serially). Expected: PASS, apart from the known pre-existing failures listed in the background-jobs memory notes.
- [ ] **Step 5: Commit** `git commit -m "Leaving a trip keeps your visits as your own copies"`

### Task 9: API docs and schema

**Files:**
- Modify:
  - `backend/server/API.md` (a "Travelers" section: the visited-per-person rule, endpoints, delete semantics)
  - `backend/server/openapi/schema.yaml`
  - `frontend/src/lib/api/schema.d.ts`
- [ ] **Step 1:** Regenerate the schema with a Python 3.13 env (see Global Constraints), then run the CI schema check steps from `backend-test.yml`. Expected: no warnings and no diff after regeneration.
- [ ] **Step 2:** Regenerate `schema.d.ts`, then run `cd frontend && npm run check`. Expected: 0 errors.
- [ ] **Step 3: Commit** `git commit -m "Document travelers in the API"`

### Task 10: Frontend: travelers on a location's visits

**Files:**
- Modify:
  - `frontend/src/lib/types.ts:776` (`Visit`)
  - `frontend/src/lib/components/locations/LocationVisits.svelte`
  - `frontend/src/lib/components/DeleteWarning.svelte` (only if it needs a second action), or the visit delete confirm inside `LocationVisits.svelte`
  - `frontend/src/locales/en.json`
- Create: `frontend/src/lib/components/locations/TravelerPicker.svelte`

**Interfaces:**
- Produces:
  - `Visit.travelers?: TravelerSummary[]`, and `export type TravelerSummary = { uuid: string; username: string; first_name: string | null; last_name: string | null; profile_pic?: string | null }`
  - `TravelerPicker` props:
    - `candidates: TravelerSummary[]`
    - `selected: string[]` (bindable, uuids)
    - `lockedUuid?: string`: the current user, always checked

  `TravelerPicker` renders avatars using `discussion/PersonAvatar.svelte`.

- [ ] **Step 1:** On each visit, show traveler avatars.
  - Editors: show the picker, fed from `/api/locations/<id>/traveler-candidates/`, and save `traveler_uuids`.
  - Members not on the visit: show the **"I was there too"** button (`/join/`).
  - Travelers: show **"I wasn't there"** (`/leave/`).
  - Hide the picker when the candidates list is only the current user.
- [ ] **Step 2:** Delete confirm:
  - If others are on the visit, the primary button reads "Remove me from this visit".
  - The owner also sees "Delete for everyone", with the others named ("{names} will lose it too"), which sends `?for_everyone=1`.
- [ ] **Step 3:** Copy in `en.json` under `visits.*`:
  - `who_was_there`
  - `i_was_there_too`
  - `i_wasnt_there`
  - `remove_me_from_visit`
  - `delete_for_everyone`
  - `others_lose_it`
- [ ] **Step 4: Run** `cd frontend && npm run format && npm run check`. Expected: 0 errors.
- [ ] **Step 5: Commit** `git commit -m "Show and edit who was on each visit"`

### Task 11: Frontend: Log visit checklist in the trip workspace

**Files:**
- Modify:
  - `frontend/src/lib/components/collections/DayPlanRow.svelte` (~137-165, ~307)
  - `frontend/src/lib/components/collections/TripDayPlanner.svelte` (`logVisit` :609, day log :979, prop :1287)
  - `frontend/src/lib/collections/plan.ts` (a small helper for remembered picks)
  - `frontend/src/locales/en.json`
- Test: `frontend/src/lib/collections/plan.test.ts`

**Interfaces:**
- Consumes:
  - `collection.collaborators` (already serialized, `Collaborator[]` in `types.ts`)
  - `TravelerPicker`
- Produces:
  - `rememberedTravelers(collectionId: string): string[]` and `rememberTravelers(collectionId: string, uuids: string[]): void` in `plan.ts`. They use `localStorage` key `trip-travelers:<collectionId>`, and return `[]` when storage is missing or unparsable.
  - `onLogVisit(row, date?, travelerUuids?: string[])`

- [ ] **Step 1: Write the failing test** in `plan.test.ts`:
  - `rememberTravelers('c1', ['a'])`, then `rememberedTravelers('c1')` deep-equals `['a']`
  - `rememberedTravelers('missing')` deep-equals `[]`
  - corrupt JSON returns `[]`
- [ ] **Step 2: Run** `cd frontend && npx vitest run src/lib/collections/plan.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** the helpers.
  - When the collaborators other than me aren't empty, Log visit opens a small "Who went with you?" popover with the `TravelerPicker`. It's preselected from `rememberedTravelers`, filtered to current collaborators. Confirm logs the visit and calls `rememberTravelers`.
  - With no other collaborators, Log visit logs immediately, as it does today.
  - A logged row shows its travelers' avatars, which come from the visit in the log response or from `collection.locations[].visits`.
  - If the row is logged and the current user isn't among its travelers, the button reads **"I was there too"** (viewers included). It calls `/api/visits/<id>/join/`.
- [ ] **Step 4: Run** vitest on that file, then `npm run format && npm run check`. Expected: PASS and 0 errors.
- [ ] **Step 5: Commit** `git commit -m "Pick who went with you when logging a visit"`

### Task 12: Frontend: sharing, leaving, lists and deleting locations

**Files:**
- Modify:
  - `frontend/src/lib/components/collections/CollectionShareSheet.svelte` (member rows ~562)
  - `frontend/src/routes/collections/+page.svelte` (leave :245, :339)
  - the leave flow on `frontend/src/routes/collections/[id]/+page.svelte`, if it has one
  - `frontend/src/lib/components/cards/LocationCard.svelte`
  - `frontend/src/lib/components/map/MapDetailPanel.svelte`, or wherever the map pin popup names the location
  - the location delete confirm on `frontend/src/routes/locations/[id]/+page.svelte`
  - `frontend/src/locales/en.json`

- [ ] **Step 1: Share sheet.** Each member row gets "Add to this trip's visits":
  - fetch the dry run, confirm "Add {name} to the {visits} visits at {locations} locations already logged?", then POST
  - when the dry run's `visits` is 0, show a toast instead
- [ ] **Step 2: Leave dialog.**
  - Add a checkbox, checked by default: "Keep your own copies of the {count} locations you visited". `count` comes from `leave?dry_run=1`, and the checkbox is hidden when it's 0.
  - Unchecked, it adds the note "These locations will leave your map."
  - It sends `{keep_copies}`.
- [ ] **Step 3: Lists and map.** When `location.user` isn't the current user, show a small "with {owner first name or username}" badge on location cards and the map panel.
- [ ] **Step 4: Location delete warning.** When any visit has travelers other than the owner, add "{names} visited this too and will lose it from their map."
- [ ] **Step 5: Run** `npm run format && npm run check`. Expected: 0 errors.
- [ ] **Step 6: Commit** `git commit -m "Trip sharing, leaving and lists show who traveled"`

### Task 13: End-to-end check

- [ ] **Step 1:** Bring up the stack (`scripts/e2e-stack.sh up`, with nothing else heavy running). In the browser at http://localhost:8015, with two accounts:
  1. Owner logs a trip.
  2. Shares it with the second account as editor, and uses "Add to this trip's visits".
  3. Second account: the locations show visited, the world-travel countries and regions count them, and the map and list show "with {owner}".
  4. Owner logs a stop with the second account ticked, and both get the credit. The second account logs a stop alone, and only they get it.
  5. A viewer uses "I was there too".
  6. The second account deletes a shared visit, and the owner still has it.
  7. Leave with "keep copies": the copies are owned by the second account, the visited count is unchanged, and the owner's visit no longer lists them.
- [ ] **Step 2:** Run `scripts/e2e-stack.sh down`, and report what was seen, including anything that didn't match.
