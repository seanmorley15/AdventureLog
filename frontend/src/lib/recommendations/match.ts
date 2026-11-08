import type { Collection, Recommendation } from '#lib/types.js';

function normalize(name: string): string {
	return (name || '')
		.normalize('NFKD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase()
		.replace(/[^\p{L}\p{N}\s]/gu, ' ')
		.replace(/\s+/g, ' ')
		.trim();
}

function metersBetween(lat1: number, lon1: number, lat2: number, lon2: number): number {
	const rad = Math.PI / 180;
	const dLat = (lat2 - lat1) * rad;
	const dLon = (lon2 - lon1) * rad;
	const a =
		Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
	return 2 * 6371000 * Math.asin(Math.sqrt(a));
}

type Candidate = { id: string; name: string; latitude?: unknown; longitude?: unknown };

/** The collection location or lodging a recommendation already is, if any. */
export function findCollectionMatch(
	rec: Recommendation,
	collection: Collection
): { kind: 'location' | 'lodging'; id: string } | null {
	const target = normalize(rec.name);
	if (!target) return null;
	const candidates: { kind: 'location' | 'lodging'; item: Candidate }[] = [
		...(collection.locations ?? []).map((item) => ({ kind: 'location' as const, item })),
		...(collection.lodging ?? []).map((item) => ({ kind: 'lodging' as const, item }))
	];
	for (const { kind, item } of candidates) {
		const name = normalize(item.name);
		if (!name || (name !== target && !name.includes(target) && !target.includes(name))) continue;
		const lat = Number(item.latitude);
		const lon = Number(item.longitude);
		if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
		if (metersBetween(rec.latitude, rec.longitude, lat, lon) <= 100) {
			return { kind, id: String(item.id) };
		}
	}
	return null;
}
