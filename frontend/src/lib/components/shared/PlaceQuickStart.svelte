<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import FullMap from '$lib/components/map/FullMap.svelte';
	import { Marker } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import CategoryDropdown from '../CategoryDropdown.svelte';
	import type { Category } from '$lib/types';
	import { fetchFormattedLocation } from '$lib/map/places';

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
		provider?: string;
	};

	type LocationData = {
		city?: { name: string; id: string; visited: boolean };
		region?: { name: string; id: string; visited: boolean };
		country?: { name: string; country_code: string; visited: boolean };
		display_name?: string;
		location_name?: string;
		provider?: string;
	};

	const dispatch = createEventDispatcher();

	interface Props {
		mode?: 'location' | 'lodging';
		googleEnabled?: boolean;
		collectionId?: string | null;
		itineraryDate?: string | null;
		itineraryLabel?: string | null;
		basemapType?: string;
	}

	let {
		mode = 'location',
		googleEnabled = false,
		collectionId = null,
		itineraryDate = null,
		itineraryLabel = null,
		basemapType = 'default'
	}: Props = $props();

	let searchQuery = $state('');
	let searchResults: SelectedPlace[] = $state([]);
	let selectedLocation: SelectedPlace | null = $state(null);
	let mapCenter: [number, number] = $state([-74.5, 40]);
	let mapZoom = $state(2);
	let isSearching = $state(false);
	let isReverseGeocoding = $state(false);
	let isEnrichingDescription = $state(false);
	let isQuickAdding = $state(false);
	let quickAddedLocation: any = $state(null);
	let searchTimeout: ReturnType<typeof setTimeout>;
	let selectedMarker: { lng: number; lat: number } | null = $state(null);
	let locationData: LocationData | null = $state(null);
	let selectedQuickAddCategory: Category | null = $state(null);
	const placeDetailsCache = new Map<string, any>();
	let searchProvider: string | null = $state(null);

	function formatProviderLabel(provider?: string | null): string | null {
		const normalized = (provider || '').trim().toLowerCase();
		if (!normalized) return null;
		if (normalized === 'google') return 'Google Maps';
		if (normalized === 'osm' || normalized === 'nominatim') return 'OpenStreetMap';
		if (normalized === 'mixed') return 'Google Maps + OpenStreetMap';
		if (normalized === 'google+wikipedia') return 'Google Maps + Wikipedia';
		if (normalized === 'wikipedia') return 'Wikipedia';
		return provider || null;
	}

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
			powered_by: result.powered_by,
			provider: result.provider || result.powered_by
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
			const response = await fetch(`/api/places/search/?query=${encodeURIComponent(query)}`);
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
			`/api/places/place_details/?place_id=${encodeURIComponent(placeId)}&name=${encodeURIComponent(name || '')}`
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
			searchProvider = null;
			return;
		}

		isSearching = true;
		try {
			const response = await fetch(
				`/api/places/search/?query=${encodeURIComponent(query)}&include_meta=1`
			);
			const payload = await response.json();
			const rawResults = Array.isArray(payload) ? payload : payload?.results || [];
			searchProvider = Array.isArray(payload) ? null : payload?.provider_used || null;
			searchResults = Array.isArray(rawResults) ? rawResults.map(toPlaceResult) : [];
		} catch (error) {
			console.error('Search error:', error);
			searchResults = [];
			searchProvider = null;
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
			const response = await fetch(`/api/places/search/?query=${lat},${lng}&include_meta=1`);
			const payload = await response.json();
			const results = Array.isArray(payload) ? payload : payload?.results || [];
			searchProvider = Array.isArray(payload) ? null : payload?.provider_used || null;

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
			const formatted = await fetchFormattedLocation(lat, lng);
			if (!formatted) {
				locationData = null;
				return;
			}

			locationData = formatted;

			if (selectedLocation) {
				const isCoordinatePlaceholder = selectedLocation.name.startsWith('Location at ');
				const shouldAutoEnrichQuickAdd = isCoordinatePlaceholder || !selectedLocation.place_id;
				const resolvedLocationName = (formatted.location_name || '').trim();
				const resolvedDisplayName = (formatted.display_name || '').trim();

				selectedLocation = {
					...selectedLocation,
					name: isCoordinatePlaceholder
						? resolvedLocationName || resolvedDisplayName || selectedLocation.name
						: selectedLocation.name,
					location: resolvedDisplayName || `${lat.toFixed(4)}, ${lng.toFixed(4)}`
				};
				searchQuery = selectedLocation.name;

				if (shouldAutoEnrichQuickAdd && resolvedLocationName) {
					await enrichFromResolvedName(lat, lng, resolvedLocationName);
				}
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
		searchProvider = null;
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
		await ensureAdventureLogFormattedLocation();

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
	let supportsCategory = $derived(mode === 'location');
	let itemLabel = $derived(mode === 'lodging' ? 'lodging' : 'location');
	let quickAddEndpoint = $derived(
		mode === 'lodging' ? '/api/lodging/quick-add/' : '/api/locations/quick-add/'
	);
	let formattedItineraryLabel = $derived(itineraryLabel || formatItineraryDate(itineraryDate));
</script>

<div class="h-full min-h-0 flex flex-col">
	<div class="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-4 md:py-5 space-y-6">
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
						onclick={() => dispatch('quickAddedEdit', { location: quickAddedLocation })}
					>
						<PencilIcon class="w-4 h-4" />
						{$t('adventures.add_details') || 'Add Details'}
					</button>
					<button
						class="btn btn-outline flex-1"
						onclick={() => dispatch('quickAddedDone', { location: quickAddedLocation })}
					>
						{$t('adventures.done') || 'Done'}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<div class="card bg-base-200/50 border border-base-300">
		<div class="card-body p-6 space-y-4">
			<div class="flex flex-col">
				<label class="field-label" for="quickstart-search-location">
					{#if googleEnabled}
						{mode === 'lodging' ? 'Search Google Maps for Lodging' : 'Search Google Maps'}
					{:else}
						{$t('adventures.search_location')}
					{/if}
				</label>
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<SearchIcon class="w-5 h-5 text-base-content/40" />
					</div>
					<input
						type="text"
						id="quickstart-search-location"
						bind:value={searchQuery}
						oninput={handleSearchInput}
						placeholder={$t('adventures.search_placeholder') ||
							'Enter city, location, or landmark...'}
						class="input w-full pl-10 pr-4"
						class:input-primary={selectedLocation}
					/>
					{#if searchQuery && !selectedLocation}
						<button
							class="absolute inset-y-0 right-0 pr-3 flex items-center"
							onclick={clearSelection}
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
					<label class="field-label text-sm" for="quickstart-search-results">{$t('adventures.search_results')}</label>
					{#if searchProvider}
						<div class="text-xs text-base-content/60">
							Source: {formatProviderLabel(searchProvider)}
						</div>
					{/if}
					<div id="quickstart-search-results" class="max-h-52 overflow-y-auto space-y-1">
						{#each searchResults as result}
							<button
								class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-primary/50 transition-colors"
								onclick={() => selectSearchResult(result)}
							>
								<div class="flex items-start gap-3">
									<PinIcon class="w-4 h-4 text-primary mt-1 shrink-0" />
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
										{#if result.provider || result.powered_by}
											<div class="text-xs text-base-content/50">
												Source: {formatProviderLabel(result.provider || result.powered_by)}
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

			<button class="btn btn-outline gap-2 w-full" onclick={useCurrentLocation}>
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
					<button class="btn btn-ghost btn-sm gap-1" onclick={clearSelection}>
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
						{#if locationData?.provider || selectedLocation.provider || selectedLocation.powered_by}
							<p class="text-xs text-base-content/60 mt-1">
								Source: {formatProviderLabel(
									locationData?.provider || selectedLocation.provider || selectedLocation.powered_by
								)}
							</p>
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
					<div class="flex flex-col gap-2">
						<label class="field-label" for="quick-add-category">Category for Quick Add</label>
						<CategoryDropdown
							id="quick-add-category"
							bind:selected_category={selectedQuickAddCategory}
						/>
						<p class="field-hint">
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

	</div>

	<div
		class="shrink-0 border-t border-base-300 bg-base-100/90 backdrop-blur-lg px-4 md:px-6 py-3 md:py-4 flex flex-col sm:flex-row gap-3"
	>
		<button class="btn btn-ghost sm:flex-1" onclick={() => dispatch('cancel')}>
			{$t('adventures.cancel') || 'Cancel'}
		</button>

		{#if selectedLocation && selectedMarker && googleEnabled}
			<button class="btn btn-outline sm:flex-1" onclick={continueWithDetails}>
				<PencilIcon class="w-4 h-4" />
				{$t('adventures.add_details') || 'Add Details'}
			</button>
			<button class="btn btn-primary sm:flex-1" onclick={quickAdd} disabled={isQuickAdding}>
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
				onclick={continueWithDetails}
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
