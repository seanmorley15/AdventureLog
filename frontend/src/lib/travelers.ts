import type { PersonSummary } from '#lib/components/collections/discussion/PersonAvatar.svelte';
import type { TravelerSummary } from '#lib/types.js';

/** A traveler's full name, or their username when they have not set one. */
export function travelerName(traveler: TravelerSummary): string {
	const full = [traveler.first_name, traveler.last_name].filter(Boolean).join(' ').trim();
	return full || traveler.username;
}

/** A traveler as the shared avatar component wants them. */
export function travelerPerson(traveler: TravelerSummary): PersonSummary {
	return {
		name: travelerName(traveler),
		username: traveler.username,
		profile_pic: traveler.profile_pic ?? null
	};
}
