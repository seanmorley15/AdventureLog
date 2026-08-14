<script lang="ts">
	import { run } from 'svelte/legacy';

	import RegionCard from '$lib/components/cards/RegionCard.svelte';
	import type { Region, VisitedRegion } from '$lib/types';
	import ClusterMap from '$lib/components/ClusterMap.svelte';
	import type { ClusterOptions } from 'svelte-maplibre';
	import type { PageData } from './$types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';

	// Icons
	import MapMarker from '~icons/mdi/map-marker';
	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Filter from '~icons/mdi/filter-variant';
	import Map from '~icons/mdi/map';
	import Check from '~icons/mdi/check-circle';
	import Info from '~icons/mdi/information-outline';
	import Cancel from '~icons/mdi/cancel';
	import Trophy from '~icons/mdi/trophy';
	import Flag from '~icons/mdi/flag';
	import { normalizeBasemapType } from '$lib';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let regions: Region[] = $derived(data.props?.regions || []);
	let visitedRegions: VisitedRegion[] = $state<VisitedRegion[]>([]);
	let description: string = $derived(data.props?.description || '');
	let filteredRegions: Region[] = $state([]);
	let searchQuery: string = $state('');
	let showGeo: boolean = true;
	let showMap: boolean = $state(false);
	let sidebarOpen = $state(false);
	let filterOption: string = $state('all');

	const country = $derived(data.props?.country || null);
	$effect(() => {
		console.log(data);
	});

	// Statistics
	let numRegions: number = $derived(country?.num_regions || 0);
	let numVisitedRegions: number = $state(0);

	$effect.pre(() => {
		visitedRegions = (data.props?.visitedRegions || []).filter(
			(visitedRegion, index, self) =>
				index === self.findIndex((t) => t.region === visitedRegion.region)
		);
		numVisitedRegions = country?.num_visits || 0;
	});

	let visitedCount = $derived(visitedRegions.length);
	let notVisitedCount = $derived(regions.length - visitedCount);
	let completionPercentage =
		$derived(regions.length > 0 ? Math.round((visitedCount / regions.length) * 100) : 0);

	// Filter regions based on search and filter options
	run(() => {
		if (searchQuery === '') {
			filteredRegions = regions;
		} else {
			filteredRegions = regions.filter((region) =>
				region.name.toLowerCase().includes(searchQuery.toLowerCase())
			);
		}

		if (filterOption === 'visited') {
			filteredRegions = filteredRegions.filter((region) =>
				visitedRegions.some((visitedRegion) => visitedRegion.region === region.id)
			);
		} else if (filterOption === 'not-visited') {
			filteredRegions = filteredRegions.filter(
				(region) => !visitedRegions.some((visitedRegion) => visitedRegion.region === region.id)
			);
		}
	});

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function clearFilters() {
		searchQuery = '';
		filterOption = 'all';
	}

	function togleVisited(region: Region) {
		return () => {
			const visitedRegion = visitedRegions.find(
				(visitedRegion) => visitedRegion.region === region.id
			);
			if (visitedRegion) {
				visitedRegions = visitedRegions.filter(
					(visitedRegion) => visitedRegion.region !== region.id
				);
				removeVisit(region);
			} else {
				markVisited(region);
			}
		};
	}

	async function markVisited(region: Region) {
		let res = await fetch(`/api/visitedregion/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ region: region.id })
		});
		if (!res.ok) {
			console.error('Failed to mark region as visited');
			addToast('error', `${$t('worldtravel.failed_to_mark_visit')} ${region.name}`);
			return;
		} else {
			visitedRegions = [...visitedRegions, await res.json()];
			addToast(
				'success',
				`${$t('worldtravel.visit_to')} ${region.name} ${$t('worldtravel.marked_visited')}`
			);
		}
	}

	async function removeVisit(region: Region) {
		let res = await fetch(`/api/visitedregion/${region.id}`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'DELETE'
		});
		if (!res.ok) {
			console.error($t('worldtravel.region_failed_visited'));
			addToast('error', `${$t('worldtravel.failed_to_mark_visit')} ${region.name}`);
			return;
		} else {
			visitedRegions = visitedRegions.filter((visitedRegion) => visitedRegion.region !== region.id);
			addToast('info', `${$t('worldtravel.visit_to')} ${region.name} ${$t('worldtravel.removed')}`);
		}
	}

	// ClusterMap integration for regions
	type VisitStatus = 'visited' | 'not_visited';

	type RegionFeatureProperties = {
		id: string | number;
		name: string;
		visitStatus: VisitStatus;
	};

	type RegionFeature = {
		type: 'Feature';
		geometry: {
			type: 'Point';
			coordinates: [number, number];
		};
		properties: RegionFeatureProperties;
	};

	type RegionFeatureCollection = {
		type: 'FeatureCollection';
		features: RegionFeature[];
	};

	function parseCoordinate(value: number | string | null | undefined): number | null {
		if (value === null || value === undefined) return null;
		const numeric = typeof value === 'number' ? value : Number(value);
		return Number.isFinite(numeric) ? numeric : null;
	}

	function hasCoordinates(item: {
		latitude: number | string | null;
		longitude: number | string | null;
	}) {
		return parseCoordinate(item.latitude) !== null && parseCoordinate(item.longitude) !== null;
	}

	let hasMappableRegions = $derived(regions.some(hasCoordinates));

	function regionToFeature(region: Region): RegionFeature | null {
		const lat = parseCoordinate(region.latitude);
		const lon = parseCoordinate(region.longitude);
		if (lat === null || lon === null) return null;

		const isVisited = visitedRegions.some((vr) => vr.region === region.id);
		return {
			type: 'Feature',
			geometry: { type: 'Point', coordinates: [lon, lat] },
			properties: {
				id: region.id,
				name: region.name,
				visitStatus: isVisited ? 'visited' : 'not_visited'
			}
		};
	}

	const REGION_SOURCE_ID = 'worldtravel-regions';
	const regionClusterOptions: ClusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 };

	let regionsGeoJson: RegionFeatureCollection = $state({ type: 'FeatureCollection', features: [] });
	run(() => {
		// Explicitly depend on visitedRegions to trigger reactivity when visit status changes
		visitedRegions;
		regionsGeoJson = {
			type: 'FeatureCollection',
			features: regions.map((r) => regionToFeature(r)).filter((f): f is RegionFeature => f !== null)
		};
	});

	function getMarkerProps(feature: any): RegionFeatureProperties | null {
		return feature && feature.properties ? feature.properties : null;
	}

	function getVisitStatusClass(status: VisitStatus): string {
		switch (status) {
			case 'visited':
				return 'bg-green-200';
			case 'not_visited':
			default:
				return 'bg-red-200';
		}
	}

	function markerClassResolver(props: { visitStatus?: string } | null): string {
		if (!props?.visitStatus) return '';
		return getVisitStatusClass(props.visitStatus as VisitStatus);
	}

	function markerLabelResolver(props: { name?: string } | null): string {
		// Toggle label visibility while keeping marker visible
		if (!props) return '';
		return showGeo ? (props.name ?? '') : '';
	}

	function handleMarkerSelect(event: CustomEvent<any>) {
		const id = event.detail?.markerProps?.id as string | number | undefined;
		if (id === undefined || id === null) return;
		const region = regions.find((r) => String(r.id) === String(id));
		if (!region) return;
		// Toggle visit on click
		const isVisited = visitedRegions.some((vr) => vr.region === region.id);
		if (isVisited) {
			removeVisit(region);
		} else {
			markVisited(region);
		}
	}
</script>

<svelte:head>
	<title
		>{data.props && data.props.country ? `Regions in ${data.props.country.name}` : 'Regions'}</title
	>
	<meta
		name="description"
		content="View the regions in countries and mark them visited to track your world travel."
	/>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="regions-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<!-- Header Section -->
			<div class="sticky top-0 z-40 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4">
							<button class="btn btn-ghost btn-square lg:hidden" onclick={toggleSidebar}>
								<Filter class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-xl overflow-hidden">
									{#if country?.flag_url}
										<img src={country.flag_url} alt="" class="w-8 h-8 object-cover rounded-lg" />
									{:else}
										<Flag class="w-8 h-8 text-primary" />
									{/if}
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-primary">
										{$t('worldtravel.regions_in')}
										{country?.name}
									</h1>
									<p class="text-sm text-base-content/60">
										{filteredRegions.length}
										{$t('worldtravel.of')}
										{regions.length} regions ·
										<span class="text-success">{visitedCount} {$t('adventures.visited')}</span>
									</p>
								</div>
							</div>
						</div>

						<div class="hidden md:flex items-center gap-2">
							{#if completionPercentage === 100}
								<div class="badge badge-success gap-2 p-3">
									<Trophy class="w-4 h-4" />
									{$t('worldtravel.complete')}
								</div>
							{:else}
								<div class="badge badge-primary gap-2 p-3">
									{completionPercentage}%
								</div>
							{/if}
						</div>
					</div>

					{#if description}
						<details class="mt-3 group">
							<summary
								class="text-sm text-base-content/70 cursor-pointer hover:text-primary flex items-center gap-2 list-none"
							>
								<Info class="w-4 h-4" />
								{$t('worldtravel.about_country')}
							</summary>
							<p
								class="text-sm text-base-content/70 mt-2 pl-6 leading-relaxed max-h-32 overflow-y-auto"
							>
								{description}
							</p>
						</details>
					{/if}

					<!-- Search and Filters -->
					<div class="mt-4 flex flex-col lg:flex-row lg:items-center gap-4">
						<!-- Search Bar -->
						<div class="relative flex-1 max-w-md">
							<Search
								class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-base-content/40"
							/>
							<input
								type="text"
								placeholder={$t('navbar.search')}
								class="input w-full pl-10 pr-10 bg-base-100/80"
								bind:value={searchQuery}
							/>
							{#if searchQuery.length > 0}
								<button
									class="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content"
									onclick={() => (searchQuery = '')}
								>
									<Clear class="w-4 h-4" />
								</button>
							{/if}
						</div>

						{#if hasMappableRegions}
							<button
								class="btn btn-outline gap-2 {showMap ? 'btn-active' : ''}"
								onclick={() => (showMap = !showMap)}
							>
								<Map class="w-4 h-4" />
								<span class="hidden sm:inline">
									{showMap ? $t('worldtravel.hide_map') : $t('worldtravel.show_map')}
								</span>
							</button>
						{/if}

						<!-- Filter Chips -->
						<div class="flex flex-wrap items-center gap-2">
							<span class="text-sm font-medium text-base-content/60 hidden sm:inline"
								>{$t('worldtravel.filter_by')}:</span
							>
							<div class="tabs tabs-box bg-base-200">
								<button
									class="tab tab-sm gap-2 {filterOption === 'all' ? 'tab-active' : ''}"
									onclick={() => (filterOption = 'all')}
								>
									<MapMarker class="w-3 h-3" />
									{$t('adventures.all')}
								</button>
								<button
									class="tab tab-sm gap-2 {filterOption === 'visited' ? 'tab-active' : ''}"
									onclick={() => (filterOption = 'visited')}
								>
									<Check class="w-3 h-3" />
									{$t('adventures.visited')}
								</button>
								<button
									class="tab tab-sm gap-2 {filterOption === 'not-visited' ? 'tab-active' : ''}"
									onclick={() => (filterOption = 'not-visited')}
								>
									<Cancel class="w-3 h-3" />
									{$t('adventures.not_visited')}
								</button>
							</div>

							{#if searchQuery || filterOption !== 'all'}
								<button class="btn btn-ghost btn-xs gap-1" onclick={clearFilters}>
									<Clear class="w-3 h-3" />
									{$t('worldtravel.clear_all')}
								</button>
							{/if}
						</div>
					</div>
				</div>
			</div>

			<!-- Map Section -->
			{#if showMap && hasMappableRegions}
				<div class="container mx-auto px-6 py-4">
					<div class="card bg-base-100 shadow-xl overflow-hidden">
						<div
							class="flex items-center justify-between px-4 py-3 bg-base-200/50 border-b border-base-300"
						>
							<span class="font-semibold flex items-center gap-2">
								<Map class="w-5 h-5 text-primary" />
								{$t('worldtravel.interactive_map')}
							</span>
							<div class="flex items-center gap-4 text-sm text-base-content/60">
								<span class="flex items-center gap-1.5">
									<span class="w-3 h-3 bg-green-200 rounded-full border"></span>
									{$t('adventures.visited')}
								</span>
								<span class="flex items-center gap-1.5">
									<span class="w-3 h-3 bg-red-200 rounded-full border"></span>
									{$t('adventures.not_visited')}
								</span>
							</div>
						</div>
						<ClusterMap
							geoJson={regionsGeoJson}
							sourceId={REGION_SOURCE_ID}
							clusterOptions={regionClusterOptions}
							basemapType={normalizeBasemapType(data.user?.map_style)}
							mapClass="aspect-[16/10] w-full"
							fitLevel="region"
							on:markerSelect={handleMarkerSelect}
							{getMarkerProps}
							markerClass={markerClassResolver}
							markerLabel={markerLabelResolver}
						/>
					</div>
				</div>
			{/if}

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-6">
				{#if filteredRegions.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							<MapMarker class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{$t('worldtravel.no_regions_found')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md mb-6">
							{$t('worldtravel.no_countries_found_desc')}
						</p>
						<button class="btn btn-primary gap-2" onclick={clearFilters}>
							<Clear class="w-4 h-4" />
							{$t('worldtravel.clear_filters')}
						</button>
					</div>
				{:else}
					<div class="card bg-base-100 shadow-xl overflow-hidden">
						<div
							class="hidden sm:grid items-center gap-3 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-base-content/50 bg-base-200/50 border-b border-base-300"
							style="grid-template-columns: 2.5rem 1fr 7rem 5rem 8rem"
						>
							<span></span>
							<span>{$t('map.regions')}</span>
							<span>Country</span>
							<span>{$t('worldtravel.cities')}</span>
							<span></span>
						</div>
						<div class="divide-y divide-base-300/50">
							{#each filteredRegions as region (region.id)}
								<RegionCard
									{region}
									visited={visitedRegions.some(
										(visitedRegion) => visitedRegion.region === region.id
									)}
									on:visit={(e) => {
										visitedRegions = [...visitedRegions, e.detail];
										numVisitedRegions++;
									}}
									on:remove={() => {
										visitedRegions = visitedRegions.filter(
											(visitedRegion) => visitedRegion.region !== region.id
										);
										numVisitedRegions--;
									}}
								/>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label for="regions-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Filter class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('worldtravel.progress_and_stats')}</h2>
					</div>

					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Flag class="w-5 h-5" />
							{country?.name}
						</h3>

						<div class="space-y-4">
							<div class="stat p-0">
								<div class="stat-title text-sm">{$t('worldtravel.total_regions')}</div>
								<div class="stat-value text-2xl">{regions.length}</div>
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

							<div class="space-y-2">
								<div class="flex justify-between text-sm">
									<span>{$t('worldtravel.progress')}</span>
									<span>{completionPercentage}%</span>
								</div>
								<progress
									class="progress progress-primary w-full"
									value={visitedCount}
									max={regions.length || 1}
								></progress>
							</div>

							{#if completionPercentage === 100}
								<div class="alert alert-success py-2">
									<Trophy class="w-4 h-4" />
									<span class="text-sm">{$t('worldtravel.country_completed')}!</span>
								</div>
							{/if}
						</div>
					</div>

					{#if hasMappableRegions}
						<div class="space-y-3">
							<button class="btn btn-outline w-full gap-2" onclick={() => (showMap = !showMap)}>
								<Map class="w-4 h-4" />
								{showMap ? $t('worldtravel.hide_map') : $t('worldtravel.show_map')}
							</button>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>
