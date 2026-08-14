<script lang="ts" module>
	export type FullMapPointGeometry = {
		type: 'Point';
		coordinates: [number, number];
	};

	export type FullMapFeature<P = Record<string, unknown>> = {
		type: 'Feature';
		geometry: FullMapPointGeometry;
		properties: P;
	};

	export type FullMapFeatureCollection<P = Record<string, unknown>> = {
		type: 'FeatureCollection';
		features: FullMapFeature<P>[];
	};
</script>

<script lang="ts">
	import { run } from 'svelte/legacy';

	import { createEventDispatcher, onMount } from 'svelte';
	import { CircleLayer, GeoJSON, MapEvents, MapLibre, MarkerLayer } from 'svelte-maplibre';
	import type { ClusterOptions, LayerClickInfo } from 'svelte-maplibre';
	import { getBasemapUrl, getIsDarkMode } from '$lib';
	import { getMapViewportCenter } from '$lib/map/viewportCenter';
	import MapFloatingControls from '$lib/components/map/MapFloatingControls.svelte';
	import { resolveThemeColor, withAlpha } from '$lib/utils/resolveThemeColor';

	type Feature = FullMapFeature;
	type FeatureCollection = FullMapFeatureCollection;

	

	

	
	
	
	

	

	let mapRootEl: HTMLDivElement | null = $state(null);

	

	

	

	


	function getPointCoordinates(feature: unknown): [number, number] | null {
		if (!feature || typeof feature !== 'object') return null;
		const geometry = (feature as any).geometry as unknown;
		if (!geometry || typeof geometry !== 'object') return null;
		const type = (geometry as any).type;
		const coordinates = (geometry as any).coordinates;
		if (type !== 'Point' || !Array.isArray(coordinates) || coordinates.length < 2) return null;
		const lon = Number(coordinates[0]);
		const lat = Number(coordinates[1]);
		if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
		return [lon, lat];
	}

	// Effective GeoJSON (either derived from items or passed directly)
	let effectiveGeoJson: FeatureCollection = $state({ type: 'FeatureCollection', features: [] });

	
	interface Props {
		// Generic item input (optional). If you provide `items` + `toFeature`, FullMap builds the GeoJSON.
		items?: unknown[];
		toFeature?: ((item: unknown) => Feature | null) | null;
		// Or pass prebuilt GeoJSON.
		geoJson?: FeatureCollection;
		// Map presentation
		mapClass?: string;
		/** Custom floating map controls (zoom, locate, fullscreen, basemap). */
		showMapControls?: boolean;
		/** Render controls inline (no absolute positioning) — for parent toolbars. */
		controlsEmbedded?: boolean;
		/** Element to fullscreen; defaults to the FullMap root container. */
		fullscreenTarget?: HTMLElement | null;
		zoom?: number | undefined;
		center?: [number, number] | { lng: number; lat: number };
		bounds?: [[number, number], [number, number]] | undefined;
		mapClickEnabled?: boolean;
		// Basemap
		basemapType?: string;
		mapStyle?: string | null;
		showBasemapSelector?: boolean;
		// GeoJSON source
		sourceId?: string;
		// Clustering
		clusterEnabled?: boolean;
		clusterOptions?: ClusterOptions;
		expandClusterOnClick?: boolean;
		// Optional cluster style overrides
		clusterCirclePaint?: Record<string, any> | null;
		clusterSymbolLayout?: Record<string, any> | null;
		clusterSymbolPaint?: Record<string, any> | null;
		// Marker plumbing
		getMarkerProps?: (feature: unknown) => Record<string, unknown> | null;
		getMarkerId?: (markerProps: Record<string, unknown> | null) => string | null;
		// Map instance
		map?: any;
		overlayControls?: import('svelte').Snippet<[any]>;
		marker?: import('svelte').Snippet<[any]>;
		children?: import('svelte').Snippet<[any]>;
		overlays?: import('svelte').Snippet<[any]>;
	}

	let {
		items = [],
		toFeature = null,
		geoJson = { type: 'FeatureCollection', features: [] },
		mapClass = 'w-full h-full',
		showMapControls = true,
		controlsEmbedded = false,
		fullscreenTarget = null,
		zoom = 2,
		center = [0, 0],
		bounds = undefined,
		mapClickEnabled = true,
		basemapType = $bindable('default'),
		mapStyle = null,
		showBasemapSelector = true,
		sourceId = 'fullmap-source',
		clusterEnabled = true,
		clusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 },
		expandClusterOnClick = true,
		clusterCirclePaint = null,
		clusterSymbolLayout = null,
		clusterSymbolPaint = null,
		getMarkerProps = (feature) =>
		feature && typeof feature === 'object' && feature !== null && 'properties' in (feature as any)
			? ((feature as any).properties as Record<string, unknown>)
			: null,
		getMarkerId = (
		markerProps
	) => (markerProps && typeof markerProps.id === 'string' ? markerProps.id : null),
		map = $bindable(undefined),
		overlayControls,
		marker,
		children,
		overlays
	}: Props = $props();

	// When MapLibre's style changes (basemap switch), it drops all custom sources/layers.
	// Force the GeoJSON/layer subtree to remount after the new style finishes loading.
	let styleNonce = $state(0);
	let lastStyleKey: string | null = $state(null);
	let isDarkUi = $state(false);
	let themeEpoch = $state(0);
	let styleKey = $state(basemapType);

	let resolvedStyle = $state(getBasemapUrl(basemapType));

	// Active marker tracking (used for map-level z-index + slot convenience)
	let activeMarkerId: string | null = $state(null);

	const dispatch = createEventDispatcher<{
		mapClick: { lngLat: { lng: number; lat: number } };
		markerClick: { feature: unknown; markerProps: Record<string, unknown> | null };
		clusterClick: LayerClickInfo;
		mapMove: { center: { lng: number; lat: number }; zoom: number };
	}>();

	function handleMapClick(e: CustomEvent<{ lngLat: { lng: number; lat: number } }>) {
		dispatch('mapClick', e.detail);
	}

	function handleMapMove() {
		if (!map) return;
		const mapZoom = map.getZoom();
		if (typeof mapZoom === 'number') {
			dispatch('mapMove', {
				center: getMapViewportCenter(map),
				zoom: mapZoom
			});
		}
	}

	function setBasemapType(next: string) {
		basemapType = next;
	}

	// Theme-aware cluster styling (defaults to semantic daisyUI tokens)
	let clusterBaseContent = $state('#111827');
	let clusterInfo = $state('#38bdf8');
	let clusterWarning = $state('#f59e0b');
	let clusterError = $state('#f87171');
	let clusterInfoContent = $state('#082f49');
	let clusterWarningContent = $state('#111827');
	let clusterErrorContent = $state('#450a0a');

	onMount(() => {
		const syncTheme = () => {
			isDarkUi = getIsDarkMode();
			themeEpoch += 1;
			clusterBaseContent = resolveThemeColor('--color-base-content', clusterBaseContent);
			clusterInfo = resolveThemeColor('--color-info', clusterInfo);
			clusterWarning = resolveThemeColor('--color-warning', clusterWarning);
			clusterError = resolveThemeColor('--color-error', clusterError);
			clusterInfoContent = resolveThemeColor('--color-info-content', clusterInfoContent);
			clusterWarningContent = resolveThemeColor('--color-warning-content', clusterWarningContent);
			clusterErrorContent = resolveThemeColor('--color-error-content', clusterErrorContent);
		};

		syncTheme();

		const observer = new MutationObserver(syncTheme);
		observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
		const mq = window.matchMedia('(prefers-color-scheme: dark)');
		mq.addEventListener('change', syncTheme);

		return () => {
			observer.disconnect();
			mq.removeEventListener('change', syncTheme);
		};
	});

	let resolvedClusterCirclePaint: Record<string, any> = $state({});
	let resolvedClusterSymbolLayout: Record<string, any> = $state({});
	let resolvedClusterSymbolPaint: Record<string, any> = $state({});




	type ClusterSource = {
		getClusterExpansionZoom: (
			clusterId: number,
			callback: (error: unknown, zoom: number) => void
		) => void;
	};

	function handleClusterClick(e: CustomEvent<LayerClickInfo>) {
		dispatch('clusterClick', e.detail);

		if (!expandClusterOnClick) return;
		const { clusterId, features, map: eventMap, source } = e.detail ?? ({} as any);
		if (!clusterId || !features?.length || !eventMap || !source) return;

		const center = getPointCoordinates(features[0]);
		if (!center) return;

		const geoJsonSource = eventMap.getSource(source) as ClusterSource | undefined;
		if (!geoJsonSource || typeof geoJsonSource.getClusterExpansionZoom !== 'function') return;

		geoJsonSource.getClusterExpansionZoom(
			Number(clusterId),
			(error: unknown, zoomLevel: number) => {
				if (error) {
					console.error('Failed to expand cluster', error);
					return;
				}
				eventMap.easeTo({ center, zoom: zoomLevel });
			}
		);
	}

	function handleMarkerLayerClick(event: CustomEvent<any>) {
		const feature = event.detail?.feature;
		const markerProps = getMarkerProps(feature);
		dispatch('markerClick', { feature, markerProps });
	}

	function setMarkerActiveByProps(markerProps: Record<string, unknown> | null, active: boolean) {
		const markerId = getMarkerId(markerProps);
		if (!markerId) return;
		activeMarkerId = active ? markerId : activeMarkerId === markerId ? null : activeMarkerId;
	}

	function makeSetActive(markerProps: Record<string, unknown> | null) {
		return (active: boolean) => setMarkerActiveByProps(markerProps, active);
	}
	run(() => {
		effectiveGeoJson =
			toFeature && Array.isArray(items)
				? {
						type: 'FeatureCollection',
						features: items
							.map((i) => toFeature(i))
							.filter((f): f is Feature => f !== null) as Feature[]
					}
				: geoJson;
	});
	run(() => {
		styleKey = mapStyle ?? `${basemapType}:${isDarkUi ? 'dark' : 'light'}`;
	});
	run(() => {
		if (map && lastStyleKey !== styleKey) {
			lastStyleKey = styleKey;

			const m = map as any;
			const bump = () => {
				styleNonce += 1;
			};

			if (typeof m?.once === 'function') {
				m.once('style.load', bump);
			} else if (typeof m?.on === 'function' && typeof m?.off === 'function') {
				const handler = () => {
					m.off('style.load', handler);
					bump();
				};
				m.on('style.load', handler);
			} else {
				// Fallback: at least trigger a remount.
				bump();
			}
		}
	});
	run(() => {
		themeEpoch;
		resolvedStyle = mapStyle ?? getBasemapUrl(basemapType);
	});
	run(() => {
		resolvedClusterCirclePaint = clusterCirclePaint ?? {
			'circle-color': [
				'step',
				['get', 'point_count'],
				withAlpha(clusterInfo, 0.7),
				25,
				withAlpha(clusterWarning, 0.7),
				80,
				withAlpha(clusterError, 0.65)
			],
			'circle-radius': ['step', ['get', 'point_count'], 22, 20, 32, 60, 44],
			'circle-opacity': 1,
			'circle-stroke-color': withAlpha(clusterBaseContent, 0.25),
			'circle-stroke-width': 2,
			'circle-blur': 0
		};
	});
	run(() => {
		resolvedClusterSymbolLayout = clusterSymbolLayout ?? {
			'text-field': '{point_count_abbreviated}',
			'text-font': ['Open Sans Semibold', 'Open Sans Regular', 'Arial Unicode MS Regular'],
			'text-size': 13
		};
	});
	run(() => {
		resolvedClusterSymbolPaint = clusterSymbolPaint ?? {
			'text-color': [
				'step',
				['get', 'point_count'],
				clusterInfoContent,
				25,
				clusterWarningContent,
				80,
				clusterErrorContent
			],
			'text-halo-color': withAlpha(clusterBaseContent, 0.12),
			'text-halo-width': 0.75,
			'text-halo-blur': 0
		};
	});
</script>

<div class="fullmap-root relative h-full w-full min-h-[inherit]" bind:this={mapRootEl}>
	<MapLibre
		bind:map
		style={resolvedStyle}
		class="{mapClass} fullmap-map"
		standardControls={false}
		{zoom}
		{center}
		{bounds}
	>
		{#key styleNonce}
			{#if effectiveGeoJson && Array.isArray(effectiveGeoJson.features) && effectiveGeoJson.features.length > 0}
				{#if clusterEnabled}
					<GeoJSON id={sourceId} data={effectiveGeoJson} cluster={clusterOptions} generateId>
						<CircleLayer
							id={`${sourceId}-clusters`}
							applyToClusters
							hoverCursor="pointer"
							paint={resolvedClusterCirclePaint}
							on:click={handleClusterClick}
						/>
						<!-- Render cluster counts as HTML so they don't depend on map glyph/font availability -->
						<MarkerLayer applyToClusters >
							{#snippet children({ feature: clusterFeature }: { feature: unknown })}
														{@const clusterProps = getMarkerProps(clusterFeature)}
								{@const abbreviated = clusterProps && clusterProps['point_count_abbreviated']}
								{@const count = abbreviated ?? (clusterProps && clusterProps['point_count'])}
								{#if typeof count !== 'undefined' && count !== null}
									<div
										class="pointer-events-none select-none font-sans text-xs font-bold text-base-content drop-shadow-xs"
									>
										{count}
									</div>
								{/if}
																				{/snippet}
												</MarkerLayer>
						<MarkerLayer
							applyToClusters={false}
							on:click={handleMarkerLayerClick}
							
						>
							{#snippet children({ feature: featureData }: { feature: unknown })}
														{@const markerProps = getMarkerProps(featureData)}
								{@const markerLngLat = getPointCoordinates(featureData)}
								{@const markerId = getMarkerId(markerProps)}
								{@const isActive = markerId !== null && activeMarkerId === markerId}
								{@render marker?.({ featureData, markerProps, markerLngLat, isActive, setActive: makeSetActive(markerProps), })}
																				{/snippet}
												</MarkerLayer>
					</GeoJSON>
				{:else}
					<GeoJSON id={sourceId} data={effectiveGeoJson} generateId>
						<MarkerLayer
							applyToClusters={false}
							on:click={handleMarkerLayerClick}
							
						>
							{#snippet children({ feature: featureData }: { feature: unknown })}
														{@const markerProps = getMarkerProps(featureData)}
								{@const markerLngLat = getPointCoordinates(featureData)}
								{@const markerId = getMarkerId(markerProps)}
								{@const isActive = markerId !== null && activeMarkerId === markerId}
								{@render marker?.({ featureData, markerProps, markerLngLat, isActive, setActive: makeSetActive(markerProps), })}
																				{/snippet}
												</MarkerLayer>
					</GeoJSON>
				{/if}
			{/if}
		{/key}

		{#if mapClickEnabled}
			<MapEvents on:click={handleMapClick} on:moveend={handleMapMove} />
		{:else}
			<MapEvents on:moveend={handleMapMove} />
		{/if}
		{@render children?.({ map, })}
		{@render overlays?.({ map, })}
	</MapLibre>

	{#if showMapControls}
		{#if overlayControls}
			{@render overlayControls?.({ basemapType, setBasemapType, map, mapRootEl, fullscreenTarget: fullscreenTarget ?? mapRootEl, })}
		{:else}
			<MapFloatingControls
				{map}
				bind:basemapType
				{showBasemapSelector}
				embedded={controlsEmbedded}
				fullscreenTarget={fullscreenTarget ?? mapRootEl}
			/>
		{/if}
	{/if}
</div>

<style>
	/* Ensure map popups render above HTML markers/pins */
	:global(.maplibregl-popup),
	:global(.mapboxgl-popup) {
		z-index: 2147483647 !important;
	}

	/* Markers can be assigned z-index by the map library; keep them below popups by default */
	:global(.maplibregl-marker),
	:global(.mapboxgl-marker) {
		z-index: 1 !important;
	}

	/* But raise the actively hovered/focused marker above other markers */
	:global(.maplibregl-marker.map-pin-active),
	:global(.mapboxgl-marker.map-pin-active) {
		z-index: 2147483000 !important;
	}

	:global(.fullmap-root .fullmap-map),
	:global(.fullmap-root .maplibregl-map) {
		position: relative;
		z-index: 0;
	}

	:global(.fullmap-root:fullscreen) {
		height: 100%;
		width: 100%;
		max-height: none;
		min-height: 100%;
		background-color: var(--color-base-100, #1a1a1a);
	}

	:global(.fullmap-root:fullscreen .fullmap-map),
	:global(.fullmap-root:fullscreen .fullmap-map .maplibregl-map),
	:global(.fullmap-root:fullscreen .fullmap-map .maplibregl-canvas-container) {
		height: 100% !important;
		width: 100% !important;
		min-height: 100% !important;
	}
</style>
