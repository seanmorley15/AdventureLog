<script lang="ts">
	// @ts-nocheck
	import type { OpenStreetMapPlace, Point } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { appVersion } from '$lib/config';

	import { DefaultMarker, MapEvents, MapLibre, Popup } from 'svelte-maplibre';

	let markers: Point[] = [];

	export let query: string | null = null;

	if (query) {
		geocode();
	}

	export let longitude: number | null = null;
	export let latitude: number | null = null;

	function addMarker(e: CustomEvent<MouseEvent>) {
		markers = [];
		markers = [...markers, { lngLat: e.detail.lngLat, name: 'Marker 1' }];
		console.log(markers);
	}

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		if (longitude && latitude) {
			markers = [{ lngLat: { lng: longitude, lat: latitude }, name: 'Marker 1' }];
		}
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	let places: OpenStreetMapPlace[] = [];

	async function geocode(e: Event | null) {
		if (e) {
			e.preventDefault();
		}
		if (!query) {
			alert('Please enter a location');
			return;
		}
		let res = await fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=jsonv2`, {
			headers: {
				'User-Agent': `AdventureLog / ${appVersion} `
			}
		});
		console.log(res);
		let data = (await res.json()) as OpenStreetMapPlace[];
		places = data;
	}

	function submit() {
		if (markers.length === 0) {
			alert('Please select a point on the map');
			return;
		}
		let coordArray: [number, number] = [markers[0].lngLat.lng, markers[0].lngLat.lat];
		console.log(coordArray);
		dispatch('submit', coordArray);
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box w-11/12 max-w-4xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<form on:submit={geocode}>
			<input
				type="text"
				placeholder="Seach for a location"
				class="input input-bordered w-full max-w-xs"
				id="search"
				name="search"
				bind:value={query}
			/>
			<button type="submit">Search</button>
		</form>
		<h3 class="font-bold text-lg mb-4">Choose a Point</h3>
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

		{#if places.length > 0}
			<div class="mt-4">
				<h3 class="font-bold text-lg mb-4">Search Results</h3>
				<ul>
					{#each places as place}
						<li>
							<button
								class="btn btn-neutral mb-2"
								on:click={() => {
									markers = [
										{
											lngLat: { lng: Number(place.lon), lat: Number(place.lat) },
											name: place.display_name
										}
									];
								}}
							>
								{place.display_name}
							</button>
						</li>
					{/each}
				</ul>
			</div>
		{:else}
			<p class="text-error text-lg">No results found</p>
		{/if}

		<div class="mb-4 mt-4"></div>
		<button class="btn btn-primary" on:click={submit}>Submit</button>
		<button class="btn btn-neutral" on:click={close}>Close</button>
	</div>
</dialog>
