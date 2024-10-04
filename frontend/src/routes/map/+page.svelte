<script>
	// @ts-nocheck

	import { isAdventureVisited } from '$lib';
	import AdventureModal from '$lib/components/AdventureModal.svelte';
	import {
		DefaultMarker,
		MapEvents,
		MapLibre,
		Popup,
		Marker,
		GeoJSON,
		LineLayer,
		FillLayer,
		SymbolLayer
	} from 'svelte-maplibre';
	export let data;

	let clickedName = '';

	console.log(data);

	let showVisited = true;
	let showPlanned = true;

	$: filteredMarkers = markers.filter(
		(marker) =>
			(showVisited && isAdventureVisited(marker)) || (showPlanned && !isAdventureVisited(marker))
	);

	let newMarker = [];

	let newLongitude = null;
	let newLatitude = null;

	function addMarker(e) {
		newMarker = [];
		newMarker = [...newMarker, { lngLat: e.detail.lngLat, name: 'Marker 1' }];
		newLongitude = e.detail.lngLat.lng;
		newLatitude = e.detail.lngLat.lat;
	}

	let markers = [];

	$: {
		markers = data.props.markers;
	}

	function createNewAdventure(event) {
		let newMarker = {
			lngLat: [event.detail.longitude, event.detail.latitude],
			name: event.detail.name,
			type: event.detail.type,
			visits: event.detail.visits
		};
		markers = [...markers, newMarker];
		clearMarkers();
		createModalOpen = false;
	}
	let visitedRegions = data.props.visitedRegions;

	let allRegions = [];

	let visitArray = [];

	// turns in into an array of the visits
	visitedRegions.forEach((el) => {
		visitArray.push(el.region);
	});

	function clearMarkers() {
		newMarker = [];
		newLatitude = null;
		newLongitude = null;
	}

	// mapped to the checkbox
	let showGEO = false;
	$: {
		if (showGEO && allRegions.length === 0) {
			(async () => {
				allRegions = await fetch('/api/visitedregion/').then((res) => res.json());
			})();
		} else if (!showGEO) {
			allRegions = [];
		}
	}

	let createModalOpen = false;
</script>

<h1 class="text-center font-bold text-4xl">Adventure Map</h1>

<div class="m-2 flex flex-col items-center justify-center">
	<div class="gap-4 border-solid border-2 rounded-lg p-2 mb-4 border-neutral max-w-4xl">
		<p class="font-semibold text-center text-xl mb-2">Map Options</p>
		<div class="flex flex-wrap items-center justify-center gap-4">
			<label class="label cursor-pointer">
				<span class="label-text mr-1">Visited</span>
				<input type="checkbox" bind:checked={showVisited} class="checkbox checkbox-primary" />
			</label>
			<label class="label cursor-pointer">
				<span class="label-text mr-1">Planned</span>
				<input type="checkbox" bind:checked={showPlanned} class="checkbox checkbox-primary" />
			</label>
			<!-- <div class="divider divider-horizontal"></div> -->
			<label for="show-geo">Show Visited Regions</label>
			<input
				type="checkbox"
				id="show-geo"
				name="show-geo"
				class="checkbox"
				bind:checked={showGEO}
			/>
			<!-- <div class="divider divider-horizontal"></div> -->
			{#if newMarker.length > 0}
				<button type="button" class="btn btn-primary mb-2" on:click={() => (createModalOpen = true)}
					>Add New Adventure at Marker</button
				>
				<button type="button" class="btn btn-neutral mb-2" on:click={clearMarkers}
					>Clear Marker</button
				>
			{:else}
				<button type="button" class="btn btn-primary mb-2" on:click={() => (createModalOpen = true)}
					>Add New Adventure</button
				>
			{/if}
		</div>
	</div>
</div>

{#if createModalOpen}
	<AdventureModal
		on:close={() => (createModalOpen = false)}
		on:save={createNewAdventure}
		latitude={newLatitude}
		longitude={newLongitude}
	/>
{/if}

<MapLibre
	style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
	class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full"
	standardControls
>
	{#each filteredMarkers as marker}
		{#if isAdventureVisited(marker)}
			<Marker
				lngLat={marker.lngLat}
				on:click={() => (clickedName = marker.name)}
				class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-red-300 text-black shadow-md"
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
					<div class="text-lg text-black font-bold">{marker.name}</div>
					<p class="font-semibold text-black text-md">Visited</p>
				</Popup>
			</Marker>
		{:else}
			<Marker
				lngLat={marker.lngLat}
				on:click={() => (clickedName = marker.name)}
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
					<div class="text-lg text-black font-bold">{marker.name}</div>
					<p class="font-semibold text-black text-md">Planned</p>
				</Popup>
			</Marker>
		{/if}
	{/each}

	<MapEvents on:click={addMarker} />
	{#each newMarker as marker}
		<DefaultMarker lngLat={marker.lngLat} />
	{/each}

	{#each allRegions as { longitude, latitude, name, region }}
		<Marker
			lngLat={[longitude, latitude]}
			on:click={() => (clickedName = name)}
			class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-green-300 text-black shadow-md"
		>
			<svg
				width="24"
				height="24"
				viewBox="0 0 24 24"
				fill="none"
				xmlns="http://www.w3.org/2000/svg"
			>
				<!-- green circle -->
				<circle cx="12" cy="12" r="10" stroke="green" stroke-width="2" fill="green" />
			</svg>
			<Popup openOn="click" offset={[0, -10]}>
				<div class="text-lg text-black font-bold">{name}</div>
				<p class="font-semibold text-black text-md">{region}</p>
			</Popup>
		</Marker>
	{/each}
</MapLibre>

<svelte:head>
	<title>Travel Map</title>
	<meta name="description" content="View your travels on a map." />
</svelte:head>

<style>
	:global(.map) {
		height: 500px;
	}
</style>
