<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { MapLibre, Marker, MapEvents } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { getBasemapUrl } from '$lib';

	// Icons
	import SearchIcon from '~icons/mdi/magnify';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import MapIcon from '~icons/mdi/map';
	import CheckIcon from '~icons/mdi/check';
	import ClearIcon from '~icons/mdi/close';
	import PinIcon from '~icons/mdi/map-marker';

	const dispatch = createEventDispatcher();

	let searchQuery = '';
	let searchResults: any[] = [];
	let selectedLocation: any = null;
	let mapCenter: [number, number] = [-74.5, 40];
	let mapZoom = 2;
	let isSearching = false;
	let isReverseGeocoding = false;
	let searchTimeout: ReturnType<typeof setTimeout>;
	let mapComponent: any;
	let selectedMarker: { lng: number; lat: number } | null = null;

	// Search for locations using the API
	async function searchLocations(query: string) {
		if (!query.trim() || query.length < 3) {
			searchResults = [];
			return;
		}

		isSearching = true;
		try {
			const response = await fetch(
				`/api/reverse-geocode/search/?query=${encodeURIComponent(query)}`
			);
			const results = await response.json();

			searchResults = results.map((result: any) => ({
				id: result.name + result.lat + result.lon,
				name: result.name,
				lat: parseFloat(result.lat),
				lng: parseFloat(result.lon),
				type: result.type,
				category: result.category,
				location: result.display_name,
				importance: result.importance
			}));
		} catch (error) {
			console.error('Search error:', error);
			searchResults = [];
		} finally {
			isSearching = false;
		}
	}

	// Debounced search
	function handleSearchInput() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			searchLocations(searchQuery);
		}, 300);
	}

	// Select a location from search results
	async function selectSearchResult(location: any) {
		selectedLocation = location;
		selectedMarker = { lng: location.lng, lat: location.lat };
		mapCenter = [location.lng, location.lat];
		mapZoom = 14;
		searchResults = [];
		searchQuery = location.name;
	}

	// Handle map click to place marker
	async function handleMapClick(e: { detail: { lngLat: { lng: number; lat: number } } }) {
		selectedMarker = {
			lng: e.detail.lngLat.lng,
			lat: e.detail.lngLat.lat
		};
		await reverseGeocode(e.detail.lngLat.lng, e.detail.lngLat.lat);
	}

	// Reverse geocode coordinates
	async function reverseGeocode(lng: number, lat: number) {
		isReverseGeocoding = true;

		try {
			const response = await fetch(`/api/reverse-geocode/search/?query=${lat},${lng}`);
			const results = await response.json();

			if (results && results.length > 0) {
				const result = results[0];
				selectedLocation = {
					name: result.name,
					lat: lat,
					lng: lng,
					location: result.display_name,
					type: result.type,
					category: result.category
				};
				searchQuery = result.name;
			} else {
				selectedLocation = {
					name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
					lat: lat,
					lng: lng,
					location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
				};
				searchQuery = selectedLocation.name;
			}
		} catch (error) {
			console.error('Reverse geocoding error:', error);
			selectedLocation = {
				name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
				lat: lat,
				lng: lng,
				location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
			};
			searchQuery = selectedLocation.name;
		} finally {
			isReverseGeocoding = false;
		}
	}

	// Use current location
	function useCurrentLocation() {
		if ('geolocation' in navigator) {
			navigator.geolocation.getCurrentPosition(
				async (position) => {
					const lat = position.coords.latitude;
					const lng = position.coords.longitude;
					selectedMarker = { lng, lat };
					mapCenter = [lng, lat];
					mapZoom = 14;
					await reverseGeocode(lng, lat);
				},
				(error) => {
					console.error('Geolocation error:', error);
				}
			);
		}
	}

	// Continue with selected location
	function continueWithLocation() {
		if (selectedLocation && selectedMarker) {
			dispatch('locationSelected', {
				name: selectedLocation.name,
				latitude: selectedMarker.lat,
				longitude: selectedMarker.lng,
				location: selectedLocation.location
			});
		} else {
			dispatch('next');
		}
	}

	// Clear selection
	function clearSelection() {
		selectedLocation = null;
		selectedMarker = null;
		searchQuery = '';
		searchResults = [];
		mapCenter = [-74.5, 40];
		mapZoom = 2;
	}

	onMount(() => {
		return () => {
			clearTimeout(searchTimeout);
		};
	});
</script>

<div class="space-y-6">
	<!-- Search Section -->
	<div class="card bg-base-200/50 border border-base-300">
		<div class="card-body p-6">
			<div class="space-y-4">
				<!-- Search Input -->
				<div class="form-control">
					<label class="label">
						<span class="label-text font-medium">
							{$t('adventures.search_location') || 'Search for a location'}
						</span>
					</label>
					<div class="relative">
						<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
							<SearchIcon class="w-5 h-5 text-base-content/40" />
						</div>
						<input
							type="text"
							bind:value={searchQuery}
							on:input={handleSearchInput}
							placeholder={$t('lodging.search_placeholder') || 'Enter hotel, address, or city...'}
							class="input input-bordered w-full pl-10 pr-4"
							class:input-primary={selectedLocation}
						/>
						{#if searchQuery && !selectedLocation}
							<button
								class="absolute inset-y-0 right-0 pr-3 flex items-center"
								on:click={clearSelection}
							>
								<ClearIcon class="w-4 h-4 text-base-content/40 hover:text-base-content" />
							</button>
						{/if}
					</div>
				</div>

				<!-- Search Results -->
				{#if isSearching}
					<div class="flex items-center justify-center py-4">
						<span class="loading loading-spinner loading-sm"></span>
						<span class="ml-2 text-sm text-base-content/60">{$t('adventures.searching')}...</span>
					</div>
				{:else if searchResults.length > 0}
					<div class="space-y-2">
						<label class="label">
							<span class="label-text text-sm font-medium">{$t('adventures.search_results')}</span>
						</label>
						<div class="max-h-48 overflow-y-auto space-y-1">
							{#each searchResults as result}
								<button
									class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-primary/50 transition-colors"
									on:click={() => selectSearchResult(result)}
								>
									<div class="flex items-start gap-3">
										<PinIcon class="w-4 h-4 text-primary mt-1 flex-shrink-0" />
										<div class="min-w-0 flex-1">
											<div class="font-medium text-sm truncate">{result.name}</div>
											<div class="text-xs text-base-content/60 truncate">{result.location}</div>
										</div>
									</div>
								</button>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Current Location Button -->
				<div class="flex items-center gap-2">
					<div class="divider divider-horizontal text-xs">OR</div>
				</div>

				<button class="btn btn-outline gap-2 w-full" on:click={useCurrentLocation}>
					<LocationIcon class="w-4 h-4" />
					{$t('adventures.use_current_location') || 'Use Current Location'}
				</button>
			</div>
		</div>
	</div>

	<!-- Map Section -->
	<div class="card bg-base-100 border border-base-300">
		<div class="card-body p-4">
			<div class="flex items-center justify-between mb-4">
				<h3 class="font-semibold flex items-center gap-2">
					<MapIcon class="w-5 h-5" />
					{$t('adventures.select_on_map') || 'Select on Map'}
				</h3>
				{#if selectedMarker}
					<button class="btn btn-ghost btn-sm gap-1" on:click={clearSelection}>
						<ClearIcon class="w-4 h-4" />
						Clear
					</button>
				{/if}
			</div>

			{#if !selectedMarker}
				<p class="text-sm text-base-content/60 mb-4">
					{$t('adventures.click_map') || 'Click on the map to select a location'}
				</p>
			{/if}

			{#if isReverseGeocoding}
				<div class="flex items-center justify-center py-2 mb-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="ml-2 text-sm text-base-content/60"
						>{$t('adventures.getting_location_details')}...</span
					>
				</div>
			{/if}

			<div class="relative">
				<MapLibre
					bind:this={mapComponent}
					style={getBasemapUrl()}
					class="w-full h-80 rounded-lg border border-base-300"
					center={mapCenter}
					zoom={mapZoom}
					standardControls
				>
					<MapEvents on:click={handleMapClick} />

					{#if selectedMarker}
						<Marker
							lngLat={[selectedMarker.lng, selectedMarker.lat]}
							class="grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-primary shadow-lg cursor-pointer"
						>
							<PinIcon class="w-5 h-5 text-primary-content" />
						</Marker>
					{/if}
				</MapLibre>
			</div>
		</div>
	</div>

	<!-- Selected Location Display -->
	{#if selectedLocation && selectedMarker}
		<div class="card bg-success/10 border border-success/30">
			<div class="card-body p-4">
				<div class="flex items-start gap-3">
					<div class="p-2 bg-success/20 rounded-lg">
						<CheckIcon class="w-5 h-5 text-success" />
					</div>
					<div class="flex-1 min-w-0">
						<h4 class="font-semibold text-success mb-1">{$t('adventures.location_selected')}</h4>
						<p class="text-sm text-base-content/80 truncate">{selectedLocation.name}</p>
						<p class="text-xs text-base-content/60 mt-1">
							{selectedMarker.lat.toFixed(6)}, {selectedMarker.lng.toFixed(6)}
						</p>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Action Buttons -->
	<div class="flex gap-3 pt-4">
		<button class="btn btn-neutral-200 flex-1" on:click={() => dispatch('cancel')}>
			{$t('adventures.cancel') || 'Cancel'}
		</button>
		<button class="btn btn-primary flex-1" on:click={continueWithLocation}>
			{#if isReverseGeocoding}
				<span class="loading loading-spinner loading-xs"></span>
				{$t('adventures.getting_location_details') || 'Getting details...'}
			{:else}
				{$t('adventures.continue')}
			{/if}
		</button>
	</div>
</div>
