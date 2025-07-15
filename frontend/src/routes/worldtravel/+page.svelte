<script lang="ts">
	import { goto } from '$app/navigation';
	import CountryCard from '$lib/components/CountryCard.svelte';
	import type { Country } from '$lib/types';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import { MapLibre, Marker } from 'svelte-maplibre';

	// Icons
	import Globe from '~icons/mdi/earth';
	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Filter from '~icons/mdi/filter-variant';
	import Map from '~icons/mdi/map';
	import Pin from '~icons/mdi/map-marker';
	import Check from '~icons/mdi/check-circle';
	import Progress from '~icons/mdi/progress-check';
	import Cancel from '~icons/mdi/cancel';
	import { getBasemapUrl } from '$lib';

	export let data: PageData;
	console.log(data);

	let searchQuery: string = '';
	let filteredCountries: Country[] = [];
	const allCountries: Country[] = data.props?.countries || [];
	let worldSubregions: string[] = [];
	let showMap: boolean = false;
	let sidebarOpen = false;

	worldSubregions = [...new Set(allCountries.map((country) => country.subregion))];
	worldSubregions = worldSubregions.filter((subregion) => subregion !== '');
	console.log(worldSubregions);

	let filterOption: string = 'all';
	let subRegionOption: string = '';

	// Statistics
	$: totalCountries = allCountries.length;
	$: visitedCountries = allCountries.filter((country) => country.num_visits > 0).length;
	$: completeCountries = allCountries.filter(
		(country) => country.num_visits === country.num_regions
	).length;
	$: partialCountries = allCountries.filter(
		(country) => country.num_visits > 0 && country.num_visits < country.num_regions
	).length;
	$: notVisitedCountries = allCountries.filter((country) => country.num_visits === 0).length;

	$: {
		if (searchQuery === '') {
			filteredCountries = allCountries;
		} else {
			filteredCountries = allCountries.filter((country) =>
				country.name.toLowerCase().includes(searchQuery.toLowerCase())
			);
		}

		if (filterOption === 'partial') {
			filteredCountries = filteredCountries.filter(
				(country) => country.num_visits > 0 && country.num_visits < country.num_regions
			);
		} else if (filterOption === 'complete') {
			filteredCountries = filteredCountries.filter(
				(country) => country.num_visits === country.num_regions
			);
		} else if (filterOption === 'not') {
			filteredCountries = filteredCountries.filter((country) => country.num_visits === 0);
		}

		if (subRegionOption !== '') {
			filteredCountries = filteredCountries.filter(
				(country) => country.subregion === subRegionOption
			);
		}
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function clearFilters() {
		searchQuery = '';
		filterOption = 'all';
		subRegionOption = '';
	}
</script>

<svelte:head>
	<title>Countries | World Travel</title>
	<meta name="description" content="Explore the world and add countries to your visited list!" />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open p-[12px]">
		<input id="travel-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content bg-white rounded-[24px] overflow-hidden">
			<!-- Header Section -->
			<div class="sticky top-0 z-30">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4">
							<button class="btn btn-ghost btn-square lg:hidden" on:click={toggleSidebar}>
								<Filter class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-xl">
									<Globe class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold text-black bg-clip-text">
										{$t('worldtravel.country_list')}
									</h1>
									<p class="text-sm text-base-content/60">
										{filteredCountries.length}
										{$t('worldtravel.of')}
										{totalCountries}
										{$t('worldtravel.countries')}
									</p>
								</div>
							</div>
						</div>

						<!-- Quick Stats -->
						<div class="hidden md:flex items-center gap-2">
							<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('adventures.visited')}</div>
									<div class="stat-value text-lg text-success">{visitedCountries}</div>
								</div>
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('worldtravel.remaining')}</div>
									<div class="stat-value text-lg text-error">{notVisitedCountries}</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Search Bar -->
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

						<!-- Map Toggle -->
						<button
							class="btn btn-outline gap-2 {showMap ? 'btn-active' : ''}"
							on:click={() => (showMap = !showMap)}
						>
							{#if showMap}
								<Map class="w-4 h-4" />
								<span class="hidden sm:inline">{$t('worldtravel.hide_map')}</span>
							{:else}
								<Map class="w-4 h-4" />
								<span class="hidden sm:inline">{$t('worldtravel.show_map')}</span>
							{/if}
						</button>
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
								<Globe class="w-3 h-3" />
								{$t('adventures.all')}
							</button>
							<button
								class="tab tab-sm gap-2 {filterOption === 'complete' ? 'tab-active' : ''}"
								on:click={() => (filterOption = 'complete')}
							>
								<Check class="w-3 h-3" />
								{$t('worldtravel.complete')}
							</button>
							<button
								class="tab tab-sm gap-2 {filterOption === 'partial' ? 'tab-active' : ''}"
								on:click={() => (filterOption = 'partial')}
							>
								<Progress class="w-3 h-3" />
								{$t('worldtravel.partial')}
							</button>
							<button
								class="tab tab-sm gap-2 {filterOption === 'not' ? 'tab-active' : ''}"
								on:click={() => (filterOption = 'not')}
							>
								<Cancel class="w-3 h-3" />
								{$t('adventures.not_visited')}
							</button>
						</div>

						{#if subRegionOption}
							<div class="badge badge-primary gap-1">
								{subRegionOption}
								<button on:click={() => (subRegionOption = '')}>
									<Clear class="w-3 h-3" />
								</button>
							</div>
						{/if}

						{#if searchQuery || filterOption !== 'all' || subRegionOption}
							<button class="btn btn-ghost btn-xs gap-1" on:click={clearFilters}>
								<Clear class="w-3 h-3" />
								{$t('worldtravel.clear_all')}
							</button>
						{/if}
					</div>
				</div>
			</div>

			<!-- Map Section -->
			{#if showMap}
				<div class="container mx-auto px-6 py-4">
					<div class="card bg-base-100">
						<div class="card-body p-4">
							<MapLibre
								style={getBasemapUrl()}
								class="aspect-[16/10] w-full rounded-lg"
								standardControls
								zoom={2}
							>
								{#each filteredCountries as country}
									{#if country.latitude && country.longitude}
										<Marker
											lngLat={[country.longitude, country.latitude]}
											class={`grid px-2 py-1 place-items-center rounded-full border border-gray-200 ${
												country.num_visits === 0
													? 'bg-red-200'
													: country.num_visits === country.num_regions
														? 'bg-green-200'
														: 'bg-blue-200'
											} text-black focus:outline-6 focus:outline-black cursor-pointer`}
											on:click={() => goto(`/worldtravel/${country.country_code}`)}
										>
											<span class="text-xs font-medium">
												{country.name}
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
				{#if filteredCountries.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							<Globe class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{$t('worldtravel.no_countries_found')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md mb-6">
							{$t('worldtravel.no_countries_found_desc')}
						</p>
						<button class="btn btn-primary gap-2" on:click={clearFilters}>
							<Clear class="w-4 h-4" />
							{$t('worldtravel.clear_filters')}
						</button>

						{#if allCountries.length === 0}
							<div class="mt-8 text-center">
								<div class="alert alert-warning max-w-md">
									<div>
										<h4 class="font-bold">{$t('worldtravel.no_country_data_available')}</h4>
										<p class="text-sm">{$t('worldtravel.no_country_data_available_desc')}</p>
									</div>
								</div>
								<a
									class="link link-primary mt-4 inline-block"
									href="https://adventurelog.app/docs/configuration/updating.html#updating-the-region-data"
									target="_blank"
								>
									{$t('settings.documentation_link')}
								</a>
							</div>
						{/if}
					</div>
				{:else}
					<!-- Countries Grid -->
					<div
						class="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6"
					>
						{#each filteredCountries as country}
							<CountryCard {country} />
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label for="travel-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<!-- Sidebar Header -->
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Filter class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('adventures.filters_and_stats')}</h2>
					</div>

					<!-- Travel Statistics -->
					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Globe class="w-5 h-5" />
							{$t('adventures.travel_progress')}
						</h3>

						<div class="space-y-4">
							<div class="stat p-0">
								<div class="stat-title text-sm">{$t('worldtravel.total_countries')}</div>
								<div class="stat-value text-2xl">{totalCountries}</div>
								<div class="stat-desc">{$t('worldtravel.available_to_explore')}</div>
							</div>

							<div class="grid grid-cols-2 gap-4">
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('adventures.visited')}</div>
									<div class="stat-value text-lg text-success">{visitedCountries}</div>
								</div>
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('worldtravel.remaining')}</div>
									<div class="stat-value text-lg text-error">{notVisitedCountries}</div>
								</div>
							</div>

							<div class="grid grid-cols-2 gap-4">
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('worldtravel.complete')}</div>
									<div class="stat-value text-sm text-success">{completeCountries}</div>
								</div>
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('worldtravel.partial')}</div>
									<div class="stat-value text-sm text-warning">{partialCountries}</div>
								</div>
							</div>

							<!-- Progress Bar -->
							<div class="space-y-2">
								<div class="flex justify-between text-sm">
									<span>{$t('worldtravel.progress')}</span>
									<span>{Math.round((visitedCountries / totalCountries) * 100)}%</span>
								</div>
								<progress
									class="progress progress-primary w-full"
									value={visitedCountries}
									max={totalCountries}
								></progress>
							</div>
						</div>
					</div>

					<!-- Region Filter -->
					<div class="card bg-base-200/50 p-4">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Pin class="w-5 h-5" />
							{$t('worldtravel.filter_by_region')}
						</h3>

						<div class="space-y-2">
							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="radio"
									name="region"
									class="radio radio-primary radio-sm"
									checked={subRegionOption === ''}
									on:change={() => (subRegionOption = '')}
								/>
								<span class="label-text">{$t('worldtravel.all_regions')}</span>
							</label>

							{#each worldSubregions as subregion}
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="radio"
										name="region"
										class="radio radio-primary radio-sm"
										checked={subRegionOption === subregion}
										on:change={() => (subRegionOption = subregion)}
									/>
									<span class="label-text text-sm">{subregion}</span>
								</label>
							{/each}
						</div>
					</div>

					<!-- Quick Actions -->
					<div class="space-y-3 mt-6">
						<button class="btn btn-outline w-full gap-2" on:click={() => (showMap = !showMap)}>
							{#if showMap}
								<Map class="w-4 h-4" />
								{$t('worldtravel.hide_map')}
							{:else}
								<Map class="w-4 h-4" />
								{$t('worldtravel.show_map')}
							{/if}
						</button>

						<button class="btn btn-ghost w-full gap-2" on:click={clearFilters}>
							<Clear class="w-4 h-4" />
							{$t('worldtravel.clear_all_filters')}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
