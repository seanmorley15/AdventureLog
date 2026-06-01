<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import FullMap from '$lib/components/map/FullMap.svelte';
	import { Marker } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';

	import SearchIcon from '~icons/mdi/magnify';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import MapIcon from '~icons/mdi/map';
	import CheckIcon from '~icons/mdi/check';
	import ClearIcon from '~icons/mdi/close';
	import PinIcon from '~icons/mdi/map-marker';
	import AirplaneIcon from '~icons/mdi/airplane';
	import SwapIcon from '~icons/mdi/swap-horizontal';

	type GeoSelection = {
		name: string;
		lat: number;
		lng: number;
		location: string;
		type?: string;
		category?: string;
	};

	type LocationMeta = {
		city?: { name: string; id: string; visited: boolean };
		region?: { name: string; id: string; visited: boolean };
		country?: { name: string; country_code: string; visited: boolean };
		display_name?: string;
		location_name?: string;
	};

	const dispatch = createEventDispatcher();

	export let initialSelection: GeoSelection | null = null;
	export let searchQuery = '';
	export let displayName = '';
	export let showDisplayNameInput = true;
	export let displayNamePosition: 'before' | 'after' = 'before';
	export let displayNameLabel = '';
	export let displayNamePlaceholder = '';
	export let basemapType: string = 'default';
	export let isReverseGeocoding = false;
	export let transportationMode = false; // New prop for transportation mode
	export let airportMode = false; // New prop for airport-specific search
	// Props for initial transportation locations when editing
	export let initialStartLocation: {
		name: string;
		lat: number;
		lng: number;
		location: string;
	} | null = null;
	export let initialEndLocation: {
		name: string;
		lat: number;
		lng: number;
		location: string;
	} | null = null;
	export let initialStartCode: string | null = null;
	export let initialEndCode: string | null = null;

	let isSearching = false;
	let searchResults: GeoSelection[] = [];
	let selectedLocation: GeoSelection | null = null;
	let selectedMarker: { lng: number; lat: number } | null = null;
	let locationData: LocationMeta | null = null;
	let mapCenter: [number, number] = [-74.5, 40];
	let mapZoom: number | undefined = 2;
	let mapBounds: [[number, number], [number, number]] | null = null;
	let searchTimeout: ReturnType<typeof setTimeout>;
	let initialApplied = false;
	let initialTransportationApplied = false;
	let isInitializing = false;

	function isFiniteCoordinatePair(lat: unknown, lng: unknown): boolean {
		return Number.isFinite(Number(lat)) && Number.isFinite(Number(lng));
	}

	// Track any provided codes (airport / station / etc)
	let startCode: string | null = null;
	let endCode: string | null = null;

	// track previous airport mode to detect toggles
	let prevAirportMode = airportMode;
	let airportModeInitialized = false;

	// Clear inputs/selections when airportMode is toggled (but not during initial setup)
	$: if (prevAirportMode !== airportMode) {
		prevAirportMode = airportMode;

		// Only clear if this is not the first time airportMode is being set
		// This prevents wiping out initial location data when editing existing plane transportations
		if (airportModeInitialized) {
			// clear single-location search state
			searchQuery = '';
			searchResults = [];
			selectedLocation = null;
			selectedMarker = null;
			locationData = null;

			// clear transportation-mode search state
			startSearchQuery = '';
			endSearchQuery = '';
			startSearchResults = [];
			endSearchResults = [];
			selectedStartLocation = null;
			selectedEndLocation = null;
			startMarker = null;
			endMarker = null;
			mapBounds = null;
			startLocationData = null;
			startCode = null;
			endCode = null;
			endLocationData = null;
		}

		airportModeInitialized = true;
	}

	// Transportation mode variables
	let startSearchQuery = '';
	let endSearchQuery = '';
	let startSearchResults: GeoSelection[] = [];
	let endSearchResults: GeoSelection[] = [];
	let selectedStartLocation: GeoSelection | null = null;
	let selectedEndLocation: GeoSelection | null = null;
	let startMarker: { lng: number; lat: number } | null = null;
	let endMarker: { lng: number; lat: number } | null = null;
	let startLocationData: LocationMeta | null = null;
	let endLocationData: LocationMeta | null = null;
	let isSearchingStart = false;
	let isSearchingEnd = false;
	let startSearchTimeout: ReturnType<typeof setTimeout>;
	let endSearchTimeout: ReturnType<typeof setTimeout>;

	async function applyInitialSelection(selection: GeoSelection) {
		selectedLocation = selection;
		selectedMarker = { lng: selection.lng, lat: selection.lat };
		mapCenter = [selection.lng, selection.lat];
		mapZoom = 14;
		searchQuery = selection.location || selection.name || '';
		displayName = selection.location || selection.name;
		await performDetailedReverseGeocode(selection.lat, selection.lng);
	}

	async function applyInitialTransportationLocations() {
		isInitializing = true;

		if (initialStartLocation) {
			selectedStartLocation = {
				name: initialStartLocation.name,
				lat: initialStartLocation.lat,
				lng: initialStartLocation.lng,
				location: initialStartLocation.location
			};
			startMarker = { lng: initialStartLocation.lng, lat: initialStartLocation.lat };
			if (airportMode) {
				startCode =
					initialStartCode || deriveCode(initialStartLocation.name, initialStartLocation.name);
				startSearchQuery = startCode || initialStartLocation.location || initialStartLocation.name;
			} else {
				startCode = null;
				startSearchQuery = initialStartLocation.location || initialStartLocation.name;
			}
			// Never perform reverse geocoding when we have initial location data
			// to avoid overwriting airport names with generic locations
		}

		if (initialEndLocation) {
			selectedEndLocation = {
				name: initialEndLocation.name,
				lat: initialEndLocation.lat,
				lng: initialEndLocation.lng,
				location: initialEndLocation.location
			};
			endMarker = { lng: initialEndLocation.lng, lat: initialEndLocation.lat };
			if (airportMode) {
				endCode = initialEndCode || deriveCode(initialEndLocation.name, initialEndLocation.name);
				endSearchQuery = endCode || initialEndLocation.location || initialEndLocation.name;
			} else {
				endCode = null;
				endSearchQuery = initialEndLocation.location || initialEndLocation.name;
			}
			// Never perform reverse geocoding when we have initial location data
			// to avoid overwriting airport names with generic locations
		}

		updateMapBounds();
		emitTransportationUpdate();

		// Small delay to ensure all reactive updates complete before allowing searches
		setTimeout(() => {
			isInitializing = false;
		}, 100);
	}

	async function searchLocations(query: string) {
		if (!query.trim() || query.length < 3) {
			searchResults = [];
			return;
		}

		isSearching = true;
		try {
			const searchTerm = airportMode ? `${query} Airport` : query;
			const response = await fetch(
				`/api/reverse-geocode/search/?query=${encodeURIComponent(searchTerm)}`
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
				importance: result.importance,
				powered_by: result.powered_by
			}));
		} catch (error) {
			console.error('Search error:', error);
			searchResults = [];
		} finally {
			isSearching = false;
		}
	}

	async function searchStartLocation(query: string) {
		if (!query.trim() || query.length < 3) {
			startSearchResults = [];
			return;
		}

		isSearchingStart = true;
		try {
			const searchTerm = airportMode ? `${query} Airport` : query;
			const response = await fetch(
				`/api/reverse-geocode/search/?query=${encodeURIComponent(searchTerm)}`
			);
			const results = await response.json();

			startSearchResults = results.map((result: any) => ({
				id: result.name + result.lat + result.lon,
				name: result.name,
				lat: parseFloat(result.lat),
				lng: parseFloat(result.lon),
				type: result.type,
				category: result.category,
				location: result.display_name,
				importance: result.importance,
				powered_by: result.powered_by
			}));
		} catch (error) {
			console.error('Search error:', error);
			startSearchResults = [];
		} finally {
			isSearchingStart = false;
		}
	}

	async function searchEndLocation(query: string) {
		if (!query.trim() || query.length < 3) {
			endSearchResults = [];
			return;
		}

		isSearchingEnd = true;
		try {
			const searchTerm = airportMode ? `${query} Airport` : query;
			const response = await fetch(
				`/api/reverse-geocode/search/?query=${encodeURIComponent(searchTerm)}`
			);
			const results = await response.json();

			endSearchResults = results.map((result: any) => ({
				id: result.name + result.lat + result.lon,
				name: result.name,
				lat: parseFloat(result.lat),
				lng: parseFloat(result.lon),
				type: result.type,
				category: result.category,
				location: result.display_name,
				importance: result.importance,
				powered_by: result.powered_by
			}));
		} catch (error) {
			console.error('Search error:', error);
			endSearchResults = [];
		} finally {
			isSearchingEnd = false;
		}
	}

	function handleSearchInput() {
		if (isInitializing) return;
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			searchLocations(searchQuery);
		}, 300);
	}

	function handleStartSearchInput() {
		if (isInitializing) return;
		clearTimeout(startSearchTimeout);
		startSearchTimeout = setTimeout(() => {
			searchStartLocation(startSearchQuery);
		}, 300);
	}

	function handleEndSearchInput() {
		if (isInitializing) return;
		clearTimeout(endSearchTimeout);
		endSearchTimeout = setTimeout(() => {
			searchEndLocation(endSearchQuery);
		}, 300);
	}

	function deriveCode(value: string | undefined, fallback?: string): string | null {
		if (!value && !fallback) return null;
		const match = value?.match(/\b([A-Z0-9]{3,5})\b/) || value?.match(/\(([A-Z0-9]{3,5})\)/);
		if (match && match[1]) return match[1].toUpperCase();
		const candidate = (fallback || '').trim();
		if (candidate.length && candidate.length <= 5) return candidate.toUpperCase();
		return null;
	}

	function resolveCode(selection: GeoSelection | null, typedQuery: string): string | null {
		// Prefer explicit user-typed code when in airport mode
		const fromTyped = deriveCode(typedQuery, typedQuery);
		if (fromTyped) return fromTyped;
		if (selection) {
			const fromName = deriveCode(selection.name, typedQuery);
			if (fromName) return fromName;
			const fromLocation = deriveCode(selection.location, typedQuery);
			if (fromLocation) return fromLocation;
		}
		return null;
	}

	function emitUpdate(selection: GeoSelection) {
		dispatch('update', {
			name: selection.name,
			lat: selection.lat,
			lng: selection.lng,
			location: selection.location
		});
	}

	function emitTransportationUpdate() {
		if (selectedStartLocation && selectedEndLocation) {
			dispatch('transportationUpdate', {
				start: {
					name: selectedStartLocation.name,
					lat: selectedStartLocation.lat,
					lng: selectedStartLocation.lng,
					location: selectedStartLocation.location,
					code: startCode
				},
				end: {
					name: selectedEndLocation.name,
					lat: selectedEndLocation.lat,
					lng: selectedEndLocation.lng,
					location: selectedEndLocation.location,
					code: endCode
				}
			});
		}
	}

	async function selectSearchResult(searchResult: GeoSelection) {
		selectedLocation = searchResult;
		selectedMarker = { lng: searchResult.lng, lat: searchResult.lat };
		mapCenter = [searchResult.lng, searchResult.lat];
		mapZoom = 14;
		searchResults = [];
		searchQuery = searchResult.location || searchResult.name;

		displayName = searchResult.location || searchResult.name;

		emitUpdate(searchResult);
		await performDetailedReverseGeocode(searchResult.lat, searchResult.lng);
	}

	async function selectStartSearchResult(searchResult: GeoSelection) {
		selectedStartLocation = searchResult;
		startMarker = { lng: searchResult.lng, lat: searchResult.lat };
		startSearchResults = [];

		const typedQuery = startSearchQuery;

		// Only auto-derive and surface codes in airport mode
		if (airportMode) {
			const airportCodeMatch = searchResult.name.match(/\(([A-Z]{3})\)/);
			startSearchQuery = airportCodeMatch ? airportCodeMatch[1] : searchResult.name;
			startCode = resolveCode(searchResult, typedQuery);
			if (!startCode) {
				startCode =
					deriveCode(searchResult.name, startSearchQuery) || deriveCode(searchResult.location);
			}
			if (startCode) {
				startSearchQuery = startCode;
			}
		} else {
			startSearchQuery = searchResult.location || searchResult.name;
			startCode = null;
		}

		await performDetailedReverseGeocode(searchResult.lat, searchResult.lng, 'start');
		updateMapBounds();
		emitTransportationUpdate();
	}

	async function selectEndSearchResult(searchResult: GeoSelection) {
		selectedEndLocation = searchResult;
		endMarker = { lng: searchResult.lng, lat: searchResult.lat };
		endSearchResults = [];

		const typedQuery = endSearchQuery;

		// Only auto-derive and surface codes in airport mode
		if (airportMode) {
			const airportCodeMatch = searchResult.name.match(/\(([A-Z]{3})\)/);
			endSearchQuery = airportCodeMatch ? airportCodeMatch[1] : searchResult.name;
			endCode = resolveCode(searchResult, typedQuery);
			if (!endCode) {
				endCode =
					deriveCode(searchResult.name, endSearchQuery) || deriveCode(searchResult.location);
			}
			if (endCode) {
				endSearchQuery = endCode;
			}
		} else {
			endSearchQuery = searchResult.location || searchResult.name;
			endCode = null;
		}

		await performDetailedReverseGeocode(searchResult.lat, searchResult.lng, 'end');
		updateMapBounds();
		emitTransportationUpdate();
	}

	function updateMapBounds() {
		if (startMarker && endMarker) {
			const minLng = Math.min(startMarker.lng, endMarker.lng);
			const maxLng = Math.max(startMarker.lng, endMarker.lng);
			const minLat = Math.min(startMarker.lat, endMarker.lat);
			const maxLat = Math.max(startMarker.lat, endMarker.lat);

			// Add a small padding so pins are not flush against the edge when fitting
			const lonPadding = Math.max((maxLng - minLng) * 0.1, 0.5);
			const latPadding = Math.max((maxLat - minLat) * 0.1, 0.5);

			mapBounds = [
				[minLng - lonPadding, minLat - latPadding],
				[maxLng + lonPadding, maxLat + latPadding]
			];
			mapCenter = [(minLng + maxLng) / 2, (minLat + maxLat) / 2];
			mapZoom = undefined;
		} else if (startMarker) {
			mapCenter = [startMarker.lng, startMarker.lat];
			mapZoom = 8;
			mapBounds = null;
		} else if (endMarker) {
			mapCenter = [endMarker.lng, endMarker.lat];
			mapZoom = 8;
			mapBounds = null;
		} else {
			mapBounds = null;
		}
	}

	async function handleMapClick(e: { detail: { lngLat: { lng: number; lat: number } } }) {
		selectedMarker = {
			lng: e.detail.lngLat.lng,
			lat: e.detail.lngLat.lat
		};

		await reverseGeocode(e.detail.lngLat.lng, e.detail.lngLat.lat);
	}

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
				searchQuery = result.display_name || result.name;
				displayName = result.display_name || result.name;
			} else {
				selectedLocation = {
					name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
					lat: lat,
					lng: lng,
					location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
				};
				searchQuery = selectedLocation.name;
				displayName = selectedLocation.location;
			}

			if (selectedLocation) {
				emitUpdate(selectedLocation);
			}

			await performDetailedReverseGeocode(lat, lng);
		} catch (error) {
			console.error('Reverse geocoding error:', error);
			selectedLocation = {
				name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
				lat: lat,
				lng: lng,
				location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
			};
			searchQuery = selectedLocation.name;
			if (!displayName) displayName = selectedLocation.location;
			locationData = null;
			if (selectedLocation) emitUpdate(selectedLocation);
		} finally {
			isReverseGeocoding = false;
		}
	}

	async function performDetailedReverseGeocode(
		lat: number,
		lng: number,
		target: 'single' | 'start' | 'end' = 'single'
	) {
		try {
			const response = await fetch(
				`/api/reverse-geocode/reverse_geocode/?lat=${lat}&lon=${lng}&format=json`
			);

			if (response.ok) {
				const data = await response.json();
				const metaData = {
					city: data.city
						? {
								name: data.city,
								id: data.city_id,
								visited: data.city_visited || false
							}
						: undefined,
					region: data.region
						? {
								name: data.region,
								id: data.region_id,
								visited: data.region_visited || false
							}
						: undefined,
					country: data.country
						? {
								name: data.country,
								country_code: data.country_id,
								visited: false
							}
						: undefined,
					display_name: data.display_name,
					location_name: data.location_name
				};

				if (target === 'start') {
					startLocationData = metaData;
				} else if (target === 'end') {
					endLocationData = metaData;
				} else {
					locationData = metaData;
					const resolvedLocationName = (data.location_name || '').trim();
					const resolvedDisplayName = (data.display_name || '').trim();

					if (selectedLocation) {
						const isCoordinatePlaceholder = selectedLocation.name.startsWith('Location at ');
						selectedLocation = {
							...selectedLocation,
							name:
								resolvedLocationName ||
								(isCoordinatePlaceholder && resolvedDisplayName
									? resolvedDisplayName
									: selectedLocation.name),
							location: resolvedDisplayName || selectedLocation.location
						};
						emitUpdate(selectedLocation);
					}

					displayName = resolvedDisplayName || resolvedLocationName || displayName;
					searchQuery = selectedLocation?.name || searchQuery;
				}
			} else {
				if (target === 'start') {
					startLocationData = null;
				} else if (target === 'end') {
					endLocationData = null;
				} else {
					locationData = null;
				}
			}
		} catch (error) {
			console.error('Detailed reverse geocoding error:', error);
			if (target === 'start') {
				startLocationData = null;
			} else if (target === 'end') {
				endLocationData = null;
			} else {
				locationData = null;
			}
		}
	}

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

	function clearLocationSelection() {
		if (transportationMode) {
			selectedStartLocation = null;
			selectedEndLocation = null;
			startMarker = null;
			endMarker = null;
			startLocationData = null;
			endLocationData = null;
			startCode = null;
			endCode = null;
			startSearchQuery = '';
			endSearchQuery = '';
			startSearchResults = [];
			endSearchResults = [];
		} else {
			selectedLocation = null;
			selectedMarker = null;
			locationData = null;
			searchQuery = '';
			searchResults = [];
			displayName = '';
		}
		mapCenter = [-74.5, 40];
		mapZoom = 2;
		mapBounds = null;
		dispatch('clear');
	}

	$: if (
		!initialApplied &&
		initialSelection &&
		isFiniteCoordinatePair(initialSelection.lat, initialSelection.lng)
	) {
		initialApplied = true;
		applyInitialSelection(initialSelection);
	}

	$: if (
		!initialTransportationApplied &&
		transportationMode &&
		(initialStartLocation || initialEndLocation)
	) {
		initialTransportationApplied = true;
		applyInitialTransportationLocations();
	}
</script>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
	<div class="space-y-4">
		<!-- Transportation Mode Toggle -->
		{#if transportationMode}
			<div class="flex items-center gap-3 p-3 bg-primary/10 rounded-lg border border-primary/30">
				<AirplaneIcon class="w-5 h-5 text-primary" />
				<div class="flex-1">
					<label class="label cursor-pointer justify-start gap-3">
						<input type="checkbox" class="toggle toggle-primary" bind:checked={airportMode} />
						<span class="label-text font-medium">
							{airportMode
								? $t('adventures.airport_search_mode')
								: $t('adventures.location_search_mode')}
						</span>
					</label>
				</div>
			</div>
		{/if}

		{#if showDisplayNameInput && displayNamePosition === 'before' && !transportationMode}
			<div class="form-control">
				<label class="label" for="location-display">
					<span class="label-text font-medium">
						{displayNameLabel || $t('adventures.location_display_name')}
					</span>
				</label>
				<input
					type="text"
					id="location-display"
					bind:value={displayName}
					class="input input-bordered bg-base-100/80 focus:bg-base-100"
					placeholder={displayNamePlaceholder || $t('adventures.enter_location_display_name')}
				/>
			</div>
		{/if}

		{#if transportationMode}
			<!-- Start Location Search -->
			<div class="form-control">
				<label class="label" for="search-start-location">
					<span class="label-text font-medium flex items-center gap-2">
						<PinIcon class="w-4 h-4 text-success" />
						{airportMode ? $t('adventures.departure_airport') : $t('adventures.start_location')}
					</span>
				</label>
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<SearchIcon class="w-4 h-4 text-base-content/40" />
					</div>
					<input
						type="text"
						id="search-start-location"
						bind:value={startSearchQuery}
						on:input={handleStartSearchInput}
						placeholder={airportMode
							? $t('adventures.airport_code_examples')
							: $t('transportation.enter_from_location')}
						class="input input-bordered w-full pl-10 pr-4 bg-base-100/80 focus:bg-base-100"
						class:input-success={selectedStartLocation}
					/>
					{#if startSearchQuery && !selectedStartLocation}
						<button
							class="absolute inset-y-0 right-0 pr-3 flex items-center"
							on:click={() => {
								startSearchQuery = '';
								startSearchResults = [];
							}}
						>
							<ClearIcon class="w-4 h-4 text-base-content/40 hover:text-base-content" />
						</button>
					{/if}
				</div>
			</div>

			{#if isSearchingStart}
				<div class="flex items-center justify-center py-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="ml-2 text-sm text-base-content/60">{$t('adventures.searching')}...</span>
				</div>
			{:else if startSearchResults.length > 0}
				<div class="space-y-2">
					<div class="max-h-48 overflow-y-auto space-y-1">
						{#each startSearchResults as result}
							<button
								class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-success/50 transition-colors"
								on:click={() => selectStartSearchResult(result)}
							>
								<div class="flex items-start gap-3">
									<PinIcon class="w-4 h-4 text-success mt-1 flex-shrink-0" />
									<div class="min-w-0 flex-1">
										<div class="font-medium text-sm truncate">{result.name}</div>
										<div class="text-xs text-base-content/60 truncate">{result.location}</div>
										{#if result.category}
											<div class="text-xs text-success/70 capitalize">{result.category}</div>
										{/if}
									</div>
								</div>
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<!-- End Location Search -->
			<div class="form-control">
				<label class="label" for="search-end-location">
					<span class="label-text font-medium flex items-center gap-2">
						<PinIcon class="w-4 h-4 text-error" />
						{airportMode ? $t('adventures.arrival_airport') : $t('adventures.end_location')}
					</span>
				</label>
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<SearchIcon class="w-4 h-4 text-base-content/40" />
					</div>
					<input
						type="text"
						id="search-end-location"
						bind:value={endSearchQuery}
						on:input={handleEndSearchInput}
						placeholder={airportMode
							? $t('adventures.airport_code_examples')
							: $t('transportation.enter_to_location')}
						class="input input-bordered w-full pl-10 pr-4 bg-base-100/80 focus:bg-base-100"
						class:input-error={selectedEndLocation}
					/>
					{#if endSearchQuery && !selectedEndLocation}
						<button
							class="absolute inset-y-0 right-0 pr-3 flex items-center"
							on:click={() => {
								endSearchQuery = '';
								endSearchResults = [];
							}}
						>
							<ClearIcon class="w-4 h-4 text-base-content/40 hover:text-base-content" />
						</button>
					{/if}
				</div>
			</div>

			{#if isSearchingEnd}
				<div class="flex items-center justify-center py-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="ml-2 text-sm text-base-content/60">{$t('adventures.searching')}...</span>
				</div>
			{:else if endSearchResults.length > 0}
				<div class="space-y-2">
					<div class="max-h-48 overflow-y-auto space-y-1">
						{#each endSearchResults as result}
							<button
								class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-error/50 transition-colors"
								on:click={() => selectEndSearchResult(result)}
							>
								<div class="flex items-start gap-3">
									<PinIcon class="w-4 h-4 text-error mt-1 flex-shrink-0" />
									<div class="min-w-0 flex-1">
										<div class="font-medium text-sm truncate">{result.name}</div>
										<div class="text-xs text-base-content/60 truncate">{result.location}</div>
										{#if result.category}
											<div class="text-xs text-error/70 capitalize">{result.category}</div>
										{/if}
									</div>
								</div>
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Selected Locations Summary for Transportation Mode -->
			{#if selectedStartLocation && selectedEndLocation}
				<div class="card bg-success/10 border border-success/30">
					<div class="card-body p-4">
						<div class="flex items-start gap-3">
							<div class="p-2 bg-success/20 rounded-lg">
								<SwapIcon class="w-4 h-4 text-success" />
							</div>
							<div class="flex-1 min-w-0 space-y-2">
								<h4 class="font-semibold text-success mb-1">{$t('adventures.route_selected')}</h4>

								<!-- Start Location -->
								<div class="flex items-start gap-2">
									<PinIcon class="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
									<div class="min-w-0 flex-1">
										<p class="text-sm font-medium text-base-content/80 truncate">
											{selectedStartLocation.name}
											{#if startCode}
												<span class="badge badge-success badge-sm ml-2">{startCode}</span>
											{/if}
										</p>
										<p class="text-xs text-base-content/60">
											{startMarker?.lat.toFixed(6)}, {startMarker?.lng.toFixed(6)}
										</p>
									</div>
								</div>

								<div class="divider my-1"></div>

								<!-- End Location -->
								<div class="flex items-start gap-2">
									<PinIcon class="w-4 h-4 text-error mt-0.5 flex-shrink-0" />
									<div class="min-w-0 flex-1">
										<p class="text-sm font-medium text-base-content/80 truncate">
											{selectedEndLocation.name}
											{#if endCode}
												<span class="badge badge-error badge-sm ml-2">{endCode}</span>
											{/if}
										</p>
										<p class="text-xs text-base-content/60">
											{endMarker?.lat.toFixed(6)}, {endMarker?.lng.toFixed(6)}
										</p>
									</div>
								</div>
							</div>
							<button class="btn btn-ghost btn-sm" on:click={clearLocationSelection}>
								<ClearIcon class="w-4 h-4" />
							</button>
						</div>
					</div>
				</div>
			{/if}
		{:else}
			<!-- Single Location Mode (Original) -->
			<div class="form-control">
				<label class="label" for="search-location">
					<span class="label-text font-medium">{$t('adventures.search_location')}</span>
				</label>
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<SearchIcon class="w-4 h-4 text-base-content/40" />
					</div>
					<input
						type="text"
						id="search-location"
						bind:value={searchQuery}
						on:input={handleSearchInput}
						placeholder={$t('adventures.search_placeholder')}
						class="input input-bordered w-full pl-10 pr-4 bg-base-100/80 focus:bg-base-100"
						class:input-primary={selectedLocation}
					/>
					{#if searchQuery && !selectedLocation}
						<button
							class="absolute inset-y-0 right-0 pr-3 flex items-center"
							on:click={clearLocationSelection}
						>
							<ClearIcon class="w-4 h-4 text-base-content/40 hover:text-base-content" />
						</button>
					{/if}
				</div>
			</div>

			{#if isSearching}
				<div class="flex items-center justify-center py-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="ml-2 text-sm text-base-content/60">{$t('adventures.searching')}...</span>
				</div>
			{:else if searchResults.length > 0}
				<div class="space-y-2">
					<div class="label">
						<span class="label-text text-sm font-medium">{$t('adventures.search_results')}</span>
					</div>
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
										{#if result.category}
											<div class="text-xs text-primary/70 capitalize">{result.category}</div>
										{/if}
									</div>
								</div>
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<div class="flex items-center gap-2">
				<div class="divider divider-horizontal text-xs">{$t('adventures.or')}</div>
			</div>

			<button class="btn btn-outline gap-2 w-full" on:click={useCurrentLocation}>
				<LocationIcon class="w-4 h-4" />
				{$t('adventures.use_current_location')}
			</button>

			{#if showDisplayNameInput && displayNamePosition === 'after'}
				<div class="form-control">
					<label class="label" for="location-display-after">
						<span class="label-text font-medium">
							{displayNameLabel || $t('adventures.location_display_name')}
						</span>
					</label>
					<input
						type="text"
						id="location-display-after"
						bind:value={displayName}
						class="input input-bordered bg-base-100/80 focus:bg-base-100"
						placeholder={displayNamePlaceholder || $t('adventures.enter_location_display_name')}
					/>
				</div>
			{/if}

			{#if selectedLocation && selectedMarker}
				<div class="card bg-success/10 border border-success/30">
					<div class="card-body p-4">
						<div class="flex items-start gap-3">
							<div class="p-2 bg-success/20 rounded-lg">
								<CheckIcon class="w-4 h-4 text-success" />
							</div>
							<div class="flex-1 min-w-0">
								<h4 class="font-semibold text-success mb-1">
									{$t('adventures.location_selected')}
								</h4>
								<p class="text-sm text-base-content/80 truncate">{selectedLocation.name}</p>
								<p class="text-xs text-base-content/60 mt-1">
									{selectedMarker.lat.toFixed(6)}, {selectedMarker.lng.toFixed(6)}
								</p>

								{#if locationData?.city || locationData?.region || locationData?.country}
									<div class="flex flex-wrap gap-2 mt-3">
										{#if locationData.city}
											<div class="badge badge-info badge-sm gap-1">
												🏙️ {locationData.city.name}
											</div>
										{/if}
										{#if locationData.region}
											<div class="badge badge-warning badge-sm gap-1">
												🗺️ {locationData.region.name}
											</div>
										{/if}
										{#if locationData.country}
											<div class="badge badge-success badge-sm gap-1">
												🌎 {locationData.country.name}
											</div>
										{/if}
									</div>
								{/if}
							</div>
							<button class="btn btn-ghost btn-sm" on:click={clearLocationSelection}>
								<ClearIcon class="w-4 h-4" />
							</button>
						</div>
					</div>
				</div>
			{/if}
		{/if}
	</div>

	<div class="space-y-4">
		<div class="flex items-center justify-between">
			<div class="label">
				<span class="label-text font-medium">{$t('worldtravel.interactive_map')}</span>
			</div>
			{#if isReverseGeocoding}
				<div class="flex items-center gap-2">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="text-sm text-base-content/60"
						>{$t('worldtravel.getting_location_details')}...</span
					>
				</div>
			{/if}
		</div>

		<div class="relative">
			<FullMap
				{basemapType}
				mapClass="w-full h-80 rounded-lg border border-base-300"
				center={mapCenter}
				zoom={mapZoom}
				bounds={mapBounds ?? undefined}
				standardControls
				on:mapClick={handleMapClick}
			>
				{#if transportationMode}
					{#if startMarker}
						<Marker
							lngLat={[startMarker.lng, startMarker.lat]}
							class="grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-success shadow-lg cursor-pointer"
						>
							<PinIcon class="w-5 h-5 text-success-content" />
						</Marker>
					{/if}
					{#if endMarker}
						<Marker
							lngLat={[endMarker.lng, endMarker.lat]}
							class="grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-error shadow-lg cursor-pointer"
						>
							<PinIcon class="w-5 h-5 text-error-content" />
						</Marker>
					{/if}
				{:else if selectedMarker}
					<Marker
						lngLat={[selectedMarker.lng, selectedMarker.lat]}
						class="grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-primary shadow-lg cursor-pointer"
					>
						<PinIcon class="w-5 h-5 text-primary-content" />
					</Marker>
				{/if}
			</FullMap>
		</div>

		{#if transportationMode}
			{#if !startMarker && !endMarker}
				<p class="text-sm text-base-content/60 text-center">
					{$t('adventures.search_start_end_locations')}
				</p>
			{:else if !startMarker}
				<p class="text-sm text-base-content/60 text-center">
					{$t('adventures.search_start_location')}
				</p>
			{:else if !endMarker}
				<p class="text-sm text-base-content/60 text-center">
					{$t('adventures.search_end_location')}
				</p>
			{/if}
		{:else if !selectedMarker}
			<p class="text-sm text-base-content/60 text-center">{$t('adventures.click_on_map')}</p>
		{/if}
	</div>
</div>
