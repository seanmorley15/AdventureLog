<script lang="ts">
	import { goto } from '$app/navigation';
	import CountryCard from '$lib/components/CountryCard.svelte';
	import ClusterMap from '$lib/components/ClusterMap.svelte';
	import type { Country } from '$lib/types';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import type { ClusterOptions } from 'svelte-maplibre';

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
	let showGlobeSpin: boolean = false;
	let sidebarOpen = false;

	type VisitStatus = 'not_visited' | 'partial' | 'complete';

	type CountryFeatureProperties = {
		name: string;
		country_code: string;
		visitStatus: VisitStatus;
		num_visits: number;
		num_regions: number;
	};

	type CountryFeature = {
		type: 'Feature';
		geometry: {
			type: 'Point';
			coordinates: [number, number];
		};
		properties: CountryFeatureProperties;
	};

	type CountryFeatureCollection = {
		type: 'FeatureCollection';
		features: CountryFeature[];
	};
	const COUNTRY_SOURCE_ID = 'worldtravel-countries';
	const countryClusterOptions: ClusterOptions = {
		radius: 300,
		maxZoom: 5,
		minPoints: 1
	};

	let countriesGeoJson: CountryFeatureCollection = {
		type: 'FeatureCollection',
		features: []
	};

	function parseCoordinate(value: number | string | null | undefined): number | null {
		if (value === null || value === undefined) {
			return null;
		}

		const numeric = typeof value === 'number' ? value : Number(value);
		return Number.isFinite(numeric) ? numeric : null;
	}

	function getCountryCoordinates(country: Country): [number, number] | null {
		const latitude = parseCoordinate(country.latitude);
		const longitude = parseCoordinate(country.longitude);

		if (latitude === null || longitude === null) {
			return null;
		}

		return [longitude, latitude];
	}

	function getVisitStatus(country: Country): VisitStatus {
		if (country.num_visits === 0) {
			return 'not_visited';
		}
		if (country.num_regions > 0 && country.num_visits >= country.num_regions) {
			return 'complete';
		}
		return 'partial';
	}

	function countryToFeature(country: Country, coordinates: [number, number]): CountryFeature {
		const visitStatus = getVisitStatus(country);
		return {
			type: 'Feature',
			geometry: {
				type: 'Point',
				coordinates
			},
			properties: {
				name: country.name,
				country_code: country.country_code,
				visitStatus,
				num_visits: country.num_visits,
				num_regions: country.num_regions
			}
		};
	}

	function getVisitStatusClass(status: VisitStatus): string {
		switch (status) {
			case 'not_visited':
				return 'bg-red-200';
			case 'complete':
				return 'bg-green-200';
			default:
				return 'bg-blue-200';
		}
	}

	function getMarkerProps(feature: any): CountryFeatureProperties | null {
		if (!feature) {
			return null;
		}

		return feature.properties ?? null;
	}

	function markerClassResolver(props: { visitStatus?: string } | null): string {
		if (!props?.visitStatus) {
			return '';
		}

		if (
			props.visitStatus === 'not_visited' ||
			props.visitStatus === 'partial' ||
			props.visitStatus === 'complete'
		) {
			return getVisitStatusClass(props.visitStatus);
		}

		return '';
	}

	function handleMarkerSelect(event: CustomEvent<{ countryCode?: string }>) {
		const countryCode = event.detail.countryCode;
		if (!countryCode) {
			return;
		}

		goto(`/worldtravel/${countryCode}`);
	}

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

	$: countriesGeoJson = {
		type: 'FeatureCollection',
		features: filteredCountries
			.map((country) => {
				const coordinates = getCountryCoordinates(country);
				if (!coordinates) {
					return null;
				}

				return countryToFeature(country, coordinates);
			})
			.filter((feature): feature is CountryFeature => feature !== null)
	};

	// when isGlobeSpin is enabled, fetch /api/globespin/
	type GlobeSpinData = {
		country: {
			flag_url: string;
			name: string;
			country_code: string;
			num_visits: number;
			subregion: string;
			capital: string;
			num_regions: number;
		};
		region: { name: string; num_cities: number };
		city: { name: string; region_name: string };
	};
	let globeSpinData: GlobeSpinData | null = null;
	let isLoadingGlobeSpin = false;

	async function fetchGlobeSpin() {
		isLoadingGlobeSpin = true;
		try {
			const response = await fetch('/api/globespin/');
			if (response.ok) {
				globeSpinData = await response.json();
			} else {
				console.error('Failed to fetch globe spin data');
			}
		} catch (error) {
			console.error('Error fetching globe spin data:', error);
		} finally {
			isLoadingGlobeSpin = false;
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
	<div class="drawer lg:drawer-open">
		<input id="travel-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

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
									<Globe class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold text-primary bg-clip-text">
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
						<!-- Globe Spin Toggle -->
						<button
							class="btn btn-outline gap-2 {showGlobeSpin ? 'btn-active' : ''}"
							on:click={() => {
								showGlobeSpin = !showGlobeSpin;
								if (showGlobeSpin) {
									fetchGlobeSpin();
								}
							}}
						>
							{#if showGlobeSpin}
								<Globe class="w-4 h-4" />
								<span class="hidden sm:inline">{$t('worldtravel.hide_globe_spin')}</span>
							{:else}
								<Globe class="w-4 h-4" />
								<span class="hidden sm:inline">{$t('worldtravel.show_globe_spin')}</span>
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
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body p-4">
							<ClusterMap
								geoJson={countriesGeoJson}
								sourceId={COUNTRY_SOURCE_ID}
								clusterOptions={countryClusterOptions}
								mapStyle={getBasemapUrl()}
								mapClass="aspect-[16/10] w-full rounded-lg"
								on:markerSelect={handleMarkerSelect}
								{getMarkerProps}
								markerClass={markerClassResolver}
							/>
						</div>
					</div>
				</div>
			{/if}

			<!-- Globe Spin Section -->
			{#if showGlobeSpin}
				<div class="container mx-auto px-6 py-4">
					<div class="card bg-base-100 shadow-xl overflow-hidden">
						<div class="card-body p-6">
							{#if isLoadingGlobeSpin}
								<!-- Loading State with Spinning Globe -->
								<div class="flex flex-col items-center py-12">
									<div class="relative">
										<!-- Spinning globe with pulse effect -->
										<div class="relative animate-spin" style="animation-duration: 3s;">
											<div
												class="w-24 h-24 rounded-full bg-gradient-to-br from-primary/20 to-accent/30 flex items-center justify-center border-4 border-primary/30"
											>
												<Globe class="w-12 h-12 text-primary" />
											</div>
											<!-- Orbit rings -->
											<div
												class="absolute inset-0 rounded-full border-2 border-dashed border-primary/20 animate-pulse"
											></div>
											<div
												class="absolute -inset-2 rounded-full border border-dashed border-accent/20 animate-pulse"
												style="animation-delay: 0.5s;"
											></div>
										</div>
										<!-- Sparkle effects -->
										<div
											class="absolute -top-2 -right-2 w-3 h-3 bg-yellow-400 rounded-full animate-ping"
										></div>
										<div
											class="absolute -bottom-3 -left-3 w-2 h-2 bg-blue-400 rounded-full animate-ping"
											style="animation-delay: 1s;"
										></div>
										<div
											class="absolute top-1/2 -right-4 w-1.5 h-1.5 bg-green-400 rounded-full animate-ping"
											style="animation-delay: 2s;"
										></div>
									</div>
									<div class="mt-6 text-center">
										<h3 class="text-xl font-bold text-primary mb-2">
											{$t('worldtravel.spinning_globe') + '...'}
										</h3>
										<p class="text-base-content/70 animate-pulse">
											{$t('worldtravel.loading_globe_spin')}
										</p>
										<div class="flex items-center justify-center gap-1 mt-3">
											<div class="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
											<div
												class="w-2 h-2 bg-primary rounded-full animate-bounce"
												style="animation-delay: 0.2s;"
											></div>
											<div
												class="w-2 h-2 bg-primary rounded-full animate-bounce"
												style="animation-delay: 0.4s;"
											></div>
										</div>
									</div>
								</div>
							{:else if globeSpinData}
								<!-- Result Display with Amazing Animations -->
								<div class="text-center">
									<div class="mb-6">
										<h3
											class="text-2xl font-bold text-primary mb-2 flex items-center justify-center gap-3"
										>
											<Globe class="w-8 h-8 animate-spin" style="animation-duration: 4s;" />
											{$t('worldtravel.destination_revealed')}
											<Globe
												class="w-8 h-8 animate-spin"
												style="animation-duration: 4s; animation-direction: reverse;"
											/>
										</h3>
										<p class="text-base-content/60">
											{$t('worldtravel.your_random_adventure_awaits')}
										</p>
									</div>

									<!-- Country Card with Entrance Animation -->
									<div class="animate-slideInUp" style="animation-duration: 0.8s;">
										<!-- Flag with Reveal Effect -->
										<div class="relative mb-6 mx-auto w-fit">
											<div
												class="relative overflow-hidden rounded-2xl shadow-2xl border-4 border-primary/20 hover:border-primary/40 transition-colors duration-300"
											>
												<img
													src={globeSpinData.country.flag_url}
													alt="{globeSpinData.country.name} flag"
													class="w-64 h-40 object-cover hover:scale-105 transition-transform duration-500"
												/>
												<!-- Shimmer overlay -->
												<div
													class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full animate-shimmer"
												></div>
											</div>
											<!-- Floating badges -->
											<div
												class="absolute -top-3 -right-3 badge badge-primary badge-lg animate-bounce shadow-lg"
											>
												{globeSpinData.country.country_code}
											</div>
											{#if globeSpinData.country.num_visits > 0}
												<div
													class="absolute -top-3 -left-3 badge badge-success badge-lg animate-pulse shadow-lg"
												>
													<Check class="w-4 h-4 mr-1" />
													{$t('adventures.visited')}
												</div>
											{/if}
										</div>

										<!-- Country Info -->
										<div class="space-y-4 animate-fadeInUp" style="animation-delay: 0.2s;">
											<h2
												class="text-4xl font-bold text-primary bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent pb-2"
											>
												{globeSpinData.country.name}
											</h2>

											<div class="flex flex-wrap justify-center gap-4">
												<div class="badge badge-lg badge-outline gap-2">
													<Pin class="w-4 h-4" />
													{globeSpinData.country.subregion}
												</div>
												{#if globeSpinData.country.capital}
													<div class="badge badge-lg badge-outline gap-2">
														<Globe class="w-4 h-4" />
														{globeSpinData.country.capital}
													</div>
												{/if}
											</div>

											<!-- Progress Info -->
											<div
												class="card bg-gradient-to-br from-base-200/50 to-base-300/30 p-4 max-w-md mx-auto"
											>
												<div class="flex justify-between items-center mb-2">
													<span class="text-sm font-medium"
														>{$t('worldtravel.exploration_progress')}</span
													>
													<span class="text-lg font-bold text-primary">
														{globeSpinData.country.num_visits}/{globeSpinData.country.num_regions}
													</span>
												</div>
												<progress
													class="progress progress-primary w-full"
													value={globeSpinData.country.num_visits}
													max={globeSpinData.country.num_regions}
												></progress>
												<div class="text-xs text-base-content/60 mt-1">
													{Math.round(
														(globeSpinData.country.num_visits / globeSpinData.country.num_regions) *
															100
													)}% explored
												</div>
											</div>
										</div>
									</div>

									<!-- Region & City Info (if available) -->
									{#if globeSpinData.region || globeSpinData.city}
										<div class="mt-8 space-y-4 animate-fadeInUp" style="animation-delay: 0.4s;">
											<div class="divider">
												<span class="text-primary font-semibold"
													>{$t('worldtravel.dive_deeper')}</span
												>
											</div>

											<div class="grid md:grid-cols-2 gap-4 max-w-2xl mx-auto">
												{#if globeSpinData.region}
													<div
														class="card bg-gradient-to-br from-accent/10 to-secondary/10 border border-accent/20"
													>
														<div class="card-body p-4">
															<h4 class="font-bold text-accent flex items-center gap-2">
																<Pin class="w-5 h-5" />
																{$t('adventures.region')}
															</h4>
															<p class="text-lg font-semibold">{globeSpinData.region.name}</p>
															<p class="text-sm text-base-content/60">
																{globeSpinData.region.num_cities}
																{$t('worldtravel.cities_available')}
															</p>
														</div>
													</div>
												{/if}

												{#if globeSpinData.city}
													<div
														class="card bg-gradient-to-br from-success/10 to-info/10 border border-success/20"
													>
														<div class="card-body p-4">
															<h4 class="font-bold text-success flex items-center gap-2">
																<Map class="w-5 h-5" />
																{$t('adventures.city')}
															</h4>
															<p class="text-lg font-semibold">{globeSpinData.city.name}</p>
															<p class="text-sm text-base-content/60">
																{$t('worldtravel.in')}
																{globeSpinData.city.region_name}
															</p>
														</div>
													</div>
												{/if}
											</div>
										</div>
									{/if}

									<!-- Action Buttons -->
									<div
										class="mt-8 flex flex-wrap justify-center gap-4 animate-fadeInUp"
										style="animation-delay: 0.6s;"
									>
										<a
											href="/worldtravel/{globeSpinData.country.country_code}"
											class="btn btn-primary btn-lg gap-2 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
										>
											<Globe class="w-5 h-5" />
											{$t('worldtravel.explore_country')}
										</a>
										<button
											class="btn btn-outline btn-lg gap-2 hover:scale-105 transition-all duration-300"
											on:click={fetchGlobeSpin}
										>
											<Globe class="w-5 h-5 animate-spin" style="animation-duration: 2s;" />
											{$t('worldtravel.spin_again')}
										</button>
									</div>
								</div>
							{:else}
								<!-- No Data State -->
								<div class="flex flex-col items-center py-12">
									<div class="p-6 bg-error/10 rounded-2xl mb-6">
										<Cancel class="w-16 h-16 text-error/50" />
									</div>
									<h3 class="text-xl font-semibold text-base-content/70 mb-2">
										{$t('worldtravel.no_globe_spin_data')}
									</h3>
									<p class="text-base-content/50 text-center max-w-md mb-6">
										{$t('worldtravel.globe_spin_error_desc')}
									</p>
									<button class="btn btn-primary gap-2" on:click={fetchGlobeSpin}>
										<Globe class="w-4 h-4" />
										{$t('worldtravel.try_again')}
									</button>
								</div>
							{/if}
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

<style>
	@keyframes slideInUp {
		from {
			opacity: 0;
			transform: translateY(30px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes fadeInUp {
		from {
			opacity: 0;
			transform: translateY(20px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes shimmer {
		0% {
			transform: translateX(-100%);
		}
		100% {
			transform: translateX(100%);
		}
	}

	.animate-slideInUp {
		animation: slideInUp ease-out forwards;
	}

	.animate-fadeInUp {
		animation: fadeInUp ease-out forwards;
	}

	.animate-shimmer {
		animation: shimmer 2s infinite;
	}
</style>
