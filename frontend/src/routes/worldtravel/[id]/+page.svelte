<script lang="ts">
	import RegionCard from '$lib/components/RegionCard.svelte';
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
	import Target from '~icons/mdi/target';
	import Flag from '~icons/mdi/flag';
	import { getBasemapUrl } from '$lib';

	export let data: PageData;

	let regions: Region[] = data.props?.regions || [];
	let visitedRegions: VisitedRegion[] = data.props?.visitedRegions || [];
	let description: string = data.props?.description || '';
	let showFullDesc = false;
	let filteredRegions: Region[] = [];
	let searchQuery: string = '';
	let showGeo: boolean = true;
	let sidebarOpen = false;
	let filterOption: string = 'all';

	const country = data.props?.country || null;
	console.log(data);

	// Statistics
	let numRegions: number = country?.num_regions || 0;
	let numVisitedRegions: number = country?.num_visits || 0;

	$: visitedCount = visitedRegions.length;
	$: notVisitedCount = regions.length - visitedCount;
	$: completionPercentage =
		regions.length > 0 ? Math.round((visitedCount / regions.length) * 100) : 0;

	// Filter regions based on search and filter options
	$: {
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
	}

	// Remove duplicates from visitedRegions
	visitedRegions = visitedRegions.filter(
		(visitedRegion, index, self) =>
			index === self.findIndex((t) => t.region === visitedRegion.region)
	);

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
	const regionClusterOptions: ClusterOptions = { radius: 300, maxZoom: 8, minPoints: 1 };

	let regionsGeoJson: RegionFeatureCollection = { type: 'FeatureCollection', features: [] };
	$: regionsGeoJson = {
		type: 'FeatureCollection',
		features: regions.map((r) => regionToFeature(r)).filter((f): f is RegionFeature => f !== null)
	};

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
							<button class="btn btn-ghost btn-square lg:hidden" on:click={toggleSidebar}>
								<Filter class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-xl">
									<Flag class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-primary">
										{$t('worldtravel.regions_in')}
										{country?.name}
									</h1>
									<p class="text-sm text-base-content/60">
										{filteredRegions.length} of {regions.length} regions
									</p>
								</div>
							</div>
						</div>

						<!-- Completion Badge -->
						<div class="hidden md:flex items-center gap-2">
							{#if completionPercentage === 100}
								<div class="badge badge-success gap-2 p-3">
									<Trophy class="w-4 h-4" />
									Complete!
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
					<div class="mt-4 flex flex-col lg:flex-row lg:items-center gap-4">
						<!-- Search Bar -->
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

						<!-- Filter Chips -->
						<div class="flex flex-wrap items-center gap-2">
							<span class="text-sm font-medium text-base-content/60 hidden sm:inline"
								>{$t('worldtravel.filter_by')}:</span
							>
							<div class="tabs tabs-boxed bg-base-200">
								<button
									class="tab tab-sm gap-2 {filterOption === 'all' ? 'tab-active' : ''}"
									on:click={() => (filterOption = 'all')}
								>
									<MapMarker class="w-3 h-3" />
									{$t('adventures.all')}
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
			</div>

			<!-- Description Section -->
			{#if description}
				<div class="container mx-auto px-6 py-4">
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body p-4">
							<div class="flex items-center gap-2 mb-4">
								<Info class="w-5 h-5 text-primary" />
								<h2 class="text-lg font-semibold">{$t('worldtravel.about_country')}</h2>
							</div>
							<p
								class="text-base-content/70 leading-relaxed"
								class:overflow-hidden={!showFullDesc}
								style={!showFullDesc && description.length > 400
									? 'max-height:8rem;overflow:hidden;'
									: ''}
							>
								{description}
							</p>
							{#if description.length > 400}
								<button
									class="btn btn-ghost btn-sm mt-3"
									on:click={() => (showFullDesc = !showFullDesc)}
								>
									{#if showFullDesc}{$t('worldtravel.show_less')}{:else}{$t(
											'worldtravel.show_more'
										)}{/if}
								</button>
							{/if}
						</div>
					</div>
				</div>
			{/if}

			<!-- Map Section -->
			{#if regions.some((region) => region.latitude && region.longitude)}
				<div class="container mx-auto px-6 py-4">
					<div class="card bg-base-100 shadow-xl">
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
							<ClusterMap
								geoJson={regionsGeoJson}
								sourceId={REGION_SOURCE_ID}
								clusterOptions={regionClusterOptions}
								mapStyle={getBasemapUrl()}
								mapClass="aspect-[16/10] w-full rounded-lg"
								fitLevel="region"
								on:markerSelect={handleMarkerSelect}
								{getMarkerProps}
								markerClass={markerClassResolver}
								markerLabel={markerLabelResolver}
							/>
						</div>
					</div>
				</div>
			{/if}

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-8">
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
						<button class="btn btn-primary gap-2" on:click={clearFilters}>
							<Clear class="w-4 h-4" />
							{$t('worldtravel.clear_filters')}
						</button>
					</div>
				{:else}
					<!-- Regions Grid -->
					<div
						class="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6"
					>
						{#each filteredRegions as region}
							<RegionCard
								{region}
								visited={visitedRegions.some((visitedRegion) => visitedRegion.region === region.id)}
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
				{/if}
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label for="regions-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<!-- Sidebar Header -->
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Filter class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('worldtravel.progress_and_stats')}</h2>
					</div>

					<!-- Country Progress -->
					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Flag class="w-5 h-5" />
							{country?.name}
						</h3>

						<div class="space-y-4">
							<div class="stat p-0">
								<div class="stat-title text-sm">{$t('worldtravel.total_regions')}</div>
								<div class="stat-value text-2xl">{regions.length}</div>
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
									max={regions.length}
								></progress>
							</div>

							{#if completionPercentage === 100}
								<div class="alert alert-success">
									<Trophy class="w-4 h-4" />
									<span class="text-sm">{$t('worldtravel.country_completed')}! 🎉</span>
								</div>
							{/if}
						</div>
					</div>
					<!-- Quick Actions -->
					{#if regions.some((region) => region.latitude && region.longitude)}
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

							<!-- <button class="btn btn-ghost w-full gap-2" on:click={clearFilters}>
							<Clear class="w-4 h-4" />
							Clear All Filters
						</button> -->
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>
