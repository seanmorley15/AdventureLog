<script lang="ts">
	import { getBasemapUrl } from '$lib';
	import CityCard from '$lib/components/CityCard.svelte';
	import { addToast } from '$lib/toasts';
	import type { City, VisitedCity } from '$lib/types';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import { MapLibre, Marker } from 'svelte-maplibre';

	// Icons
	import MapMarker from '~icons/mdi/map-marker';
	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Filter from '~icons/mdi/filter-variant';
	import Map from '~icons/mdi/map';
	import Check from '~icons/mdi/check-circle';
	import Cancel from '~icons/mdi/cancel';
	import Trophy from '~icons/mdi/trophy';
	import Target from '~icons/mdi/target';
	import CityIcon from '~icons/mdi/city';

	export let data: PageData;

	let filteredCities: City[] = [];
	let searchQuery: string = '';
	let showGeo: boolean = true;
	let sidebarOpen = false;
	let filterOption: string = 'all';

	const allCities: City[] = data.props?.cities || [];
	let visitedCities: VisitedCity[] = data.props?.visitedCities || [];
	const region = data.props?.region || null;

	console.log(data);

	// Statistics
	let numCities: number = allCities.length;
	let numVisitedCities: number = visitedCities.length;

	$: visitedCount = visitedCities.length;
	$: notVisitedCount = allCities.length - visitedCount;
	$: completionPercentage =
		allCities.length > 0 ? Math.round((visitedCount / allCities.length) * 100) : 0;

	// Filter cities based on search and filter options
	$: {
		if (searchQuery === '') {
			filteredCities = allCities;
		} else {
			filteredCities = allCities.filter((city) =>
				city.name.toLowerCase().includes(searchQuery.toLowerCase())
			);
		}

		if (filterOption === 'visited') {
			filteredCities = filteredCities.filter((city) =>
				visitedCities.some((visitedCity) => visitedCity.city === city.id)
			);
		} else if (filterOption === 'not-visited') {
			filteredCities = filteredCities.filter(
				(city) => !visitedCities.some((visitedCity) => visitedCity.city === city.id)
			);
		}
	}

	// Remove duplicates from visitedCities
	visitedCities = visitedCities.filter(
		(visitedCity, index, self) => index === self.findIndex((t) => t.city === visitedCity.city)
	);

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function clearFilters() {
		searchQuery = '';
		filterOption = 'all';
	}

	function toggleVisited(city: City) {
		return () => {
			const visitedCity = visitedCities.find((visitedCity) => visitedCity.city === city.id);
			if (visitedCity) {
				visitedCities = visitedCities.filter((visitedCity) => visitedCity.city !== city.id);
				removeVisit(city);
			} else {
				markVisited(city);
			}
		};
	}

	async function markVisited(city: City) {
		let res = await fetch(`/api/visitedcity/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ city: city.id })
		});
		if (!res.ok) {
			console.error('Failed to mark city as visited');
			addToast('error', `${$t('worldtravel.failed_to_mark_visit')} ${city.name}`);
			return;
		} else {
			visitedCities = [...visitedCities, await res.json()];
			addToast(
				'success',
				`${$t('worldtravel.visit_to')} ${city.name} ${$t('worldtravel.marked_visited')}`
			);
		}
	}

	async function removeVisit(city: City) {
		let res = await fetch(`/api/visitedcity/${city.id}`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'DELETE'
		});
		if (!res.ok) {
			console.error('Failed to remove city visit');
			addToast('error', `${$t('worldtravel.failed_to_mark_visit')} ${city.name}`);
			return;
		} else {
			visitedCities = visitedCities.filter((visitedCity) => visitedCity.city !== city.id);
			addToast('info', `${$t('worldtravel.visit_to')} ${city.name} ${$t('worldtravel.removed')}`);
		}
	}
</script>

<svelte:head>
	<title>{region ? `Cities in ${region.name}` : 'Cities'}</title>
	<meta
		name="description"
		content="View the cities in regions and mark them visited to track your world travel."
	/>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open p-[12px]">
		<input id="cities-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content bg-white rounded-[24px] overflow-hidden">
			<!-- Header Section -->
			<div class="sticky top-0 z-40">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4">
							<button class="btn btn-ghost btn-square lg:hidden" on:click={toggleSidebar}>
								<Filter class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-xl">
									<CityIcon class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-primary">
										{$t('worldtravel.cities_in')}
										{region?.name}
									</h1>
									<p class="text-sm text-base-content/60">
										{filteredCities.length}
										{$t('worldtravel.of')}
										{allCities.length}
										{$t('worldtravel.cities')}
									</p>
								</div>
							</div>
						</div>

						<!-- Completion Badge -->
						<div class="hidden md:flex items-center gap-2">
							{#if completionPercentage === 100}
								<div class="badge badge-success gap-2 p-3">
									<Trophy class="w-4 h-4" />
									{$t('worldtravel.complete')}
								</div>
							{:else}
								<div class="badge badge-primary gap-2 p-3">
									<Target class="w-4 h-4" />
									{completionPercentage}%
								</div>
							{/if}
						</div>
					</div>

					<!-- Search and Filters -->
					<div class="mt-4 flex items-center gap-4">
						<div class="relative flex-1 max-w-md">
							<Search
								class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-base-content/40"
							/>
							<input
								type="text"
								placeholder={$t('navbar.search')}
								class="input input-bordered w-full pl-10 pr-10 bg-base-100/80"
								bind:value={searchQuery}
							/>
							{#if searchQuery.length > 0}
								<button
									class="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content"
									on:click={() => (searchQuery = '')}
								>
									<Clear class="w-4 h-4" />
								</button>
							{/if}
						</div>
					</div>

					<!-- Filter Chips -->
					<div class="mt-4 flex flex-wrap items-center gap-2">
						<span class="text-sm font-medium text-base-content/60"
							>{$t('worldtravel.filter_by')}:</span
						>
						<div class="tabs tabs-boxed bg-base-200">
							<button
								class="tab tab-sm gap-2 {filterOption === 'all' ? 'tab-active' : ''}"
								on:click={() => (filterOption = 'all')}
							>
								<MapMarker class="w-3 h-3" />
								All
							</button>
							<button
								class="tab tab-sm gap-2 {filterOption === 'visited' ? 'tab-active' : ''}"
								on:click={() => (filterOption = 'visited')}
							>
								<Check class="w-3 h-3" />
								{$t('adventures.visited')}
							</button>
							<button
								class="tab tab-sm gap-2 {filterOption === 'not-visited' ? 'tab-active' : ''}"
								on:click={() => (filterOption = 'not-visited')}
							>
								<Cancel class="w-3 h-3" />
								{$t('adventures.not_visited')}
							</button>
						</div>

						{#if searchQuery || filterOption !== 'all'}
							<button class="btn btn-ghost btn-xs gap-1" on:click={clearFilters}>
								<Clear class="w-3 h-3" />
								{$t('worldtravel.clear_all')}
							</button>
						{/if}
					</div>
				</div>
			</div>

			<!-- Map Section -->
			{#if allCities.length > 0}
				<div class="container mx-auto px-6 py-4">
					<div class="card bg-base-100">
						<div class="card-body p-4">
							<div class="flex items-center justify-between mb-4">
								<div class="flex items-center gap-2">
									<Map class="w-5 h-5 text-primary" />
									<h2 class="text-lg font-semibold">{$t('worldtravel.interactive_map')}</h2>
								</div>
								<div class="flex items-center gap-2 text-sm text-base-content/60">
									<div class="flex items-center gap-1">
										<div class="w-3 h-3 bg-green-200 rounded-full border"></div>
										<span>{$t('adventures.visited')}</span>
									</div>
									<div class="flex items-center gap-1">
										<div class="w-3 h-3 bg-red-200 rounded-full border"></div>
										<span>{$t('adventures.not_visited')}</span>
									</div>
								</div>
							</div>
							<MapLibre
								style={getBasemapUrl()}
								class="aspect-[16/10] w-full rounded-lg"
								standardControls
								center={allCities[0] &&
								allCities[0].longitude !== null &&
								allCities[0].latitude !== null
									? [allCities[0].longitude, allCities[0].latitude]
									: [0, 0]}
								zoom={8}
							>
								{#each filteredCities as city}
									{#if city.latitude && city.longitude && showGeo}
										<Marker
											lngLat={[city.longitude, city.latitude]}
											class="grid px-2 py-1 place-items-center rounded-full border border-gray-200 {visitedCities.some(
												(visitedCity) => visitedCity.city === city.id
											)
												? 'bg-green-200'
												: 'bg-red-200'} text-black focus:outline-6 focus:outline-black"
											on:click={toggleVisited(city)}
										>
											<span class="text-xs">
												{city.name}
											</span>
										</Marker>
									{/if}
								{/each}
							</MapLibre>
						</div>
					</div>
				</div>
			{/if}

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-8">
				{#if filteredCities.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							<CityIcon class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{$t('worldtravel.no_cities_found')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md mb-6">
							{$t('worldtravel.no_countries_found_desc')}
						</p>
						<button class="btn btn-primary gap-2" on:click={clearFilters}>
							<Clear class="w-4 h-4" />
							{$t('worldtravel.clear_filters')}
						</button>
					</div>
				{:else}
					<!-- Cities Grid -->
					<div
						class="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6"
					>
						{#each filteredCities as city}
							<CityCard
								{city}
								visited={visitedCities.some((visitedCity) => visitedCity.city === city.id)}
								on:visit={(e) => {
									visitedCities = [...visitedCities, e.detail];
									numVisitedCities++;
								}}
								on:remove={() => {
									visitedCities = visitedCities.filter(
										(visitedCity) => visitedCity.city !== city.id
									);
									numVisitedCities--;
								}}
							/>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label for="cities-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<!-- Sidebar Header -->
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Filter class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('worldtravel.progress_and_stats')}</h2>
					</div>

					<!-- Region Progress -->
					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<CityIcon class="w-5 h-5" />
							{region?.name}
						</h3>

						<div class="space-y-4">
							<div class="stat p-0">
								<div class="stat-title text-sm">{$t('worldtravel.total_cities')}</div>
								<div class="stat-value text-2xl">{allCities.length}</div>
								<div class="stat-desc">{$t('worldtravel.available_to_explore')}</div>
							</div>

							<div class="grid grid-cols-2 gap-4">
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('adventures.visited')}</div>
									<div class="stat-value text-lg text-success">{visitedCount}</div>
								</div>
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('worldtravel.remaining')}</div>
									<div class="stat-value text-lg text-error">{notVisitedCount}</div>
								</div>
							</div>

							<!-- Progress Bar -->
							<div class="space-y-2">
								<div class="flex justify-between text-sm">
									<span>{$t('worldtravel.progress')}</span>
									<span>{completionPercentage}%</span>
								</div>
								<progress
									class="progress progress-primary w-full"
									value={visitedCount}
									max={allCities.length}
								></progress>
							</div>

							{#if completionPercentage === 100}
								<div class="alert alert-success">
									<Trophy class="w-4 h-4" />
									<span class="text-sm">{$t('worldtravel.region_completed')}! 🎉</span>
								</div>
							{/if}
						</div>
					</div>

					<!-- Quick Actions -->
					<div class="space-y-3">
						<button class="btn btn-outline w-full gap-2" on:click={() => (showGeo = !showGeo)}>
							{#if showGeo}
								<Map class="w-4 h-4" />
								{$t('worldtravel.hide_map_labels')}
							{:else}
								<Map class="w-4 h-4" />
								{$t('worldtravel.show_map_labels')}
							{/if}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
