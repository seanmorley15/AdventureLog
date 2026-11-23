<script lang="ts">
	import { GeoJSON, LineLayer } from 'svelte-maplibre';
	import { getActivityColor } from '#lib';
	import DetailMap from '#lib/components/detail/DetailMap.svelte';
	import ElevationProfile from './ElevationProfile.svelte';
	import { elevationProfile, trackBounds } from './activityForm.js';

	interface Props {
		/** The track as GeoJSON, with elevation as the third coordinate when the file has it. */
		geojson: any;
		sportType?: string;
		measurementSystem?: 'metric' | 'imperial';
	}

	let { geojson, sportType = 'General', measurementSystem = 'metric' }: Props = $props();

	const points = $derived(trackBounds(geojson));
	const profile = $derived(elevationProfile(geojson));
</script>

{#if points.length > 1}
	<div class="space-y-3">
		<DetailMap center={points[0]} fitPoints={points} mapClass="h-56 w-full" basemapType="default">
			<GeoJSON data={geojson}>
				<LineLayer
					paint={{
						'line-color': getActivityColor(sportType),
						'line-width': 4,
						'line-opacity': 0.9
					}}
				/>
			</GeoJSON>
		</DetailMap>
		<ElevationProfile {profile} {measurementSystem} />
	</div>
{/if}
