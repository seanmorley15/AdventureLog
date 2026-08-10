<script lang="ts">
	import { goto, invalidate } from '$app/navigation';
	import { page } from '$app/stores';
	import LocationCard from '$lib/components/cards/LocationCard.svelte';
	import CategoryFilterDropdown from '$lib/components/CategoryFilterDropdown.svelte';
	import CategoryModal from '$lib/components/CategoryModal.svelte';
	import type { Location } from '$lib/types';
	import { t } from 'svelte-i18n';

	import Plus from '~icons/mdi/plus';
	import Sort from '~icons/mdi/sort';
	import Filter from '~icons/mdi/filter-variant';
	import Eye from '~icons/mdi/eye';
	import Calendar from '~icons/mdi/calendar';
	import Tag from '~icons/mdi/tag';
	import Compass from '~icons/mdi/compass';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';

	export let data: any;

	const resultsPerPage = 25;

	let adventures: Location[] = [];
	let count = 0;
	let totalPages = 1;

	$: adventures = data?.props?.adventures ?? [];
	$: count = data?.props?.count ?? 0;
	$: totalPages = Math.max(1, Math.ceil(count / resultsPerPage));
	$: categoryTypes = $page.url.searchParams.get('types') ?? '';
	$: orderBy = $page.url.searchParams.get('order_by') || 'updated_at';
	$: orderDirection = $page.url.searchParams.get('order_direction') || 'asc';
	$: isVisitedFilter = $page.url.searchParams.get('is_visited') || 'all';
	$: includeCollections = $page.url.searchParams.get('include_collections') !== 'false';
	$: currentPage = parseInt($page.url.searchParams.get('page') || '1', 10);

	let locationBeingUpdated: Location | undefined = undefined;

	function toListLocation(loc: Location): Location {
		// Keep the in-memory list aligned with the slim list API payload
		return {
			...loc,
			visits: [],
			attachments: [],
			trails: []
		};
	}

	// Sync the locationBeingUpdated with the adventures array
	$: {
		if (locationBeingUpdated && locationBeingUpdated.id) {
			const listItem = toListLocation(locationBeingUpdated);
			const index = adventures.findIndex((adventure) => adventure.id === listItem.id);

			if (index !== -1) {
				adventures[index] = listItem;
				adventures = adventures; // Trigger reactivity
			} else {
				adventures = [listItem, ...adventures];
				data.props.adventures = adventures; // Update data.props.adventures as well
			}
		}
	}

	let is_category_modal_open: boolean = false;
	let adventureToEdit: Location | null = null;
	let isLocationModalOpen: boolean = false;
	let editingLocationId: string | null = null;
	let sidebarOpen = false;

	type LocationFilterOverrides = {
		types?: string;
		is_visited?: string;
		order_by?: string;
		order_direction?: string;
		include_collections?: boolean;
	};

	function buildFilterUrl(overrides: LocationFilterOverrides = {}) {
		const url = new URL($page.url);

		const types =
			overrides.types !== undefined ? overrides.types : (url.searchParams.get('types') ?? '');
		const nextIsVisited = overrides.is_visited ?? url.searchParams.get('is_visited') ?? 'all';
		const nextOrderBy = overrides.order_by ?? url.searchParams.get('order_by') ?? 'updated_at';
		const nextOrderDirection =
			overrides.order_direction ?? url.searchParams.get('order_direction') ?? 'asc';
		const includeCollectionsParam = url.searchParams.get('include_collections');
		const nextIncludeCollections =
			overrides.include_collections ??
			(includeCollectionsParam === null ? true : includeCollectionsParam !== 'false');

		if (types) {
			url.searchParams.set('types', types);
		} else {
			url.searchParams.delete('types');
		}

		url.searchParams.set('is_visited', nextIsVisited);
		url.searchParams.set('order_by', nextOrderBy);
		url.searchParams.set('order_direction', nextOrderDirection);
		url.searchParams.set('include_collections', nextIncludeCollections ? 'true' : 'false');
		url.searchParams.delete('page');

		return `${url.pathname}${url.search}`;
	}

	async function applyLocationFilters(overrides: LocationFilterOverrides = {}) {
		const target = buildFilterUrl(overrides);
		await goto(target, { keepFocus: true, noScroll: true });
		await invalidate('locations:list');
	}

	async function onCategoryChange(event: CustomEvent<{ types: string }>) {
		await applyLocationFilters({ types: event.detail.types });
	}

	async function updateVisitedFilter(value: string) {
		await applyLocationFilters({ is_visited: value });
	}

	async function updateSort(by: string, direction: string) {
		await applyLocationFilters({ order_by: by, order_direction: direction });
	}

	async function updateIncludeCollections(checked: boolean) {
		await applyLocationFilters({ include_collections: checked });
	}

	async function handleChangePage(pageNumber: number) {
		const url = new URL($page.url);
		url.searchParams.set('page', pageNumber.toString());
		const target = `${url.pathname}${url.search}`;
		await goto(target, { keepFocus: true, noScroll: true });
		await invalidate('locations:list');
	}

	function deleteAdventure(event: CustomEvent<string>) {
		adventures = adventures.filter((adventure) => adventure.id !== event.detail);
	}

	async function editAdventure(event: CustomEvent<Location>) {
		const locationId = event.detail?.id;
		if (!locationId) {
			adventureToEdit = event.detail;
			isLocationModalOpen = true;
			return;
		}

		// List endpoint returns a slim payload; fetch full location for the edit modal
		editingLocationId = locationId;
		try {
			const res = await fetch(`/api/locations/${locationId}/`);
			adventureToEdit = res.ok ? await res.json() : event.detail;
			isLocationModalOpen = true;
		} catch {
			adventureToEdit = event.detail;
			isLocationModalOpen = true;
		} finally {
			editingLocationId = null;
		}
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function getVisitedCount() {
		return adventures.filter((a) => a.is_visited).length;
	}

	function getPlannedCount() {
		return adventures.filter((a) => !a.is_visited).length;
	}
</script>

<svelte:head>
	<title>{$t('locations.locations')}</title>
	<meta name="description" content="View your completed and planned adventures." />
</svelte:head>

{#if isLocationModalOpen}
	<NewLocationModal
		on:close={() => (isLocationModalOpen = false)}
		user={data.user}
		locationToEdit={adventureToEdit}
		bind:location={locationBeingUpdated}
	/>
{/if}

{#if is_category_modal_open}
	<CategoryModal on:close={() => (is_category_modal_open = false)} />
{/if}

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="my-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<!-- Header Section -->
			<div class="sticky top-0 z-30 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4">
							<button class="btn btn-ghost btn-square lg:hidden" on:click={toggleSidebar}>
								<Filter class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-xl">
									<Compass class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-primary">
										{$t('locations.my_locations')}
									</h1>
									<p class="text-sm text-base-content/60">
										{count}
										{$t('locations.locations')} • {getVisitedCount()}
										{$t('adventures.visited')} • {getPlannedCount()}
										{$t('adventures.planned')}
									</p>
								</div>
							</div>
						</div>

						<!-- Quick Stats -->
						<div class="hidden md:flex items-center gap-3">
							<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
								<div class="stat py-2 px-4">
									<div class="stat-figure text-primary">
										<Eye class="w-5 h-5" />
									</div>
									<div class="stat-title text-xs">{$t('adventures.visited')}</div>
									<div class="stat-value text-lg">{getVisitedCount()}</div>
								</div>
								<div class="stat py-2 px-4">
									<div class="stat-figure text-secondary">
										<Calendar class="w-5 h-5" />
									</div>
									<div class="stat-title text-xs">{$t('adventures.planned')}</div>
									<div class="stat-value text-lg">{getPlannedCount()}</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-8">
				{#if adventures.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							<Compass class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{$t('adventures.no_locations_found')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md">
							{$t('adventures.no_adventures_message')}
						</p>
						<button
							class="btn btn-primary btn-wide mt-6 gap-2"
							on:click={() => {
								adventureToEdit = null;
								isLocationModalOpen = true;
							}}
						>
							<Plus class="w-5 h-5" />
							{$t('adventures.create_location')}
						</button>
					</div>
				{:else}
					<!-- Adventures Grid -->
					<div
						class="grid grid-cols-1 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6"
					>
						{#each adventures as adventure}
							<LocationCard
								user={data.user}
								{adventure}
								isEditLoading={editingLocationId === adventure.id}
								on:delete={deleteAdventure}
								on:edit={editAdventure}
								on:duplicate={(e) => {
									// Add the new location to the beginning of the list
									adventures = [e.detail, ...adventures];
								}}
							/>
						{/each}
					</div>

					<!-- Pagination -->
					{#if totalPages > 1}
						<div class="flex justify-center mt-12">
							<div class="join bg-base-100 shadow-lg rounded-2xl p-2">
								{#each Array.from({ length: totalPages }, (_, i) => i + 1) as page}
									<button
										class="join-item btn btn-sm {currentPage === page
											? 'btn-primary'
											: 'btn-ghost'}"
										on:click={() => handleChangePage(page)}
									>
										{page}
									</button>
								{/each}
							</div>
						</div>
					{/if}
				{/if}
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label
				for="my-drawer"
				class="drawer-overlay lg:hidden"
				class:pointer-events-none={!sidebarOpen}
				aria-hidden={!sidebarOpen}
			></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Sort class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('adventures.filters_and_sort')}</h2>
					</div>

					<div class="location-filters">
						<div class="card bg-base-200/50 p-4 mb-4">
							<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
								<Tag class="w-5 h-5" />
								{$t('adventures.categories')}
							</h3>
							<CategoryFilterDropdown types={categoryTypes} on:change={onCategoryChange} />
							<button
								type="button"
								on:click={() => (is_category_modal_open = true)}
								class="btn btn-outline btn-sm w-full mt-2 gap-2"
							>
								<Tag class="w-4 h-4" />
								{$t('categories.manage_categories')}
							</button>
						</div>

						<div class="card bg-base-200/50 p-4 mb-4">
							<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
								<Filter class="w-5 h-5" />
								{$t('adventures.status_filter')}
							</h3>

							<div class="space-y-3">
								<div class="space-y-1">
									<label class="label cursor-pointer justify-start gap-3 py-1 min-h-0">
										<input
											type="radio"
											name="is_visited"
											class="radio radio-primary radio-sm"
											checked={isVisitedFilter === 'all'}
											on:change={() => updateVisitedFilter('all')}
										/>
										<span class="label-text">{$t('adventures.all')}</span>
									</label>
									<label class="label cursor-pointer justify-start gap-3 py-1 min-h-0">
										<input
											type="radio"
											name="is_visited"
											class="radio radio-primary radio-sm"
											checked={isVisitedFilter === 'true'}
											on:change={() => updateVisitedFilter('true')}
										/>
										<span class="label-text">{$t('adventures.visited')}</span>
									</label>
									<label class="label cursor-pointer justify-start gap-3 py-1 min-h-0">
										<input
											type="radio"
											name="is_visited"
											class="radio radio-primary radio-sm"
											checked={isVisitedFilter === 'false'}
											on:change={() => updateVisitedFilter('false')}
										/>
										<span class="label-text">{$t('adventures.not_visited')}</span>
									</label>
								</div>

								<div class="divider my-0"></div>

								<label class="label cursor-pointer justify-start gap-3 py-1 min-h-0">
									<input
										type="checkbox"
										id="include_collections"
										class="checkbox checkbox-primary checkbox-sm"
										checked={includeCollections}
										on:change={(e) => updateIncludeCollections(e.currentTarget.checked)}
									/>
									<span class="label-text">{$t('adventures.collection_locations')}</span>
								</label>
							</div>
						</div>

						<div class="card bg-base-200/50 p-4">
							<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
								<Sort class="w-5 h-5" />
								{$t('adventures.sort')}
							</h3>

							<div class="space-y-4">
								<div>
									<!-- svelte-ignore a11y-label-has-associated-control -->
									<label class="label">
										<span class="label-text font-medium">{$t('adventures.order_direction')}</span>
									</label>
									<div class="join w-full">
										<button
											type="button"
											class="join-item btn btn-sm flex-1 {orderDirection === 'asc'
												? 'btn-active'
												: ''}"
											on:click={() => updateSort(orderBy, 'asc')}
										>
											{$t('adventures.ascending')}
										</button>
										<button
											type="button"
											class="join-item btn btn-sm flex-1 {orderDirection === 'desc'
												? 'btn-active'
												: ''}"
											on:click={() => updateSort(orderBy, 'desc')}
										>
											{$t('adventures.descending')}
										</button>
									</div>
								</div>

								<div>
									<!-- svelte-ignore a11y-label-has-associated-control -->
									<label class="label">
										<span class="label-text font-medium">{$t('adventures.order_by')}</span>
									</label>
									<div class="space-y-1">
										<label class="label cursor-pointer justify-start gap-3 py-1 min-h-0">
											<input
												type="radio"
												name="order_by"
												class="radio radio-primary radio-sm"
												checked={orderBy === 'updated_at'}
												on:change={() => updateSort('updated_at', orderDirection)}
											/>
											<span class="label-text">{$t('adventures.updated')}</span>
										</label>
										<label class="label cursor-pointer justify-start gap-3 py-1 min-h-0">
											<input
												type="radio"
												name="order_by"
												class="radio radio-primary radio-sm"
												checked={orderBy === 'name'}
												on:change={() => updateSort('name', orderDirection)}
											/>
											<span class="label-text">{$t('adventures.name')}</span>
										</label>
										<label class="label cursor-pointer justify-start gap-3 py-1 min-h-0">
											<input
												type="radio"
												name="order_by"
												class="radio radio-primary radio-sm"
												checked={orderBy === 'date'}
												on:change={() => updateSort('date', orderDirection)}
											/>
											<span class="label-text">{$t('adventures.date')}</span>
										</label>
										<label class="label cursor-pointer justify-start gap-3 py-1 min-h-0">
											<input
												type="radio"
												name="order_by"
												class="radio radio-primary radio-sm"
												checked={orderBy === 'rating'}
												on:change={() => updateSort('rating', orderDirection)}
											/>
											<span class="label-text">{$t('adventures.rating')}</span>
										</label>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Floating Action Button -->
	<div class="fixed bottom-6 right-6 z-[999]">
		<div class="dropdown dropdown-top dropdown-end">
			<div
				tabindex="0"
				role="button"
				class="btn btn-primary btn-circle w-16 h-16 shadow-2xl hover:shadow-primary/25 transition-all duration-200"
			>
				<Plus class="w-8 h-8" />
			</div>
			<ul
				tabindex="-1"
				class="dropdown-content z-[40] menu p-4 shadow-2xl bg-base-100 rounded-2xl w-64 border border-base-300"
			>
				<div class="text-center mb-4">
					<h3 class="font-bold text-lg">{$t('adventures.create_new')}</h3>
				</div>
				<button
					class="btn btn-primary gap-2 w-full"
					on:click={() => {
						isLocationModalOpen = true;
						adventureToEdit = null;
					}}
				>
					<Compass class="w-5 h-5" />
					{$t('locations.location')}
				</button>
			</ul>
		</div>
	</div>
</div>
