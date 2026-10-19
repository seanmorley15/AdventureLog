<script lang="ts">
	import type { Snippet } from 'svelte';
	import MapMarker from '~icons/mdi/map-marker';
	import DetailMap from './DetailMap.svelte';
	import type { EMPTY_IMAGE_PIN_GEOJSON } from '$lib/map/imagePins';

	interface Props {
		title: string;
		hint?: string;
		center: [number, number];
		zoom?: number;
		fitPoints?: [number, number][];
		basemapType?: string;
		imagePinGeoJson?: typeof EMPTY_IMAGE_PIN_GEOJSON;
		showActivities?: boolean;
		showTrails?: boolean;
		hasActivities?: boolean;
		hasTrails?: boolean;
		/** Height of the map. Taller than a normal card so the map leads the page. */
		mapClass?: string;
		/** Markers and layers, placed inside the map. */
		children?: Snippet;
		/** The strip under the map: place links, coordinates, "open in" buttons. */
		footer?: Snippet;
	}

	let {
		title,
		hint = '',
		center,
		zoom = 13,
		fitPoints,
		basemapType = $bindable('default'),
		imagePinGeoJson,
		showActivities = $bindable(true),
		showTrails = $bindable(true),
		hasActivities = false,
		hasTrails = false,
		mapClass = 'w-full h-[58vh] min-h-[22rem] max-h-[44rem]',
		children,
		footer
	}: Props = $props();
</script>

<!-- A map-first card: slim title, a large edge-to-edge map, then the details strip. -->
<section class="card overflow-hidden border border-base-300 bg-base-100">
	<div class="flex items-center gap-3 px-4 py-3 md:px-6">
		<div class="shrink-0 rounded-lg bg-primary/10 p-2">
			<MapMarker class="h-5 w-5 text-primary" />
		</div>
		<div class="min-w-0 flex-1">
			<h2 class="text-lg font-bold text-base-content">{title}</h2>
			{#if hint}
				<p class="field-hint truncate">{hint}</p>
			{/if}
		</div>
	</div>

	<DetailMap
		bind:basemapType
		bind:showActivities
		bind:showTrails
		{center}
		{zoom}
		{fitPoints}
		{imagePinGeoJson}
		{hasActivities}
		{hasTrails}
		{mapClass}
		bordered={false}
	>
		{@render children?.()}
	</DetailMap>

	{#if footer}
		<div class="space-y-3 border-t border-base-300 bg-base-100 px-4 py-3 md:px-6 md:py-4">
			{@render footer()}
		</div>
	{/if}
</section>
