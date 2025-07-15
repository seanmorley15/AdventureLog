<script lang="ts">
	import { enhance, deserialize } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import AdventureModal from '$lib/components/AdventureModal.svelte';
	import CategoryFilterDropdown from '$lib/components/CategoryFilterDropdown.svelte';
	import CategoryModal from '$lib/components/CategoryModal.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure, Category } from '$lib/types';
	import { t } from 'svelte-i18n';

	import Plus from '~icons/mdi/plus';
	import Filter from '~icons/mdi/filter-variant';
	import Sort from '~icons/mdi/sort';
	import MapMarker from '~icons/mdi/map-marker';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import Calendar from '~icons/mdi/calendar';
	import Star from '~icons/mdi/star';
	import Tag from '~icons/mdi/tag';
	import Compass from '~icons/mdi/compass';

	export let data: any;

	let adventures: Adventure[] = data.props.adventures || [];

	let currentSort = {
		order_by: '',
		order: '',
		visited: true,
		planned: true,
		includeCollections: true,
		is_visited: 'all'
	};

	let resultsPerPage: number = 25;
	let count = data.props.count || 0;
	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = 1;

	let is_category_modal_open: boolean = false;
	let typeString: string = '';
	let adventureToEdit: Adventure | null = null;
	let isAdventureModalOpen: boolean = false;
	let sidebarOpen = false;

	// Reactive statements
	$: {
		if (typeof window !== 'undefined') {
			let url = new URL(window.location.href);
			if (typeString) {
				url.searchParams.set('types', typeString);
			} else {
				url.searchParams.delete('types');
			}
			goto(url.toString(), { invalidateAll: true, replaceState: true });
		}
	}

	$: {
		if (typeof window !== 'undefined') {
			let url = new URL(window.location.href);
			let types = url.searchParams.get('types');
			if (types) {
				typeString = types;
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
		if (url.searchParams.get('include_collections') === 'on') {
			currentSort.includeCollections = true;
		} else {
			currentSort.includeCollections = false;
		}

		if (!currentSort.visited && !currentSort.planned) {
			currentSort.visited = true;
			currentSort.planned = true;
		}

		if (url.searchParams.get('is_visited')) {
			currentSort.is_visited = url.searchParams.get('is_visited') || 'all';
		}
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
	}

	function saveOrCreate(event: CustomEvent<Adventure>) {
		if (adventures.find((adventure) => adventure.id === event.detail.id)) {
			adventures = adventures.map((adventure) => {
				if (adventure.id === event.detail.id) {
					return event.detail;
				}
				return adventure;
			});
		} else {
			adventures = [event.detail, ...adventures];
		}
		isAdventureModalOpen = false;
	}

	function editAdventure(event: CustomEvent<Adventure>) {
		adventureToEdit = event.detail;
		isAdventureModalOpen = true;
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
	<title>{$t('navbar.adventures')}</title>
	<meta name="description" content="View your completed and planned adventures." />
</svelte:head>

{#if isAdventureModalOpen}
	<AdventureModal
		{adventureToEdit}
		on:close={() => (isAdventureModalOpen = false)}
		on:save={saveOrCreate}
	/>
{/if}

{#if is_category_modal_open}
	<CategoryModal on:close={() => (is_category_modal_open = false)} />
{/if}

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open p-[12px]">
		<input id="my-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

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
									<Compass class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-black">
										{$t('navbar.my_adventures')}
									</h1>
									<p class="text-sm text-base-content/60">
										{count}
										{$t('navbar.adventures')} • {getVisitedCount()}
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
							{$t('adventures.no_adventures_found')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md">
							{$t('adventures.no_adventures_message')}
						</p>
						<button
							class="btn btn-primary btn-wide mt-6 gap-2"
							on:click={() => {
								adventureToEdit = null;
								isAdventureModalOpen = true;
							}}
						>
							<Plus class="w-5 h-5" />
							{$t('adventures.create_adventure')}
						</button>
					</div>
				{:else}
					<!-- Adventures Grid -->
					<div
						class="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6"
					>
						{#each adventures as adventure}
							<AdventureCard
								user={data.user}
								{adventure}
								on:delete={deleteAdventure}
								on:edit={editAdventure}
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

					<!-- Filters Form -->
					<form method="get" class="space-y-6">
						<!-- Category Filter -->
						<div class="card bg-base-200/50 p-4">
							<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
								<Tag class="w-5 h-5" />
								Categories
							</h3>
							<CategoryFilterDropdown bind:types={typeString} />
							<button
								type="button"
								on:click={() => (is_category_modal_open = true)}
								class="btn btn-outline btn-sm w-full mt-3 gap-2"
							>
								<Tag class="w-4 h-4" />
								{$t('categories.manage_categories')}
							</button>
						</div>

						<!-- Sort Options -->
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
										<input
											class="join-item btn btn-sm flex-1"
											type="radio"
											name="order_direction"
											id="asc"
											value="asc"
											aria-label={$t('adventures.ascending')}
											checked={currentSort.order === 'asc'}
										/>
										<input
											class="join-item btn btn-sm flex-1"
											type="radio"
											name="order_direction"
											id="desc"
											value="desc"
											aria-label={$t('adventures.descending')}
											checked={currentSort.order === 'desc'}
										/>
									</div>
								</div>

								<div>
									<!-- svelte-ignore a11y-label-has-associated-control -->
									<label class="label">
										<span class="label-text font-medium">{$t('adventures.order_by')}</span>
									</label>
									<div class="grid grid-cols-2 gap-2">
										<label
											class="label cursor-pointer justify-start gap-2 p-2 rounded-lg hover:bg-base-300/50"
										>
											<input
												type="radio"
												name="order_by"
												value="updated_at"
												class="radio radio-primary radio-sm"
												checked={currentSort.order_by === 'updated_at'}
											/>
											<span class="label-text text-sm">{$t('adventures.updated')}</span>
										</label>
										<label
											class="label cursor-pointer justify-start gap-2 p-2 rounded-lg hover:bg-base-300/50"
										>
											<input
												type="radio"
												name="order_by"
												value="name"
												class="radio radio-primary radio-sm"
												checked={currentSort.order_by === 'name'}
											/>
											<span class="label-text text-sm">{$t('adventures.name')}</span>
										</label>
										<label
											class="label cursor-pointer justify-start gap-2 p-2 rounded-lg hover:bg-base-300/50"
										>
											<input
												type="radio"
												name="order_by"
												value="date"
												class="radio radio-primary radio-sm"
												checked={currentSort.order_by === 'date'}
											/>
											<span class="label-text text-sm">{$t('adventures.date')}</span>
										</label>
										<label
											class="label cursor-pointer justify-start gap-2 p-2 rounded-lg hover:bg-base-300/50"
										>
											<input
												type="radio"
												name="order_by"
												value="rating"
												class="radio radio-primary radio-sm"
												checked={currentSort.order_by === 'rating'}
											/>
											<span class="label-text text-sm">{$t('adventures.rating')}</span>
										</label>
									</div>
								</div>
							</div>
						</div>

						<!-- Visit Status Filter -->
						<div class="card bg-base-200/50 p-4">
							<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
								<Eye class="w-5 h-5" />
								{$t('adventures.visited')}
							</h3>
							<div class="join w-full">
								<input
									class="join-item btn btn-sm flex-1"
									type="radio"
									name="is_visited"
									id="all"
									value="all"
									aria-label={$t('adventures.all')}
									checked={currentSort.is_visited === 'all'}
								/>
								<input
									class="join-item btn btn-sm flex-1"
									type="radio"
									name="is_visited"
									id="true"
									value="true"
									aria-label={$t('adventures.visited')}
									checked={currentSort.is_visited === 'true'}
								/>
								<input
									class="join-item btn btn-sm flex-1"
									type="radio"
									name="is_visited"
									id="false"
									value="false"
									aria-label={$t('adventures.not_visited')}
									checked={currentSort.is_visited === 'false'}
								/>
							</div>
						</div>

						<!-- Sources Filter -->
						<div class="card bg-base-200/50 p-4">
							<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
								<MapMarker class="w-5 h-5" />
								{$t('adventures.sources')}
							</h3>
							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="checkbox"
									name="include_collections"
									id="include_collections"
									class="checkbox checkbox-primary"
									checked={currentSort.includeCollections}
								/>
								<span class="label-text">{$t('adventures.collection_adventures')}</span>
							</label>
						</div>

						<button type="submit" class="btn btn-primary w-full gap-2">
							<Filter class="w-4 h-4" />
							{$t('adventures.filter')}
						</button>
					</form>
				</div>
			</div>
		</div>
	</div>

	<!-- Floating Action Button -->
	<div class="fixed bottom-6 right-6 z-40">
		<div class="dropdown dropdown-top dropdown-end">
			<div
				tabindex="0"
				role="button"
				class="btn btn-primary btn-circle w-16 h-16 shadow-2xl hover:shadow-primary/25 transition-all duration-200"
			>
				<Plus class="w-8 h-8" />
			</div>
			<ul
				class="dropdown-content z-[40] menu p-4 shadow-2xl bg-base-100 rounded-2xl w-64 border border-base-300"
			>
				<div class="text-center mb-4">
					<h3 class="font-bold text-lg">{$t('adventures.create_new')}</h3>
				</div>
				<button
					class="btn btn-primary gap-2 w-full"
					on:click={() => {
						isAdventureModalOpen = true;
						adventureToEdit = null;
					}}
				>
					<Compass class="w-5 h-5" />
					{$t('adventures.adventure')}
				</button>
			</ul>
		</div>
	</div>
</div>
