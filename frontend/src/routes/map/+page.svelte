<script>
	// @ts-nocheck

	import { DefaultMarker, MapEvents, MapLibre, Popup, Marker } from 'svelte-maplibre';
	export let data;

	let clickedName = '';

	let markers = data.props.markers;
	console.log(markers);
</script>

<MapLibre
	style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
	class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full"
	standardControls
>
	{#each data.props.markers as { lngLat, name, type }}
		{#if type == 'visited'}
			<Marker
				{lngLat}
				on:click={() => (clickedName = name)}
				class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-red-300 text-black shadow-2xl focus:outline-2 focus:outline-black"
			>
				<svg
					width="24"
					height="24"
					viewBox="0 0 24 24"
					fill="none"
					xmlns="http://www.w3.org/2000/svg"
				>
					<circle cx="12" cy="12" r="10" stroke="red" stroke-width="2" fill="red" />
				</svg>
				<Popup openOn="click" offset={[0, -10]}>
					<div class="text-lg font-bold">{name}</div>
					<p class="font-semibold text-md">Visited</p>
				</Popup>
			</Marker>
		{/if}

		{#if type == 'planned'}
			<Marker
				{lngLat}
				on:click={() => (clickedName = name)}
				class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-blue-300 text-black shadow-2xl focus:outline-2 focus:outline-black"
			>
				<svg
					width="24"
					height="24"
					viewBox="0 0 24 24"
					fill="none"
					xmlns="http://www.w3.org/2000/svg"
				>
					<circle cx="12" cy="12" r="10" stroke="blue" stroke-width="2" fill="blue" />
				</svg>
				<Popup openOn="click" offset={[0, -10]}>
					<div class="text-lg font-bold">{name}</div>
					<p class="font-semibold text-md">Planned</p>
				</Popup>
			</Marker>
		{/if}
	{/each}
</MapLibre>

<style>
	:global(.map) {
		height: 500px;
	}
</style>
