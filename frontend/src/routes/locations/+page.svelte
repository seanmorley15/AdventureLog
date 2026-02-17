<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import LocationCard from '$lib/components/cards/LocationCard.svelte';
	import CategoryFilterDropdown from '$lib/components/CategoryFilterDropdown.svelte';
	import CategoryModal from '$lib/components/CategoryModal.svelte';
	import type { Location } from '$lib/types';
	import { t } from 'svelte-i18n';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';
	import {
		Pagination,
		EntityListHeader,
		SortOptions,
		RadioFilter,
		RatingFilter,
		EmptyState,
		FloatingActionButton
	} from '$lib/components/shared/list';

	import Plus from '~icons/mdi/plus';
	import Filter from '~icons/mdi/filter-variant';
	import MapMarker from '~icons/mdi/map-marker';
	import Eye from '~icons/mdi/eye';
	import Tag from '~icons/mdi/tag';
	import Compass from '~icons/mdi/compass';

	export let data: any;

	let adventures: Location[] = data.props.adventures || [];

	let currentSort = {
		order_by: '',
		order: '',
		visited: true,
		planned: true,
		includeCollections: true,
		is_visited: 'all',
		is_public: 'all',
		ownership: 'all',
		min_rating: 'all'
	};

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
				data.props.adventures = adventures; // Update data.props.adventures as well
			}
		}
	}

	let resultsPerPage: number = 25;
	let count = data.props.count || 0;
	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = 1;

	let is_category_modal_open: boolean = false;
	let typeString: string = '';
	let adventureToEdit: Location | null = null;
	let isLocationModalOpen: boolean = false;
	let sidebarOpen = false;


	// Reactive statements - Only read from URL, don't write
	$: {
		if (typeof window !== 'undefined') {
			let url = new URL(window.location.href);
			let types = url.searchParams.get('types');
			if (types) {
				typeString = types;
			} else {
				typeString = '';
			}
		}
	}

	$: {
		let url = new URL($page.url);
		let page = url.searchParams.get('page');
		if (page) {
			currentPage = parseInt(page);
		}
	}

	$: {
		if (data.props.adventures) {
			adventures = data.props.adventures;
		}
		if (data.props.count) {
			count = data.props.count;
			totalPages = Math.ceil(count / resultsPerPage);
		}
	}

	$: {
		let url = new URL($page.url);
		currentSort.order_by = url.searchParams.get('order_by') || 'updated_at';
		currentSort.order = url.searchParams.get('order_direction') || 'asc';

		if (url.searchParams.get('planned') === 'on') {
			currentSort.planned = true;
		} else {
			currentSort.planned = false;
		}
		if (url.searchParams.get('visited') === 'on') {
			currentSort.visited = true;
		} else {
			currentSort.visited = false;
		}
		if (url.searchParams.get('include_collections') === 'true') {
			currentSort.includeCollections = true;
		} else if (url.searchParams.get('include_collections') === 'false') {
			currentSort.includeCollections = false;
		} else {
			// Default to true when no parameter is present (first visit)
			currentSort.includeCollections = true;
		}

		if (!currentSort.visited && !currentSort.planned) {
			currentSort.visited = true;
			currentSort.planned = true;
		}

		if (url.searchParams.get('is_visited')) {
			currentSort.is_visited = url.searchParams.get('is_visited') || 'all';
		}
		currentSort.is_public = url.searchParams.get('is_public') || 'all';
		currentSort.ownership = url.searchParams.get('ownership') || 'all';
		currentSort.min_rating = url.searchParams.get('min_rating') || 'all';
	}

	function handleChangePage(pageNumber: number) {
		currentPage = pageNumber;
		let url = new URL(window.location.href);
		url.searchParams.set('page', pageNumber.toString());
		adventures = [];
		adventures = data.props.adventures;
		goto(url.toString(), { invalidateAll: true, replaceState: true });
	}

	function deleteAdventure(event: CustomEvent<string>) {
		adventures = adventures.filter((adventure) => adventure.id !== event.detail);
		data.props.adventures = adventures;
		count = count - 1;
		data.props.count = count;
		totalPages = Math.ceil(count / resultsPerPage);
	}

	function editAdventure(event: CustomEvent<Location>) {
		adventureToEdit = event.detail;
		isLocationModalOpen = true;
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

	// Dynamic filter functions (like collections)
	async function updateSort(orderBy: string, orderDirection: string) {
		const url = new URL($page.url);
		url.searchParams.set('order_by', orderBy);
		url.searchParams.set('order_direction', orderDirection);
		url.searchParams.set('page', '1');
		currentPage = 1;
		currentSort.order_by = orderBy;
		currentSort.order = orderDirection;
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			adventures = data.props.adventures;
			count = data.props.count;
		}
	}

	async function updateVisitedFilter(isVisited: string) {
		const url = new URL($page.url);
		url.searchParams.set('is_visited', isVisited);
		url.searchParams.set('page', '1');
		currentPage = 1;
		currentSort.is_visited = isVisited;
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			adventures = data.props.adventures;
			count = data.props.count;
		}
	}

	async function updateVisibilityFilter(visibility: string) {
		const url = new URL($page.url);
		if (visibility && visibility !== 'all') {
			url.searchParams.set('is_public', visibility);
		} else {
			url.searchParams.delete('is_public');
		}
		url.searchParams.set('page', '1');
		currentPage = 1;
		currentSort.is_public = visibility;
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			adventures = data.props.adventures;
			count = data.props.count;
		}
	}

	async function updateOwnershipFilter(ownership: string) {
		const url = new URL($page.url);
		if (ownership && ownership !== 'all') {
			url.searchParams.set('ownership', ownership);
		} else {
			url.searchParams.delete('ownership');
		}
		url.searchParams.set('page', '1');
		currentPage = 1;
		currentSort.ownership = ownership;
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			adventures = data.props.adventures;
			count = data.props.count;
		}
	}

	async function updateRatingFilter(minRating: string) {
		const url = new URL($page.url);
		if (minRating && minRating !== 'all') {
			url.searchParams.set('min_rating', minRating);
		} else {
			url.searchParams.delete('min_rating');
		}
		url.searchParams.set('page', '1');
		currentPage = 1;
		currentSort.min_rating = minRating;
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			adventures = data.props.adventures;
			count = data.props.count;
		}
	}

	async function updateIncludeCollections(include: boolean) {
		const url = new URL($page.url);
		url.searchParams.set('include_collections', include.toString());
		url.searchParams.set('page', '1');
		currentPage = 1;
		currentSort.includeCollections = include;
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			adventures = data.props.adventures;
			count = data.props.count;
		}
	}

	async function updateCategoryFilter(event: CustomEvent<string>) {
		const types = event.detail;
		const url = new URL($page.url);
		if (types) {
			url.searchParams.set('types', types);
		} else {
			url.searchParams.delete('types');
		}
		url.searchParams.set('page', '1');
		currentPage = 1;
		typeString = types;
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			adventures = data.props.adventures;
			count = data.props.count;
		}
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
		collaborativeMode={data.collaborativeMode}
	/>
{/if}

{#if is_category_modal_open}
	<CategoryModal
		on:close={() => (is_category_modal_open = false)}
		collaborativeMode={data.collaborativeMode}
	/>
{/if}

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="my-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<EntityListHeader
				title={$t('locations.my_locations')}
				subtitle="{count} {$t('locations.locations')} • {getVisitedCount()} {$t('adventures.visited')} • {getPlannedCount()} {$t('adventures.planned')}"
				icon={Compass}
				{count}
				visitedCount={getVisitedCount()}
				plannedCount={getPlannedCount()}
				onToggleSidebar={toggleSidebar}
			/>

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-8">
				{#if adventures.length === 0}
					<EmptyState
						icon={Compass}
						title={$t('adventures.no_locations_found')}
						message={$t('adventures.no_adventures_message')}
						buttonText={$t('adventures.create_location')}
						on:create={() => {
							adventureToEdit = null;
							isLocationModalOpen = true;
						}}
					/>
				{:else}
					<!-- Adventures Grid -->
					<div
						class="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6"
					>
						{#each adventures as adventure}
							<LocationCard
								user={data.user}
								{adventure}
								on:delete={deleteAdventure}
								on:edit={editAdventure}
							/>
						{/each}
					</div>

					<!-- Pagination -->
					<Pagination {currentPage} {totalPages} on:changePage={(e) => handleChangePage(e.detail)} />
				{/if}
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-30">
			<label for="my-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<!-- Sidebar Header -->
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Filter class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('adventures.filters_and_sort')}</h2>
					</div>

					<!-- Filters (Dynamic like collections) -->
					<div class="space-y-2">
						<!-- Category Filter -->
						<CategoryFilterDropdown
							bind:types={typeString}
							on:change={updateCategoryFilter}
							title={$t('adventures.categories')}
							icon={Tag}
						>
							<button
								type="button"
								on:click={() => (is_category_modal_open = true)}
								class="btn btn-outline btn-sm w-full mt-3 gap-2"
							>
								<Tag class="w-4 h-4" />
								{$t('categories.manage_categories')}
							</button>
						</CategoryFilterDropdown>

						<SortOptions
							orderBy={currentSort.order_by}
							orderDirection={currentSort.order}
							orderByOptions={[
								{ value: 'updated_at', label: $t('adventures.updated') },
								{ value: 'name', label: $t('adventures.name') },
								{ value: 'last_visit', label: $t('adventures.last_visit') },
								{ value: 'created_at', label: $t('adventures.created_at') },
								{ value: 'rating', label: $t('adventures.rating') }
							]}
							on:change={(e) => updateSort(e.detail.orderBy, e.detail.orderDirection)}
						/>

						<RadioFilter
							title={$t('adventures.visited')}
							icon={Eye}
							value={currentSort.is_visited}
							name="visited_filter"
							options={[
								{ value: 'all', label: $t('adventures.all') },
								{ value: 'true', label: $t('adventures.visited') },
								{ value: 'false', label: $t('adventures.not_visited') }
							]}
							on:change={(e) => updateVisitedFilter(e.detail)}
						/>

						<!-- Sources Filter -->
						<div class="collapse collapse-arrow bg-base-200/50 rounded-box">
							<input type="checkbox" checked />
							<div class="collapse-title font-medium flex items-center gap-2 py-2 min-h-0">
								<MapMarker class="w-5 h-5" />
								{$t('adventures.sources')}
							</div>
							<div class="collapse-content !pb-2">
								<label class="flex items-center gap-2 cursor-pointer py-0.5">
									<input
										type="checkbox"
										class="checkbox checkbox-primary checkbox-sm"
										checked={currentSort.includeCollections}
										on:change={(e) => updateIncludeCollections(e.currentTarget.checked)}
									/>
									<span>{$t('adventures.collection_locations')}</span>
								</label>
							</div>
						</div>

						<RatingFilter
							minRating={currentSort.min_rating}
							on:change={(e) => updateRatingFilter(e.detail)}
						/>

						<!-- Visibility and Ownership Filters (collaborative mode only) -->
						{#if data.collaborativeMode}
							<RadioFilter
								title={$t('adventures.visibility')}
								icon={Eye}
								value={currentSort.is_public}
								name="visibility_filter"
								options={[
									{ value: 'all', label: $t('adventures.all') },
									{ value: 'true', label: $t('adventures.public') },
									{ value: 'false', label: $t('adventures.private') }
								]}
								on:change={(e) => updateVisibilityFilter(e.detail)}
							/>

							<RadioFilter
								title={$t('adventures.ownership_filter')}
								icon={Eye}
								value={currentSort.ownership}
								name="ownership_filter"
								options={[
									{ value: 'all', label: $t('adventures.all') },
									{ value: 'mine', label: $t('adventures.my_locations') },
									{ value: 'public', label: $t('adventures.public_locations') }
								]}
								on:change={(e) => updateOwnershipFilter(e.detail)}
							/>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>

	<FloatingActionButton
		on:click={() => {
			isLocationModalOpen = true;
			adventureToEdit = null;
		}}
	/>
</div>
