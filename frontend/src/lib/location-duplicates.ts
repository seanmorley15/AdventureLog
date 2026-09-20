import type { DuplicateLocationMatch } from '$lib/types';

export type DuplicateCheckInput = {
	name?: string | null;
	latitude?: number | null;
	longitude?: number | null;
	location?: string | null;
	excludeId?: string | null;
};

function toFiniteNumber(value: unknown): number | null {
	if (value === null || value === undefined || value === '') return null;
	const parsed = typeof value === 'number' ? value : Number(value);
	return Number.isFinite(parsed) ? parsed : null;
}

export function duplicateCheckFingerprint(input: DuplicateCheckInput): string {
	const lat = toFiniteNumber(input.latitude);
	const lng = toFiniteNumber(input.longitude);
	return JSON.stringify({
		name: (input.name || '').trim().toLowerCase(),
		location: (input.location || '').trim().toLowerCase(),
		latitude: lat === null ? null : Number(lat.toFixed(5)),
		longitude: lng === null ? null : Number(lng.toFixed(5)),
		excludeId: input.excludeId || null
	});
}

export function canCheckDuplicates(input: DuplicateCheckInput): boolean {
	const name = (input.name || '').trim();
	const lat = toFiniteNumber(input.latitude);
	const lng = toFiniteNumber(input.longitude);
	return name.length >= 3 || (lat !== null && lng !== null);
}

export async function checkDuplicateLocations(
	input: DuplicateCheckInput
): Promise<DuplicateLocationMatch[]> {
	if (!canCheckDuplicates(input)) return [];

	try {
		const res = await fetch('/api/locations/check-duplicates/', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				name: (input.name || '').trim(),
				latitude: toFiniteNumber(input.latitude),
				longitude: toFiniteNumber(input.longitude),
				location: (input.location || '').trim() || null,
				exclude_id: input.excludeId || null
			})
		});

		if (!res.ok) return [];

		const data = await res.json();
		return Array.isArray(data?.matches) ? data.matches : [];
	} catch {
		return [];
	}
}
