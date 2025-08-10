<script lang="ts">
	import { DefaultMarker, MapEvents, MapLibre, Popup, Marker } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import type { Location, VisitedRegion } from '$lib/types.js';
	import CardCarousel from '$lib/components/CardCarousel.svelte';
	import { goto } from '$app/navigation';
	import { getBasemapUrl } from '$lib';

	// Icons
	import MapIcon from '~icons/mdi/map';
	import Filter from '~icons/mdi/filter-variant';
	import Plus from '~icons/mdi/plus';
	import Clear from '~icons/mdi/close';
	import Eye from '~icons/mdi/eye';
	import Pin from '~icons/mdi/map-marker';
	import Calendar from '~icons/mdi/calendar';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import NewLocationModal from '$lib/components/NewLocationModal.svelte';

	export let data;

	let createModalOpen: boolean = false;
	let showGeo: boolean = false;
	let sidebarOpen = false;

	export let initialLatLng: { lat: number; lng: number } | null = null;

	let visitedRegions: VisitedRegion[] = data.props.visitedRegions;
	let adventures: Location[] = data.props.adventures;

	let filteredAdventures = adventures;

	let showVisited: boolean = true;
	let showPlanned: boolean = true;

	let newMarker: { lngLat: any } | null = null;
	let newLongitude: number | null = null;
	let newLatitude: number | null = null;

	let isPopupOpen = false;

	// Statistics
	$: totalAdventures = adventures.length;
	$: visitedAdventures = adventures.filter((adventure) => adventure.is_visited).length;
	$: plannedAdventures = adventures.filter((adventure) => !adventure.is_visited).length;
	$: totalRegions = visitedRegions.length;

	// Get unique categories for filtering
	$: categories = [
		...new Set(adventures.map((adventure) => adventure.category?.display_name).filter(Boolean))
	];

	// Updates the filtered adventures based on the checkboxes
	$: {
		filteredAdventures = adventures.filter(
			(adventure) => (showVisited && adventure.is_visited) || (showPlanned && !adventure.is_visited)
		);
	}

	// Reset the longitude and latitude when the newMarker is set to null
	$: {
		if (!newMarker) {
			newLongitude = null;
			newLatitude = null;
		}
	}

	let locationBeingUpdated: Location | undefined = undefined;

	// Sync the locationBeingUpdated with the adventures array
	$: {
		if (locationBeingUpdated && locationBeingUpdated.id) {
			const index = adventures.findIndex((adventure) => adventure.id === locationBeingUpdated?.id);

			if (index !== -1) {
				adventures[index] = { ...locationBeingUpdated };
				adventures = adventures; // Trigger reactivity
			} else {
				adventures = [{ ...locationBeingUpdated }, ...adventures];
				if (data.props.adventures) {
					data.props.adventures = adventures; // Update data.props.adventure.locations as well
				}
			}
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
		adventures = [...adventures, event.detail];
		newMarker = null;
		createModalOpen = false;
	}

	function togglePopup() {
		isPopupOpen = !isPopupOpen;
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function clearMarker() {
		newMarker = null;
	}
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
							<button class="btn btn-ghost btn-square lg:hidden" on:click={toggleSidebar}>
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
										{filteredAdventures.length}
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
				<div class="card bg-base-100 shadow-xl h-full">
					<div class="card-body p-4 h-full">
						<MapLibre
							style={getBasemapUrl()}
							class="w-full h-full min-h-[70vh] rounded-lg"
							standardControls
						>
							{#each filteredAdventures as adventure}
								{#if adventure.latitude && adventure.longitude}
									<Marker
										lngLat={[adventure.longitude, adventure.latitude]}
										class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 shadow-lg cursor-pointer  hover:scale-110 {adventure.is_visited
											? 'bg-red-300 hover:bg-red-400'
											: 'bg-blue-300 hover:bg-blue-400'} text-black focus:outline-6 focus:outline-black"
										on:click={togglePopup}
									>
										<span class="text-xl">
											{adventure.category?.icon || '📍'}
										</span>
										{#if isPopupOpen}
											<Popup
												openOn="click"
												offset={[0, -10]}
												on:close={() => (isPopupOpen = false)}
											>
												<div class="min-w-64 max-w-sm">
													{#if adventure.images && adventure.images.length > 0}
														<div class="mb-3">
															<CardCarousel
																images={adventure.images}
																name={adventure.name}
																icon={adventure?.category?.icon}
															/>
														</div>
													{/if}
													<div class="space-y-2">
														<div class="text-lg text-black font-bold">{adventure.name}</div>
														<div class="flex items-center gap-2">
															<span
																class="badge {adventure.is_visited
																	? 'badge-success'
																	: 'badge-info'} badge-sm"
															>
																{adventure.is_visited
																	? $t('adventures.visited')
																	: $t('adventures.planned')}
															</span>
															{#if adventure.category}
																<span class="badge badge-outline badge-sm">
																	{adventure.category.display_name}
																	{adventure.category.icon}
																</span>
															{/if}
														</div>
														{#if adventure.visits && adventure.visits.length > 0}
															<div class="text-black text-sm space-y-1">
																{#each adventure.visits as visit}
																	<div class="flex items-center gap-1">
																		<Calendar class="w-3 h-3" />
																		<span>
																			{visit.start_date
																				? new Date(visit.start_date).toLocaleDateString(undefined, {
																						timeZone: 'UTC'
																					})
																				: ''}
																			{visit.end_date &&
																			visit.end_date !== '' &&
																			visit.end_date !== visit.start_date
																				? ' - ' +
																					new Date(visit.end_date).toLocaleDateString(undefined, {
																						timeZone: 'UTC'
																					})
																				: ''}
																		</span>
																	</div>
																{/each}
															</div>
														{/if}
														<div class="flex flex-col gap-2 pt-2">
															{#if adventure.longitude && adventure.latitude}
																<a
																	class="btn btn-outline btn-sm gap-2"
																	href={`https://maps.apple.com/?q=${adventure.latitude},${adventure.longitude}`}
																	target="_blank"
																	rel="noopener noreferrer"
																>
																	<LocationIcon class="w-4 h-4" />
																	{$t('adventures.open_in_maps')}
																</a>
															{/if}
															<button
																class="btn btn-primary btn-sm gap-2"
																on:click={() => goto(`/locations/${adventure.id}`)}
															>
																<Eye class="w-4 h-4" />
																{$t('map.view_details')}
															</button>
														</div>
													</div>
												</div>
											</Popup>
										{/if}
									</Marker>
								{/if}
							{/each}

							<MapEvents on:click={addMarker} />
							{#if newMarker}
								<DefaultMarker lngLat={newMarker.lngLat} />
							{/if}

							{#each visitedRegions as region}
								{#if showGeo}
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
									bind:checked={showGeo}
									class="checkbox checkbox-accent checkbox-sm"
								/>
								<span class="label-text flex items-center gap-2">
									<LocationIcon class="w-4 h-4" />
									{$t('map.show_visited_regions')} ({totalRegions})
								</span>
							</label>
						</div>
					</div>

					<!-- New Adventure Section -->
					<div class="card bg-base-200/50 p-4">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Plus class="w-5 h-5" />
							Add Adventure
						</h3>

						{#if newMarker}
							<div class="space-y-3">
								<div class="alert alert-info">
									<Pin class="w-4 h-4" />
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
