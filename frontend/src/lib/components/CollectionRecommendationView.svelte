<script lang="ts">
	import type { Collection, User, ContentImage } from '$lib/types';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { DefaultMarker, MapLibre, Popup } from 'svelte-maplibre';
	import { getBasemapUrl, TRANSPORTATION_TYPES_ICONS } from '$lib';
	import MagnifyIcon from '~icons/mdi/magnify';
	import MapMarker from '~icons/mdi/map-marker';
	import Star from '~icons/mdi/star';
	import StarHalfFull from '~icons/mdi/star-half-full';
	import StarOutline from '~icons/mdi/star-outline';
	import AccountMultiple from '~icons/mdi/account-multiple';
	import Phone from '~icons/mdi/phone';
	import Web from '~icons/mdi/web';
	import OpenInNew from '~icons/mdi/open-in-new';
	import ClockOutline from '~icons/mdi/clock-outline';
	import CurrencyUsd from '~icons/mdi/currency-usd';
	import TuneVariant from '~icons/mdi/tune-variant';
	import CloseCircle from '~icons/mdi/close-circle';
	import Compass from '~icons/mdi/compass';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import LocationModal from '$lib/components/locations/LocationModal.svelte';
	import LodgingModal from '$lib/components/lodging/LodgingModal.svelte';
	import { createEventDispatcher } from 'svelte';
	import type { Location, Lodging } from '$lib/types';

	export let collection: Collection;
	export let user: User | null;
	// Whether the current user can modify this collection (owner or shared user)

	type RecommendationResult = {
		name: string;
		latitude: number;
		longitude: number;
		distance_km: number;
		source: 'google' | 'osm';
		type: string;
		tags?: Record<string, string>;
		rating?: number;
		review_count?: number;
		address?: string;
		business_status?: string;
		opening_hours?: string[];
		is_open_now?: boolean;
		photos?: string[];
		phone_number?: string;
		website?: string;
		google_maps_uri?: string;
		price_level?: string;
		description?: string;
		quality_score?: number;
	};

	let searchQuery = '';
	let selectedCategory: 'tourism' | 'lodging' | 'food' = 'tourism';
	let radiusValue = 5000; // Default 5km
	let loading = false;
	let results: RecommendationResult[] = [];
	let error: string | null = null;
	let selectedLocationId: string | null = null;
	let showFilters = false;
	let mapCenter: { lng: number; lat: number } = { lng: 0, lat: 0 };
	let mapZoom = 12;

	// Filters
	let minRating = 0;
	let minReviews = 0;
	let showOpenOnly = false;

	// Photo modal
	let photoModalOpen = false;
	let selectedPhotos: ContentImage[] = [];
	let selectedPhotoIndex = 0;
	let selectedPlaceName = '';
	let selectedPlaceAddress = '';

	const dispatch = createEventDispatcher();

	// Modals for creating autofilled items
	let showLocationModal = false;
	let showLodgingModal = false;
	let modalLocationToEdit: Location | null = null;
	let modalLodgingToEdit: Lodging | null = null;

	function mapPhotosToContentImages(photos: string[]): ContentImage[] {
		return photos.map((url, i) => ({
			id: `rec-${i}-${Date.now()}`,
			image: url,
			is_primary: i === 0,
			immich_id: null
		}));
	}

	function openCreateLocationFromResult(result: RecommendationResult) {
		modalLocationToEdit = {
			id: '',
			name: result.name || '',
			location: result.address || result.description || '',
			tags: [],
			description: result.description || null,
			rating: result.rating ?? NaN,
			price: null,
			price_currency: null,
			link: result.website || null,
			images: mapPhotosToContentImages(result.photos || []),
			visits: [],
			collections: [collection.id],
			latitude: result.latitude ?? null,
			longitude: result.longitude ?? null,
			is_public: true,
			user: user ?? null,
			category: null,
			attachments: [],
			trails: []
		} as Location;

		showLocationModal = true;
	}

	function openCreateLodgingFromResult(result: RecommendationResult) {
		modalLodgingToEdit = {
			id: '',
			user: user ? user.uuid : '',
			name: result.name || '',
			type: '',
			description: result.description || null,
			rating: result.rating ?? null,
			link: result.website || null,
			check_in: null,
			check_out: null,
			timezone: null,
			reservation_number: null,
			price: null,
			price_currency: null,
			latitude: result.latitude ?? null,
			longitude: result.longitude ?? null,
			location: result.address || result.description || null,
			is_public: true,
			collections: [collection.id],
			created_at: '',
			updated_at: '',
			images: mapPhotosToContentImages(result.photos || []),
			attachments: [],
			visits: [],
			tags: null
		} as Lodging;

		showLodgingModal = true;
	}

	function handleLocationCreate(e: CustomEvent) {
		const created: Location = e.detail;
		showLocationModal = false;
		modalLocationToEdit = null;
		collection.locations = [...collection.locations, created];
	}

	function handleLodgingCreate(e: CustomEvent) {
		const created: Lodging = e.detail;
		showLodgingModal = false;
		modalLodgingToEdit = null;
		collection.lodging = [...(collection.lodging ?? []), created];
	}

	function closeLocationModal() {
		showLocationModal = false;
		modalLocationToEdit = null;
	}

	function closeLodgingModal() {
		showLodgingModal = false;
		modalLodgingToEdit = null;
	}

	$: isMetric = user?.measurement_system === 'metric';
	$: radiusDisplay = isMetric
		? `${(radiusValue / 1000).toFixed(1)} km`
		: `${(radiusValue / 1609.34).toFixed(1)} mi`;

	$: radiusOptions = isMetric
		? [
				{ value: 1000, label: '1 km' },
				{ value: 2000, label: '2 km' },
				{ value: 5000, label: '5 km' },
				{ value: 10000, label: '10 km' },
				{ value: 20000, label: '20 km' },
				{ value: 50000, label: '50 km' }
			]
		: [
				{ value: 1609, label: '1 mi' },
				{ value: 3219, label: '2 mi' },
				{ value: 8047, label: '5 mi' },
				{ value: 16093, label: '10 mi' },
				{ value: 32187, label: '20 mi' },
				{ value: 80467, label: '50 mi' }
			];

	// Types for dropdown items
	type DropdownItem = {
		id: string;
		name: string;
		type: 'location' | 'transportation-departure' | 'transportation-arrival' | 'lodging';
		latitude: number;
		longitude: number;
		icon: string;
	};

	// Helper to get transportation icon by type
	function getTransportIcon(type: string): string {
		if (type in TRANSPORTATION_TYPES_ICONS) {
			return TRANSPORTATION_TYPES_ICONS[type as keyof typeof TRANSPORTATION_TYPES_ICONS];
		}
		return '🚗';
	}

	// Get all items with coordinates for dropdown
	$: dropdownItems = (() => {
		const items: DropdownItem[] = [];

		// Locations
		collection.locations
			.filter((l) => l.latitude && l.longitude)
			.forEach((l) => {
				items.push({
					id: `location-${l.id}`,
					name: l.name,
					type: 'location',
					latitude: l.latitude!,
					longitude: l.longitude!,
					icon: '📍'
				});
			});

		// Transportations - departures (↗ for origin/departure)
		(collection.transportations || [])
			.filter((t) => t.origin_latitude && t.origin_longitude)
			.forEach((t) => {
				const typeIcon = getTransportIcon(t.type);
				items.push({
					id: `transport-dep-${t.id}`,
					name: `${t.name} (${$t('transportation.departure') || 'Departure'})`,
					type: 'transportation-departure',
					latitude: t.origin_latitude!,
					longitude: t.origin_longitude!,
					icon: `${typeIcon}↗`
				});
			});

		// Transportations - arrivals (↙ for arrival)
		(collection.transportations || [])
			.filter((t) => t.destination_latitude && t.destination_longitude)
			.forEach((t) => {
				const typeIcon = getTransportIcon(t.type);
				items.push({
					id: `transport-arr-${t.id}`,
					name: `${t.name} (${$t('transportation.arrival') || 'Arrival'})`,
					type: 'transportation-arrival',
					latitude: t.destination_latitude!,
					longitude: t.destination_longitude!,
					icon: `${typeIcon}↙`
				});
			});

		// Lodging
		(collection.lodging || [])
			.filter((l) => l.latitude && l.longitude)
			.forEach((l) => {
				items.push({
					id: `lodging-${l.id}`,
					name: l.name,
					type: 'lodging',
					latitude: l.latitude!,
					longitude: l.longitude!,
					icon: '🏨'
				});
			});

		return items;
	})();

	// For backward compatibility
	$: locationsWithCoords = collection.locations.filter((l) => l.latitude && l.longitude);

	// Set default selected item and map center
	onMount(() => {
		if (dropdownItems.length > 0) {
			selectedLocationId = dropdownItems[0].id;
			mapCenter = {
				lng: dropdownItems[0].longitude,
				lat: dropdownItems[0].latitude
			};
		}
	});

	// Update map center when selected item changes
	$: if (selectedLocationId) {
		const item = dropdownItems.find((i) => i.id === selectedLocationId);
		if (item) {
			mapCenter = { lng: item.longitude, lat: item.latitude };
		}
	}

	// Filter results
	$: filteredResults = results.filter((r) => {
		if (minRating > 0 && (r.rating === undefined || r.rating < minRating)) return false;
		if (minReviews > 0 && (r.review_count === undefined || r.review_count < minReviews))
			return false;
		if (showOpenOnly && !r.is_open_now) return false;
		return true;
	});

	async function searchRecommendations() {
		if (!searchQuery.trim() && !selectedLocationId) {
			error = 'Please select a location or enter a search query';
			return;
		}

		loading = true;
		error = null;
		results = [];

		try {
			const params = new URLSearchParams();

			if (selectedLocationId) {
				const item = dropdownItems.find((i) => i.id === selectedLocationId);
				if (item) {
					params.append('lat', item.latitude.toString());
					params.append('lon', item.longitude.toString());
				}
			} else if (searchQuery.trim()) {
				params.append('location', searchQuery);
			}

			params.append('radius', radiusValue.toString());
			params.append('category', selectedCategory);

			const response = await fetch(`/api/recommendations/query?${params.toString()}`);

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.error || 'Failed to fetch recommendations');
			}

			const data = await response.json();

			if (data.error) {
				throw new Error(data.error);
			}

			results = data.results || [];

			// Update map if we have results
			if (results.length > 0) {
				// Calculate bounds for all results
				const lats = results.map((r) => r.latitude);
				const lngs = results.map((r) => r.longitude);
				const avgLat = lats.reduce((a, b) => a + b, 0) / lats.length;
				const avgLng = lngs.reduce((a, b) => a + b, 0) / lngs.length;
				mapCenter = { lng: avgLng, lat: avgLat };
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred';
			console.error('Error fetching recommendations:', err);
		} finally {
			loading = false;
		}
	}

	function openPhotoModal(
		photos: string[],
		placeName: string,
		placeAddress: string = '',
		startIndex: number = 0
	) {
		// Convert photo URLs to ContentImage format
		selectedPhotos = photos.map((url, index) => ({
			id: `photo-${index}`,
			image: url,
			is_primary: index === 0,
			immich_id: null
		}));
		selectedPlaceName = placeName;
		selectedPlaceAddress = placeAddress;
		selectedPhotoIndex = startIndex;
		photoModalOpen = true;
	}

	function closePhotoModal() {
		photoModalOpen = false;
		selectedPhotos = [];
		selectedPhotoIndex = 0;
		selectedPlaceName = '';
		selectedPlaceAddress = '';
	}

	function renderStars(rating: number | undefined) {
		if (!rating) return [];

		const stars = [];
		const fullStars = Math.floor(rating);
		const hasHalfStar = rating % 1 >= 0.5;

		for (let i = 0; i < 5; i++) {
			if (i < fullStars) {
				stars.push({ type: 'full', key: i });
			} else if (i === fullStars && hasHalfStar) {
				stars.push({ type: 'half', key: i });
			} else {
				stars.push({ type: 'empty', key: i });
			}
		}

		return stars;
	}

	function getPriceLevelDisplay(priceLevel: string | undefined) {
		if (!priceLevel) return '';
		const levels: Record<string, string> = {
			FREE: 'Free',
			INEXPENSIVE: '$',
			MODERATE: '$$',
			EXPENSIVE: '$$$',
			VERY_EXPENSIVE: '$$$$'
		};
		return levels[priceLevel] || '';
	}

	function formatDistance(km: number) {
		if (isMetric) {
			return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
		} else {
			const miles = km / 1.60934;
			const feet = miles * 5280;
			return miles < 0.1 ? `${Math.round(feet)} ft` : `${miles.toFixed(1)} mi`;
		}
	}
</script>

<!-- Photo Modal -->
{#if photoModalOpen}
	<ImageDisplayModal
		images={selectedPhotos}
		initialIndex={selectedPhotoIndex}
		name={selectedPlaceName}
		location={selectedPlaceAddress}
		on:close={closePhotoModal}
	/>
{/if}

{#if showLocationModal}
	<LocationModal
		{user}
		{collection}
		locationToEdit={modalLocationToEdit}
		on:create={handleLocationCreate}
		on:save={handleLocationCreate}
		on:close={closeLocationModal}
	/>
{/if}

{#if showLodgingModal}
	<LodgingModal
		{user}
		{collection}
		lodgingToEdit={modalLodgingToEdit}
		on:create={handleLodgingCreate}
		on:close={closeLodgingModal}
		on:save={handleLodgingCreate}
	/>
{/if}

<div class="space-y-6">
	<!-- Search & Filter Card -->
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body">
			<h2 class="card-title text-2xl mb-4">
				<Compass class="w-8 h-8" />
				{$t('recomendations.discover_places')}
			</h2>

			<!-- Search Options -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<!-- Location Selector -->
				{#if dropdownItems.length > 0}
					<div class="form-control">
						<label class="label">
							<span class="label-text font-semibold"
								>{$t('recomendations.search_around_location')}</span
							>
						</label>
						<select class="select select-bordered w-full" bind:value={selectedLocationId}>
							<option value={null}>{$t('recomendations.use_search_instead')}...</option>
							{#each dropdownItems as item}
								<option value={item.id}>{item.icon} {item.name}</option>
							{/each}
						</select>
					</div>
				{/if}

				<!-- Search Input -->
				<div class="form-control">
					<label class="label">
						<span class="label-text font-semibold">{$t('recomendations.search_by_address')}</span>
					</label>
					<input
						type="text"
						placeholder={$t('adventures.search_placeholder')}
						class="input input-bordered w-full"
						bind:value={searchQuery}
						disabled={selectedLocationId !== null}
						on:keydown={(e) => e.key === 'Enter' && searchRecommendations()}
					/>
				</div>

				<!-- Category Selector -->
				<div class="form-control">
					<label class="label">
						<span class="label-text font-semibold">{$t('adventures.category')}</span>
					</label>
					<select class="select select-bordered w-full" bind:value={selectedCategory}>
						<option value="tourism">🏛️ {$t('recomendations.tourism')}</option>
						<option value="lodging">🏨 {$t('recomendations.lodging')}</option>
						<option value="food">🍴 {$t('recomendations.food')}</option>
					</select>
				</div>

				<!-- Radius Selector -->
				<div class="form-control">
					<label class="label">
						<span class="label-text font-semibold"
							>{$t('recomendations.search_radius_label')} {radiusDisplay}</span
						>
					</label>
					<select class="select select-bordered w-full" bind:value={radiusValue}>
						{#each radiusOptions as option}
							<option value={option.value}>{option.label}</option>
						{/each}
					</select>
				</div>
			</div>

			<!-- Filters Toggle -->
			<div class="flex gap-2 mt-4">
				<button class="btn btn-primary flex-1" on:click={searchRecommendations} disabled={loading}>
					{#if loading}
						<span class="loading loading-spinner loading-sm"></span>
						{$t('recomendations.searching')}
					{:else}
						<MagnifyIcon class="w-5 h-5" />
						{$t('navbar.search')}
					{/if}
				</button>
				<button class="btn btn-ghost" on:click={() => (showFilters = !showFilters)}>
					<TuneVariant class="w-5 h-5" />
					{$t('adventures.filter')}
				</button>
			</div>

			<!-- Advanced Filters -->
			{#if showFilters}
				<div class="divider">{$t('adventures.filter')}</div>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					<div class="form-control">
						<label class="label">
							<span class="label-text">{$t('recomendations.minimum_rating')}</span>
						</label>
						<select class="select select-bordered select-sm" bind:value={minRating}>
							<option value={0}>{$t('recomendations.any')}</option>
							<option value={3}>3+ ⭐</option>
							<option value={3.5}>3.5+ ⭐</option>
							<option value={4}>4+ ⭐</option>
							<option value={4.5}>4.5+ ⭐</option>
						</select>
					</div>

					<div class="form-control">
						<!-- svelte-ignore a11y-label-has-associated-control -->
						<label class="label">
							<span class="label-text">{$t('recomendations.minimum_reviews')}</span>
						</label>
						<select class="select select-bordered select-sm" bind:value={minReviews}>
							<option value={0}>{$t('recomendations.any')}</option>
							<option value={10}>10+</option>
							<option value={50}>50+</option>
							<option value={100}>100+</option>
							<option value={500}>500+</option>
						</select>
					</div>

					<div class="form-control">
						<label class="label cursor-pointer">
							<span class="label-text">{$t('recomendations.open_now_only')}</span>
							<input type="checkbox" class="toggle toggle-primary" bind:checked={showOpenOnly} />
						</label>
					</div>
				</div>
			{/if}

			<!-- Error Message -->
			{#if error}
				<div class="alert alert-error mt-4">
					<CloseCircle class="w-6 h-6" />
					<span>{error}</span>
				</div>
			{/if}
		</div>
	</div>

	<!-- Results -->
	{#if loading}
		<div class="flex justify-center py-12">
			<span class="loading loading-spinner loading-lg text-primary"></span>
		</div>
	{:else if filteredResults.length > 0}
		<!-- Results Stats -->
		<div class="stats shadow w-full">
			<div class="stat">
				<div class="stat-title">{$t('recomendations.total_results')}</div>
				<div class="stat-value text-primary">{filteredResults.length}</div>
			</div>
			<div class="stat">
				<div class="stat-title">{$t('recomendations.average_rating')}</div>
				<div class="stat-value text-secondary">
					{(
						filteredResults.filter((r) => r.rating).reduce((sum, r) => sum + (r.rating || 0), 0) /
						filteredResults.filter((r) => r.rating).length
					).toFixed(1)}
					⭐
				</div>
			</div>
			<div class="stat">
				<div class="stat-title">{$t('recomendations.search_radius_label')}</div>
				<div class="stat-value text-accent">{radiusDisplay}</div>
			</div>
		</div>

		<!-- Map View -->
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<h3 class="card-title text-xl mb-4">📍 {$t('recomendations.map_view')}</h3>
				<div class="rounded-lg overflow-hidden shadow-lg">
					<MapLibre
						style={getBasemapUrl()}
						class="w-full h-[500px]"
						standardControls
						center={mapCenter}
						zoom={mapZoom}
					>
						<!-- Collection Locations -->
						{#each collection.locations as location}
							{#if location.latitude && location.longitude}
								<DefaultMarker lngLat={{ lng: location.longitude, lat: location.latitude }}>
									<Popup openOn="click" offset={[0, -10]}>
										<div class="p-2">
											<a
												href={`/adventures/${location.id}`}
												class="text-lg font-bold text-black hover:underline mb-1 block"
											>
												{location.name}
											</a>
											<p class="text-xs text-black opacity-70">
												{$t('recomendations.your_location')}
											</p>
										</div>
									</Popup>
								</DefaultMarker>
							{/if}
						{/each}

						<!-- Recommendation Results -->
						{#each filteredResults as result}
							<DefaultMarker lngLat={{ lng: result.longitude, lat: result.latitude }}>
								<Popup openOn="click" offset={[0, -10]}>
									<div class="p-3 max-w-xs">
										<h4 class="text-base font-bold text-black mb-2">{result.name}</h4>
										{#if result.rating}
											<div class="flex items-center gap-2 mb-2">
												<div class="flex text-yellow-500">
													{#each renderStars(result.rating) as star}
														{#if star.type === 'full'}
															<Star class="w-4 h-4" />
														{:else if star.type === 'half'}
															<StarHalfFull class="w-4 h-4" />
														{:else}
															<StarOutline class="w-4 h-4" />
														{/if}
													{/each}
												</div>
												<span class="text-sm text-black">{result.rating.toFixed(1)}</span>
												{#if result.review_count}
													<span class="text-xs text-black opacity-70">
														({result.review_count})
													</span>
												{/if}
											</div>
										{/if}
										{#if result.address}
											<p class="text-xs text-black opacity-70 mb-2">📍 {result.address}</p>
										{/if}
										<p class="text-xs text-black font-semibold">
											🚶 {formatDistance(result.distance_km)}
											{$t('recomendations.away')}
										</p>
									</div>
								</Popup>
							</DefaultMarker>
						{/each}
					</MapLibre>
				</div>
			</div>
		</div>

		<!-- Results Grid -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each filteredResults as result}
				<div class="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow">
					<!-- Photo Carousel -->
					{#if result.photos && result.photos.length > 0}
						<figure class="relative h-48 cursor-pointer">
							<button
								class="w-full h-full"
								on:click={() =>
									openPhotoModal(result.photos || [], result.name, result.address || '')}
							>
								<img src={result.photos[0]} alt={result.name} class="w-full h-full object-cover" />
							</button>
							{#if result.photos.length > 1}
								<div
									class="badge badge-neutral badge-sm absolute bottom-2 right-2 bg-black/70 text-white border-none"
								>
									📷 {result.photos.length}
								</div>
							{/if}
						</figure>
					{:else}
						<div
							class="bg-gradient-to-br from-primary/20 to-secondary/20 h-48 flex items-center justify-center"
						>
							<MapMarker class="w-16 h-16 opacity-30" />
						</div>
					{/if}

					<div class="card-body p-4">
						<!-- Title & Type -->
						<h3 class="card-title text-lg">
							{result.name}
							{#if result.is_open_now}
								<span class="badge badge-success badge-sm">{$t('recomendations.open')}</span>
							{/if}
						</h3>

						<!-- Rating -->
						{#if result.rating}
							<div class="flex items-center gap-2 mb-2">
								<div class="flex text-yellow-500">
									{#each renderStars(result.rating) as star}
										{#if star.type === 'full'}
											<Star class="w-4 h-4" />
										{:else if star.type === 'half'}
											<StarHalfFull class="w-4 h-4" />
										{:else}
											<StarOutline class="w-4 h-4" />
										{/if}
									{/each}
								</div>
								<span class="text-sm font-semibold">{result.rating.toFixed(1)}</span>
								{#if result.review_count}
									<span class="text-xs opacity-70">
										<AccountMultiple class="w-3 h-3 inline" />
										{result.review_count}
									</span>
								{/if}
								{#if result.quality_score}
									<div class="badge badge-primary badge-sm ml-auto">
										Score: {result.quality_score}
									</div>
								{/if}
							</div>
						{/if}

						<!-- Address -->
						{#if result.address}
							<p class="text-sm opacity-70 line-clamp-2">
								<MapMarker class="w-4 h-4 inline" />
								{result.address}
							</p>
						{/if}

						<!-- Distance & Price -->
						<div class="flex gap-2 flex-wrap mt-2">
							<div class="badge badge-outline badge-sm">
								🚶 {formatDistance(result.distance_km)}
							</div>
							{#if result.price_level}
								<div class="badge badge-outline badge-sm">
									<CurrencyUsd class="w-3 h-3" />
									{getPriceLevelDisplay(result.price_level)}
								</div>
							{/if}
							<div class="badge badge-ghost badge-sm">
								{result.source === 'google' ? '🔍 Google' : '🗺️ OSM'}
							</div>
						</div>

						<!-- Description -->
						{#if result.description}
							<p class="text-sm mt-2 line-clamp-2 opacity-80">
								{result.description}
							</p>
						{/if}

						<!-- Opening Hours -->
						{#if result.opening_hours && result.opening_hours.length > 0}
							<div class="collapse collapse-arrow bg-base-200 mt-2">
								<input type="checkbox" />
								<div class="collapse-title text-sm font-medium">
									<ClockOutline class="w-4 h-4 inline" />
									{$t('recomendations.hours')}
								</div>
								<div class="collapse-content text-xs">
									{#each result.opening_hours as hours}
										<p>{hours}</p>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Action Buttons -->
						<div class="card-actions justify-end mt-4">
							{#if result.phone_number}
								<a href={`tel:${result.phone_number}`} class="btn btn-sm btn-neutral-100">
									<Phone class="w-4 h-4" />
								</a>
							{/if}
							{#if result.website}
								<a
									href={result.website}
									target="_blank"
									rel="noopener noreferrer"
									class="btn btn-sm btn-neutral-100"
								>
									<Web class="w-4 h-4" />
								</a>
							{/if}
							{#if result.google_maps_uri}
								<a
									href={result.google_maps_uri}
									target="_blank"
									rel="noopener noreferrer"
									class="btn btn-sm btn-primary"
								>
									View on Maps
									<OpenInNew class="w-4 h-4" />
								</a>
							{/if}

							<!-- Create from recommendation -->
							<button
								class="btn btn-sm btn-outline"
								on:click={() => openCreateLocationFromResult(result)}
							>
								{$t('recomendations.add_location')}
							</button>
							<button
								class="btn btn-sm btn-ghost"
								on:click={() => openCreateLodgingFromResult(result)}
							>
								{$t('recomendations.add_lodging')}
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{:else if !loading && results.length === 0 && !error}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body text-center py-12">
				<MagnifyIcon class="w-24 h-24 mx-auto opacity-30 mb-4" />
				<h3 class="text-2xl font-bold mb-2">{$t('recomendations.no_results_yet')}</h3>
				<p class="opacity-70">{$t('recomendations.select_location_or_query')}</p>
			</div>
		</div>
	{/if}
</div>
