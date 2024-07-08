<script>
	// @ts-nocheck

	import { DefaultMarker, MapEvents, MapLibre, Popup } from 'svelte-maplibre';
	export let data;

	let markers = data.props.markers;
	console.log(markers);
</script>

<MapLibre
	style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
	class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full"
	standardControls
>
	{#each data.props.markers as { lngLat, name }}
		<!-- Unlike the custom marker example, default markers do not have mouse events,
    and popups only support the default openOn="click" behavior -->
		<DefaultMarker {lngLat}>
			<Popup offset={[0, -10]}>
				<div class="text-lg font-bold">{name}</div>
			</Popup>
		</DefaultMarker>
	{/each}
</MapLibre>

<style>
	:global(.map) {
		height: 500px;
	}
</style>
