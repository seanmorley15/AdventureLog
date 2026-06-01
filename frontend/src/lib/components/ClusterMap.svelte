<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import FullMap from '$lib/components/map/FullMap.svelte';
	import type { ClusterOptions, LayerClickInfo } from 'svelte-maplibre';
	import { resolveThemeColor, withAlpha } from '$lib/utils/resolveThemeColor';

	type PointGeometry = {
		type: 'Point';
		coordinates: [number, number];
	};

	type MarkerProps = {
		name?: string;
		visitStatus?: string;
		country_code?: string;
		[key: string]: unknown;
	} | null;

	type ClusterFeature<P = Record<string, unknown>> = {
		type: 'Feature';
		geometry: PointGeometry;
		properties: P;
	};

	type ClusterFeatureCollection<P = Record<string, unknown>> = {
		type: 'FeatureCollection';
		features: ClusterFeature<P>[];
	};

	export let geoJson: ClusterFeatureCollection = { type: 'FeatureCollection', features: [] };
	export let clusterOptions: ClusterOptions = { radius: 300, maxZoom: 5, minPoints: 1 };
	export let sourceId = 'cluster-source';
	export let basemapType: string = 'default';
	export let mapStyle: string | null = null;
	export let showBasemapSelector: boolean = true;
	export let mapClass = '';
	export let zoom = 2;
	export let standardControls = true;
	export let fitToBounds: boolean = true;
	export let fitPadding: number = 40;
	export let fitMaxZoom: number = 8;
	// Optional level context (e.g. 'country' | 'region' | 'city'). When provided,
	// `fitMaxZooms` can supply level-specific maximum zoom values used when
	// fitting bounds. This lets callers choose different fit zooms for country,
	// region, and city views.
	export let fitLevel: string = '';
	export let fitMaxZooms: Record<string, number> = { country: 4, region: 7, city: 12 };

	// Effective fit max zoom (prefers level-specific value if available)
	let effectiveFitMaxZoom: number = fitMaxZoom;
	$: effectiveFitMaxZoom =
		fitLevel && fitMaxZooms && fitMaxZooms[fitLevel] !== undefined
			? fitMaxZooms[fitLevel]
			: fitMaxZoom;

	export let getMarkerProps: (feature: unknown) => MarkerProps = (feature) =>
		feature && typeof feature === 'object' && feature !== null && 'properties' in (feature as any)
			? ((feature as any).properties as MarkerProps)
			: null;

	export let markerBaseClass =
		'grid px-2 py-1 place-items-center rounded-full border border-gray-200 text-black focus:outline-6 focus:outline-black cursor-pointer whitespace-nowrap';

	export let markerClass: (props: MarkerProps) => string = (props) =>
		props && typeof props.visitStatus === 'string' ? props.visitStatus : '';

	export let markerTitle: (props: MarkerProps) => string = (props) =>
		props && typeof props.name === 'string' ? props.name : '';

	export let markerLabel: (props: MarkerProps) => string = markerTitle;

	const DEFAULT_CLUSTER_CIRCLE_PAINT: Record<string, any> = {
		'circle-color': ['step', ['get', 'point_count'], '#60a5fa', 20, '#facc15', 60, '#f472b6'],
		'circle-radius': ['step', ['get', 'point_count'], 24, 20, 34, 60, 46],
		'circle-opacity': 0.85
	};

	export let clusterCirclePaint: Record<string, any> = DEFAULT_CLUSTER_CIRCLE_PAINT;

	const DEFAULT_CLUSTER_SYMBOL_LAYOUT: Record<string, any> = {
		'text-field': '{point_count_abbreviated}',
		// Use a font stack that works across more basemap styles.
		// Many raster-only styles rely on an external `glyphs` endpoint and won't have Open Sans.
		'text-font': ['Noto Sans Regular', 'Arial Unicode MS Regular'],
		'text-size': 12
	};

	export let clusterSymbolLayout: Record<string, any> = DEFAULT_CLUSTER_SYMBOL_LAYOUT;

	const DEFAULT_CLUSTER_SYMBOL_PAINT: Record<string, any> = { 'text-color': '#1f2937' };
	export let clusterSymbolPaint: Record<string, any> = DEFAULT_CLUSTER_SYMBOL_PAINT;

	onMount(() => {
		// Only apply theme-based defaults when the consumer hasn't overridden them.
		const shouldThemeCircle = clusterCirclePaint === DEFAULT_CLUSTER_CIRCLE_PAINT;
		const shouldThemeLayout = clusterSymbolLayout === DEFAULT_CLUSTER_SYMBOL_LAYOUT;
		const shouldThemeSymbol = clusterSymbolPaint === DEFAULT_CLUSTER_SYMBOL_PAINT;
		if (!shouldThemeCircle && !shouldThemeLayout && !shouldThemeSymbol) return;

		const baseContent = resolveThemeColor('--color-base-content', '#111827');

		// Softer/pastel-ish cluster palette using daisyUI semantic tokens.
		const info = resolveThemeColor('--color-info', '#38bdf8');
		const warning = resolveThemeColor('--color-warning', '#f59e0b');
		const error = resolveThemeColor('--color-error', '#f87171');

		const infoContent = resolveThemeColor('--color-info-content', '#082f49');
		const warningContent = resolveThemeColor('--color-warning-content', '#111827');
		const errorContent = resolveThemeColor('--color-error-content', '#450a0a');

		if (shouldThemeCircle) {
			clusterCirclePaint = {
				// Use daisyUI semantic colors so clusters pop against any basemap.
				'circle-color': [
					'step',
					['get', 'point_count'],
					withAlpha(info, 0.7),
					25,
					withAlpha(warning, 0.7),
					80,
					withAlpha(error, 0.65)
				],
				'circle-radius': ['step', ['get', 'point_count'], 22, 20, 32, 60, 44],
				'circle-opacity': 1,
				'circle-stroke-color': withAlpha(baseContent, 0.25),
				'circle-stroke-width': 2,
				// Keep clusters crisp; blur can look fuzzy on some displays.
				'circle-blur': 0
			};
		}

		if (shouldThemeLayout) {
			clusterSymbolLayout = {
				...clusterSymbolLayout,
				'text-size': 13
			};
		}

		if (shouldThemeSymbol) {
			clusterSymbolPaint = {
				// Keep numbers highly readable: use each fill's matching *-content color.
				'text-color': [
					'step',
					['get', 'point_count'],
					infoContent,
					25,
					warningContent,
					80,
					errorContent
				],
				// Tiny crisp halo just to help glyph edges.
				'text-halo-color': withAlpha(baseContent, 0.12),
				'text-halo-width': 0.75,
				'text-halo-blur': 0
			};
		}
	});

	const dispatch = createEventDispatcher<{
		markerSelect: { feature: unknown; markerProps: MarkerProps; countryCode?: string };
		clusterClick: LayerClickInfo;
	}>();

	let resolvedClusterCirclePaint: Record<string, any> = clusterCirclePaint as Record<string, any>;
	$: resolvedClusterCirclePaint = clusterCirclePaint as Record<string, any>;

	// Map instance (bound from FullMap) and bounding state
	let map: any = undefined;
	let _lastBoundsKey: string | null = null;

	// When `geoJson` changes, compute bounding box and fit map to bounds (only when changed)
	$: if (
		map &&
		fitToBounds &&
		geoJson &&
		Array.isArray(geoJson.features) &&
		geoJson.features.length > 0
	) {
		let minLon = 180;
		let minLat = 90;
		let maxLon = -180;
		let maxLat = -90;

		for (const f of geoJson.features) {
			const coords = (f && f.geometry && f.geometry.coordinates) || null;
			if (!coords || !Array.isArray(coords) || coords.length < 2) continue;
			const lon = Number(coords[0]);
			const lat = Number(coords[1]);
			if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
			minLon = Math.min(minLon, lon);
			minLat = Math.min(minLat, lat);
			maxLon = Math.max(maxLon, lon);
			maxLat = Math.max(maxLat, lat);
		}

		if (minLon <= maxLon && minLat <= maxLat) {
			const boundsKey = `${minLon},${minLat},${maxLon},${maxLat}`;
			if (boundsKey !== _lastBoundsKey) {
				_lastBoundsKey = boundsKey;

				// If bounds represent effectively a single point, use easeTo with a sensible zoom
				const lonDelta = Math.abs(maxLon - minLon);
				const latDelta = Math.abs(maxLat - minLat);
				const isSinglePoint = lonDelta < 1e-6 && latDelta < 1e-6;

				try {
					if (isSinglePoint) {
						const center = [(minLon + maxLon) / 2, (minLat + maxLat) / 2];
						map.easeTo({ center, zoom: Math.max(zoom, effectiveFitMaxZoom), duration: 1000 });
					} else {
						const bounds: [[number, number], [number, number]] = [
							[minLon, minLat],
							[maxLon, maxLat]
						];
						// Use fitBounds to contain all points with padding and a max zoom
						if (typeof map.fitBounds === 'function') {
							map.fitBounds(bounds, {
								padding: fitPadding,
								maxZoom: effectiveFitMaxZoom,
								duration: 1000
							});
						} else {
							// Fallback: center and set zoom if fitBounds not available
							const center = [(minLon + maxLon) / 2, (minLat + maxLat) / 2];
							map.easeTo({ center, duration: 1000 });
						}
					}
				} catch (err) {
					// If something fails (map not ready), ignore — it will re-run when map is available.
					console.error('ClusterMap: fitBounds failed', err);
				}
			}
		}
	}

	function handleClusterClick(event: CustomEvent<LayerClickInfo>) {
		dispatch('clusterClick', event.detail);
	}

	function handleMarkerClick(event: CustomEvent<{ feature: unknown; markerProps: MarkerProps }>) {
		const feature = event.detail?.feature;
		const markerProps = event.detail?.markerProps ?? getMarkerProps(feature);
		const countryCode =
			markerProps && typeof markerProps.country_code === 'string'
				? markerProps.country_code
				: undefined;

		dispatch('markerSelect', { feature, markerProps, countryCode });
	}
</script>

<FullMap
	bind:map
	{mapStyle}
	{basemapType}
	{mapClass}
	{showBasemapSelector}
	{standardControls}
	{zoom}
	{geoJson}
	{sourceId}
	{clusterOptions}
	clusterCirclePaint={resolvedClusterCirclePaint}
	{clusterSymbolLayout}
	{clusterSymbolPaint}
	{getMarkerProps}
	on:clusterClick={handleClusterClick}
	on:markerClick={handleMarkerClick}
>
	<svelte:fragment
		slot="marker"
		let:featureData
		let:markerProps
		let:markerLngLat
		let:isActive
		let:setActive
	>
		<slot name="marker" {featureData} {markerProps} {markerLngLat} {isActive} {setActive}>
			{#if markerProps}
				<button
					type="button"
					class={`${markerBaseClass} ${markerClass(markerProps)}`.trim()}
					title={markerTitle(markerProps)}
					aria-label={markerLabel(markerProps)}
				>
					<span class="text-xs font-medium">{markerLabel(markerProps)}</span>
				</button>
			{/if}
		</slot>
	</svelte:fragment>
</FullMap>

<style>
	:global(.mapboxgl-canvas) {
		border-radius: inherit;
	}
</style>
