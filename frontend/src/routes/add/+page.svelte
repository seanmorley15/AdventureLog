<script lang="ts">
	// @ts-nocheck

	import { DefaultMarker, MapEvents, MapLibre, Popup } from 'svelte-maplibre';
	function addMarker(e: CustomEvent<MapMouseEvent>) {
		markers = [];
		markers = [...markers, { lngLat: e.detail.lngLat }];
		console.log(markers);
	}
	let markers = [];
</script>

<MapLibre
	style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
	class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full"
	standardControls
>
	<!-- MapEvents gives you access to map events even from other components inside the map,
  where you might not have access to the top-level `MapLibre` component. In this case
  it would also work to just use on:click on the MapLibre component itself. -->
	<MapEvents on:click={addMarker} />

	{#each markers as marker}
		<DefaultMarker lngLat={marker.lngLat} />
	{/each}
</MapLibre>
