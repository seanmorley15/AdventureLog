<script lang="ts">
	import { DefaultMarker, Popup, Marker, GeoJSON, LineLayer } from 'svelte-maplibre';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { Activity, Location, VisitedCity, VisitedRegion, Pin } from '$lib/types.js';
	import type { ClusterOptions } from 'svelte-maplibre';
	import { goto } from '$app/navigation';
	import { getActivityColor } from '$lib';
	import { page } from '$app/stores';

	// Icons
	import MapIcon from '~icons/mdi/map';
	import Filter from '~icons/mdi/filter-variant';
	import Plus from '~icons/mdi/plus';
	import Clear from '~icons/mdi/close';
	import Eye from '~icons/mdi/eye';
	import PinIcon from '~icons/mdi/map-marker';
	import Calendar from '~icons/mdi/calendar';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';
	import ActivityIcon from '~icons/mdi/run-fast';
	import SearchIcon from '~icons/mdi/magnify';
	import FullMap from '$lib/components/map/FullMap.svelte';

	export let data;

	let createModalOpen: boolean = false;
	let showRegions: boolean = false;
	let showActivities: boolean = false;
	let showCities: boolean = false;
	let sidebarOpen: boolean = false;

	let basemapType: string = 'default';

	// Map state from URL params
	let mapZoom: number = 2;
	let mapCenter: [number, number] = [0, 0];
	let updateUrlTimeout: NodeJS.Timeout | null = null;

	export let initialLatLng: { lat: number; lng: number } | null = null;

	let visitedRegions: VisitedRegion[] = data.props.visitedRegions;
	let visitedCities: VisitedCity[] = [];
	let pins: Pin[] = data.props.pins; // Lightweight pin objects
	let activities: Activity[] = [];

	let filteredPins = pins;

	let showVisited: boolean = true;
	let showPlanned: boolean = true;
	let searchQuery: string = '';

	// Ownership filter for collaborative mode
	let ownershipFilter: 'all' | 'mine' | 'public' = 'all';

	let newMarker: { lngLat: any } | null = null;
	let newLongitude: number | null = null;
	let newLatitude: number | null = null;

	// Cache for full location data
	let locationCache: Map<string, Location> = new Map();
	let loadingLocations: Set<string> = new Set();
	let locationRequests: Map<string, Promise<Location | null>> = new Map();

	// Hover/focus popup state
	let hoveredPinId: string | null = null;
	let hoveredLocation: Location | null = null;
	let hoveredLocationLoading: boolean = false;
	let hoveredLocationError: string | null = null;
	let hoverRequestSeq = 0;

	// Touch/coarse-pointer devices: tap should open preview instead of navigating.
	let isTouchLike: boolean = false;

	let locationBeingUpdated: Location | undefined = undefined;

	// Clustering configuration
	const PIN_SOURCE_ID = 'map-pins';
	const pinClusterOptions: ClusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 };

	type VisitStatus = 'visited' | 'planned';

	type PinFeatureProperties = {
		id: string;
		name: string;
		visitStatus: VisitStatus;
		categoryIcon?: string;
	};

	type PinFeature = {
		type: 'Feature';
		geometry: {
			type: 'Point';
			coordinates: [number, number];
		};
		properties: PinFeatureProperties;
	};

	type PinFeatureCollection = {
		type: 'FeatureCollection';
		features: PinFeature[];
	};

	function parseCoordinate(value: number | string | null | undefined): number | null {
		if (value === null || value === undefined) return null;
		const numeric = typeof value === 'number' ? value : Number(value);
		return Number.isFinite(numeric) ? numeric : null;
	}

	function pinToFeature(pin: Pin): PinFeature | null {
		const lat = parseCoordinate(pin.latitude);
		const lon = parseCoordinate(pin.longitude);
		if (lat === null || lon === null) return null;

		return {
			type: 'Feature',
			geometry: { type: 'Point', coordinates: [lon, lat] },
			properties: {
				id: pin.id,
				name: pin.name,
				visitStatus: pin.is_visited ? 'visited' : 'planned',
				categoryIcon: pin.category?.icon || '📍'
			}
		};
	}

	function pinToFeatureUnknown(item: unknown) {
		return pinToFeature(item as Pin);
	}

	function getMarkerProps(feature: any): PinFeatureProperties | null {
		return feature && feature.properties ? feature.properties : null;
	}

	function getVisitStatusClass(status: VisitStatus): string {
		switch (status) {
			case 'visited':
				return 'bg-gradient-to-br from-emerald-400 to-emerald-600';
			case 'planned':
				return 'bg-gradient-to-br from-blue-400 to-blue-600';
			default:
				return 'bg-gray-200';
		}
	}

	function markerClassResolver(props: { visitStatus?: string } | null): string {
		if (!props?.visitStatus) return '';
		return getVisitStatusClass(props.visitStatus as VisitStatus);
	}

	function markerLabelResolver(props: { categoryIcon?: string } | null): string {
		if (!props) return '📍';
		return props.categoryIcon || '📍';
	}

	async function handleViewDetails(pinId: string) {
		goto(`/locations/${pinId}`);
	}

	// Statistics
	$: totalAdventures = pins.length;
	$: visitedAdventures = pins.filter((pin) => pin.is_visited).length;
	$: plannedAdventures = pins.filter((pin) => !pin.is_visited).length;
	$: totalRegions = visitedRegions.length;

	// Get unique categories for filtering
	$: categories = [...new Set(pins.map((pin) => pin.category?.display_name).filter(Boolean))];

	// Updates the filtered pins based on the checkboxes, search query, and ownership
	$: {
		const query = searchQuery.toLowerCase().trim();
		filteredPins = pins.filter((pin) => {
			// Filter by visited/planned status
			const statusMatch =
				(showVisited && pin.is_visited === true) || (showPlanned && pin.is_visited !== true);
			if (!statusMatch) return false;

			// Filter by ownership (collaborative mode)
			if (data.collaborativeMode && ownershipFilter !== 'all') {
				if (ownershipFilter === 'mine' && pin.is_owned !== true) return false;
				if (ownershipFilter === 'public' && pin.is_owned !== false) return false;
			}

			// Filter by search query
			if (!query) return true;
			return (
				pin.name?.toLowerCase().includes(query) ||
				pin.category?.display_name?.toLowerCase().includes(query)
			);
		});

		// Auto-zoom to search results when search query changes
		if (query && filteredPins.length > 0 && typeof window !== 'undefined') {
			zoomToFilteredPins();
		}
	}

	// Reset the longitude and latitude when the newMarker is set to null
	$: {
		if (!newMarker) {
			newLongitude = null;
			newLatitude = null;
		}
	}

	// Sync the locationBeingUpdated with the pins array
	$: {
		if (locationBeingUpdated && locationBeingUpdated.id) {
			const index = pins.findIndex((pin) => pin.id === locationBeingUpdated?.id);

			if (index !== -1) {
				// Update existing pin with new data
				pins[index] = {
					id: locationBeingUpdated.id,
					name: locationBeingUpdated.name,
					latitude: locationBeingUpdated.latitude?.toString() || '',
					longitude: locationBeingUpdated.longitude?.toString() || '',
					is_visited: locationBeingUpdated.is_visited,
					category: locationBeingUpdated.category
				};
				pins = pins; // Trigger reactivity
			} else {
				// Add new pin
				const newPin: Pin = {
					id: locationBeingUpdated.id,
					name: locationBeingUpdated.name,
					latitude: locationBeingUpdated.latitude?.toString() || '',
					longitude: locationBeingUpdated.longitude?.toString() || '',
					is_visited: locationBeingUpdated.is_visited,
					category: locationBeingUpdated.category
				};
				pins = [newPin, ...pins];
			}

			// Also update the cache
			locationCache.set(locationBeingUpdated.id, locationBeingUpdated);
		}
	}

	$: {
		// if show activities is true, fetch all activities
		if (showActivities && activities.length === 0) {
			fetchAllActivities();
		}
	}

	async function fetchAllActivities() {
		const response = await fetch('/api/activities');
		activities = await response.json();
	}

	$: {
		if (showCities && visitedCities.length === 0) {
			fetchVisitedCities();
		}
	}

	async function fetchVisitedCities() {
		const response = await fetch('/api/visitedcity');
		visitedCities = await response.json();
	}

	function formatDateForPopup(value: string | null | undefined): string {
		if (!value) return '';
		// Most API date strings here are ISO-ish; for a popup, a short date is enough.
		return value.split('T')[0] ?? value;
	}

	function truncateForPopup(value: string | null | undefined, max = 140): string {
		if (!value) return '';
		const normalized = value.replace(/\s+/g, ' ').trim();
		if (normalized.length <= max) return normalized;
		return `${normalized.slice(0, max).trim()}…`;
	}

	async function fetchLocationDetails(locationId: string): Promise<Location | null> {
		// Check cache first
		if (locationCache.has(locationId)) {
			return locationCache.get(locationId)!;
		}

		// Reuse in-flight requests so hover doesn't trigger duplicate fetches
		const existing = locationRequests.get(locationId);
		if (existing) return existing;

		const request = (async () => {
			try {
				loadingLocations.add(locationId);
				const response = await fetch(`/api/locations/${locationId}`);

				if (!response.ok) {
					throw new Error(`Failed to fetch location: ${response.statusText}`);
				}

				const location: Location = await response.json();
				locationCache.set(locationId, location);
				return location;
			} catch (error) {
				console.error('Error fetching location details:', error);
				return null;
			} finally {
				loadingLocations.delete(locationId);
				locationRequests.delete(locationId);
			}
		})();

		locationRequests.set(locationId, request);
		return request;
	}

	async function prefetchLocationDetailsForPopup(locationId: string) {
		hoveredPinId = locationId;
		hoveredLocationError = null;

		const cached = locationCache.get(locationId) ?? null;
		hoveredLocation = cached;

		// If we already have full data, no need to show a loading state.
		if (cached) {
			hoveredLocationLoading = false;
			return;
		}

		const seq = ++hoverRequestSeq;
		hoveredLocationLoading = true;

		const location = await fetchLocationDetails(locationId);
		if (seq !== hoverRequestSeq || hoveredPinId !== locationId) return;

		hoveredLocationLoading = false;
		if (!location) {
			hoveredLocationError = $t('errors.generic_error') ?? 'Failed to load details';
			hoveredLocation = cached;
			return;
		}

		hoveredLocation = location;
	}

	function clearHoverPopupIfActive(locationId: string) {
		if (hoveredPinId !== locationId) return;
		hoveredPinId = null;
		hoveredLocation = null;
		hoveredLocationLoading = false;
		hoveredLocationError = null;
	}

	function addMarker(e: CustomEvent<{ lngLat: { lng: any; lat: any } }>) {
		newMarker = null;
		newMarker = { lngLat: e.detail.lngLat };
		newLongitude = e.detail.lngLat.lng;
		newLatitude = e.detail.lngLat.lat;
	}

	function newAdventure() {
		initialLatLng = { lat: newLatitude, lng: newLongitude } as { lat: number; lng: number };
		createModalOpen = true;
	}

	function createNewAdventure(event: CustomEvent) {
		const location: Location = event.detail;

		// Add to pins array
		const newPin: Pin = {
			id: location.id,
			name: location.name,
			latitude: location.latitude?.toString() || '',
			longitude: location.longitude?.toString() || '',
			is_visited: location.is_visited,
			category: location.category
		};

		pins = [...pins, newPin];

		// Add to cache
		locationCache.set(location.id, location);

		newMarker = null;
		createModalOpen = false;
	}

	function clearMarker() {
		newMarker = null;
	}

	function zoomToFilteredPins() {
		if (filteredPins.length === 0) return;

		const lngs = filteredPins
			.map((pin) => parseCoordinate(pin.longitude))
			.filter((lng): lng is number => lng !== null);
		const lats = filteredPins
			.map((pin) => parseCoordinate(pin.latitude))
			.filter((lat): lat is number => lat !== null);

		if (lngs.length === 0 || lats.length === 0) return;

		const minLng = Math.min(...lngs);
		const maxLng = Math.max(...lngs);
		const minLat = Math.min(...lats);
		const maxLat = Math.max(...lats);

		if (filteredPins.length === 1) {
			// Single pin - center on it with a nice zoom level
			mapCenter = [lngs[0], lats[0]];
			mapZoom = 12;
		} else {
			// Multiple pins - fit bounds with padding
			const centerLng = (minLng + maxLng) / 2;
			const centerLat = (minLat + maxLat) / 2;
			mapCenter = [centerLng, centerLat];

			// Calculate appropriate zoom level based on bounds
			const lngDiff = maxLng - minLng;
			const latDiff = maxLat - minLat;
			const maxDiff = Math.max(lngDiff, latDiff);

			if (maxDiff > 50) mapZoom = 3;
			else if (maxDiff > 20) mapZoom = 4;
			else if (maxDiff > 10) mapZoom = 5;
			else if (maxDiff > 5) mapZoom = 6;
			else if (maxDiff > 2) mapZoom = 7;
			else if (maxDiff > 1) mapZoom = 8;
			else if (maxDiff > 0.5) mapZoom = 9;
			else mapZoom = 10;
		}
	}

	function updateUrlParams(lat: number, lng: number, zoom: number) {
		if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
		updateUrlTimeout = setTimeout(() => {
			const params = new URLSearchParams($page.url.searchParams);
			params.set('lat', lat.toFixed(6));
			params.set('lng', lng.toFixed(6));
			params.set('zoom', zoom.toFixed(2));
			goto(`?${params.toString()}`, { replaceState: true, noScroll: true, keepFocus: true });
		}, 500);
	}

	function handleMapMove(e: CustomEvent<{ center: { lng: number; lat: number }; zoom: number }>) {
		const { center, zoom } = e.detail;
		updateUrlParams(center.lat, center.lng, zoom);
	}

	onMount(() => {
		// Initialize from URL params
		const params = $page.url.searchParams;
		const lat = params.get('lat');
		const lng = params.get('lng');
		const zoom = params.get('zoom');

		if (lat && lng && zoom) {
			const parsedLat = parseFloat(lat);
			const parsedLng = parseFloat(lng);
			const parsedZoom = parseFloat(zoom);

			if (Number.isFinite(parsedLat) && Number.isFinite(parsedLng) && Number.isFinite(parsedZoom)) {
				mapCenter = [parsedLng, parsedLat];
				mapZoom = parsedZoom;
			}
		}

		if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
		const mql = window.matchMedia('(hover: none), (pointer: coarse)');
		const update = () => {
			isTouchLike = mql.matches;
		};
		update();
		if (typeof mql.addEventListener === 'function') {
			mql.addEventListener('change', update);
			return () => {
				mql.removeEventListener('change', update);
				if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
			};
		}
		// Safari < 14
		(mql as any).addListener?.(update);
		return () => {
			(mql as any).removeListener?.(update);
			if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
		};
	});

	// FullMap handles cluster theme styling + cluster expansion on click.
</script>

<svelte:head>
	<title>Adventure Map</title>
	<meta name="description" content="View your travels on a map." />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="map-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<!-- Header Section -->
			<div class="sticky top-0 z-40 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4">
							<button
								class="btn btn-ghost btn-square lg:hidden"
								on:click={() => (sidebarOpen = !sidebarOpen)}
							>
								<Filter class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-xl">
									<MapIcon class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-primary">
										{$t('map.location_map')}
									</h1>
									<p class="text-sm text-base-content/60">
										{filteredPins.length}
										{$t('worldtravel.of')}
										{totalAdventures}
										{$t('map.locations_shown')}
									</p>
								</div>
							</div>
						</div>

						<!-- Quick Stats -->
						<div class="hidden md:flex items-center gap-2">
							<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('adventures.visited')}</div>
									<div class="stat-value text-lg text-success">{visitedAdventures}</div>
								</div>
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('adventures.planned')}</div>
									<div class="stat-value text-lg text-info">{plannedAdventures}</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Controls -->
					<div class="mt-4 flex flex-wrap items-center gap-4">
						<!-- Search Bar -->
						<label class="input input-bordered input-sm flex items-center gap-2 flex-1 max-w-md">
							<SearchIcon class="h-4 w-4 opacity-70" />
							<input
								type="text"
								class="grow"
								placeholder={$t('map.search_locations')}
								bind:value={searchQuery}
							/>
							{#if searchQuery}
								<button
									type="button"
									class="btn btn-ghost btn-xs btn-circle"
									on:click={() => (searchQuery = '')}
									aria-label="Clear search"
								>
									✕
								</button>
							{/if}
						</label>

						<!-- Action Buttons -->
						<div class="flex items-center gap-2">
							{#if newMarker}
								<button type="button" class="btn btn-primary btn-sm gap-2" on:click={newAdventure}>
									<Plus class="w-4 h-4" />
									{$t('map.add_location_at_marker')}
								</button>
								<button type="button" class="btn btn-ghost btn-sm gap-2" on:click={clearMarker}>
									<Clear class="w-4 h-4" />
									{$t('map.clear_marker')}
								</button>
							{:else}
								<button
									type="button"
									class="btn btn-primary btn-sm gap-2"
									on:click={() => (createModalOpen = true)}
								>
									<Plus class="w-4 h-4" />
									{$t('map.add_location')}
								</button>
							{/if}
						</div>
					</div>
				</div>
			</div>

			<!-- Map Section -->
			<div class="container mx-auto px-6 py-4 flex-1">
				<div class="card bg-base-100 shadow-xl h-full relative">
					<div class="card-body p-0 h-full">
						<FullMap
							bind:basemapType
							sourceId={PIN_SOURCE_ID}
							items={filteredPins}
							toFeature={pinToFeatureUnknown}
							clusterEnabled={true}
							clusterOptions={pinClusterOptions}
							{getMarkerProps}
							mapClass="w-full h-full min-h-[70vh] rounded-lg"
							standardControls
							zoom={mapZoom}
							center={mapCenter}
							on:mapClick={addMarker}
							on:mapMove={handleMapMove}
						>
							<svelte:fragment
								slot="marker"
								let:markerProps
								let:markerLngLat
								let:isActive
								let:setActive
							>
								{#if markerProps && markerLngLat}
									<Marker lngLat={markerLngLat} class={isActive ? 'map-pin-active' : 'map-pin'}>
										<div
											class="relative group z-[1000] group-hover:z-[10000] focus-within:z-[10000]"
										>
											<!-- Marker Pin -->
											<div
												class="map-pin-hit grid place-items-center w-8 h-8 rounded-full border-2 border-white shadow-lg text-base cursor-pointer group-hover:scale-110 transition-all duration-200 {markerClassResolver(
													markerProps
												)}"
												class:scale-110={isActive}
												role="button"
												tabindex="0"
												aria-label={markerProps.name}
												title=""
												on:mouseenter={() => {
													setActive(true);
													prefetchLocationDetailsForPopup(markerProps.id);
												}}
												on:mouseleave={() => {
													if (isTouchLike) return;
													setActive(false);
													clearHoverPopupIfActive(markerProps.id);
												}}
												on:focus={() => {
													setActive(true);
													prefetchLocationDetailsForPopup(markerProps.id);
												}}
												on:blur={() => {
													if (isTouchLike) return;
													setActive(false);
													clearHoverPopupIfActive(markerProps.id);
												}}
												on:click={(e) => {
													e.stopPropagation();
													if (isTouchLike) {
														// On touch devices: first tap shows popup, second tap navigates
														if (isActive && hoveredPinId === markerProps.id && hoveredLocation) {
															// Already active with details loaded - navigate
															handleViewDetails(markerProps.id);
															return;
														}
														// First tap or details not loaded - show popup
														setActive(true);
														prefetchLocationDetailsForPopup(markerProps.id);
														return;
													}
													// Desktop: click navigates directly
													handleViewDetails(markerProps.id);
												}}
												on:keydown={(e) => {
													if (e.key !== 'Enter') return;
													e.stopPropagation();
													handleViewDetails(markerProps.id);
												}}
											>
												{markerLabelResolver(markerProps)}
											</div>

											<!-- View Details button moved here -->
											<!-- Custom DaisyUI Popup -->
											<div
												class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:pointer-events-auto transition-all duration-200 z-[9999]"
												class:opacity-100={isActive}
												class:pointer-events-auto={isActive}
											>
												<div
													class="card card-compact bg-base-100 shadow-xl border border-base-300 min-w-56 max-w-80"
												>
													<div class="card-body gap-3">
														<!-- Always-visible (fast) content -->
														<div class="space-y-2">
															<div class="min-w-0">
																<h3 class="card-title text-sm leading-tight truncate">
																	{markerProps.name}
																</h3>
																<div class="mt-1 flex items-center gap-2">
																	<div
																		class="badge badge-sm {markerProps.visitStatus === 'visited'
																			? 'badge-success'
																			: 'badge-info'}"
																	>
																		{markerProps.visitStatus === 'visited'
																			? $t('adventures.visited')
																			: $t('adventures.planned')}
																	</div>
																	{#if markerProps.categoryIcon}
																		<div class="badge badge-ghost badge-sm">
																			{markerProps.categoryIcon}
																		</div>
																	{/if}
																</div>
															</div>
														</div>

														{#if isActive}
															<!-- Progressive (fetched) content -->
															{#if hoveredPinId !== markerProps.id}
																<div class="space-y-2">
																	<div class="flex items-center gap-2">
																		<span class="loading loading-spinner loading-xs"></span>
																		<span class="text-xs text-base-content/60">Loading more…</span>
																	</div>
																	<div class="skeleton h-3 w-3/4"></div>
																	<div class="skeleton h-3 w-full"></div>
																	<div class="skeleton h-3 w-2/3"></div>
																	<div class="grid grid-cols-2 gap-2">
																		<div class="skeleton h-6 w-full"></div>
																		<div class="skeleton h-6 w-full"></div>
																	</div>
																</div>
															{:else if hoveredLocationError}
																<div role="alert" class="alert alert-error alert-soft">
																	<span class="text-sm">{hoveredLocationError}</span>
																</div>
															{:else if hoveredLocationLoading && !hoveredLocation}
																<div class="space-y-2">
																	<div class="flex items-center gap-2">
																		<span class="loading loading-spinner loading-xs"></span>
																		<span class="text-xs text-base-content/60">Loading more…</span>
																	</div>
																	<div class="skeleton h-3 w-3/4"></div>
																	<div class="skeleton h-3 w-full"></div>
																	<div class="skeleton h-3 w-2/3"></div>
																	<div class="grid grid-cols-2 gap-2">
																		<div class="skeleton h-6 w-full"></div>
																		<div class="skeleton h-6 w-full"></div>
																	</div>
																</div>
															{:else if hoveredLocation}
																{#if hoveredLocation.category?.display_name}
																	<div class="badge badge-outline badge-sm">
																		{hoveredLocation.category.display_name}
																	</div>
																{/if}

																{#if hoveredLocation.location}
																	<div class="text-xs text-base-content/70">
																		{truncateForPopup(hoveredLocation.location, 90)}
																	</div>
																{/if}

																<div class="flex flex-wrap items-center gap-2">
																	{#if hoveredLocation.rating !== null && hoveredLocation.rating !== undefined}
																		<div class="badge badge-neutral badge-sm">
																			★ {hoveredLocation.rating}
																		</div>
																	{/if}
																	<div class="badge badge-ghost badge-sm">
																		Visits: {hoveredLocation.visits?.length ?? 0}
																	</div>
																	<div class="badge badge-ghost badge-sm">
																		Media: {hoveredLocation.images?.length ?? 0}
																	</div>
																	<div class="badge badge-ghost badge-sm">
																		Files: {hoveredLocation.attachments?.length ?? 0}
																	</div>
																	<div class="badge badge-ghost badge-sm">
																		Trails: {hoveredLocation.trails?.length ?? 0}
																	</div>
																</div>

																{#if hoveredLocation.visits && hoveredLocation.visits.length > 0}
																	<div class="text-xs text-base-content/70">
																		Last visit: {formatDateForPopup(
																			hoveredLocation.visits[0]?.start_date
																		)}
																	</div>
																{/if}

																{#if hoveredLocation.description}
																	<p class="text-xs leading-snug text-base-content/80">
																		{truncateForPopup(hoveredLocation.description, 160)}
																	</p>
																{/if}

																{#if hoveredLocation.tags && hoveredLocation.tags.length > 0}
																	<div class="flex flex-wrap gap-1">
																		{#each hoveredLocation.tags.slice(0, 6) as tag}
																			<span class="badge badge-ghost badge-sm">{tag}</span>
																		{/each}
																		{#if hoveredLocation.tags.length > 6}
																			<span class="badge badge-ghost badge-sm"
																				>+{hoveredLocation.tags.length - 6}</span
																			>
																		{/if}
																	</div>
																{/if}
															{/if}
														{/if}

														<div class="card-actions justify-end">
															<button
																type="button"
																class="btn btn-primary btn-sm"
																on:click={(e) => {
																	e.stopPropagation();
																	handleViewDetails(markerProps.id);
																}}
															>
																{$t('map.view_details')}
															</button>
														</div>
													</div>
												</div>
												<!-- Arrow pointer -->
												<div
													class="absolute top-full left-1/2 -translate-x-1/2 -mt-px w-3 h-3 rotate-45 bg-base-100 border-r border-b border-base-300"
												></div>
											</div>
										</div>
									</Marker>
								{/if}
							</svelte:fragment>

							<svelte:fragment slot="overlays">
								{#if newMarker}
									<DefaultMarker lngLat={newMarker.lngLat} />
								{/if}

								{#each visitedRegions as region}
									{#if showRegions}
										<Marker
											lngLat={[region.longitude, region.latitude]}
											class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-green-300 hover:bg-green-400 text-black shadow-lg cursor-pointer transition-transform hover:scale-110"
										>
											<LocationIcon class="w-5 h-5 text-green-700" />
											<Popup openOn="click" offset={[0, -10]}>
												<div class="space-y-2">
													<div class="text-lg text-black font-bold">{region.name}</div>
													<div class="badge badge-success badge-sm">{region.region}</div>
												</div>
											</Popup>
										</Marker>
									{/if}
								{/each}

								{#if showCities}
									{#each visitedCities as city}
										<Marker
											lngLat={[city.longitude, city.latitude]}
											class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-blue-300 hover:bg-blue-400 text-black shadow-lg cursor-pointer transition-transform hover:scale-110"
										>
											<LocationIcon class="w-5 h-5 text-blue-700" />
											<Popup openOn="click" offset={[0, -10]}>
												<div class="space-y-2">
													<div class="text-lg text-black font-bold">{city.name}</div>
													<div class="badge badge-success badge-sm">{city.id}</div>
												</div>
											</Popup>
										</Marker>
									{/each}
								{/if}

								{#if showActivities}
									{#each activities as activity}
										{#if activity.geojson}
											<GeoJSON data={activity.geojson}>
												<LineLayer
													paint={{
														'line-color': getActivityColor(activity.sport_type),
														'line-width': 3,
														'line-opacity': 0.8
													}}
												/>
											</GeoJSON>
										{/if}
									{/each}
								{/if}
							</svelte:fragment>
						</FullMap>
					</div>
				</div>
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label for="map-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<!-- Sidebar Header -->
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Filter class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('map.map_controls')}</h2>
					</div>

					<!-- Adventure Statistics -->
					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<MapIcon class="w-5 h-5" />
							{$t('map.adventure_stats')}
						</h3>

						<div class="space-y-4">
							<div class="stat p-0">
								<div class="stat-title text-sm">{$t('dashboard.total_adventures')}</div>
								<div class="stat-value text-2xl">{totalAdventures}</div>
							</div>

							<div class="grid grid-cols-2 gap-4">
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('adventures.visited')}</div>
									<div class="stat-value text-lg text-success">{visitedAdventures}</div>
								</div>
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('adventures.planned')}</div>
									<div class="stat-value text-lg text-info">{plannedAdventures}</div>
								</div>
							</div>

							<div class="stat p-0">
								<div class="stat-title text-xs">{$t('map.regions')}</div>
								<div class="stat-value text-lg text-accent">{totalRegions}</div>
							</div>

							<!-- Progress Bar -->
							<div class="space-y-2">
								<div class="flex justify-between text-sm">
									<span>{$t('map.completion')}</span>
									<span>{Math.round((visitedAdventures / totalAdventures) * 100)}%</span>
								</div>
								<progress
									class="progress progress-primary w-full"
									value={visitedAdventures}
									max={totalAdventures}
								></progress>
							</div>
						</div>
					</div>

					<!-- Display Options -->
					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Eye class="w-5 h-5" />
							{$t('map.display_options')}
						</h3>

						<div class="space-y-3">
							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="checkbox"
									bind:checked={showVisited}
									class="checkbox checkbox-success checkbox-sm"
								/>
								<span class="label-text flex items-center gap-2">
									<Eye class="w-4 h-4" />
									{$t('adventures.visited')} ({visitedAdventures})
								</span>
							</label>

							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="checkbox"
									bind:checked={showPlanned}
									class="checkbox checkbox-info checkbox-sm"
								/>
								<span class="label-text flex items-center gap-2">
									<Calendar class="w-4 h-4" />
									{$t('adventures.planned')} ({plannedAdventures})
								</span>
							</label>

							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="checkbox"
									bind:checked={showRegions}
									class="checkbox checkbox-accent checkbox-sm"
								/>
								<span class="label-text flex items-center gap-2">
									<LocationIcon class="w-4 h-4" />
									{$t('profile.visited_regions')} ({totalRegions})
								</span>
							</label>

							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="checkbox"
									bind:checked={showCities}
									class="checkbox checkbox-warning checkbox-sm"
								/>
								<span class="label-text flex items-center gap-2">
									<LocationIcon class="w-4 h-4" />
									{$t('map.show_visited_cities')}
									{visitedCities.length > 0 ? ` (${visitedCities.length})` : ''}
								</span>
							</label>

							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="checkbox"
									bind:checked={showActivities}
									class="checkbox checkbox-error checkbox-sm"
								/>
								<span class="label-text flex items-center gap-2">
									<ActivityIcon class="w-4 h-4" />
									{$t('settings.activities')}{activities.length > 0
										? ` (${activities.length})`
										: ''}
								</span>
							</label>
						</div>
					</div>

					<!-- Ownership Filter (collaborative mode only) -->
					{#if data.collaborativeMode}
						<div class="card bg-base-200/50 p-4 mb-6">
							<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
								<Eye class="w-5 h-5" />
								{$t('adventures.ownership_filter')}
							</h3>
							<div class="space-y-2">
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="radio"
										name="ownership"
										class="radio radio-primary radio-sm"
										checked={ownershipFilter === 'all'}
										on:change={() => (ownershipFilter = 'all')}
									/>
									<span class="label-text">{$t('adventures.all_locations')}</span>
								</label>
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="radio"
										name="ownership"
										class="radio radio-primary radio-sm"
										checked={ownershipFilter === 'mine'}
										on:change={() => (ownershipFilter = 'mine')}
									/>
									<span class="label-text">{$t('adventures.my_locations')}</span>
								</label>
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="radio"
										name="ownership"
										class="radio radio-primary radio-sm"
										checked={ownershipFilter === 'public'}
										on:change={() => (ownershipFilter = 'public')}
									/>
									<span class="label-text">{$t('adventures.public_locations')}</span>
								</label>
							</div>
						</div>
					{/if}

					<!-- New Location Section -->
					<div class="card bg-base-200/50 p-4">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Plus class="w-5 h-5" />
							{$t('adventures.new_location')}
						</h3>

						{#if newMarker}
							<div class="space-y-3">
								<div class="alert alert-info">
									<PinIcon class="w-4 h-4" />
									<span class="text-sm">{$t('map.marker_placed_on_map')}</span>
								</div>
								<button type="button" class="btn btn-primary w-full gap-2" on:click={newAdventure}>
									<Plus class="w-4 h-4" />
									{$t('map.add_location_at_marker')}
								</button>
								<button type="button" class="btn btn-ghost w-full gap-2" on:click={clearMarker}>
									<Clear class="w-4 h-4" />
									{$t('map.clear_marker')}
								</button>
							</div>
						{:else}
							<div class="space-y-3">
								<p class="text-sm text-base-content/60">
									{$t('map.place_marker_desc_location')}
								</p>
								<button
									type="button"
									class="btn btn-primary w-full gap-2"
									on:click={() => (createModalOpen = true)}
								>
									<Plus class="w-4 h-4" />
									{$t('map.add_location')}
								</button>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

{#if createModalOpen}
	<NewLocationModal
		on:close={() => (createModalOpen = false)}
		on:save={createNewAdventure}
		{initialLatLng}
		user={data.user}
		bind:location={locationBeingUpdated}
	/>
{/if}

<style>
	/* Ensure only the explicit hit area handles pointer events to avoid unintended edge hover/tap popups */
	:global(.maplibregl-marker.map-pin),
	:global(.mapboxgl-marker.map-pin) {
		pointer-events: none;
	}

	:global(.maplibregl-marker.map-pin .map-pin-hit),
	:global(.mapboxgl-marker.map-pin .map-pin-hit) {
		pointer-events: auto;
	}

	/* Suppress any default map popups so only the custom rich popup shows */
	:global(.maplibregl-popup),
	:global(.mapboxgl-popup) {
		display: none !important;
	}
</style>
