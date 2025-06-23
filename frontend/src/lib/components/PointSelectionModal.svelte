<script lang="ts">
	// @ts-nocheck
	import type { Location, GeocodeSearchResult, Point } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { appVersion } from '$lib/config';

	import { DefaultMarker, MapEvents, MapLibre, Popup } from 'svelte-maplibre';
	import { getBasemapUrl } from '$lib';

	let markers: Point[] = [];

	export let query: string | null = null;
	export let adventure: Location;

	if (query) {
		geocode();
	}

	function addMarker(e: CustomEvent<MouseEvent>) {
		markers = [];
		markers = [...markers, { lngLat: e.detail.lngLat, name: '' }];
		console.log(markers);
	}

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		if (adventure.longitude && adventure.latitude) {
			markers = [
				{
					lngLat: { lng: adventure.longitude, lat: adventure.latitude },
					name: adventure.name,
					location: adventure.location
				}
			];
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

	let places: GeocodeSearchResult[] = [];

	async function geocode(e: Event | null) {
		if (e) {
			e.preventDefault();
		}
		if (!query) {
			alert('Please enter a location');
			return;
		}
		let res = await fetch(`/api/reverse-geocode/search/?query=${query}`);
		console.log(res);
		let data = (await res.json()) as GeocodeSearchResult[];
		places = data;
	}

	function submit() {
		if (markers.length === 0) {
			alert('Please select a point on the map');
			return;
		}

		console.log(markers[0]);
		adventure.longitude = markers[0].lngLat.lng;
		adventure.latitude = markers[0].lngLat.lat;
		if (!adventure.location) {
			adventure.location = markers[0].location;
		}
		if (!adventure.name) {
			adventure.name = markers[0].name;
		}
		if (adventure.type == 'visited' || adventure.type == 'planned') {
			adventure.tags = [...adventure.tags, markers[0].activity_type];
		}
		dispatch('submit', adventure);
		close();
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
			style={getBasemapUrl()}
			class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full rounded-lg"
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
											location: place.display_name,
											name: place.name,
											activity_type: place.type
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
