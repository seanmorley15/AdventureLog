/**
 * Real app screenshots and travel photos served from /public.
 *
 * Screenshots are captured from a running instance in both app themes
 * (scripts/capture-screenshots.mjs) and encoded by scripts/optimize-images.sh.
 * Files: /screenshots/<name>-<light|dark>-<width>.<avif|webp>
 */
export const SITE_ORIGIN = "https://adventurelog.app";

export const SHOT_WIDTHS = [800, 1440, 2200];
export const SHOT_SIZE = { width: 2200, height: 1375 };

export type Theme = "light" | "dark";

export const shots = {
  locations:
    "AdventureLog locations page: a grid of locations with photos, categories, ratings, and visited status",
  place:
    "A location in AdventureLog: Reinebringen, Norway, with photos, rating, visit, trail, tags, and description",
  collections:
    "AdventureLog collections: trips and folders such as Island Escapes, US National Parks, and Australia East Coast",
  trip: "Day 3 of the Japan in Autumn trip in AdventureLog: the hotel stay and timed stops around Tokyo beside a route map",
  map: "AdventureLog map of visited and planned locations across Europe, Africa, and Asia",
  world:
    "AdventureLog world travel page: 51 of 250 countries visited, shown on a world map",
  calendar:
    "AdventureLog calendar with a trip's stops, transport, and lodging laid out by day",
  dashboard:
    "AdventureLog dashboard with countries visited, locations logged, and the current trip",
} as const;

export type ShotName = keyof typeof shots;

export function shotSrcset(
  name: ShotName,
  theme: Theme,
  format: "avif" | "webp",
): string {
  return SHOT_WIDTHS.map(
    (w) => `/screenshots/${name}-${theme}-${w}.${format} ${w}w`,
  ).join(", ");
}

export function shotFallback(name: ShotName, theme: Theme): string {
  return `/screenshots/${name}-${theme}-1440.webp`;
}

/**
 * Travel photos by Sean Morley, the same ones the app ships as login
 * backgrounds (frontend/static/backgrounds, credits in backgrounds.json).
 */
export const PHOTO_WIDTHS = [800, 1600, 2400];

export const photos = {
  philmont: {
    width: 2400,
    height: 1050,
    alt: "A mountain catching the last pink light above dark forested hills at dusk",
    place: "Philmont Scout Ranch, New Mexico",
  },
} as const;

export type PhotoName = keyof typeof photos;

export function photoSrcset(name: PhotoName, format: "avif" | "webp"): string {
  return PHOTO_WIDTHS.map((w) => `/photos/${name}-${w}.${format} ${w}w`).join(
    ", ",
  );
}
