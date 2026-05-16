<script lang="ts">
	export let placeName: string | null = null;
	export let latitude: number | null = null;
	export let longitude: number | null = null;
	export let className = '';

	const normalize = (value: string | null | undefined) => value?.trim() || null;

	$: hasCoords =
		latitude !== null && latitude !== undefined && longitude !== null && longitude !== undefined;
	$: coordsLabel = hasCoords ? `${latitude}, ${longitude}` : null;
	$: displayName = normalize(placeName) || null;
	$: baseQuery =
		displayName && coordsLabel ? `${displayName} ${coordsLabel}` : displayName || coordsLabel || '';

	$: appleMapsUrl = hasCoords
		? `https://maps.apple.com/?q=${encodeURIComponent(displayName ?? coordsLabel ?? '')}&ll=${latitude},${longitude}`
		: `https://maps.apple.com/?q=${encodeURIComponent(displayName ?? '')}`;

	$: googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
		baseQuery
	)}`;

	$: osmMapsUrl = hasCoords
		? `https://www.openstreetmap.org/search?query=${encodeURIComponent(
				baseQuery
			)}&mlat=${latitude}&mlon=${longitude}`
		: `https://www.openstreetmap.org/search?query=${encodeURIComponent(baseQuery)}`;
</script>

{#if displayName || hasCoords}
	<div
		class={`rounded-lg p-3 bg-gradient-to-br from-primary/10 to-secondary/10 border border-base-300/60 shadow-sm ${className}`}
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
