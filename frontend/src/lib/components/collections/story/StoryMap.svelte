<script lang="ts">
	import { GeoJSON, LineLayer, Marker } from 'svelte-maplibre';
	import FullMap, { type FullMapFeatureCollection } from '#lib/components/map/FullMap.svelte';
	import type { Activity } from '#lib/types.js';
	import { pinBounds, type StoryPin } from '#lib/collections/story.js';

	interface Props {
		pins: StoryPin[];
		tracks?: Activity[];
		/** The chapter being read: its pins stay bright and the map fits to them. */
		activeChapter?: string | null;
		/** The stop being read: the map flies to it. */
		focusKey?: string | null;
		/** The card under the pointer: its pin is highlighted without moving the map. */
		highlightKey?: string | null;
		onPinClick?: (pin: StoryPin) => void;
		mapClass?: string;
	}

	let {
		pins,
		tracks = [],
		activeChapter = null,
		focusKey = null,
		highlightKey = null,
		onPinClick,
		mapClass = 'h-full w-full'
	}: Props = $props();

	let map: any = $state(undefined);

	// Pins are rendered as markers directly. A GeoJSON marker layer reads features back
	// from MapLibre, which flattens nested properties and loses the pin's color and number.
	const EMPTY: FullMapFeatureCollection = { type: 'FeatureCollection', features: [] };

	let chapterPins = $derived(pins.filter((pin) => pin.chapter === activeChapter));
	let focusPin = $derived(pins.find((pin) => pin.key === focusKey) ?? null);

	// The current day's stops in order, as a route.
	let routeGeoJson = $derived.by(() => {
		const stops = chapterPins.filter((pin) => pin.kind !== 'transportation');
		if (stops.length < 2) return null;
		return {
			type: 'FeatureCollection',
			features: [
				{
					type: 'Feature',
					properties: { color: stops[0].color },
					geometry: { type: 'LineString', coordinates: stops.map((pin) => [pin.lng, pin.lat]) }
				}
			]
		} as GeoJSON.FeatureCollection;
	});

	let trackGeoJson = $derived.by(() => {
		const features: GeoJSON.Feature[] = [];
		for (const activity of tracks) {
			const data = activity.geojson;
			if (!data) continue;
			const list =
				data.type === 'FeatureCollection' ? data.features : data.type === 'Feature' ? [data] : [];
			for (const feature of list) {
				if (feature?.geometry?.type?.includes('LineString')) features.push(feature);
			}
		}
		return features.length
			? ({ type: 'FeatureCollection', features } as GeoJSON.FeatureCollection)
			: null;
	});

	function reducedMotion() {
		return (
			typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
		);
	}

	// Follow the reader: center on the stop being read, else fit the day, else the whole
	// trip (also the first view once the map loads). A day with no pins leaves the map
	// where it is.
	//
	// svelte-maplibre copies the view into its own `bounds` prop on every `moveend` and
	// fits back to that prop whenever it differs from the map. Interrupting a flight fires
	// `moveend` mid-way, so a new flight started in the same tick gets cancelled by a fit
	// back to where the old one stopped. Stop first, let that settle for a frame, then move.
	// No `bounds` prop is passed in, for the same reason.
	const FOCUS_ZOOM = 13;
	let moveId = 0;
	$effect(() => {
		if (!map) return;
		const pin = focusPin;
		const bounds = activeChapter ? pinBounds(chapterPins) : pinBounds(pins);
		if (!pin && !bounds) return;
		const duration = reducedMotion() ? 0 : 1000;
		const id = ++moveId;
		let frame = 0;
		const fly = () => {
			if (id !== moveId) return;
			try {
				if (pin) {
					map.flyTo({ center: [pin.lng, pin.lat], zoom: FOCUS_ZOOM, duration, essential: true });
				} else if (bounds) {
					map.fitBounds(bounds, { padding: 72, maxZoom: FOCUS_ZOOM, duration });
				}
			} catch {
				// Camera calls can fail mid style switch; the next change moves it again.
			}
		};
		const move = () => {
			try {
				map.stop?.();
			} catch {
				// Nothing to stop.
			}
			frame = requestAnimationFrame(() => {
				frame = requestAnimationFrame(fly);
			});
		};
		if (map.loaded?.() === false) {
			map.once('load', move);
			return () => {
				map.off?.('load', move);
				cancelAnimationFrame(frame);
			};
		}
		move();
		return () => cancelAnimationFrame(frame);
	});
</script>

<FullMap
	geoJson={EMPTY}
	bind:map
	{mapClass}
	clusterEnabled={false}
	mapClickEnabled={false}
	showBasemapSelector={false}
	sourceId="story-pins"
>
	{#snippet children()}
		{#each pins as pin (pin.key)}
			{@const inChapter = !activeChapter || pin.chapter === activeChapter}
			{@const lit = pin.key === focusKey || pin.key === highlightKey}
			<Marker lngLat={[pin.lng, pin.lat]} zIndex={lit ? 30 : inChapter ? 20 : 10}>
				<button
					type="button"
					class="flex items-center justify-center rounded-full border-2 border-white font-bold text-white shadow-lg transition-all duration-300 {lit
						? 'h-10 w-10 text-sm ring-4 ring-white/70'
						: inChapter
							? 'h-8 w-8 text-xs'
							: 'h-6 w-6 text-[10px] opacity-40'}"
					style="background-color: {pin.color}"
					title={pin.name}
					aria-label={pin.name}
					onclick={() => onPinClick?.(pin)}
				>
					{pin.label}
				</button>
			</Marker>
		{/each}
	{/snippet}
	{#snippet overlays()}
		{#if routeGeoJson}
			<GeoJSON id="story-route" data={routeGeoJson}>
				<LineLayer
					id="story-route-line"
					layout={{ 'line-cap': 'round', 'line-join': 'round' }}
					paint={{
						'line-color': ['get', 'color'],
						'line-width': 3,
						'line-opacity': 0.8,
						'line-dasharray': [1.5, 1.5]
					}}
				/>
			</GeoJSON>
		{/if}
		{#if trackGeoJson}
			<GeoJSON id="story-tracks" data={trackGeoJson}>
				<LineLayer
					id="story-tracks-casing"
					layout={{ 'line-cap': 'round', 'line-join': 'round' }}
					paint={{ 'line-color': '#ffffff', 'line-width': 6, 'line-opacity': 0.85 }}
				/>
				<LineLayer
					id="story-tracks-line"
					layout={{ 'line-cap': 'round', 'line-join': 'round' }}
					paint={{ 'line-color': '#ef4444', 'line-width': 3 }}
				/>
			</GeoJSON>
		{/if}
	{/snippet}
</FullMap>
