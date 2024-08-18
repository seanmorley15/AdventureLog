<script>
	// @ts-nocheck
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

	let showVisited = true;
	let showPlanned = true;

	$: {
		if (!showVisited) {
			markers = data.props.markers.filter((marker) => marker.type !== 'visited');
		} else {
			const visitedMarkers = data.props.markers.filter((marker) => marker.type === 'visited');
			markers = [...markers, ...visitedMarkers];
		}
		if (!showPlanned) {
			markers = data.props.markers.filter((marker) => marker.type !== 'planned');
		} else {
			const plannedMarkers = data.props.markers.filter((marker) => marker.type === 'planned');
			markers = [...markers, ...plannedMarkers];
		}
		console.log(markers);
	}

	let newMarker = [];

	let newLongitude = null;
	let newLatitude = null;

	function addMarker(e) {
		newMarker = [];
		newMarker = [...newMarker, { lngLat: e.detail.lngLat, name: 'Marker 1' }];
		console.log(newMarker);
		newLongitude = e.detail.lngLat.lng;
		newLatitude = e.detail.lngLat.lat;
	}

	let markers = [];

	$: {
		markers = data.props.markers;
	}

	function createNewAdventure(event) {
		console.log(event.detail);

		let newMarker = {
			lngLat: [event.detail.longitude, event.detail.latitude],
			name: event.detail.name,
			type: 'planned'
		};
		markers = [...markers, newMarker];
		clearMarkers();
		console.log(markers);
		createModalOpen = false;
	}

	let visitedRegions = data.props.visitedRegions;

	let geoJSON = [];

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
		if (showGEO && geoJSON.length === 0) {
			(async () => {
				geoJSON = await fetch('/api/geojson/').then((res) => res.json());
			})();
		} else if (!showGEO) {
			geoJSON = [];
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
			<label for="show-geo">Show Borders</label>
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
	{#each markers as { lngLat, name, type }}
		{#if type == 'visited'}
			<Marker
				{lngLat}
				on:click={() => (clickedName = name)}
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
					<div class="text-lg text-black font-bold">{name}</div>
					<p class="font-semibold text-black text-md">Visited</p>
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
					<div class="text-lg text-black font-bold">{name}</div>
					<p class="font-semibold text-black text-md">Planned</p>
				</Popup>
			</Marker>
		{/if}
	{/each}
	{#if showGEO}
		<GeoJSON id="states" data={geoJSON} promoteId="ISOCODE">
			<LineLayer
				layout={{ 'line-cap': 'round', 'line-join': 'round' }}
				paint={{ 'line-color': 'grey', 'line-width': 3 }}
				beforeLayerType="symbol"
			/>
			<FillLayer
				paint={{ 'fill-color': 'rgba(37, 244, 26, 0.15)' }}
				filter={['in', 'ISOCODE', ...visitArray]}
			/>
			<SymbolLayer
				layout={{
					'text-field': ['get', 'name'],
					'text-size': 12,
					'text-anchor': 'center'
				}}
				paint={{
					'text-color': 'black'
				}}
			/>
		</GeoJSON>
	{/if}
	<MapEvents on:click={addMarker} />
	{#each newMarker as marker}
		<DefaultMarker lngLat={marker.lngLat} />
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
