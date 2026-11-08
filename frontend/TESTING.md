# Testing the frontend

Three layers, all run from `frontend/`:

| Layer                           | Command               | What it covers                                                   |
| ------------------------------- | --------------------- | ---------------------------------------------------------------- |
| Unit (Vitest, node)             | `pnpm test:unit`      | Pure logic in `src/lib/**`, `hooks.server.ts`, locale key checks |
| Component (Vitest browser mode) | `pnpm test:component` | Single components mounted in real Chromium (`*.svelte.test.ts`)  |
| E2E (Playwright)                | `pnpm test:e2e`       | Whole user journeys against the production all-in-one image      |

`pnpm test` runs unit + component. `pnpm test:coverage` writes a unit coverage report to `coverage/`.

## Running the E2E suite

```sh
scripts/e2e-stack.sh up      # builds the AIO image, starts it with Postgres on :8015
cd frontend
pnpm exec playwright install chromium   # first time only
pnpm test:e2e                # or pnpm test:e2e:ui to debug
scripts/e2e-stack.sh down    # delete the stack and its data
```

- `E2E_SKIP_BUILD=1` reuses an existing image. `E2E_BASE_URL` points the suite at any running instance.
- The stack uses its own compose project and `.e2e/` env file, and pins the settings the tests rely on
  (no email verification, registration open, rate limits off). It never reads your development `.env`.
- Each Playwright worker signs up its own user through the real `/signup` page, so tests are
  isolated and can run in parallel without resetting the database.
- Projects: `chromium-desktop` runs everything; `chromium-mobile` (Pixel 7) runs only specs tagged `@mobile`.

## Writing a spec

Import `test` and `expect` from `e2e/fixtures.ts`, not from `@playwright/test`. The fixtures give you:

- `account`: the signed-in worker user (storage state is applied automatically).
- An automatic **broken-UI guard**: a test fails on an uncaught JS error, a `console.error`
  (minus the allowlist in `e2e/support/guard.ts`), any `/api` 5xx, or a raw translation key on screen.
  A test that deliberately provokes errors sets `test.use({ allowBrokenUI: true })`.
- Stubbed external network (map styles, images, geocoding), see `e2e/support/network.ts`.
  The suite does not hit the internet.

Guidelines:

- Prefer `getByRole` / `getByLabel`. Modals are a `<dialog>` wrapping an inner `role=dialog`, so
  use `.last()` or find them by heading.
- Journeys (`e2e/specs/journeys/`) start from a new account and do everything through the UI;
  wrap each phase in `test.step`.
- Use `test.fail()` to pin a known app bug. The test turns red once the bug is fixed, which is your
  cue to remove the marker.
- Helpers for the location wizard and trip planner live in `e2e/support/`.

## CI

- `frontend-test.yml`: lint, API types, `svelte-check`, unit coverage, component tests, build.
- `frontend-e2e.yml`: builds the AIO image once, runs the suite in 3 shards, merges the HTML report
  (artifact `playwright-report`).
