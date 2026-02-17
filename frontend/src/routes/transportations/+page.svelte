<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import TransportationCard from '$lib/components/cards/TransportationCard.svelte';
	import TypeFilterDropdown from '$lib/components/TypeFilterDropdown.svelte';
	import type { Transportation } from '$lib/types';
	import { t } from 'svelte-i18n';
	import { TRANSPORTATION_TYPES_ICONS } from '$lib';
	import TransportationModal from '$lib/components/transportation/TransportationModal.svelte';
	import {
		Pagination,
		EntityListHeader,
		SortOptions,
		RadioFilter,
		RatingFilter,
		EmptyState,
		FloatingActionButton
	} from '$lib/components/shared/list';
	import { transportationTypes, fetchEntityTypes } from '$lib/stores/entityTypes';

	import Filter from '~icons/mdi/filter-variant';
	import Airplane from '~icons/mdi/airplane';
	import Eye from '~icons/mdi/eye';
	import MapMarker from '~icons/mdi/map-marker';

	export let data: any;

	onMount(() => {
		fetchEntityTypes();
	});

	let transportations: Transportation[] = data.props.transportations || [];
	let transportationBeingUpdated: Transportation | undefined = undefined;

	// Sync the transportationBeingUpdated with the transportations array
	$: {
		if (transportationBeingUpdated && transportationBeingUpdated.id) {
			const index = transportations.findIndex((t) => t.id === transportationBeingUpdated?.id);

			if (index !== -1) {
				transportations[index] = { ...transportationBeingUpdated };
				transportations = transportations;
			} else {
				transportations = [{ ...transportationBeingUpdated }, ...transportations];
				data.props.transportations = transportations;
			}
		}
	}

	let resultsPerPage: number = 25;
	let count = data.props.count || 0;
	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = 1;

	let typeString: string = '';
	let transportationToEdit: Transportation | null = null;
	let isTransportationModalOpen: boolean = false;
	let sidebarOpen = false;

	let currentSort = {
		order_by: 'updated_at',
		order: 'asc',
		includeCollections: true,
		is_visited: 'all',
		is_public: 'all',
		ownership: 'all',
		min_rating: 'all'
	};

	// Get type options from store first, fallback to hardcoded icons
	$: typeOptions = $transportationTypes.length > 0
		? $transportationTypes.map((type) => ({
				value: type.key,
				label: type.name,
				icon: type.icon
			}))
		: Object.entries(TRANSPORTATION_TYPES_ICONS).map(([value, icon]) => ({
				value,
				label: $t(`transportation.modes.${value}`),
				icon
			}));

	// Reactive statements - Only read from URL, don't write
	$: {
		if (typeof window !== 'undefined') {
			let url = new URL(window.location.href);
			let types = url.searchParams.get('types');
			if (types && types !== 'all') {
				typeString = types;
			} else {
				typeString = '';
			}
		}
	}

	$: {
		let url = new URL($page.url);
		let pageParam = url.searchParams.get('page');
		if (pageParam) {
			currentPage = parseInt(pageParam);
		}
	}

	$: {
		if (data.props.transportations) {
			transportations = data.props.transportations;
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
		currentSort.is_visited = url.searchParams.get('is_visited') || 'all';
		if (url.searchParams.get('include_collections') === 'true') {
			currentSort.includeCollections = true;
		} else if (url.searchParams.get('include_collections') === 'false') {
			currentSort.includeCollections = false;
		} else {
			currentSort.includeCollections = true;
		}
		currentSort.is_public = url.searchParams.get('is_public') || 'all';
		currentSort.ownership = url.searchParams.get('ownership') || 'all';
		currentSort.min_rating = url.searchParams.get('min_rating') || 'all';
	}

	function getVisitedCount() {
		return transportations.filter((t) => t.is_visited).length;
	}

	function getPlannedCount() {
		return transportations.filter((t) => !t.is_visited).length;
	}

	function handleChangePage(pageNumber: number) {
		currentPage = pageNumber;
		let url = new URL(window.location.href);
		url.searchParams.set('page', pageNumber.toString());
		transportations = [];
		transportations = data.props.transportations;
		goto(url.toString(), { invalidateAll: true, replaceState: true });
	}

	function deleteTransportation(event: CustomEvent<string>) {
		transportations = transportations.filter((t) => t.id !== event.detail);
		data.props.transportations = transportations;
		count = count - 1;
		data.props.count = count;
		totalPages = Math.ceil(count / resultsPerPage);
	}

	function editTransportation(event: CustomEvent<Transportation>) {
		transportationToEdit = event.detail;
		isTransportationModalOpen = true;
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function getTypeCount(type: string): number {
		return transportations.filter((t) => t.type === type).length;
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
		if (data.props.transportations) {
			transportations = data.props.transportations;
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
		if (data.props.transportations) {
			transportations = data.props.transportations;
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
		if (data.props.transportations) {
			transportations = data.props.transportations;
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
		if (data.props.transportations) {
			transportations = data.props.transportations;
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
		if (data.props.transportations) {
			transportations = data.props.transportations;
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
		if (data.props.transportations) {
			transportations = data.props.transportations;
			count = data.props.count;
		}
	}

	async function updateTypeFilter(event: CustomEvent<string>) {
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
		if (data.props.transportations) {
			transportations = data.props.transportations;
			count = data.props.count;
		}
	}
</script>

<svelte:head>
	<title>{$t('transportation.my_transportations') || 'My Transportations'}</title>
	<meta name="description" content="View and manage your transportations." />
</svelte:head>

{#if isTransportationModalOpen}
	<TransportationModal
		on:close={() => (isTransportationModalOpen = false)}
		user={data.user}
		transportationToEdit={transportationToEdit}
		bind:transportation={transportationBeingUpdated}
		collaborativeMode={data.collaborativeMode}
	/>
{/if}

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="my-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<EntityListHeader
				title={$t('transportation.my_transportations') || 'My Transportations'}
				subtitle="{count} {$t('adventures.transportations')}"
				icon={Airplane}
				{count}
				visitedCount={getVisitedCount()}
				plannedCount={getPlannedCount()}
				onToggleSidebar={toggleSidebar}
			/>

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-8">
				{#if transportations.length === 0}
					<EmptyState
						icon={Airplane}
						title={$t('transportation.no_transportations_found') || 'No transportations found'}
						message={$t('adventures.no_adventures_message')}
						buttonText={$t('transportation.create_transportation') || 'Create Transportation'}
						on:create={() => {
							transportationToEdit = null;
							isTransportationModalOpen = true;
						}}
					/>
				{:else}
					<!-- Transportations Grid -->
					<div
						class="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6"
					>
						{#each transportations as transportation}
							<TransportationCard
								user={data.user}
								{transportation}
								on:delete={deleteTransportation}
								on:edit={editTransportation}
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

					<!-- Filters -->
					<div class="space-y-2">
						<!-- Type Filter -->
						<TypeFilterDropdown
							bind:types={typeString}
							{typeOptions}
							on:change={updateTypeFilter}
							title={$t('transportation.type') || 'Type'}
							icon={Airplane}
						/>

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

						<RatingFilter
							minRating={currentSort.min_rating}
							on:change={(e) => updateRatingFilter(e.detail)}
						/>
					</div>
				</div>
			</div>
		</div>
	</div>

	<FloatingActionButton
		on:click={() => {
			isTransportationModalOpen = true;
			transportationToEdit = null;
		}}
	/>
</div>
