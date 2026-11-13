#!/usr/bin/env node
/**
 * Captures the app screenshots used on the docs homepage, in the app's light
 * and dark themes, from a running AdventureLog instance.
 *
 *   cd frontend
 *   APP_URL=http://localhost:5174 APP_USER=demo APP_PASSWORD=... \
 *     node ../documentation/scripts/capture-screenshots.mjs /tmp/shots
 *   ../documentation/scripts/optimize-images.sh shots /tmp/shots
 *
 * Run it from frontend/ so Playwright resolves from frontend/node_modules.
 * Output: <dir>/{light,dark}/<name>.png at 2880x1800 (1440x900 @2x).
 *
 * The trip and place are looked up by name, so any account works as long as
 * it has them: override with SHOT_TRIP and SHOT_PLACE.
 *
 * Headless Chromium on a bare Linux box has no emoji font and an odd default
 * UI font, so the script loads Noto Color Emoji and Inter as web fonts from
 * documentation/node_modules. The app itself is not modified.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(path.join(process.cwd(), "/"))(
  "@playwright/test",
);

const out = path.resolve(process.argv[2] ?? "screenshots-out");
const APP = (process.env.APP_URL ?? "http://localhost:8015").replace(/\/$/, "");
const USER = process.env.APP_USER ?? "demo";
const PASSWORD = process.env.APP_PASSWORD;
const TRIP = process.env.SHOT_TRIP ?? "Japan in Autumn";
const PLACE = process.env.SHOT_PLACE ?? "Reinebringen";
if (!PASSWORD) {
  console.error("Set APP_PASSWORD.");
  process.exit(1);
}

const docs = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const emojiDir = path.join(docs, "node_modules/@fontsource/noto-color-emoji");
const interDir = path.join(
  docs,
  "node_modules/vitepress/dist/client/theme-default/fonts",
);
const FONT_HOST = "http://fonts.capture.local";
let fontCss = "";
if (fs.existsSync(emojiDir) && fs.existsSync(interDir)) {
  fontCss =
    fs
      .readFileSync(path.join(emojiDir, "emoji.css"), "utf8")
      .replace(/url\(\.\/files\//g, `url(${FONT_HOST}/emoji/files/`) +
    `@font-face{font-family:'InterUI';font-weight:100 900;src:url(${FONT_HOST}/inter/inter-roman-latin.woff2) format('woff2')}` +
    `*{font-family:'InterUI',ui-sans-serif,system-ui,sans-serif,'Noto Color Emoji' !important}`;
} else {
  console.warn(
    "Fonts not found (run pnpm install in documentation/); using system fonts.",
  );
}

const browser = await chromium.launch();

async function context(theme, storageState) {
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: theme,
    storageState,
  });
  await ctx.addCookies([{ name: "colortheme", value: theme, url: APP }]);
  await ctx.route(`${FONT_HOST}/**`, (route) => {
    const p = new URL(route.request().url()).pathname;
    const file = p.startsWith("/inter/")
      ? path.join(interDir, p.slice(7))
      : path.join(emojiDir, p.slice(7));
    route.fulfill({
      path: file,
      contentType: "font/woff2",
      headers: { "access-control-allow-origin": "*" },
    });
  });
  return ctx;
}

// Sign in once, then reuse the session for both themes.
const loginCtx = await context("light");
const login = await loginCtx.newPage();
await login.goto(`${APP}/login`, { waitUntil: "networkidle" });
await login.fill('input[name="username"]', USER);
await login.fill('input[name="password"]', PASSWORD);
await Promise.all([
  login.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 30000 }),
  login.click('button[type="submit"]'),
]);
const find = (endpoint, name) =>
  login.evaluate(
    async ([endpoint, name]) => {
      const res = await fetch(`/api/${endpoint}/?page_size=1000`);
      const data = await res.json();
      return (
        (data.results ?? data).find((item) => item.name === name)?.id ?? null
      );
    },
    [endpoint, name],
  );
const tripId = await find("collections", TRIP);
const placeId = await find("locations", PLACE);
if (!tripId || !placeId) {
  console.error(
    `Could not find trip "${TRIP}" or place "${PLACE}" in this account.`,
  );
  process.exit(1);
}
const session = await loginCtx.storageState();
await loginCtx.close();

/** name, path, settle time in ms, optional step before the capture */
const shots = [
  ["locations", "/locations", 5000],
  ["place", `/locations/${placeId}`, 6000],
  ["collections", "/collections", 5000],
  // Open the plan on a day with stops, not the trip-wide notes at the top.
  ["trip", `/collections/${tripId}?day=${process.env.SHOT_DAY ?? 3}`, 8000],
  ["map", "/map?lat=28&lng=35&zoom=2.4", 8000],
  [
    "world",
    "/worldtravel",
    4000,
    async (page) => {
      await page
        .getByRole("button", { name: /Show Map/ })
        .first()
        .click();
      await page.waitForTimeout(7000);
    },
  ],
  ["calendar", "/calendar", 5000],
  ["dashboard", "/dashboard", 5000],
];

for (const theme of ["light", "dark"]) {
  fs.mkdirSync(path.join(out, theme), { recursive: true });
  const ctx = await context(theme, session);
  const page = await ctx.newPage();
  for (const [name, url, settle, step] of shots) {
    await page.goto(APP + url, { waitUntil: "networkidle", timeout: 60000 });
    if (fontCss) await page.addStyleTag({ content: fontCss });
    await page.waitForTimeout(settle);
    if (step) await step(page);
    await page.screenshot({ path: path.join(out, theme, `${name}.png`) });
    console.log(`${theme}/${name}`);
  }
  await ctx.close();
}

await browser.close();
