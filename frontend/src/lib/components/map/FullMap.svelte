<script lang="ts" context="module">
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
	import { createEventDispatcher, onMount } from 'svelte';
	import { CircleLayer, GeoJSON, MapEvents, MapLibre, MarkerLayer } from 'svelte-maplibre';
	import type { ClusterOptions, LayerClickInfo } from 'svelte-maplibre';
	import { getBasemapUrl } from '$lib';
	import MapStyleSelector from '$lib/components/map/MapStyleSelector.svelte';
	import { resolveThemeColor, withAlpha } from '$lib/utils/resolveThemeColor';

	type Feature = FullMapFeature;
	type FeatureCollection = FullMapFeatureCollection;

	// Generic item input (optional). If you provide `items` + `toFeature`, FullMap builds the GeoJSON.
	export let items: unknown[] = [];
	export let toFeature: ((item: unknown) => Feature | null) | null = null;

	// Or pass prebuilt GeoJSON.
	export let geoJson: FeatureCollection = { type: 'FeatureCollection', features: [] };

	// Map presentation
	export let mapClass = 'w-full h-full';
	export let standardControls = true;
	export let zoom: number | undefined = 2;
	export let center: [number, number] | { lng: number; lat: number } = [0, 0];
	export let bounds: [[number, number], [number, number]] | undefined = undefined;
	export let mapClickEnabled: boolean = true;

	// Basemap
	export let basemapType: string = 'default';
	export let mapStyle: string | null = null;
	export let showBasemapSelector: boolean = true;

	// GeoJSON source
	export let sourceId = 'fullmap-source';

	// Clustering
	export let clusterEnabled: boolean = true;
	export let clusterOptions: ClusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 };
	export let expandClusterOnClick: boolean = true;

	// Optional cluster style overrides
	export let clusterCirclePaint: Record<string, any> | null = null;
	export let clusterSymbolLayout: Record<string, any> | null = null;
	export let clusterSymbolPaint: Record<string, any> | null = null;

	// Marker plumbing
	export let getMarkerProps: (feature: unknown) => Record<string, unknown> | null = (feature) =>
		feature && typeof feature === 'object' && feature !== null && 'properties' in (feature as any)
			? ((feature as any).properties as Record<string, unknown>)
			: null;

	export let getMarkerId: (markerProps: Record<string, unknown> | null) => string | null = (
		markerProps
	) => (markerProps && typeof markerProps.id === 'string' ? markerProps.id : null);

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
	let effectiveGeoJson: FeatureCollection = geoJson;
	$: effectiveGeoJson =
		toFeature && Array.isArray(items)
			? {
					type: 'FeatureCollection',
					features: items
						.map((i) => toFeature(i))
						.filter((f): f is Feature => f !== null) as Feature[]
				}
			: geoJson;

	// Map instance
	export let map: any = undefined;

	// When MapLibre's style changes (basemap switch), it drops all custom sources/layers.
	// Force the GeoJSON/layer subtree to remount after the new style finishes loading.
	let styleNonce = 0;
	let lastStyleKey: string | null = null;
	let styleKey = basemapType;
	$: styleKey = mapStyle ?? basemapType;
	$: if (map && lastStyleKey !== styleKey) {
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

	let resolvedStyle = getBasemapUrl(basemapType);
	$: resolvedStyle = mapStyle ?? getBasemapUrl(basemapType);

	// Active marker tracking (used for map-level z-index + slot convenience)
	let activeMarkerId: string | null = null;

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
		const mapCenter = map.getCenter();
		const mapZoom = map.getZoom();
		if (mapCenter && typeof mapZoom === 'number') {
			dispatch('mapMove', {
				center: { lng: mapCenter.lng, lat: mapCenter.lat },
				zoom: mapZoom
			});
		}
	}

	function setBasemapType(next: string) {
		basemapType = next;
	}

	// Theme-aware cluster styling (defaults to semantic daisyUI tokens)
	let clusterBaseContent = '#111827';
	let clusterInfo = '#38bdf8';
	let clusterWarning = '#f59e0b';
	let clusterError = '#f87171';
	let clusterInfoContent = '#082f49';
	let clusterWarningContent = '#111827';
	let clusterErrorContent = '#450a0a';

	onMount(() => {
		clusterBaseContent = resolveThemeColor('--color-base-content', clusterBaseContent);
		clusterInfo = resolveThemeColor('--color-info', clusterInfo);
		clusterWarning = resolveThemeColor('--color-warning', clusterWarning);
		clusterError = resolveThemeColor('--color-error', clusterError);
		clusterInfoContent = resolveThemeColor('--color-info-content', clusterInfoContent);
		clusterWarningContent = resolveThemeColor('--color-warning-content', clusterWarningContent);
		clusterErrorContent = resolveThemeColor('--color-error-content', clusterErrorContent);
	});

	let resolvedClusterCirclePaint: Record<string, any> = {};
	let resolvedClusterSymbolLayout: Record<string, any> = {};
	let resolvedClusterSymbolPaint: Record<string, any> = {};

	$: resolvedClusterCirclePaint = clusterCirclePaint ?? {
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

	$: resolvedClusterSymbolLayout = clusterSymbolLayout ?? {
		'text-field': '{point_count_abbreviated}',
		'text-font': ['Open Sans Semibold', 'Open Sans Regular', 'Arial Unicode MS Regular'],
		'text-size': 13
	};

	$: resolvedClusterSymbolPaint = clusterSymbolPaint ?? {
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
</script>

<div class="relative">
	{#if showBasemapSelector}
		{#if $$slots.overlayControls}
			<slot name="overlayControls" {basemapType} {setBasemapType} />
		{:else}
			<div class="absolute top-4 right-4 z-10 bg-base-200 backdrop-blur-sm rounded-lg shadow-lg">
				<div class="p-2">
					<MapStyleSelector bind:basemapType />
				</div>
			</div>
		{/if}
	{/if}

	<MapLibre
		bind:map
		style={resolvedStyle}
		class={mapClass}
		{standardControls}
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
						<MarkerLayer applyToClusters let:feature={clusterFeature}>
							{@const clusterProps = getMarkerProps(clusterFeature)}
							{@const abbreviated = clusterProps && clusterProps['point_count_abbreviated']}
							{@const count = abbreviated ?? (clusterProps && clusterProps['point_count'])}
							{#if typeof count !== 'undefined' && count !== null}
								<div
									class="pointer-events-none select-none font-sans text-xs font-bold text-base-content drop-shadow-sm"
								>
									{count}
								</div>
							{/if}
						</MarkerLayer>
						<MarkerLayer
							applyToClusters={false}
							on:click={handleMarkerLayerClick}
							let:feature={featureData}
						>
							{@const markerProps = getMarkerProps(featureData)}
							{@const markerLngLat = getPointCoordinates(featureData)}
							{@const markerId = getMarkerId(markerProps)}
							{@const isActive = markerId !== null && activeMarkerId === markerId}
							<slot
								name="marker"
								{featureData}
								{markerProps}
								{markerLngLat}
								{isActive}
								setActive={makeSetActive(markerProps)}
							/>
						</MarkerLayer>
					</GeoJSON>
				{:else}
					<GeoJSON id={sourceId} data={effectiveGeoJson} generateId>
						<MarkerLayer
							applyToClusters={false}
							on:click={handleMarkerLayerClick}
							let:feature={featureData}
						>
							{@const markerProps = getMarkerProps(featureData)}
							{@const markerLngLat = getPointCoordinates(featureData)}
							{@const markerId = getMarkerId(markerProps)}
							{@const isActive = markerId !== null && activeMarkerId === markerId}
							<slot
								name="marker"
								{featureData}
								{markerProps}
								{markerLngLat}
								{isActive}
								setActive={makeSetActive(markerProps)}
							/>
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
		<slot {map} />
		<slot name="overlays" {map} />
	</MapLibre>
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
</style>
