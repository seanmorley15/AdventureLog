<script lang="ts">
	import { appVersion } from '$lib/config';
	import { addToast } from '$lib/toasts';
	import type { Adventure, Lodging, GeocodeSearchResult, Point, ReverseGeocode } from '$lib/types';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { DefaultMarker, MapEvents, MapLibre } from 'svelte-maplibre';

	export let item: Adventure | Lodging;
	export let triggerMarkVisted: boolean = false;

	export let initialLatLng: { lat: number; lng: number } | null = null; // Used to pass the location from the map selection to the modal

	let reverseGeocodePlace: ReverseGeocode | null = null;
	let markers: Point[] = [];

	let query: string = '';
	let is_custom_location: boolean = false;
	let willBeMarkedVisited: boolean = false;
	let previousCoords: { lat: number; lng: number } | null = null;
	let old_display_name: string = '';
	let places: GeocodeSearchResult[] = [];
	let noPlaces: boolean = false;

	onMount(() => {
		if (initialLatLng) {
			markers = [
				{
					lngLat: { lng: initialLatLng.lng, lat: initialLatLng.lat },
					name: '',
					location: '',
					activity_type: ''
				}
			];
			item.latitude = initialLatLng.lat;
			item.longitude = initialLatLng.lng;
			reverseGeocode();
		}
	});

	$: if (markers.length > 0) {
		const newLat = Math.round(markers[0].lngLat.lat * 1e6) / 1e6;
		const newLng = Math.round(markers[0].lngLat.lng * 1e6) / 1e6;

		if (!previousCoords || previousCoords.lat !== newLat || previousCoords.lng !== newLng) {
			item.latitude = newLat;
			item.longitude = newLng;
			previousCoords = { lat: newLat, lng: newLng };
			reverseGeocode();
		}

		// if (!item.name) {
		// 	item.name = markers[0].name;
		// }
	}

	$: if (triggerMarkVisted && willBeMarkedVisited) {
		displaySuccessToast(); // since the server will trigger the geocode automatically, we just need to show the toast and let the server handle the rest. It's kinda a placebo effect
		triggerMarkVisted = false;
	}

	$: {
		is_custom_location = Boolean(
			item.location != reverseGeocodePlace?.display_name && item.location
		);
	}

	if (item.longitude && item.latitude) {
		markers = [];
		markers = [
			{
				lngLat: { lng: item.longitude, lat: item.latitude },
				location: item.location || '',
				name: item.name,
				activity_type: ''
			}
		];
	}

	$: {
		if ('visits' in item) {
			willBeMarkedVisited = false; // Reset before evaluating

			const today = new Date(); // Cache today's date to avoid redundant calculations

			for (const visit of item.visits) {
				const startDate = new Date(visit.start_date);
				const endDate = visit.end_date ? new Date(visit.end_date) : null;

				// If the visit has both a start date and an end date, check if it started by today
				if (startDate && endDate && startDate <= today) {
					willBeMarkedVisited = true;
					break; // Exit the loop since we've determined the result
				}

				// If the visit has a start date but no end date, check if it started by today
				if (startDate && !endDate && startDate <= today) {
					willBeMarkedVisited = true;
					break; // Exit the loop since we've determined the result
				}
			}
		}
	}

	function displaySuccessToast() {
		if (reverseGeocodePlace) {
			if (reverseGeocodePlace.region) {
				addToast('success', `Visit to ${reverseGeocodePlace.region} marked`);
			}
			if (reverseGeocodePlace.city) {
				addToast('success', `Visit to ${reverseGeocodePlace.city} marked`);
			}
		}
	}

	async function markVisited() {
		console.log(reverseGeocodePlace);
		if (reverseGeocodePlace) {
			if (!reverseGeocodePlace.region_visited && reverseGeocodePlace.region_id) {
				let region_res = await fetch(`/api/visitedregion`, {
					headers: { 'Content-Type': 'application/json' },
					method: 'POST',
					body: JSON.stringify({ region: reverseGeocodePlace.region_id })
				});
				if (region_res.ok) {
					reverseGeocodePlace.region_visited = true;
					addToast('success', `Visit to ${reverseGeocodePlace.region} marked`);
				} else {
					addToast('error', `Failed to mark visit to ${reverseGeocodePlace.region}`);
				}
			}
			if (!reverseGeocodePlace.city_visited && reverseGeocodePlace.city_id != null) {
				let city_res = await fetch(`/api/visitedcity`, {
					headers: { 'Content-Type': 'application/json' },
					method: 'POST',
					body: JSON.stringify({ city: reverseGeocodePlace.city_id })
				});
				if (city_res.ok) {
					reverseGeocodePlace.city_visited = true;
					addToast('success', `Visit to ${reverseGeocodePlace.city} marked`);
				} else {
					addToast('error', `Failed to mark visit to ${reverseGeocodePlace.city}`);
				}
			}
		}
	}

	async function addMarker(e: CustomEvent<any>) {
		markers = [];
		markers = [
			...markers,
			{
				lngLat: e.detail.lngLat,
				name: '',
				location: '',
				activity_type: ''
			}
		];
		console.log(markers);
	}

	async function geocode(e: Event | null) {
		if (e) {
			e.preventDefault();
		}
		if (!query) {
			alert($t('adventures.no_location'));
			return;
		}
		let res = await fetch(`/api/reverse-geocode/search/?query=${query}`);
		console.log(res);
		let data = (await res.json()) as GeocodeSearchResult[];
		places = data;
		if (data.length === 0) {
			noPlaces = true;
		} else {
			noPlaces = false;
		}
	}

	async function reverseGeocode(force_update: boolean = false) {
		let res = await fetch(
			`/api/reverse-geocode/reverse_geocode/?lat=${item.latitude}&lon=${item.longitude}`
		);
		let data = await res.json();
		if (data.error) {
			console.log(data.error);
			reverseGeocodePlace = null;
			return;
		}
		reverseGeocodePlace = data;

		console.log(reverseGeocodePlace);
		console.log(is_custom_location);

		if (
			reverseGeocodePlace &&
			reverseGeocodePlace.display_name &&
			(!is_custom_location || force_update)
		) {
			old_display_name = reverseGeocodePlace.display_name;
			item.location = reverseGeocodePlace.display_name;
			if (reverseGeocodePlace.location_name && !item.name) {
				item.name = reverseGeocodePlace.location_name;
			}
		}
		console.log(data);
	}

	function clearMap() {
		console.log('CLEAR');
		markers = [];
		item.latitude = null;
		item.longitude = null;
	}
</script>

<div class="collapse collapse-plus bg-base-200 mb-4">
	<input type="checkbox" />
	<div class="collapse-title text-xl font-medium">
		{$t('adventures.location_information')}
	</div>
	<div class="collapse-content">
		<!-- <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"> -->
		<div>
			<label for="latitude">{$t('adventures.location')}</label><br />
			<div class="flex items-center">
				<input
					type="text"
					id="location"
					name="location"
					bind:value={item.location}
					class="input input-bordered w-full"
				/>
				{#if is_custom_location}
					<button
						class="btn btn-primary ml-2"
						type="button"
						on:click={() => (item.location = reverseGeocodePlace?.display_name)}
						>{$t('adventures.set_to_pin')}</button
					>
				{/if}
			</div>
		</div>

		<div>
			<form on:submit={geocode} class="mt-2">
				<input
					type="text"
					placeholder={$t('adventures.search_for_location')}
					class="input input-bordered w-full max-w-xs mb-2"
					id="search"
					name="search"
					bind:value={query}
				/>
				<button class="btn btn-neutral -mt-1" type="submit">{$t('navbar.search')}</button>
				<button class="btn btn-neutral -mt-1" type="button" on:click={clearMap}
					>{$t('adventures.clear_map')}</button
				>
			</form>
		</div>
		{#if places.length > 0}
			<div class="mt-4 max-w-full">
				<h3 class="font-bold text-lg mb-4">{$t('adventures.search_results')}</h3>

				<div class="flex flex-wrap">
					{#each places as place}
						<button
							type="button"
							class="btn btn-neutral mb-2 mr-2 max-w-full break-words whitespace-normal text-left"
							on:click={() => {
								markers = [
									{
										lngLat: { lng: Number(place.lon), lat: Number(place.lat) },
										location: place.display_name ?? '',
										name: place.name ?? '',
										activity_type: place.type ?? ''
									}
								];

								item.name = place.name ?? '';
							}}
						>
							<span>{place.name}</span>
							<br />
							<small class="text-xs text-neutral-300">{place.display_name}</small>
						</button>
					{/each}
				</div>
			</div>
		{:else if noPlaces}
			<p class="text-error text-lg">{$t('adventures.no_results')}</p>
		{/if}
		<!-- </div> -->
		<div>
			<MapLibre
				style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
				class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full rounded-lg"
				standardControls
				zoom={item.latitude && item.longitude ? 12 : 1}
				center={{ lng: item.longitude || 0, lat: item.latitude || 0 }}
			>
				<!-- MapEvents gives you access to map events even from other components inside the map,
where you might not have access to the top-level `MapLibre` component. In this case
it would also work to just use on:click on the MapLibre component itself. -->
				<MapEvents on:click={addMarker} />

				{#each markers as marker}
					<DefaultMarker lngLat={marker.lngLat} />
				{/each}
			</MapLibre>
			{#if reverseGeocodePlace}
				<div class="mt-2 p-4 bg-neutral rounded-lg shadow-md">
					<h3 class="text-lg font-bold mb-2">{$t('adventures.location_details')}</h3>
					<p class="mb-1">
						<span class="font-semibold">{$t('adventures.display_name')}:</span>
						{reverseGeocodePlace.city
							? reverseGeocodePlace.city + ', '
							: ''}{reverseGeocodePlace.region}, {reverseGeocodePlace.country}
					</p>
					<p class="mb-1">
						<span class="font-semibold">{$t('adventures.region')}:</span>
						{reverseGeocodePlace.region}
						{reverseGeocodePlace.region_visited ? '✅' : '❌'}
					</p>
					{#if reverseGeocodePlace.city}
						<p class="mb-1">
							<span class="font-semibold">{$t('adventures.city')}:</span>
							{reverseGeocodePlace.city}
							{reverseGeocodePlace.city_visited ? '✅' : '❌'}
						</p>
					{/if}
				</div>
				{#if !reverseGeocodePlace.region_visited || (!reverseGeocodePlace.city_visited && !willBeMarkedVisited)}
					<button type="button" class="btn btn-primary mt-2" on:click={markVisited}>
						{$t('adventures.mark_visited')}
					</button>
				{/if}
				{#if (willBeMarkedVisited && !reverseGeocodePlace.region_visited && reverseGeocodePlace.region_id) || (!reverseGeocodePlace.city_visited && willBeMarkedVisited && reverseGeocodePlace.city_id)}
					<div role="alert" class="alert alert-info mt-2 flex items-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							class="h-6 w-6 shrink-0 stroke-current mr-2"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							></path>
						</svg>
						<span>
							{reverseGeocodePlace.city
								? reverseGeocodePlace.city + ', '
								: ''}{reverseGeocodePlace.region}, {reverseGeocodePlace.country}
							{$t('adventures.will_be_marked')}
						</span>
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>
