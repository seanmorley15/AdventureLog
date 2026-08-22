<script lang="ts">
	import { GeoJSON, FillLayer, LineLayer } from 'svelte-maplibre';
	import { circleFeatureCollection } from '$lib/map/circleGeoJson';

	export let visible = false;
	export let center: { lng: number; lat: number } | null = null;
	export let radiusMeters = 5000;

	const SOURCE_ID = 'map-nearby-radius';

	$: circleData =
		visible && center && Number.isFinite(center.lng) && Number.isFinite(center.lat)
			? circleFeatureCollection(center.lng, center.lat, radiusMeters)
			: { type: 'FeatureCollection' as const, features: [] };
</script>

{#if visible && center}
	<GeoJSON id={SOURCE_ID} data={circleData}>
		<FillLayer
			paint={{
				'fill-color': '#6366f1',
				'fill-opacity': 0.1
			}}
		/>
		<LineLayer
			paint={{
				'line-color': '#6366f1',
				'line-width': 2,
				'line-opacity': 0.55,
				'line-dasharray': [2, 2]
			}}
		/>
	</GeoJSON>
{/if}
