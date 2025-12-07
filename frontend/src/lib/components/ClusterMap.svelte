<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { CircleLayer, GeoJSON, MapLibre, MarkerLayer, SymbolLayer } from 'svelte-maplibre';
	import type { ClusterOptions, LayerClickInfo } from 'svelte-maplibre';
	import { getBasemapUrl } from '$lib';

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

	type ClusterSource = {
		getClusterExpansionZoom: (
			clusterId: number,
			callback: (error: unknown, zoom: number) => void
		) => void;
	};

	export let geoJson: ClusterFeatureCollection = { type: 'FeatureCollection', features: [] };
	export let clusterOptions: ClusterOptions = { radius: 300, maxZoom: 5, minPoints: 1 };
	export let sourceId = 'cluster-source';
	export let mapStyle: string = getBasemapUrl();
	export let mapClass = '';
	export let zoom = 2;
	export let standardControls = true;

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

	export let clusterCirclePaint = {
		'circle-color': ['step', ['get', 'point_count'], '#60a5fa', 20, '#facc15', 60, '#f472b6'],
		'circle-radius': ['step', ['get', 'point_count'], 24, 20, 34, 60, 46],
		'circle-opacity': 0.85
	};

	export let clusterSymbolLayout = {
		'text-field': '{point_count_abbreviated}',
		'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
		'text-size': 12
	};

	export let clusterSymbolPaint = { 'text-color': '#1f2937' };

	const dispatch = createEventDispatcher<{
		markerSelect: { feature: unknown; markerProps: MarkerProps; countryCode?: string };
		clusterClick: LayerClickInfo;
	}>();

	let resolvedClusterCirclePaint: Record<string, unknown> = clusterCirclePaint;
	$: resolvedClusterCirclePaint = clusterCirclePaint as Record<string, unknown>;

	function handleClusterClick(event: CustomEvent<LayerClickInfo>) {
		const { clusterId, features, map, source } = event.detail;
		if (!clusterId || !features?.length) {
			return;
		}

		const clusterFeature = features[0] as {
			geometry?: { type?: string; coordinates?: [number, number] };
		};

		const coordinates =
			clusterFeature?.geometry?.type === 'Point' ? clusterFeature.geometry.coordinates : undefined;
		if (!coordinates) {
			return;
		}

		const geoJsonSource = map.getSource(source) as ClusterSource | undefined;
		if (!geoJsonSource || typeof geoJsonSource.getClusterExpansionZoom !== 'function') {
			return;
		}

		geoJsonSource.getClusterExpansionZoom(
			Number(clusterId),
			(error: unknown, zoomLevel: number) => {
				if (error) {
					console.error('Failed to expand cluster', error);
					return;
				}

				map.easeTo({
					center: coordinates,
					zoom: zoomLevel
				});
			}
		);

		dispatch('clusterClick', event.detail);
	}

	function handleMarkerClick(event: CustomEvent<any>) {
		const feature = event.detail?.feature;
		const markerProps = getMarkerProps(feature);
		const countryCode =
			markerProps && typeof markerProps.country_code === 'string'
				? markerProps.country_code
				: undefined;

		dispatch('markerSelect', { feature, markerProps, countryCode });
	}
</script>

<MapLibre style={mapStyle} class={mapClass} {standardControls} {zoom}>
	<GeoJSON id={sourceId} data={geoJson} cluster={clusterOptions} generateId>
		<CircleLayer
			id={`${sourceId}-clusters`}
			applyToClusters
			hoverCursor="pointer"
			paint={resolvedClusterCirclePaint}
			on:click={handleClusterClick}
		/>
		<SymbolLayer
			id={`${sourceId}-cluster-count`}
			applyToClusters
			layout={clusterSymbolLayout}
			paint={clusterSymbolPaint}
		/>
		<MarkerLayer applyToClusters={false} on:click={handleMarkerClick} let:feature={featureData}>
			{@const markerProps = getMarkerProps(featureData)}
			<slot name="marker" {featureData} {markerProps}>
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
		</MarkerLayer>
	</GeoJSON>
</MapLibre>

<style>
	:global(.mapboxgl-canvas) {
		border-radius: inherit;
	}
</style>
