import type { ProfileVisibility } from '#lib/types.js';

type Person = {
	uuid: string;
	profile_visibility?: ProfileVisibility | null;
	/** From servers older than `profile_visibility`. */
	public_profile?: boolean;
};

/**
 * Whether `viewer` (null when signed out) can open `person`'s profile page (#1226): it is
 * public, shown to signed-in users and the viewer is signed in, or it is the viewer's own.
 * The server decides in the end; this only avoids links that would land on a 404.
 */
export function canOpenProfile(
	person: Person,
	viewer: { uuid: string } | null | undefined
): boolean {
	if (viewer && viewer.uuid === person.uuid) return true;
	const level = person.profile_visibility ?? (person.public_profile ? 'public' : 'private');
	if (level === 'public') return true;
	return level === 'signed_in' && Boolean(viewer);
}
