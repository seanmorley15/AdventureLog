<script lang="ts">
	import { t } from 'svelte-i18n';
	import Apple from '~icons/mdi/apple';
	import GoogleMaps from '~icons/mdi/google-maps';
	import MapOutline from '~icons/mdi/map-outline';
	import ImageMultiple from '~icons/mdi/image-multiple';

	interface Props {
		placeName?: string | null;
		latitude?: number | null;
		longitude?: number | null;
		className?: string;
		/** Hide the "Open in" label, e.g. where the context is already clear. */
		showLabel?: boolean;
		/** The viewer's Immich web app. Adds a link to this spot on its map (#1117). */
		immichUrl?: string | null;
	}

	let {
		placeName = null,
		latitude = null,
		longitude = null,
		className = '',
		showLabel = true,
		immichUrl = null
	}: Props = $props();

	const normalize = (value: string | null | undefined) => value?.trim() || null;

	let hasCoords = $derived(
		latitude !== null && latitude !== undefined && longitude !== null && longitude !== undefined
	);
	let coordsLabel = $derived(hasCoords ? `${latitude}, ${longitude}` : null);
	let displayName = $derived(normalize(placeName) || null);
	let baseQuery = $derived(
		displayName && coordsLabel ? `${displayName} ${coordsLabel}` : displayName || coordsLabel || ''
	);

	let appleMapsUrl = $derived(
		hasCoords
			? `https://maps.apple.com/?q=${encodeURIComponent(displayName ?? coordsLabel ?? '')}&ll=${latitude},${longitude}`
			: `https://maps.apple.com/?q=${encodeURIComponent(displayName ?? '')}`
	);

	let googleMapsUrl = $derived(
		`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(baseQuery)}`
	);

	let osmMapsUrl = $derived(
		hasCoords
			? `https://www.openstreetmap.org/search?query=${encodeURIComponent(
					baseQuery
				)}&mlat=${latitude}&mlon=${longitude}`
			: `https://www.openstreetmap.org/search?query=${encodeURIComponent(baseQuery)}`
	);

	// Immich's map opens at #zoom/lat/lng; it needs coordinates, not a name.
	let immichMapUrl = $derived(
		immichUrl && hasCoords
			? `${immichUrl.replace(/\/+$/, '')}/map#15/${latitude}/${longitude}`
			: null
	);

	const LINKS = $derived([
		{ name: 'Apple Maps', short: 'Apple', href: appleMapsUrl, icon: Apple },
		{ name: 'Google Maps', short: 'Google', href: googleMapsUrl, icon: GoogleMaps },
		{ name: 'OpenStreetMap', short: 'OSM', href: osmMapsUrl, icon: MapOutline },
		...(immichMapUrl
			? [{ name: 'Immich', short: 'Immich', href: immichMapUrl, icon: ImageMultiple }]
			: [])
	]);
</script>

<!-- One compact segmented control: no card, no repeated place name. -->
{#if displayName || hasCoords}
	<div class="flex flex-wrap items-center gap-2 {className}">
		{#if showLabel}
			<span class="text-sm text-base-content/60">{$t('detail.open_in')}</span>
		{/if}
		<div class="join">
			{#each LINKS as link (link.name)}
				<a
					class="btn btn-sm join-item gap-1.5"
					href={link.href}
					target="_blank"
					rel="noopener noreferrer"
					title={link.name}
					aria-label={`${$t('detail.open_in')} ${link.name}`}
				>
					<link.icon class="h-4 w-4" />
					{link.short}
				</a>
			{/each}
		</div>
	</div>
{/if}
