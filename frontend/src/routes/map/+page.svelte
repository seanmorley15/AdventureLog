<script lang="ts">
	import {
		DefaultMarker,
		MapEvents,
		MapLibre,
		Popup,
		Marker,
		GeoJSON,
		LineLayer
	} from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import type { Activity, Location, VisitedCity, VisitedRegion, Pin } from '$lib/types.js';
	import CardCarousel from '$lib/components/CardCarousel.svelte';
	import { goto } from '$app/navigation';
	import { basemapOptions, getActivityColor, getBasemapLabel, getBasemapUrl } from '$lib';

	// Icons
	import MapIcon from '~icons/mdi/map';
	import Filter from '~icons/mdi/filter-variant';
	import Plus from '~icons/mdi/plus';
	import Clear from '~icons/mdi/close';
	import Eye from '~icons/mdi/eye';
	import PinIcon from '~icons/mdi/map-marker';
	import Calendar from '~icons/mdi/calendar';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import NewLocationModal from '$lib/components/NewLocationModal.svelte';
	import ActivityIcon from '~icons/mdi/run-fast';
	import MapStyleSelector from '$lib/components/MapStyleSelector.svelte';

	export let data;

	let createModalOpen: boolean = false;
	let showRegions: boolean = false;
	let showActivities: boolean = false;
	let showCities: boolean = false;
	let sidebarOpen: boolean = false;

	let basemapType: string = 'default';

	export let initialLatLng: { lat: number; lng: number } | null = null;

	let visitedRegions: VisitedRegion[] = data.props.visitedRegions;
	let visitedCities: VisitedCity[] = [];
	let pins: Pin[] = data.props.pins; // Lightweight pin objects
	let activities: Activity[] = [];

	let filteredPins = pins;

	let showVisited: boolean = true;
	let showPlanned: boolean = true;

	let newMarker: { lngLat: any } | null = null;
	let newLongitude: number | null = null;
	let newLatitude: number | null = null;

	// Cache for full location data
	let locationCache: Map<string, Location> = new Map();
	let loadingLocations: Set<string> = new Set();

	let locationBeingUpdated: Location | undefined = undefined;

	// Statistics
	$: totalAdventures = pins.length;
	$: visitedAdventures = pins.filter((pin) => pin.is_visited).length;
	$: plannedAdventures = pins.filter((pin) => !pin.is_visited).length;
	$: totalRegions = visitedRegions.length;

	// Get unique categories for filtering
	$: categories = [...new Set(pins.map((pin) => pin.category?.display_name).filter(Boolean))];

	// Updates the filtered pins based on the checkboxes
	$: {
		filteredPins = pins.filter(
			(pin) => (showVisited && pin.is_visited === true) || (showPlanned && pin.is_visited !== true)
		);
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

	async function fetchLocationDetails(locationId: string): Promise<Location | null> {
		// Check cache first
		if (locationCache.has(locationId)) {
			return locationCache.get(locationId)!;
		}

		// Prevent duplicate requests
		if (loadingLocations.has(locationId)) {
			return null;
		}

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
		}
	}

	function addMarker(e: { detail: { lngLat: { lng: any; lat: any } } }) {
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

	// Function to handle popup opening - only fetch when actually needed
	let openPopups = new Set<string>();

	function handlePopupOpen(pinId: string) {
		openPopups.add(pinId);
		openPopups = openPopups; // Trigger reactivity
	}

	function handlePopupClose(pinId: string) {
		openPopups.delete(pinId);
		openPopups = openPopups; // Trigger reactivity
	}
</script>

<svelte:head>
	<title>Location Map</title>
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
					<!-- Integrated Map Type Selector -->
					<div
						class="absolute top-4 right-4 z-10 bg-base-200 backdrop-blur-sm rounded-lg shadow-lg"
					>
						<div class="p-2">
							<MapStyleSelector bind:basemapType />
						</div>
					</div>

					<div class="card-body p-0 h-full">
						<MapLibre
							style={getBasemapUrl(basemapType)}
							class="w-full h-full min-h-[70vh] rounded-lg"
							standardControls
						>
							{#each filteredPins as pin}
								{#if pin.latitude && pin.longitude}
									<Marker
										lngLat={[parseFloat(pin.longitude), parseFloat(pin.latitude)]}
										class="grid h-8 w-8 place-items-center rounded-full border-2 border-white shadow-lg cursor-pointer hover:scale-110 transition-all duration-200 {pin.is_visited
											? 'bg-gradient-to-br from-emerald-400 to-emerald-600 hover:from-emerald-500 hover:to-emerald-700'
											: 'bg-gradient-to-br from-blue-400 to-blue-600 hover:from-blue-500 hover:to-blue-700'} text-white focus:outline-4 focus:outline-primary/50"
									>
										<span class="text-xl">
											{pin.category?.icon || '📍'}
										</span>

										<Popup
											openOn="click"
											offset={[0, -10]}
											on:open={() => handlePopupOpen(pin.id)}
											on:close={() => handlePopupClose(pin.id)}
										>
											<div class="min-w-64 max-w-sm">
												{#if openPopups.has(pin.id)}
													{#await fetchLocationDetails(pin.id)}
														<div class="flex items-center justify-center p-4">
															<span class="loading loading-spinner loading-sm"></span>
															<span class="ml-2 text-sm">Loading details...</span>
														</div>
													{:then location}
														{#if location}
															{#if location.images && location.images.length > 0}
																<div class="mb-3">
																	<CardCarousel
																		images={location.images}
																		name={location.name}
																		icon={location?.category?.icon}
																	/>
																</div>
															{/if}
															<div class="space-y-2">
																<div class="text-lg text-black font-bold">{location.name}</div>
																<div class="flex items-center gap-2">
																	<span
																		class="badge {location.is_visited
																			? 'badge-success'
																			: 'badge-info'} badge-sm"
																	>
																		{location.is_visited
																			? $t('adventures.visited')
																			: $t('adventures.planned')}
																	</span>
																	{#if location.category}
																		<span class="badge badge-outline badge-sm">
																			{location.category.display_name}
																			{location.category.icon}
																		</span>
																	{/if}
																</div>
																{#if location.visits && location.visits.length > 0}
																	<div class="text-black text-sm space-y-1">
																		{#each location.visits as visit}
																			<div class="flex items-center gap-1">
																				<Calendar class="w-3 h-3" />
																				<span>
																					{visit.start_date
																						? new Date(visit.start_date).toLocaleDateString(
																								undefined,
																								{
																									timeZone: 'UTC'
																								}
																							)
																						: ''}
																					{visit.end_date &&
																					visit.end_date !== '' &&
																					visit.end_date !== visit.start_date
																						? ' - ' +
																							new Date(visit.end_date).toLocaleDateString(
																								undefined,
																								{
																									timeZone: 'UTC'
																								}
																							)
																						: ''}
																				</span>
																			</div>
																		{/each}
																	</div>
																{/if}
																<div class="flex flex-col gap-2 pt-2">
																	{#if location.longitude && location.latitude}
																		<a
																			class="btn btn-outline btn-sm gap-2"
																			href={`https://maps.apple.com/?q=${location.latitude},${location.longitude}`}
																			target="_blank"
																			rel="noopener noreferrer"
																		>
																			<LocationIcon class="w-4 h-4" />
																			{$t('adventures.open_in_maps')}
																		</a>
																	{/if}
																	<button
																		class="btn btn-primary btn-sm gap-2"
																		on:click={() => goto(`/locations/${location.id}`)}
																	>
																		<Eye class="w-4 h-4" />
																		{$t('map.view_details')}
																	</button>
																</div>
															</div>
														{:else}
															<div class="p-4 text-center">
																<div class="text-lg text-black font-bold">{pin.name}</div>
																<div class="text-sm text-gray-600">Failed to load details</div>
																<button
																	class="btn btn-primary btn-sm gap-2 mt-2"
																	on:click={() => goto(`/locations/${pin.id}`)}
																>
																	<Eye class="w-4 h-4" />
																	{$t('map.view_details')}
																</button>
															</div>
														{/if}
													{:catch error}
														<div class="p-4 text-center">
															<div class="text-lg text-black font-bold">{pin.name}</div>
															<div class="text-sm text-red-600">Error loading details</div>
															<button
																class="btn btn-primary btn-sm gap-2 mt-2"
																on:click={() => goto(`/locations/${pin.id}`)}
															>
																<Eye class="w-4 h-4" />
																{$t('map.view_details')}
															</button>
														</div>
													{/await}
												{:else}
													<div class="p-4 text-center">
														<div class="text-lg text-black font-bold">{pin.name}</div>
														<div class="text-sm text-gray-600">Click to load details...</div>
													</div>
												{/if}
											</div>
										</Popup>
									</Marker>
								{/if}
							{/each}

							<MapEvents on:click={addMarker} />
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
						</MapLibre>
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
	:global(.map) {
		height: 500px;
	}
</style>
