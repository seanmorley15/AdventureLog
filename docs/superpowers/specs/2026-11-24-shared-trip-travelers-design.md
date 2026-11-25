# Shared trips: travelers on visits

## Context

A user logged a trip they took with their wife, then made her an account and shared the collection with her. She can *see* every place, but none of them count as visited for her: no visited badge, no countries or regions, no dashboard stats. Open request #420 (with duplicate #899) asks for the same thing.

The cause is in the model. `Visit` (`adventures/models/location.py:50`) has no user field. It belongs to a `Location`, and each location has one owner (`Location.user`). Every "visited" calculation works from `location.user`. A location created inside a shared collection is owned by the collection owner (`views/locations.py:211`), so when an editor clicks **Log visit** in the workspace, the owner gets the credit and the person who clicked gets nothing.

Collection roles (editor/viewer via `CollectionMember`), invites, leave and remove already exist and are not being redesigned.

**Intended outcome:** ownership of a place and who visited it become two separate facts. A place keeps one owner. A visit records **who was there**, and each traveler gets the credit on their own account. Leaving a trip never takes away a past visit.

## Goals
- A trip logged once credits everyone who went: visited badge, countries, regions, cities, dashboard, stats, calendar, map and Locations list.
- **Travelers live on the visit** *(decided by Sean)*. When you log a visit, you're on it, and you tick the collaborators who went with you. There's no trip-wide traveler list.
- The #420 case (a trip logged before she joined) takes one action: "Add Mia to this trip's visits".
- Leaving or being removed is predictable. It's a clean break from the owner's trip, and you keep your history as your own copies.
- Nobody can erase someone else's visit by accident.

## Non-goals
- Changing collection roles, invites or guest links.
- Per-traveler notes, ratings or photos on a shared visit. Travelers share the visit, and anyone who wants their own can keep a copy.
- Carrying travelers through backup export/import. A backup holds your own visits; other people's are dropped on restore.
- Tagging people who aren't on the trip. There is no friend graph.

## Anti-goals (a failure even if it works)
- Someone is credited with a visit they never agreed to be part of. Travelers must already be members of the collection.
- Who traveled with whom is shown to the public. Travelers are visible only to the owner, collection members, and the travelers themselves.
- The owner loses their own "visited" because someone else logged a visit or removed themselves from one.
- Duplicate places appear without the user asking for copies.

## Approaches considered
1. **Stats-only credit.** The visit gets travelers, and only the counts and region credit change. Rejected: her map and Locations list stay empty after the trip, which feels broken.
2. **A copy for each traveler.** Logging creates a place owned by each person. Rejected: duplicates drift apart, and photos and notes get split.
3. **Travelers on visits, one owner per place, places shown in each traveler's list (chosen).** This touches more queries, but it's the only option that is both intuitive and keeps a single source of truth. Copies happen only when someone asks for them (when leaving, or "Make my own copy").

## Design

### Data
- `Visit.travelers = ManyToManyField(User, related_name='visits_traveled', blank=True)`.
- No change to `Collection`. Travelers are only ever stored on visits.
- Migration: backfill every existing visit with `travelers = [location.user]`. After this, no existing behavior changes.

### What "visited" means
- A location is visited **for user U** when it has a visit with `start_date <= today` that has U among its travelers. This replaces `is_location_visited(location)` with `is_location_visited(location, user)`. Add a matching `visited_by_q(user)` / `Exists` helper for querysets, next to `adventures/utils/get_is_visited.py`.
- **Whose view is used:**
  - If the request user is the owner, a member of a collection holding the place, or a traveler on it, use the request user.
  - Otherwise (public views, public profile) use the location owner.
  - PDF export uses the exporting user.
- Every visit always has at least one traveler. The last traveler leaving deletes the visit, and an edit that would leave nobody is refused with 400.

### Deleting a shared visit *(decided by Sean)*
- If a visit has travelers other than the person deleting it, **"Delete" only removes that person** from the visit. The visit and everyone else's credit stay.
- **Only the location owner** can delete a shared visit for everyone. They get a warning naming the other travelers first (e.g. a `?for_everyone=1` flag on DELETE).
- A visit whose last traveler removes themselves is deleted.
- This applies to every path that deletes visits:
  - `VisitViewSet.perform_destroy` (`views/visits.py:89`)
  - visits dropped when a location is saved with its visit list (`LocationVisitSerializer` handling in `serializers/location.py`)
  - removing a stop with `confirm_delete_visits` (`views/itineraries.py:339`)
  - un-logging a stop

  Each one detaches the person rather than deleting when others remain.

### Who can change travelers
- Only the owner, plus the members (any role) of a collection that contains the location, can be candidates.
- If a location is in no shared collection, the only candidate is its owner, and the picker is hidden.
- **Anyone who can edit the location** (owner, or an editor of a containing collection) can add or remove any *current candidate*. Travelers who are no longer candidates are kept on the visit and can't be removed by an editor. Only the traveler can remove themselves. *(My call.)*
- **Any member, viewers included, and any current traveler** can add or remove *themselves* with "I was there too" / "I wasn't there". This only affects their own account.
- A new visit with no travelers given defaults to `[request.user]`. Visits made through the plain API therefore credit the creator, which matches today's behavior for owners.

### Region and city credit
- When a past visit is created, or its dates or travelers change, mark the location's region and city as visited for **each traveler**.
- Change `geocode_and_assign_location` (`services/geocoding/assignment.py:41,48`) so it marks regions and cities for the travelers of past visits instead of `location.user_id`.
- `sync_visited_regions(user)` (`services/visited_regions.py:16`) iterates locations where the user is a traveler on a past visit.
- Removing a traveler never un-marks a region. That matches today: region rows are manual-sticky.

### Queries switching from "I own it" to "I own it or I traveled there"
Builder: grep `Location.objects.filter(user`, `location__user` and `is_visited_status` and decide each one by this rule:
- **Visited counts** and **where I've been** include traveled places.
- **What I manage** (edit, suggest-to-add, tags, categories, account export) stays owned-only.

Known ones:
- `LocationViewSet.list` (`views/locations.py:163`): owned ∪ traveled. `annotated_is_visited` becomes per-user. The category filter matches by name for places owned by others.
- `pins` (`views/locations.py:392`): owned ∪ traveled, `is_visited` per user.
- `services/dashboard.py:46`: recent visited, owned ∪ traveled.
- `services/user_stats.py:18` `get_visited_locations_count`: `Visit.objects.filter(travelers=user, ...)`.
- `services/calendar_events.py:184`: visit events where the user is a traveler.
- `users/views/public.py:40`: the public profile still shows only owned public places.
- Serializer `is_visited` fields (`serializers/location.py:87,299,398`): per user, using the view rules above.
- Access: no change to `can_read_location` or `retrieve_locations`. Being a traveler doesn't grant access on its own. Traveled places appear in your list only while you are the owner or a member of a collection holding them. Leaving is a clean break, and copies are how you keep your history (below).

### API
- `VisitSerializer` (`serializers/activity.py:400`):
  - Read `travelers: [{uuid, username, first_name, last_name, profile_pic}]`. Only included for viewers allowed to see travelers (owner, collection members, travelers). Omitted on public and guest-link views.
  - Write `traveler_uuids`, validated against the candidates. Only editors can set it.
- `GET /api/locations/<id>/traveler-candidates/`: owner plus members of the collections holding the place. It feeds the picker.
- `POST /api/visits/<id>/join/` and `POST /api/visits/<id>/leave/`: add or remove yourself. Allowed for members and travelers.
- **Log visit** (`views/itineraries.py:359`, `services/day_plan/visits.py:31 log_visited`, `log_day` at :74):
  - Travelers are `{request.user}` plus any collaborators ticked in `traveler_uuids`. `log_day` takes the same list for every stop it logs.
  - If the stop already has a logged visit, add `request.user` (and any given travelers) to it, and return 200 with the updated visit. This is the "I was there too" path.
  - Editing stays editor-only. Viewers use `visits/<id>/join/`.
- `POST /api/collections/<id>/add-travelers/` `{user_uuids}` (editors; collaborators on the trip only). This is the one-time fix for a trip logged before someone joined. It adds those people to **this trip's** existing visits. That means:
    - visits logged from its day plan (`CollectionItineraryItem.logged_visit`), plus
    - visits on its locations dated within the collection's start/end, when it has dates.

    It never touches all visits on a location, so an earlier solo visit to the same place isn't credited. *(My call.)*
  - It returns the number of visits and places it affected. A `?dry_run=1` variant gives the count for the confirm dialog.
- **Leaving and removal** (`views/collections/sharing.py:318 leave`, `:292 member DELETE`). Leaving is a clean break. *(Decided by Sean: she chooses to keep copies when leaving.)*
  - `leave` accepts `keep_copies: bool`, and the dialog defaults it to on. For each place in the collection they don't own that has a visit with them as a traveler:
    - Copy it to their account with `copy_location` (`services/locations/copy.py:43`), using the original name, not "Copy of …". Photos come along as the existing copy already does.
    - Copy *their* visits onto it with `travelers=[them]`.
  - Either way, they are then removed from the original visits on places they don't own, so nothing is counted twice and they leave no trace in the owner's trip. A visit left with no travelers is deleted.
  - Region and city credit already marked for them stays, because those rows are kept per user.
  - **Removal by the owner** does the same with `keep_copies` always on. The removed person never chose to leave, so they keep their history. *(My call.)*
  - Places they own and linked into the collection are untouched and stay theirs, as today.
- `duplicate` (`views/locations.py:307`) gains `take_my_visits: bool`, the same move for a single place, for a current member who wants their own copy before leaving.
- Record collection activity (`record_activity`) when travelers are added to visits.
- Update `backend/server/API.md` and regenerate the OpenAPI schema / `frontend/src/lib/api/schema.d.ts`.

### UI (frontend)
- **Location page visits** (`lib/components/locations/LocationVisits.svelte`): traveler avatars on each visit. Editors get a picker (from candidates). Members not on a visit get an "I was there too" button, and travelers get "I wasn't there".
- **Workspace stop row and Log day** (`lib/components/collections/DayPlanRow.svelte`, `TripDayPlanner.svelte:609,979`):
  - **Log visit** opens a small "Who went with you?" checklist of the trip's collaborators. You are pre-checked but may uncheck yourself (2026-11-25), as long as someone is checked.
  - The checklist remembers your last picks for this trip in the browser, so logging a whole trip together is one click per stop. *(My call.)*
  - After logging, the row shows the avatars of who it was logged for.
  - If the stop is logged but the viewer isn't on it, the button reads **"I was there too"**.
  - When the trip has no other collaborators, there's no checklist, and Log visit behaves as it does today.
- **Sharing panel, per member:** "Add to this trip's visits" opens a confirm: "Add Mia to the 23 visits at 18 places already logged?" This is the one-action fix for #420.
- **Leave dialog** (`routes/collections/+page.svelte:245,339`): a checkbox, on by default, "Keep your own copies of the N places you visited". N comes from a dry-run count. If it's unchecked, a note says those places will leave your map.
- **Visit delete confirm:** if others are on the visit, the button reads "Remove me from this visit". The owner also gets "Delete for everyone (Mia loses it too)".
- **Locations list and map:** traveled places appear with a small "with {owner name}" badge and are read-only unless the user is an editor.
- **Location delete confirm:** if other people traveled there, warn: "Mia was there too and will lose this place from her map."
- Locale strings in `frontend/src/locales/en.json`. Other locales fall back.

### Left to the builder
- Whether `travelers` uses a through model (e.g. to record `added_by`). A plain M2M is enough unless notifications need it.
- The exact layout of the "Who went with you?" checklist.
- Query performance: prefetch travelers in `optimize_locations` (`utils/query_optimization.py`), and keep the `Exists` subqueries indexed.
- The MCP project (`../AdventureLogMCP`) and the docs site: follow-up, not this change.

## Delivery
1. Commit this design to `docs/superpowers/specs/2026-11-24-shared-trip-travelers-design.md`, then invoke `superpowers:writing-plans` to produce the step-by-step plan.
2. Work on a feature branch off `development` (e.g. `feature/trip-travelers`). Write tests first (TDD) in `backend/server/adventures/tests/` (new `travelers/` package, following `tests/collections` and `tests/day_plan`). Use `factories.py`.

## Verification
- Backend tests (in the app container, run serially (heavy jobs crash WSL when run in parallel)):
  - backfill migration
  - per-user visited
  - candidates and permissions (an editor sets travelers; a viewer can only join or leave themselves; a non-member is refused)
  - log visit with ticked collaborators (the clicker is pre-checked but may be unchecked; see the 2026-11-25 note below; non-collaborators are refused), and the "I was there too" path
  - add-travelers: only this trip's visits, with dry-run counts
  - leave with and without `keep_copies` (no double counting, detached from the originals, no access to the owner's places afterwards)
  - owner removal always copies
  - deleting a shared visit detaches the person instead of deleting it, owner-only delete-for-everyone, and the same rule for stop removal and un-logging
  - region marking for each traveler
  - travelers hidden on public and guest views
- `python3 manage.py makemigrations --check` and the schema check. `cd frontend && npm run format && npm run check`.
- Manual end to end at http://localhost:8015, with two accounts:
  1. Owner logs a trip.
  2. Shares it with the second account as editor, then uses "Add to this trip's visits" for them.
  3. Second account: places show visited, countries and regions count, the map and Locations list show them "with owner".
  4. Owner logs a new stop with the second account ticked, and both get the credit. The second account logs a stop alone, and only they get it.
  5. A viewer uses "I was there too".
  6. Leave with "keep copies": the copies are owned by the second account and stats are unchanged (no double count). The owner's place no longer lists them.

> **Changed 2026-11-25:** "the clicker is always included" no longer holds. Log visit and Log day pre-check you but you may uncheck yourself to record a visit for someone else. The only rule is at least one traveler: an explicit `traveler_uuids` list is exactly who is credited (an empty list is a 400), and an omitted list means you alone.
