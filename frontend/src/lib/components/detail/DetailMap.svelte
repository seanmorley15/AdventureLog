<script lang="ts">
	import type { Snippet } from 'svelte';
	import FullMap from '#lib/components/map/FullMap.svelte';
	import MapFloatingControls from '#lib/components/map/MapFloatingControls.svelte';
	import MapTrackLayerControls from '#lib/components/map/MapTrackLayerControls.svelte';
	import MapImagePinLayer from '#lib/components/map/MapImagePinLayer.svelte';
	import type { EMPTY_IMAGE_PIN_GEOJSON } from '#lib/map/imagePins.js';

	interface Props {
		center: [number, number];
		zoom?: number;
		/** Zoom to the box that holds all of these points, instead of using center and zoom. */
		fitPoints?: [number, number][];
		basemapType?: string;
		/** Photo locations to show as pins. */
		imagePinGeoJson?: typeof EMPTY_IMAGE_PIN_GEOJSON;
		mapClass?: string;
		/** Draw a border and rounded corners. Off when the map sits edge to edge in a panel. */
		bordered?: boolean;
		/** Layer toggles for pages with recorded activities or trails. */
		showActivities?: boolean;
		showTrails?: boolean;
		hasActivities?: boolean;
		hasTrails?: boolean;
		/** Markers and layers, placed inside the map. */
		children?: Snippet;
	}

	let {
		center,
		zoom = 13,
		fitPoints,
		basemapType = $bindable('default'),
		imagePinGeoJson,
		mapClass = 'w-full h-96',
		bordered = true,
		showActivities = $bindable(true),
		showTrails = $bindable(true),
		hasActivities = false,
		hasTrails = false,
		children
	}: Props = $props();

	let map: any = $state(undefined);
	let showImagePins = $state(true);

	// Fit once the map exists, and again only when the points themselves change.
	let fitKey = $derived(fitPoints && fitPoints.length > 1 ? JSON.stringify(fitPoints) : null);
	$effect(() => {
		if (!map || !fitKey || !fitPoints) return;
		const points = fitPoints;
		const fit = () => {
			const lngs = points.map((p) => p[0]);
			const lats = points.map((p) => p[1]);
			try {
				map.fitBounds(
					[
						[Math.min(...lngs), Math.min(...lats)],
						[Math.max(...lngs), Math.max(...lats)]
					],
					{ padding: { top: 80, bottom: 60, left: 60, right: 60 }, maxZoom: 15, duration: 0 }
				);
			} catch {
				// The map can reject camera moves while its style is switching.
			}
		};
		if (map.loaded?.() === false) {
			map.once('load', fit);
			return () => map.off?.('load', fit);
		}
		fit();
	});
	let hasImagePins = $derived((imagePinGeoJson?.features.length ?? 0) > 0);
</script>

<!-- The same map frame, controls, and photo pins on every detail page. -->
<div class={bordered ? 'overflow-hidden rounded-xl border border-base-300' : ''}>
	<FullMap bind:map bind:basemapType {mapClass} {center} {zoom}>
		{#snippet overlayControls({ map, fullscreenTarget })}
			<div class="pointer-events-none absolute inset-0 z-20">
				<MapTrackLayerControls
					bind:showActivities
					bind:showTrails
					bind:showImagePins
					{hasActivities}
					{hasTrails}
					{hasImagePins}
				/>
				<MapFloatingControls {map} {fullscreenTarget} bind:basemapType />
			</div>
		{/snippet}

		{@render children?.()}

		{#if imagePinGeoJson}
			<MapImagePinLayer geoJson={imagePinGeoJson} visible={showImagePins} />
		{/if}
	</FullMap>
</div>
