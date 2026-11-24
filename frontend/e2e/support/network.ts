import type { BrowserContext } from '@playwright/test';

/**
 * A MapLibre style with no sources or layers: the map initialises and fires `load` without
 * fetching a single tile, so tests stay deterministic and work offline.
 */
export const EMPTY_MAP_STYLE = {
	version: 8,
	name: 'e2e-empty',
	sources: {},
	layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#dfe6ee' } }]
};

// 1x1 transparent PNG, used for any remote image so cards and avatars render without the network.
const PIXEL_PNG = Buffer.from(
	'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
	'base64'
);

const STYLE_HOSTS = ['tiles.openfreemap.org', 'basemaps.cartocdn.com'];
const BLOCKED_HOSTS = [
	'nominatim.openstreetmap.org',
	'overpass-api.de',
	'cloud.umami.is',
	'analytics.umami.is',
	'fonts.googleapis.com',
	'fonts.gstatic.com'
];
const IMAGE_HOSTS = ['flagcdn.com', 'upload.wikimedia.org', 'maps.googleapis.com'];

/**
 * Keep the browser inside the app under test. Anything on the app's own origin passes through;
 * known third-party hosts are stubbed or blocked so a run never depends on (or hits) the internet.
 */
export async function stubExternalNetwork(context: BrowserContext, appOrigin: string) {
	const appHost = new URL(appOrigin).host;

	await stubGeocoding(context, appHost);

	await context.route(
		(url) => STYLE_HOSTS.some((host) => url.host === host || url.host.endsWith(`.${host}`)),
		(route) => route.fulfill({ json: EMPTY_MAP_STYLE })
	);

	await context.route(
		(url) => IMAGE_HOSTS.some((host) => url.host === host || url.host.endsWith(`.${host}`)),
		(route) => route.fulfill({ status: 200, contentType: 'image/png', body: PIXEL_PNG })
	);

	await context.route(
		(url) => BLOCKED_HOSTS.some((host) => url.host === host || url.host.endsWith(`.${host}`)),
		(route) => route.abort()
	);

	// Fail loudly if the app starts talking to a host nobody has decided about yet.
	await context.route(
		(url) => url.protocol.startsWith('http') && url.host !== appHost && !isDecided(url),
		(route) => {
			console.warn(`[e2e] unexpected external request blocked: ${route.request().url()}`);
			return route.abort();
		}
	);
}

function isDecided(url: URL): boolean {
	const all = [...STYLE_HOSTS, ...BLOCKED_HOSTS, ...IMAGE_HOSTS];
	return all.some((host) => url.host === host || url.host.endsWith(`.${host}`));
}

// A fixed spot in Paris, so every geocoding answer is the same on every run.
const PARIS = { lat: 48.8584, lon: 2.2945 };

/**
 * The backend answers place lookups by calling Nominatim, Wikipedia and Google. Those calls
 * are slow, rate-limited and can fail, which made location creation flaky in practice (one
 * run saw a 502 from `/api/places/reverse/`). The browser reaches them through the app's own
 * `/api/places/*` routes, so they are answered here instead.
 *
 * This means the suite does not exercise the backend's geocoding itself. That belongs to the
 * backend tests.
 */
async function stubGeocoding(context: BrowserContext, appHost: string) {
	const slug = (text: string) => text.toLowerCase().replace(/[^a-z0-9]+/g, '-');

	await context.route(
		(url) => url.host === appHost && url.pathname.startsWith('/api/places/'),
		(route) => {
			const url = new URL(route.request().url());
			const endpoint = url.pathname.replace('/api/places/', '').replace(/\/$/, '');

			switch (endpoint) {
				case 'search': {
					const query = url.searchParams.get('q') ?? '';
					// Clicking the map looks up "lat,lng": answer with the place at that point,
					// like the real backend. A typed search answers with a place of that name.
					const isPoint = /^-?\d+(\.\d+)?,\s*-?\d+(\.\d+)?$/.test(query.trim());
					const name = isPoint ? 'Champ de Mars' : query;
					// Named places get a stable spot near Paris derived from the name, so a trip's start
					// and end are two different points (a route needs two).
					const seed = [...query].reduce((sum, ch) => sum + ch.charCodeAt(0), 0);
					const [lat, lon] = isPoint
						? query.split(',').map((n) => n.trim())
						: [
								(PARIS.lat + (seed % 50) / 100).toFixed(4),
								(PARIS.lon + (seed % 37) / 100).toFixed(4)
							];
					return route.fulfill({
						json: {
							count: 1,
							provider_used: 'e2e',
							providers_attempted: ['e2e'],
							results: [
								{
									name,
									lat: String(lat),
									lon: String(lon),
									display_name: `${name}, Paris, France`,
									place_id: `e2e-${slug(name)}`,
									type: 'attraction',
									category: 'tourism',
									types: ['tourist_attraction'],
									provider: 'e2e'
								}
							]
						}
					});
				}
				case 'reverse':
					return route.fulfill({
						json: {
							display_name: 'Champ de Mars, 5 Avenue Anatole France, Paris, France',
							location_name: 'Champ de Mars',
							city: 'Paris',
							region: 'Île-de-France',
							country: 'France',
							country_id: 'FR',
							provider: 'e2e'
						}
					});
				case 'details':
					return route.fulfill({
						json: {
							name: url.searchParams.get('name') ?? '',
							formatted_address: 'Paris, France',
							description: ''
						}
					});
				default:
					// description, images, photo: nothing found, the same as an unknown place.
					return route.fulfill({
						status: 404,
						json: { detail: 'Not found.', code: 'not_found' }
					});
			}
		}
	);
}
