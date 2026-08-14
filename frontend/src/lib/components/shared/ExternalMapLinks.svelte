<script lang="ts">
	interface Props {
		placeName?: string | null;
		latitude?: number | null;
		longitude?: number | null;
		className?: string;
	}

	let {
		placeName = null,
		latitude = null,
		longitude = null,
		className = ''
	}: Props = $props();

	const normalize = (value: string | null | undefined) => value?.trim() || null;

	let hasCoords =
		$derived(latitude !== null && latitude !== undefined && longitude !== null && longitude !== undefined);
	let coordsLabel = $derived(hasCoords ? `${latitude}, ${longitude}` : null);
	let displayName = $derived(normalize(placeName) || null);
	let baseQuery =
		$derived(displayName && coordsLabel ? `${displayName} ${coordsLabel}` : displayName || coordsLabel || '');

	let appleMapsUrl = $derived(hasCoords
		? `https://maps.apple.com/?q=${encodeURIComponent(displayName ?? coordsLabel ?? '')}&ll=${latitude},${longitude}`
		: `https://maps.apple.com/?q=${encodeURIComponent(displayName ?? '')}`);

	let googleMapsUrl = $derived(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
		baseQuery
	)}`);

	let osmMapsUrl = $derived(hasCoords
		? `https://www.openstreetmap.org/search?query=${encodeURIComponent(
				baseQuery
			)}&mlat=${latitude}&mlon=${longitude}`
		: `https://www.openstreetmap.org/search?query=${encodeURIComponent(baseQuery)}`);
</script>

{#if displayName || hasCoords}
	<div
		class={`rounded-lg p-3 bg-gradient-to-br from-primary/10 to-secondary/10 border border-base-300/60 shadow-xs ${className}`}
	>
		<div class="flex flex-wrap items-center justify-between gap-2 mb-3">
			<div class="flex items-center gap-2">
				<span class="badge badge-primary badge-outline">Open in maps</span>
				{#if displayName}
					<span class="text-sm font-semibold">{displayName}</span>
				{/if}
			</div>
			{#if coordsLabel}
				<span class="badge badge-ghost badge-sm">{coordsLabel}</span>
			{/if}
		</div>
		<div class="grid grid-cols-3 gap-2">
			<a
				class="btn btn-sm btn-outline hover:btn-neutral"
				href={appleMapsUrl}
				target="_blank"
				rel="noopener noreferrer"
			>
				🍎 Apple
			</a>
			<a
				class="btn btn-sm btn-outline hover:btn-accent"
				href={googleMapsUrl}
				target="_blank"
				rel="noopener noreferrer"
			>
				🌍 Google
			</a>
			<a
				class="btn btn-sm btn-outline hover:btn-primary"
				href={osmMapsUrl}
				target="_blank"
				rel="noopener noreferrer"
			>
				🗺️ OSM
			</a>
		</div>
	</div>
{/if}
