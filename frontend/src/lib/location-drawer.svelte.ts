export type LocationDrawerTarget = {
	id: string;
	hash: string;
};

export const locationDrawer = $state({
	target: null as LocationDrawerTarget | null
});

const LOCATION_PATH = /^\/locations\/([^/]+)\/?$/;

export function parseLocationHref(href: string): LocationDrawerTarget | null {
	if (typeof window === 'undefined') return null;

	let url: URL;
	try {
		url = new URL(href, window.location.origin);
	} catch {
		return null;
	}

	if (url.origin !== window.location.origin) return null;

	const match = url.pathname.match(LOCATION_PATH);
	const id = match?.[1] ? decodeURIComponent(match[1]) : '';
	if (!id) return null;

	return { id, hash: url.hash };
}

export function openLocationDrawer(id: string, hash = '') {
	locationDrawer.target = {
		id,
		hash: hash.startsWith('#') || hash === '' ? hash : `#${hash}`
	};
}

export function closeLocationDrawer() {
	locationDrawer.target = null;
}

/** Opens the drawer for a location URL. Returns false when the URL is not a location. */
export function openLocationHref(href: string): boolean {
	const target = parseLocationHref(href);
	if (!target) return false;

	const path = window.location.pathname.replace(/\/$/, '');
	if (path === `/locations/${target.id}` && window.location.hash === target.hash) {
		return false;
	}

	locationDrawer.target = target;
	return true;
}
