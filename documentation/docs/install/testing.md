# Testing 🧪

The Playwright end-to-end suite lives in `frontend/tests/e2e` and drives the real app in a browser. It runs against the Standard Deployment image built from your working tree, so it exercises the same nginx, SvelteKit and Django wiring users get.

## Prerequisites

- Docker with the Compose plugin
- Node.js 22 and pnpm (`corepack enable` picks up the version pinned in `frontend/package.json`)

## Running the suite

```bash
cd frontend
pnpm install
pnpm exec playwright install chromium

pnpm e2e:up      # build the image and start it on http://localhost:8017
pnpm test:e2e    # run the suite
pnpm e2e:down    # stop the stack and drop its volumes
```

`pnpm e2e:up` layers `docker/docker-compose.e2e.yml` over the root `docker-compose.yml`. The stack uses its own project name, container names and port, so it can run beside a normal local instance. World data is skipped so it boots in seconds, and the usual `admin` / `admin` superuser is created on first boot.

`pnpm test:e2e:ui` opens the Playwright UI for stepping through a spec. A failed run writes an HTML report to `frontend/playwright-report` and traces to `frontend/test-results`.

## Running against another instance

Set `PLAYWRIGHT_BASE_URL` to point the suite somewhere else:

```bash
PLAYWRIGHT_BASE_URL=http://localhost:8015 pnpm test:e2e
```

The instance needs an `admin` / `admin` user and rate limits off (`ENABLE_RATE_LIMITS=false`, the default). Tests delete the data they create, but run them against a throwaway database anyway.

## Writing tests

- Put specs in `frontend/tests/e2e/*.spec.ts` and import `test` and `expect` from `./fixtures`, not from `@playwright/test`.
- Specs start logged in as `admin`; `auth.setup.ts` logs in once and the session is reused. Use `test.use({ storageState: { cookies: [], origins: [] } })` for logged-out flows.
- Seed data through the `api` fixture, which goes through the SvelteKit `/api` proxy with the browser session. Anything it creates is deleted after the test.
- Requests to hosts other than the app are blocked, so specs never depend on map tiles, geocoding or Wikipedia. Prefer the details step of the location modal over the Quick Start map.
- Prefer `getByRole` and `getByLabel` with the English strings from `src/locales/en.json`; the suite pins the browser locale to `en-US`.
- New spec files are type-checked by `pnpm check` and formatted by `pnpm format`.

## CI

`.github/workflows/e2e-test.yml` builds the image, starts the stack and runs the suite on pull requests and pushes that touch the frontend, backend or Docker files. The HTML report is uploaded as a workflow artifact.
