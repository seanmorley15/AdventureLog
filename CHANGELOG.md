# Changelog

## [Unreleased] - 2026-02-10

### Bug Fixes
- Fix #888: PATCH Location with visits fails — extract `visits_data` before `setattr` loop in `LocationSerializer.update()`
- Fix #991: Wikipedia/URL image upload fails — add server-side image proxy (`/api/images/fetch_from_url/`) with SSRF protection
- Fix #617: Cannot change adventure from Private to Public — persist `is_public` in serializer update
- Fix #984: Lodging "Continue" button doesn't progress UI — add `res.ok` checks, error toasts, double-click prevention (`isSaving` state)
- Fix: Location creation fails with broken image display — add content-type checks in server actions
- Fix: Invalid URL handling for Locations, Lodging, and Transportation — silently set invalid URLs to `null` instead of blocking save
- Fix: World Map country highlighting colors — update CSS from `bg-*-200` to `bg-*-400` for visibility
- Fix: Clipboard API fails in HTTP contexts — add global polyfill for non-secure contexts
- Fix: `MultipleObjectsReturned` for duplicate images — change `get()` to `filter().first()` in `file_permissions.py`
- Fix: AI description generation ignores user language setting — pass `lang` parameter from frontend locale to Wikipedia API
- Fix: Missing i18n keys for Strava activity toggle buttons — add `show_strava_activities` / `hide_strava_activities` translations

### Features
- Add Duplicate Location button (list and detail view)
- Add Duplicate Adventure button (list and detail view)

### Improvements
- Full i18n support for all 19 languages (new keys for lodging, transportation, and adventure features)
- Enhanced error handling and user feedback in Lodging and Transportation forms
- Consistent URL validation across Locations, Lodging, and Transportation modules

### Technical
- Switch `docker-compose.yml` from `image:` to `build:` for frontend and backend
- Remove internal documentation from public repository tracking
