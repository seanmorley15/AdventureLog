# Changelog

## [Unreleased] - 2026-02-15

### 🐛 Bug Fixes
- Fix #990: Category filter not working in v0.12.0 — replace `$:` reactive block with `afterNavigate` to prevent Svelte from resetting `typeString`; replace DaisyUI collapse with Svelte-controlled toggle to fix click interception; auto-apply filter on checkbox change for better UX
- Fix #981: Collection filter UI state resets on navigation — add `afterNavigate` callback to sync filter/sort/data state after every navigation event (same pattern as #990); fix `orderDirection` default mismatch (`asc` → `desc`); add visual indicator for active filters on mobile and sidebar; remove debug `console.log`
- Fix #891: "Adventures" → "Locations" terminology inconsistency — update 18 translation values across all 19 locale files, 2 backend error/response strings, and 1 frontend download filename to use consistent "Locations" terminology
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

### ✨ Features
- Feat #977: Cost tracking per visit — add `price` (MoneyField) to Visit model so users can record cost per visit instead of only per location; add MoneyInput to visit form with currency selector; display price in visit list and location detail timeline; keep existing Location.price as estimated/reference price
- Feat #987: Partial date support for visits — add `date_precision` field to Visit model with three levels: full date (YYYY-MM-DD), month+year (MM/YYYY), year-only (YYYY); dynamic input types, precision selector with visual feedback, `formatPartialDate()` / `formatPartialDateRange()` helpers, badges in location detail view, i18n support for all locale files
- Add Duplicate Location button (list and detail view)
- Add Duplicate Adventure button (list and detail view)

### 🔧 Improvements
- Full i18n support for all 19 languages (new keys for lodging, transportation, and adventure features)
- Enhanced error handling and user feedback in Lodging and Transportation forms
- Consistent URL validation across Locations, Lodging, and Transportation modules
- Docker Compose: Switch from `image:` to `build:` for local development builds

### 📦 Technical
- Remove internal documentation from public repository tracking
