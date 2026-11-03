export type CollectionMembership = {
	id: string;
	name: string;
	start_date: string | null;
	end_date: string | null;
	is_shared: boolean;
	owner_name: string;
	role: string | null;
	is_linked: boolean;
	can_link: boolean;
	can_unlink: boolean;
	placements: { day_index: number | null; is_global: boolean }[];
};

export async function fetchMembership(
	locationId: string,
	query = ''
): Promise<CollectionMembership[]> {
	const params = query ? `?q=${encodeURIComponent(query)}` : '';
	const res = await fetch(`/api/locations/${locationId}/collections/${params}`);
	if (!res.ok) throw new Error('membership fetch failed');
	return res.json();
}

export async function linkLocationToCollection(
	locationId: string,
	collectionId: string
): Promise<boolean> {
	const res = await fetch(`/api/locations/${locationId}/collections/${collectionId}/`, {
		method: 'POST'
	});
	return res.ok;
}

/** Returns the number of plan placements removed, or null on failure. */
export async function unlinkLocationFromCollection(
	locationId: string,
	collectionId: string
): Promise<number | null> {
	const res = await fetch(`/api/locations/${locationId}/collections/${collectionId}/`, {
		method: 'DELETE'
	});
	if (!res.ok) return null;
	const data = await res.json().catch(() => ({}));
	return data.removed_placements ?? 0;
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
