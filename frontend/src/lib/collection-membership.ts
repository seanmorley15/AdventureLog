import type { Schemas } from '#lib/api/index.js';

/** `GET /api/locations/{id}/collections/`: one collection and where the location sits in it. */
export type CollectionMembership = Schemas['CollectionMembership'];

export async function fetchMembership(
	locationId: string,
	query = ''
): Promise<CollectionMembership[]> {
	const params = query ? `?q=${encodeURIComponent(query)}` : '';
	const res = await fetch(`/api/locations/${locationId}/collections/${params}`);
	if (!res.ok) throw new Error('membership fetch failed');
	return res.json();
}

/** A membership change: the result, or the error body to show with `apiErrorMessage`. */
export type MembershipChange<T> = ({ ok: true } & T) | { ok: false; error: unknown };

async function membershipRequest(
	locationId: string,
	collectionId: string,
	method: 'POST' | 'DELETE'
): Promise<MembershipChange<{ result: Schemas['CollectionLinkResult'] }>> {
	try {
		const res = await fetch(`/api/locations/${locationId}/collections/${collectionId}/`, {
			method
		});
		const data = await res.json().catch(() => null);
		if (!res.ok) return { ok: false, error: data };
		return {
			ok: true,
			result: (data ?? { linked: method === 'POST' }) as Schemas['CollectionLinkResult']
		};
	} catch {
		return { ok: false, error: null };
	}
}

export async function linkLocationToCollection(
	locationId: string,
	collectionId: string
): Promise<MembershipChange<object>> {
	return membershipRequest(locationId, collectionId, 'POST');
}

/** On success, `removed` is how many plan placements went with the place. */
export async function unlinkLocationFromCollection(
	locationId: string,
	collectionId: string
): Promise<MembershipChange<{ removed: number }>> {
	const change = await membershipRequest(locationId, collectionId, 'DELETE');
	return change.ok ? { ok: true, removed: change.result.removed_placements ?? 0 } : change;
}

/** "Day 2, Day 4" style summary of where a place sits on a plan. */
export function placementDays(
	placements: CollectionMembership['placements'],
	dayLabel: (n: number) => string,
	tripWide: string,
	ideas: string
): string {
	return placements
		.map((p) => (p.is_global ? tripWide : p.day_index != null ? dayLabel(p.day_index) : ideas))
		.join(', ');
}
