<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import FullMap from '$lib/components/map/FullMap.svelte';
	import { Marker } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import CategoryDropdown from '../CategoryDropdown.svelte';
	import type { Category } from '$lib/types';

	import SearchIcon from '~icons/mdi/magnify';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import MapIcon from '~icons/mdi/map';
	import CheckIcon from '~icons/mdi/check';
	import ClearIcon from '~icons/mdi/close';
	import PinIcon from '~icons/mdi/map-marker';
	import StarIcon from '~icons/mdi/star';
	import LightningIcon from '~icons/mdi/lightning-bolt';
	import PencilIcon from '~icons/mdi/pencil';

	type SelectedPlace = {
		id: string;
		name: string;
		lat: number;
		lng: number;
		location: string;
		type?: string;
		category?: string;
		types?: string[];
		rating?: number | null;
		review_count?: number | null;
		photos?: string[];
		description?: string | null;
		website?: string | null;
		phone_number?: string | null;
		place_id?: string | null;
		google_maps_url?: string | null;
		powered_by?: string;
	};

	type LocationData = {
		city?: { name: string; id: string; visited: boolean };
		region?: { name: string; id: string; visited: boolean };
		country?: { name: string; country_code: string; visited: boolean };
		display_name?: string;
		location_name?: string;
	};

	const dispatch = createEventDispatcher();

	export let mode: 'location' | 'lodging' = 'location';
	export let googleEnabled = false;
	export let collectionId: string | null = null;
	export let itineraryDate: string | null = null;
	export let itineraryLabel: string | null = null;
	export let basemapType: string = 'default';

	$: supportsCategory = mode === 'location';
	$: itemLabel = mode === 'lodging' ? 'lodging' : 'location';
	$: quickAddEndpoint =
		mode === 'lodging' ? '/api/lodging/quick-add/' : '/api/locations/quick-add/';
	$: formattedItineraryLabel = itineraryLabel || formatItineraryDate(itineraryDate);

	let searchQuery = '';
	let searchResults: SelectedPlace[] = [];
	let selectedLocation: SelectedPlace | null = null;
	let mapCenter: [number, number] = [-74.5, 40];
	let mapZoom = 2;
	let isSearching = false;
	let isReverseGeocoding = false;
	let isEnrichingDescription = false;
	let isQuickAdding = false;
	let quickAddedLocation: any = null;
	let searchTimeout: ReturnType<typeof setTimeout>;
	let selectedMarker: { lng: number; lat: number } | null = null;
	let locationData: LocationData | null = null;
	let selectedQuickAddCategory: Category | null = null;
	const placeDetailsCache = new Map<string, any>();

	function toPlaceResult(result: any): SelectedPlace {
		return {
			id: result.place_id || `${result.name || 'place'}-${result.lat}-${result.lon}`,
			name: result.name,
			lat: parseFloat(result.lat),
			lng: parseFloat(result.lon),
			location: result.display_name,
			type: result.type,
			category: result.category,
			types: result.types || [],
			rating: result.rating ?? null,
			review_count: result.review_count ?? null,
			photos: result.photos || [],
			description: result.description || null,
			website: result.website || null,
			phone_number: result.phone_number || null,
			place_id: result.place_id || null,
			google_maps_url: result.google_maps_url || null,
			powered_by: result.powered_by
		};
	}

	function pickBestNearbyResult(
		results: SelectedPlace[],
		lat: number,
		lng: number,
		preferredName?: string
	): SelectedPlace | null {
		if (!results.length) {
			return null;
		}

		const normalizedPreferredName = (preferredName || '').trim().toLowerCase();
		const scored = results
			.filter((item) => Number.isFinite(item.lat) && Number.isFinite(item.lng))
			.map((item) => {
				const dLat = item.lat - lat;
				const dLng = item.lng - lng;
				const distanceScore = dLat * dLat + dLng * dLng;
				const nameScore =
					normalizedPreferredName && item.name?.trim().toLowerCase() === normalizedPreferredName
						? -1
						: 0;
				const placeScore = item.place_id ? -0.5 : 0;
				return {
					item,
					score: distanceScore + nameScore + placeScore
				};
			});

		if (!scored.length) {
			return results[0];
		}

		scored.sort((a, b) => a.score - b.score);
		return scored[0].item;
	}

	async function enrichFromResolvedName(lat: number, lng: number, resolvedName: string) {
		const query = resolvedName.trim();
		if (!query) {
			return;
		}

		try {
			const response = await fetch(
				`/api/reverse-geocode/search/?query=${encodeURIComponent(query)}`
			);
			if (!response.ok) {
				return;
			}

			const rawResults = await response.json();
			const mappedResults = Array.isArray(rawResults) ? rawResults.map(toPlaceResult) : [];
			const bestMatch = pickBestNearbyResult(mappedResults, lat, lng, query);
			if (!bestMatch || !selectedLocation) {
				return;
			}

			selectedLocation = {
				...selectedLocation,
				...bestMatch,
				lat,
				lng,
				name: bestMatch.name || selectedLocation.name,
				location: selectedLocation.location || bestMatch.location
			};
			searchQuery = selectedLocation.name;
		} catch (error) {
			console.error('Resolved name enrichment error:', error);
		}
	}

	function needsDescriptionEnrichment(place: SelectedPlace | null) {
		if (!place?.place_id) {
			return false;
		}

		const text = (place.description || '').trim();
		return text.length < 220;
	}

	async function fetchPlaceDetails(placeId: string, name: string) {
		if (placeDetailsCache.has(placeId)) {
			return placeDetailsCache.get(placeId);
		}

		const response = await fetch(
			`/api/reverse-geocode/place_details/?place_id=${encodeURIComponent(placeId)}&name=${encodeURIComponent(name || '')}`
		);
		if (!response.ok) {
			throw new Error('Unable to fetch place details');
		}

		const details = await response.json();
		placeDetailsCache.set(placeId, details);
		return details;
	}

	async function enrichSelectedLocationDescription(force = false) {
		if (!selectedLocation?.place_id) {
			return;
		}

		const placeId = selectedLocation.place_id;
		if (!placeId || (!force && !needsDescriptionEnrichment(selectedLocation))) {
			return;
		}

		isEnrichingDescription = true;
		try {
			const details = await fetchPlaceDetails(placeId, selectedLocation.name || '');

			if (!selectedLocation || selectedLocation.place_id !== placeId) {
				return;
			}

			selectedLocation = {
				...selectedLocation,
				name: details.name || selectedLocation.name,
				location: details.formatted_address || selectedLocation.location,
				types:
					Array.isArray(details.types) && details.types.length > 0
						? details.types
						: selectedLocation.types,
				rating: details.rating ?? selectedLocation.rating ?? null,
				review_count: details.review_count ?? selectedLocation.review_count ?? null,
				description: details.description || selectedLocation.description || null,
				website: details.website || selectedLocation.website || null,
				phone_number: details.phone_number || selectedLocation.phone_number || null,
				google_maps_url: details.google_maps_url || selectedLocation.google_maps_url || null
			};
		} catch (error) {
			console.error('Place details enrichment error:', error);
		} finally {
			isEnrichingDescription = false;
		}
	}

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
			searchResults = Array.isArray(results) ? results.map(toPlaceResult) : [];
		} catch (error) {
			console.error('Search error:', error);
			searchResults = [];
		} finally {
			isSearching = false;
		}
	}

	function handleSearchInput() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			searchLocations(searchQuery);
		}, 300);
	}

	async function selectSearchResult(location: SelectedPlace) {
		selectedLocation = location;
		selectedMarker = { lng: location.lng, lat: location.lat };
		mapCenter = [location.lng, location.lat];
		mapZoom = 14;
		searchResults = [];
		searchQuery = location.name;
		await performDetailedReverseGeocode(location.lat, location.lng);
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

			if (Array.isArray(results) && results.length > 0) {
				selectedLocation = {
					...toPlaceResult(results[0]),
					lat,
					lng
				};
				searchQuery = selectedLocation.name;
			} else {
				selectedLocation = {
					id: `manual-${lat}-${lng}`,
					name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
					lat,
					lng,
					location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`,
					types: [],
					photos: []
				};
				searchQuery = selectedLocation.name;
			}

			await performDetailedReverseGeocode(lat, lng);
		} catch (error) {
			console.error('Reverse geocoding error:', error);
			selectedLocation = {
				id: `manual-${lat}-${lng}`,
				name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
				lat,
				lng,
				location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`,
				types: [],
				photos: []
			};
			searchQuery = selectedLocation.name;
			locationData = null;
		} finally {
			isReverseGeocoding = false;
		}
	}

	async function performDetailedReverseGeocode(lat: number, lng: number) {
		try {
			const response = await fetch(
				`/api/reverse-geocode/reverse_geocode/?lat=${lat}&lon=${lng}&format=json`
			);

			if (response.ok) {
				const data = await response.json();
				locationData = {
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

				if (selectedLocation) {
					const isCoordinatePlaceholder = selectedLocation.name.startsWith('Location at ');
					const shouldAutoEnrichQuickAdd = isCoordinatePlaceholder || !selectedLocation.place_id;
					const resolvedLocationName = (data.location_name || '').trim();
					const resolvedDisplayName = (data.display_name || '').trim();

					selectedLocation = {
						...selectedLocation,
						name:
							resolvedLocationName ||
							(isCoordinatePlaceholder && resolvedDisplayName
								? resolvedDisplayName
								: selectedLocation.name),
						location: resolvedDisplayName || `${lat.toFixed(4)}, ${lng.toFixed(4)}`
					};
					searchQuery = selectedLocation.name;

					if (shouldAutoEnrichQuickAdd && resolvedLocationName) {
						await enrichFromResolvedName(lat, lng, resolvedLocationName);
					}
				}
			} else {
				locationData = null;
			}
		} catch (error) {
			console.error('Detailed reverse geocoding error:', error);
			locationData = null;
		}
	}

	async function ensureAdventureLogFormattedLocation() {
		if (!selectedMarker) {
			return;
		}

		if (locationData?.display_name?.trim()) {
			return;
		}

		await performDetailedReverseGeocode(selectedMarker.lat, selectedMarker.lng);
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

	function clearSelection() {
		selectedLocation = null;
		selectedMarker = null;
		locationData = null;
		searchQuery = '';
		searchResults = [];
		quickAddedLocation = null;
		selectedQuickAddCategory = null;
		mapCenter = [-74.5, 40];
		mapZoom = 2;
	}

	function buildPrefillPayload() {
		if (!selectedLocation || !selectedMarker) {
			return null;
		}

		const formattedLocation =
			locationData?.display_name?.trim() || selectedLocation.location?.trim() || '';

		return {
			name: selectedLocation.name,
			latitude: selectedMarker.lat,
			longitude: selectedMarker.lng,
			location: formattedLocation,
			type: selectedLocation.type,
			category: selectedLocation.category,
			city: locationData?.city,
			region: locationData?.region,
			country: locationData?.country,
			display_name: locationData?.display_name,
			location_name: locationData?.location_name,
			rating: selectedLocation.rating ?? null,
			review_count: selectedLocation.review_count ?? null,
			photos: selectedLocation.photos || [],
			description: selectedLocation.description || null,
			website: selectedLocation.website || null,
			phone_number: selectedLocation.phone_number || null,
			place_id: selectedLocation.place_id || null,
			google_maps_url: selectedLocation.google_maps_url || null,
			types: selectedLocation.types || [],
			selected_category: selectedQuickAddCategory
		};
	}

	function formatItineraryDate(value: string | null) {
		if (!value) {
			return null;
		}

		const date = new Date(`${value}T00:00:00`);
		if (Number.isNaN(date.getTime())) {
			return value;
		}

		return date.toLocaleDateString(undefined, {
			weekday: 'short',
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		});
	}

	async function continueWithDetails() {
		await ensureAdventureLogFormattedLocation();

		if (selectedLocation?.place_id && needsDescriptionEnrichment(selectedLocation)) {
			await enrichSelectedLocationDescription();
		}

		const prefill = buildPrefillPayload();
		if (prefill) {
			dispatch('addDetails', { prefill });
			return;
		}

		dispatch('manual');
	}

	async function quickAdd() {
		const prefill = buildPrefillPayload();
		if (!prefill) {
			addToast('warning', `Please select a place or drop a pin first`);
			return;
		}

		isQuickAdding = true;
		try {
			const payload: Record<string, any> = {
				name: prefill.name,
				type: prefill.type,
				location: prefill.location,
				latitude: prefill.latitude,
				longitude: prefill.longitude,
				place_id: prefill.place_id,
				rating: prefill.rating,
				review_count: prefill.review_count,
				description: prefill.description,
				website: prefill.website,
				phone_number: prefill.phone_number,
				google_maps_url: prefill.google_maps_url,
				types: prefill.types || [],
				photos: prefill.photos || [],
				collection_id: collectionId,
				itinerary_date: itineraryDate,
				is_public: false
			};

			if (supportsCategory && selectedQuickAddCategory) {
				payload.category = selectedQuickAddCategory;
			}

			const res = await fetch(quickAddEndpoint, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});

			if (!res.ok) {
				const errorData = await res.json().catch(() => ({}));
				throw new Error(errorData?.error || errorData?.detail || `Failed to create ${itemLabel}`);
			}

			quickAddedLocation = await res.json();
			const itineraryItem = quickAddedLocation?.quick_add_itinerary_item || null;

			addToast(
				'success',
				`${itemLabel[0].toUpperCase()}${itemLabel.slice(1)} created successfully`
			);
			dispatch('quickAdded', {
				location: quickAddedLocation,
				prefill,
				itineraryItem,
				itineraryDate
			});
		} catch (error) {
			addToast('error', error instanceof Error ? error.message : `Failed to create ${itemLabel}`);
		} finally {
			isQuickAdding = false;
		}
	}

	onMount(() => {
		return () => {
			clearTimeout(searchTimeout);
		};
	});
</script>

<div class="space-y-6">
	{#if quickAddedLocation}
		<div class="card bg-success/10 border border-success/30">
			<div class="card-body p-5 space-y-4">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-success/20 rounded-lg">
						<CheckIcon class="w-5 h-5 text-success" />
					</div>
					<div>
						<h4 class="font-semibold text-success">
							{mode === 'lodging' ? 'Lodging added' : 'Location added'}
						</h4>
						<p class="text-sm text-base-content/70">{quickAddedLocation.name}</p>
					</div>
				</div>
				<div class="flex flex-col sm:flex-row gap-3">
					<button
						class="btn btn-primary flex-1"
						on:click={() => dispatch('quickAddedEdit', { location: quickAddedLocation })}
					>
						<PencilIcon class="w-4 h-4" />
						{$t('adventures.add_details') || 'Add Details'}
					</button>
					<button
						class="btn btn-outline flex-1"
						on:click={() => dispatch('quickAddedDone', { location: quickAddedLocation })}
					>
						{$t('adventures.done') || 'Done'}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<div class="card bg-base-200/50 border border-base-300">
		<div class="card-body p-6 space-y-4">
			<div class="form-control">
				<label class="label" for="quickstart-search-location">
					<span class="label-text font-medium">
						{#if googleEnabled}
							{mode === 'lodging' ? 'Search Google Maps for Lodging' : 'Search Google Maps'}
						{:else}
							{$t('adventures.search_location')}
						{/if}
					</span>
				</label>
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<SearchIcon class="w-5 h-5 text-base-content/40" />
					</div>
					<input
						type="text"
						id="quickstart-search-location"
						bind:value={searchQuery}
						on:input={handleSearchInput}
						placeholder={$t('adventures.search_placeholder') ||
							'Enter city, location, or landmark...'}
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

			{#if isSearching}
				<div class="flex items-center justify-center py-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="ml-2 text-sm text-base-content/60">{$t('adventures.searching')}...</span>
				</div>
			{:else if searchResults.length > 0}
				<div class="space-y-2">
					<label class="label" for="quickstart-search-results">
						<span class="label-text text-sm font-medium">{$t('adventures.search_results')}</span>
					</label>
					<div id="quickstart-search-results" class="max-h-52 overflow-y-auto space-y-1">
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
										{#if result.rating}
											<div class="text-xs text-warning mt-1 inline-flex items-center gap-1">
												<StarIcon class="w-3 h-3" />
												{result.rating}
												{#if result.review_count}
													<span class="text-base-content/60">({result.review_count})</span>
												{/if}
											</div>
										{/if}
									</div>
								</div>
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<div class="flex items-center gap-2">
				<div class="divider divider-horizontal text-xs">{$t('adventures.or') || 'OR'}</div>
			</div>

			<button class="btn btn-outline gap-2 w-full" on:click={useCurrentLocation}>
				<LocationIcon class="w-4 h-4" />
				{$t('adventures.use_current_location') || 'Use Current Location'}
			</button>
		</div>
	</div>

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
						{$t('adventures.clear') || 'Clear'}
					</button>
				{/if}
			</div>

			{#if !selectedMarker}
				<p class="text-sm text-base-content/60 mb-4">
					{#if mode === 'lodging'}
						Click on the map to select a lodging
					{:else}
						{$t('adventures.click_map') || 'Click on the map to select a location'}
					{/if}
				</p>
			{/if}

			{#if isReverseGeocoding}
				<div class="flex items-center justify-center py-2 mb-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="ml-2 text-sm text-base-content/60"
						>{$t('adventures.getting_location_details') || 'Getting details...'}
					</span>
				</div>
			{/if}

			<FullMap
				{basemapType}
				mapClass="w-full h-80 rounded-lg border border-base-300"
				center={mapCenter}
				zoom={mapZoom}
				standardControls
				on:mapClick={handleMapClick}
			>
				{#if selectedMarker}
					<Marker
						lngLat={[selectedMarker.lng, selectedMarker.lat]}
						class="grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-primary shadow-lg cursor-pointer"
					>
						<PinIcon class="w-5 h-5 text-primary-content" />
					</Marker>
				{/if}
			</FullMap>
		</div>
	</div>

	{#if selectedLocation && selectedMarker}
		<div class="card bg-success/10 border border-success/30">
			<div class="card-body p-4">
				<div class="flex gap-4 items-start">
					{#if selectedLocation.photos && selectedLocation.photos.length > 0}
						<img
							src={selectedLocation.photos[0]}
							alt={selectedLocation.name}
							class="w-24 h-24 rounded-lg object-cover border border-base-300"
						/>
					{/if}
					<div class="flex-1 min-w-0">
						<h4 class="font-semibold text-success mb-1">
							{mode === 'lodging'
								? $t('lodging.new_lodging') || 'Lodging selected'
								: $t('adventures.location_selected')}
						</h4>
						<p class="text-sm font-medium text-base-content truncate">{selectedLocation.name}</p>
						<p class="text-xs text-base-content/70 truncate">{selectedLocation.location}</p>
						{#if selectedLocation.rating}
							<div class="text-xs text-warning mt-2 inline-flex items-center gap-1">
								<StarIcon class="w-3 h-3" />
								{selectedLocation.rating}
								{#if selectedLocation.review_count}
									<span class="text-base-content/60">({selectedLocation.review_count} reviews)</span
									>
								{/if}
							</div>
						{/if}
						{#if isEnrichingDescription}
							<div class="text-xs text-base-content/60 mt-2 inline-flex items-center gap-1">
								<span class="loading loading-spinner loading-xs"></span>
								Improving description quality...
							</div>
						{/if}
						<p class="text-xs text-base-content/60 mt-1">
							{selectedMarker.lat.toFixed(6)}, {selectedMarker.lng.toFixed(6)}
						</p>
						{#if selectedLocation.types && selectedLocation.types.length > 0}
							<div class="flex flex-wrap gap-1 mt-2">
								{#each selectedLocation.types.slice(0, 5) as typeName}
									<span class="badge badge-outline badge-sm capitalize">{typeName}</span>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>

		{#if googleEnabled && supportsCategory}
			<div class="card bg-base-100 border border-base-300">
				<div class="card-body p-4">
					<div class="form-control gap-2">
						<label class="label" for="quick-add-category">
							<span class="label-text font-medium">Category for Quick Add</span>
						</label>
						<div id="quick-add-category">
							<CategoryDropdown bind:selected_category={selectedQuickAddCategory} />
						</div>
						<p class="text-xs text-base-content/60">
							Optional. If not selected, backend defaults to General.
						</p>
					</div>
				</div>
			</div>
		{/if}
	{/if}

	{#if itineraryDate}
		<div class="alert alert-info alert-soft">
			<span class="text-sm">
				Will be added to {formattedItineraryLabel || itineraryDate}
			</span>
		</div>
	{/if}

	<div class="flex flex-col sm:flex-row gap-3 pt-2">
		<button class="btn btn-neutral-200 sm:flex-1" on:click={() => dispatch('cancel')}>
			{$t('adventures.cancel') || 'Cancel'}
		</button>

		{#if selectedLocation && selectedMarker && googleEnabled}
			<button class="btn btn-outline sm:flex-1" on:click={continueWithDetails}>
				<PencilIcon class="w-4 h-4" />
				{$t('adventures.add_details') || 'Add Details'}
			</button>
			<button class="btn btn-primary sm:flex-1" on:click={quickAdd} disabled={isQuickAdding}>
				{#if isQuickAdding}
					<span class="loading loading-spinner loading-xs"></span>
					{$t('adventures.processing') || 'Processing'}...
				{:else}
					<LightningIcon class="w-4 h-4" />
					Quick Add
				{/if}
			</button>
		{:else}
			<button
				class="btn btn-primary sm:flex-1"
				on:click={continueWithDetails}
				disabled={isReverseGeocoding}
			>
				{#if isReverseGeocoding}
					<span class="loading loading-spinner loading-xs"></span>
					{$t('adventures.getting_location_details') || 'Getting details...'}
				{:else}
					{$t('adventures.continue')}
				{/if}
			</button>
		{/if}
	</div>
</div>
