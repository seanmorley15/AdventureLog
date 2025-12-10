<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { MapLibre, Marker, MapEvents } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { getBasemapUrl } from '$lib';
	import CategoryDropdown from '../CategoryDropdown.svelte';
	import type { Collection, Location } from '$lib/types';

	// Icons
	import SearchIcon from '~icons/mdi/magnify';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import MapIcon from '~icons/mdi/map';
	import CheckIcon from '~icons/mdi/check';
	import ClearIcon from '~icons/mdi/close';
	import PinIcon from '~icons/mdi/map-marker';
	import InfoIcon from '~icons/mdi/information';
	import CategoryIcon from '~icons/mdi/tag';
	import GenerateIcon from '~icons/mdi/lightning-bolt';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import SaveIcon from '~icons/mdi/content-save';
	import type { Category, User } from '$lib/types';
	import MarkdownEditor from '../MarkdownEditor.svelte';
	import TagComplete from '../TagComplete.svelte';

	const dispatch = createEventDispatcher();

	// Location selection properties
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

	// Enhanced location data
	let locationData: {
		city?: { name: string; id: string; visited: boolean };
		region?: { name: string; id: string; visited: boolean };
		country?: { name: string; country_code: string; visited: boolean };
		display_name?: string;
		location_name?: string;
	} | null = null;

	// Form data properties
	let location: {
		name: string;
		category: Category | null;
		rating: number;
		is_public: boolean;
		link: string;
		description: string;
		latitude: number | null;
		longitude: number | null;
		location: string;
		tags: string[];
		collections?: string[];
	} = {
		name: '',
		category: null,
		rating: NaN,
		is_public: false,
		link: '',
		description: '',
		latitude: null,
		longitude: null,
		location: '',
		tags: [],
		collections: []
	};

	let user: User | null = null;
	let locationToEdit: Location | null = null;
	let wikiError = '';
	let isGeneratingDesc = false;
	let ownerUser: User | null = null;

	// Props (would be passed in from parent component)
	export let initialLocation: any = null;
	export let currentUser: any = null;
	export let editingLocation: any = null;
	export let collection: Collection | null = null;

	$: user = currentUser;
	$: locationToEdit = editingLocation;

	// Location selection functions
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

	function handleSearchInput() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			searchLocations(searchQuery);
		}, 300);
	}

	async function selectSearchResult(searchResult: any) {
		selectedLocation = searchResult;
		selectedMarker = { lng: searchResult.lng, lat: searchResult.lat };
		mapCenter = [searchResult.lng, searchResult.lat];
		mapZoom = 14;
		searchResults = [];
		searchQuery = searchResult.name;

		// Update form data
		if (!location.name) location.name = searchResult.name;
		location.latitude = searchResult.lat;
		location.longitude = searchResult.lng;
		location.name = searchResult.name;

		await performDetailedReverseGeocode(searchResult.lat, searchResult.lng);
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
				searchQuery = result.name;
				if (!location.name) location.name = result.name;
			} else {
				selectedLocation = {
					name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
					lat: lat,
					lng: lng,
					location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
				};
				searchQuery = selectedLocation.name;
				if (!location.name) location.name = selectedLocation.name;
			}

			location.latitude = lat;
			location.longitude = lng;
			location.location = selectedLocation.location;

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
			if (!location.name) location.name = selectedLocation.name;
			location.latitude = lat;
			location.longitude = lng;
			location.location = selectedLocation.location;
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
				location.location = data.display_name;
			} else {
				locationData = null;
			}
		} catch (error) {
			console.error('Detailed reverse geocoding error:', error);
			locationData = null;
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
		selectedLocation = null;
		selectedMarker = null;
		locationData = null;
		searchQuery = '';
		searchResults = [];
		location.latitude = null;
		location.longitude = null;
		location.location = '';
		mapCenter = [-74.5, 40];
		mapZoom = 2;
	}

	async function generateDesc() {
		if (!location.name) return;

		isGeneratingDesc = true;
		wikiError = '';

		try {
			// Mock Wikipedia API call - replace with actual implementation
			const response = await fetch(`/api/generate/desc/?name=${encodeURIComponent(location.name)}`);
			if (response.ok) {
				const data = await response.json();
				location.description = data.extract || '';
			} else {
				wikiError = `${$t('adventures.wikipedia_error') || 'Error fetching description from Wikipedia'}`;
			}
		} catch (error) {
			wikiError = `${$t('adventures.wikipedia_error') || ''}`;
		} finally {
			isGeneratingDesc = false;
		}
	}

	async function handleSave() {
		if (!location.name || !location.category) {
			return;
		}

		// round latitude and longitude to 6 decimal places
		if (location.latitude !== null && typeof location.latitude === 'number') {
			location.latitude = parseFloat(location.latitude.toFixed(6));
		}
		if (location.longitude !== null && typeof location.longitude === 'number') {
			location.longitude = parseFloat(location.longitude.toFixed(6));
		}
		if (collection && collection.id) {
			location.collections = [collection.id];
		}

		// Build payload and avoid sending an empty `collections` array when editing
		const payload: any = { ...location };

		// If we're editing and the original location had collections, but the form's collections
		// is empty (i.e. user didn't modify collections), omit collections from payload so the
		// server doesn't clear them unintentionally.
		if (locationToEdit && locationToEdit.id) {
			if (
				(!payload.collections || payload.collections.length === 0) &&
				locationToEdit.collections &&
				locationToEdit.collections.length > 0
			) {
				delete payload.collections;
			}

			let res = await fetch(`/api/locations/${locationToEdit.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
			let updatedLocation = await res.json();
			location = updatedLocation;
		} else {
			let res = await fetch(`/api/locations`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
			let newLocation = await res.json();
			location = newLocation;
		}

		dispatch('save', {
			...location
		});
	}

	function handleBack() {
		dispatch('back');
	}

	onMount(async () => {
		if (initialLocation.latitude && initialLocation.longitude) {
			selectedMarker = {
				lng: initialLocation.longitude,
				lat: initialLocation.latitude
			};
			location.latitude = initialLocation.latitude;
			location.longitude = initialLocation.longitude;
			mapCenter = [initialLocation.longitude, initialLocation.latitude];
			mapZoom = 14;
			selectedLocation = {
				name: initialLocation.name || '',
				lat: initialLocation.latitude,
				lng: initialLocation.longitude,
				location: initialLocation.location || '',
				type: 'point',
				category: initialLocation.category || null
			};
			selectedMarker = {
				lng: Number(initialLocation.longitude),
				lat: Number(initialLocation.latitude)
			};
			// trigger reverse geocoding to populate location data
			await performDetailedReverseGeocode(initialLocation.latitude, initialLocation.longitude);
		}
	});

	onMount(() => {
		if (initialLocation && typeof initialLocation === 'object') {
			// Only update location properties if they don't already have values
			// This prevents overwriting user selections
			if (!location.name) location.name = initialLocation.name || '';
			if (!location.link) location.link = initialLocation.link || '';
			if (!location.description) location.description = initialLocation.description || '';
			if (Number.isNaN(location.rating)) location.rating = initialLocation.rating || NaN;
			if (location.is_public === false) location.is_public = initialLocation.is_public || false;

			// Only set category if location doesn't have one or if initialLocation has a valid category
			if (!location.category || !location.category.id) {
				if (initialLocation.category && initialLocation.category.id) {
					location.category = initialLocation.category;
				}
			}

			if (initialLocation.tags && Array.isArray(initialLocation.tags)) {
				location.tags = initialLocation.tags;
			}

			// Preserve existing collections when editing so we don't accidentally send an empty array
			if (initialLocation.collections && Array.isArray(initialLocation.collections)) {
				location.collections = initialLocation.collections.map((c: any) =>
					typeof c === 'string' ? c : c.id
				);
			} else if (
				locationToEdit &&
				locationToEdit.collections &&
				Array.isArray(locationToEdit.collections)
			) {
				location.collections = locationToEdit.collections.map((c: any) =>
					typeof c === 'string' ? c : c.id
				);
			}

			if (initialLocation.location) {
				location.location = initialLocation.location;
			}

			if (initialLocation.user) {
				ownerUser = initialLocation.user;
			}
		}

		searchQuery = initialLocation.name || '';
		return () => {
			clearTimeout(searchTimeout);
		};
	});
</script>

<div class="min-h-screen bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5 p-6">
	<div class="max-w-full mx-auto space-y-6">
		<!-- Basic Information Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-primary/10 rounded-lg">
						<InfoIcon class="w-5 h-5 text-primary" />
					</div>
					<h2 class="text-xl font-bold">{$t('adventures.basic_information')}</h2>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
					<!-- Left Column -->
					<div class="space-y-4">
						<!-- Name Field -->
						<div class="form-control">
							<label class="label" for="name">
								<span class="label-text font-medium">
									{$t('adventures.name')} <span class="text-error">*</span>
								</span>
							</label>
							<input
								type="text"
								id="name"
								bind:value={location.name}
								class="input input-bordered bg-base-100/80 focus:bg-base-100"
								placeholder="Enter location name"
								required
							/>
						</div>

						<!-- Category Field -->
						<div class="form-control">
							<label class="label" for="category">
								<span class="label-text font-medium">
									{$t('adventures.category')} <span class="text-error">*</span>
								</span>
							</label>
							{#if (user && ownerUser && user.uuid == ownerUser.uuid) || !ownerUser}
								<CategoryDropdown bind:selected_category={location.category} />
							{:else}
								<div
									class="flex items-center gap-3 p-3 bg-base-100/80 border border-base-300 rounded-lg"
								>
									{#if location.category?.icon}
										<span class="text-xl flex-shrink-0">{location.category.icon}</span>
									{/if}
									<span class="font-medium">
										{location.category?.display_name || location.category?.name}
									</span>
								</div>
							{/if}
						</div>

						<!-- Rating Field -->
						<div class="form-control">
							<label class="label" for="rating">
								<span class="label-text font-medium">{$t('adventures.rating')}</span>
							</label>
							<div
								class="flex items-center gap-4 p-3 bg-base-100/80 border border-base-300 rounded-lg"
							>
								<div class="rating">
									<input
										type="radio"
										name="rating"
										id="rating"
										class="rating-hidden"
										checked={Number.isNaN(location.rating)}
									/>
									{#each [1, 2, 3, 4, 5] as star}
										<input
											type="radio"
											name="rating"
											class="mask mask-star-2 bg-warning"
											on:click={() => (location.rating = star)}
											checked={location.rating === star}
										/>
									{/each}
								</div>
								{#if !Number.isNaN(location.rating)}
									<button
										type="button"
										class="btn btn-sm btn-error btn-outline gap-2"
										on:click={() => (location.rating = NaN)}
									>
										<ClearIcon class="w-4 h-4" />
										{$t('adventures.remove')}
									</button>
								{/if}
							</div>
						</div>
					</div>

					<!-- Right Column -->
					<div class="space-y-4">
						<!-- Link Field -->
						<div class="form-control">
							<label class="label" for="link">
								<span class="label-text font-medium">{$t('adventures.link')}</span>
							</label>
							<input
								type="url"
								id="link"
								bind:value={location.link}
								class="input input-bordered bg-base-100/80 focus:bg-base-100"
								placeholder="https://example.com"
							/>
						</div>

						<!-- Public Toggle -->
						{#if !locationToEdit || (locationToEdit.collections && locationToEdit.collections.length === 0)}
							<div class="form-control">
								<label class="label cursor-pointer justify-start gap-4" for="is_public">
									<input
										type="checkbox"
										class="toggle toggle-primary"
										id="is_public"
										bind:checked={location.is_public}
									/>
									<div>
										<span class="label-text font-medium">{$t('adventures.public_location')}</span>
										<p class="text-sm text-base-content/60">
											{$t('adventures.public_location_description')}
										</p>
									</div>
								</label>
							</div>
						{/if}

						<!-- Description Field -->
						<div class="form-control">
							<label class="label" for="description">
								<span class="label-text font-medium">{$t('adventures.description')}</span>
							</label>
							<MarkdownEditor bind:text={location.description} editor_height="h-32" />

							<div class="flex items-center gap-4 mt-3">
								<button
									type="button"
									class="btn btn-neutral btn-sm gap-2"
									on:click={generateDesc}
									disabled={!location.name || isGeneratingDesc}
								>
									{#if isGeneratingDesc}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<GenerateIcon class="w-4 h-4" />
									{/if}
									{$t('adventures.generate_desc')}
								</button>
								{#if wikiError}
									<div class="alert alert-error alert-sm">
										<InfoIcon class="w-4 h-4" />
										<span class="text-sm">{wikiError}</span>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Tags Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-warning/10 rounded-lg">
						<CategoryIcon class="w-5 h-5 text-warning" />
					</div>
					<h2 class="text-xl font-bold">{$t('adventures.tags')} ({location.tags?.length || 0})</h2>
				</div>
				<div class="space-y-4">
					<!-- Hidden input for form submission (same as old version) -->
					<input
						type="text"
						id="tags"
						name="tags"
						hidden
						bind:value={location.tags}
						class="input input-bordered w-full"
					/>
					<!-- Use the same ActivityComplete component as the old version -->
					<TagComplete bind:tags={location.tags} />
				</div>
			</div>
		</div>

		<!-- Location Selection Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-secondary/10 rounded-lg">
						<MapIcon class="w-5 h-5 text-secondary" />
					</div>
					<h2 class="text-xl font-bold">{$t('adventures.location_map')}</h2>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
					<!-- Search & Controls -->
					<div class="space-y-4">
						<!-- Location Display Name Input -->
						<div class="form-control">
							<label class="label" for="location-display">
								<span class="label-text font-medium">{$t('adventures.location_display_name')}</span>
							</label>
							<input
								type="text"
								id="location-display"
								bind:value={location.location}
								class="input input-bordered bg-base-100/80 focus:bg-base-100"
								placeholder="Enter location display name"
							/>
						</div>

						<!-- Search Input -->
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
									placeholder="Enter city, location, or landmark..."
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

						<!-- Search Results -->
						{#if isSearching}
							<div class="flex items-center justify-center py-4">
								<span class="loading loading-spinner loading-sm"></span>
								<span class="ml-2 text-sm text-base-content/60"
									>{$t('adventures.searching')}...</span
								>
							</div>
						{:else if searchResults.length > 0}
							<div class="space-y-2">
								<div class="label">
									<span class="label-text text-sm font-medium"
										>{$t('adventures.search_results')}</span
									>
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

						<!-- Current Location Button -->
						<div class="flex items-center gap-2">
							<div class="divider divider-horizontal text-xs">{$t('adventures.or')}</div>
						</div>

						<button class="btn btn-outline gap-2 w-full" on:click={useCurrentLocation}>
							<LocationIcon class="w-4 h-4" />
							{$t('adventures.use_current_location')}
						</button>

						<!-- Selected Location Display -->
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

											<!-- Geographic Tags -->
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
					</div>

					<!-- Map -->
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

						{#if !selectedMarker}
							<p class="text-sm text-base-content/60 text-center">
								{$t('adventures.click_on_map')}
							</p>
						{/if}
					</div>
				</div>
			</div>
		</div>

		<!-- Action Buttons -->
		<div class="flex gap-3 justify-end pt-4">
			<button class="btn btn-neutral-200 gap-2" on:click={handleBack}>
				<ArrowLeftIcon class="w-5 h-5" />
				{$t('adventures.back')}
			</button>
			<button
				class="btn btn-primary gap-2"
				disabled={!location.name || !location.category || isReverseGeocoding}
				on:click={handleSave}
			>
				{#if isReverseGeocoding}
					<span class="loading loading-spinner loading-sm"></span>
					{$t('adventures.processing')}...
				{:else}
					<SaveIcon class="w-5 h-5" />
					{$t('adventures.continue')}
				{/if}
			</button>
		</div>
	</div>
</div>
