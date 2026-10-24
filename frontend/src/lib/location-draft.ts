import type { Location } from '$lib/types';

/** Blank location used as a bindable draft. Must not be `undefined` — Svelte throws `props_invalid_value` when `bind:` passes `undefined` into a prop that has a fallback. */
export function createEmptyLocation(): Location {
	return {
		id: '',
		name: '',
		visits: [],
		link: null,
		description: null,
		tags: [],
		rating: NaN,
		price: null,
		price_currency: null,
		is_public: false,
		latitude: NaN,
		longitude: NaN,
		location: null,
		images: [],
		user: null,
		category: {
			id: '',
			name: '',
			display_name: '',
			icon: '',
			user: ''
		},
		attachments: [],
		trails: []
	};
}
