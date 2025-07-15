<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import CollectionCard from '$lib/components/CollectionCard.svelte';
	import CollectionLink from '$lib/components/CollectionLink.svelte';
	import CollectionModal from '$lib/components/CollectionModal.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Collection } from '$lib/types';
	import { t } from 'svelte-i18n';

	import Plus from '~icons/mdi/plus';
	import Filter from '~icons/mdi/filter-variant';
	import Sort from '~icons/mdi/sort';
	import Archive from '~icons/mdi/archive';
	import Share from '~icons/mdi/share-variant';
	import CollectionIcon from '~icons/mdi/folder-multiple';

	export let data: any;
	console.log('Collections page data:', data);

	let collections: Collection[] = data.props.adventures || [];
	let sharedCollections: Collection[] = data.props.sharedCollections || [];
	let archivedCollections: Collection[] = data.props.archivedCollections || [];

	let newType: string = '';
	let resultsPerPage: number = 25;
	let isShowingCollectionModal: boolean = false;
	let activeView: 'owned' | 'shared' | 'archived' = 'owned';

	let next: string | null = data.props.next || null;
	let previous: string | null = data.props.previous || null;
	let count = data.props.count || 0;
	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = data.props.currentPage || 1;
	let orderBy = data.props.order_by || 'updated_at';
	let orderDirection = data.props.order_direction || 'asc';

	let sidebarOpen = false;
	let collectionToEdit: Collection | null = null;

	$: currentCollections =
		activeView === 'owned'
			? collections
			: activeView === 'shared'
				? sharedCollections
				: activeView === 'archived'
					? archivedCollections
					: [];

	$: currentCount =
		activeView === 'owned'
			? collections.length
			: activeView === 'shared'
				? sharedCollections.length
				: activeView === 'archived'
					? archivedCollections.length
					: 0;

	// Optionally, keep count in sync with collections only for owned view
	$: {
		if (activeView === 'owned' && count !== collections.length) {
			count = collections.length;
		}
	}

	async function goToPage(pageNum: number) {
		const url = new URL($page.url);
		url.searchParams.set('page', pageNum.toString());
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			collections = data.props.adventures;
		}
		if (data.props.archivedCollections) {
			archivedCollections = data.props.archivedCollections;
		}
		currentPage = pageNum;
	}

	async function updateSort(by: string, direction: string) {
		const url = new URL($page.url);
		url.searchParams.set('order_by', by);
		url.searchParams.set('order_direction', direction);
		url.searchParams.set('page', '1'); // Reset to first page when sorting changes
		currentPage = 1;
		orderBy = by;
		orderDirection = direction;
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			collections = data.props.adventures;
		}
		if (data.props.archivedCollections) {
			archivedCollections = data.props.archivedCollections;
		}
	}

	function deleteCollection(event: CustomEvent<string>) {
		const collectionId = event.detail;
		collections = collections.filter((collection) => collection.id !== collectionId);
		sharedCollections = sharedCollections.filter((collection) => collection.id !== collectionId);
		archivedCollections = archivedCollections.filter(
			(collection) => collection.id !== collectionId
		);
	}

	function archiveCollection(event: CustomEvent<string>) {
		const collectionId = event.detail;
		console.log('Archiving collection with ID:', collectionId);
		// Find the collection in owned collections
		const collectionToArchive = collections.find((collection) => collection.id === collectionId);

		if (collectionToArchive) {
			// Remove from owned collections
			collections = collections.filter((collection) => collection.id !== collectionId);
			// Add to archived collections
			archivedCollections = [...archivedCollections, { ...collectionToArchive, is_archived: true }];
		}
	}

	function unarchiveCollection(event: CustomEvent<string>) {
		const collectionId = event.detail;
		// Find the collection in archived collections
		const collectionToUnarchive = archivedCollections.find(
			(collection) => collection.id === collectionId
		);

		if (collectionToUnarchive) {
			// Remove from archived collections
			archivedCollections = archivedCollections.filter(
				(collection) => collection.id !== collectionId
			);
			// Add to owned collections
			collections = [...collections, { ...collectionToUnarchive, is_archived: false }];
		}
	}

	function saveOrCreate(event: CustomEvent<Collection>) {
		if (collections.find((collection) => collection.id === event.detail.id)) {
			collections = collections.map((collection) => {
				if (collection.id === event.detail.id) {
					return event.detail;
				}
				return collection;
			});
		} else {
			collections = [event.detail, ...collections];
		}
		isShowingCollectionModal = false;
	}

	function editCollection(event: CustomEvent<Collection>) {
		collectionToEdit = event.detail;
		isShowingCollectionModal = true;
	}

	function saveEdit(event: CustomEvent<Collection>) {
		collections = collections.map((adventure) => {
			if (adventure.id === event.detail.id) {
				return event.detail;
			}
			return adventure;
		});
		isShowingCollectionModal = false;
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function switchView(view: 'owned' | 'shared' | 'archived') {
		activeView = view;
	}
</script>

<svelte:head>
	<title>Collections</title>
	<meta name="description" content="View your adventure collections." />
</svelte:head>

{#if isShowingCollectionModal}
	<CollectionModal
		{collectionToEdit}
		on:close={() => (isShowingCollectionModal = false)}
		on:saveEdit={saveEdit}
		on:save={saveOrCreate}
	/>
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
									<CollectionIcon class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-primary">
										{$t(`adventures.my_collections`)}
									</h1>
									<p class="text-sm text-base-content/60">
										{currentCount}
										{activeView === 'owned'
											? $t('navbar.collections')
											: activeView === 'shared'
												? $t('collection.shared_collections')
												: $t('adventures.archived_collections')}
									</p>
								</div>
							</div>
						</div>

						<!-- View Toggle -->
						<div class="tabs tabs-boxed bg-base-200">
							<button
								class="tab gap-2 {activeView === 'owned' ? 'tab-active' : ''}"
								on:click={() => switchView('owned')}
							>
								<CollectionIcon class="w-4 h-4" />
								<span class="hidden sm:inline">{$t('adventures.my_collections')}</span>
								<div
									class="badge badge-sm {activeView === 'owned' ? 'badge-primary' : 'badge-ghost'}"
								>
									{collections.length}
								</div>
							</button>
							<button
								class="tab gap-2 {activeView === 'shared' ? 'tab-active' : ''}"
								on:click={() => switchView('shared')}
							>
								<Share class="w-4 h-4" />
								<span class="hidden sm:inline">{$t('share.shared')}</span>
								<div
									class="badge badge-sm {activeView === 'shared' ? 'badge-primary' : 'badge-ghost'}"
								>
									{sharedCollections.length}
								</div>
							</button>
							<button
								class="tab gap-2 {activeView === 'archived' ? 'tab-active' : ''}"
								on:click={() => switchView('archived')}
							>
								<Archive class="w-4 h-4" />
								<span class="hidden sm:inline">{$t('adventures.archived')}</span>
								<div
									class="badge badge-sm {activeView === 'archived'
										? 'badge-primary'
										: 'badge-ghost'}"
								>
									{archivedCollections.length}
								</div>
							</button>
						</div>
					</div>
				</div>
			</div>

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-8">
				{#if currentCollections.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							{#if activeView === 'owned'}
								<CollectionIcon class="w-16 h-16 text-base-content/30" />
							{:else if activeView === 'shared'}
								<Share class="w-16 h-16 text-base-content/30" />
							{:else}
								<Archive class="w-16 h-16 text-base-content/30" />
							{/if}
						</div>
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{activeView === 'owned'
								? $t('collection.no_collections_yet')
								: activeView === 'shared'
									? $t('collection.no_shared_collections')
									: $t('collection.no_archived_collections')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md">
							{activeView === 'owned'
								? $t('collection.create_first')
								: activeView === 'shared'
									? $t('collection.make_sure_public')
									: $t('collection.archived_appear_here')}
						</p>
						{#if activeView === 'owned'}
							<button
								class="btn btn-primary btn-wide mt-6 gap-2"
								on:click={() => {
									collectionToEdit = null;
									isShowingCollectionModal = true;
									newType = 'visited';
								}}
							>
								<Plus class="w-5 h-5" />
								{$t('collection.create')}
							</button>
						{/if}
					</div>
				{:else}
					<!-- Collections Grid -->
					<div
						class="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6"
					>
						{#each currentCollections as collection}
							<CollectionCard
								type=""
								{collection}
								on:delete={deleteCollection}
								on:edit={editCollection}
								on:archive={archiveCollection}
								on:unarchive={unarchiveCollection}
								user={data.user}
							/>
						{/each}
					</div>

					<!-- Pagination -->
					{#if activeView === 'owned' && (next || previous)}
						<div class="flex justify-center mt-12">
							<div class="join bg-base-100 shadow-lg rounded-2xl p-2">
								{#each Array.from({ length: totalPages }, (_, i) => i + 1) as page}
									<button
										class="join-item btn btn-sm {currentPage === page
											? 'btn-primary'
											: 'btn-ghost'}"
										on:click={() => goToPage(page)}
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
			<label for="my-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<!-- Sidebar Header -->
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Sort class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('adventures.filters_and_sort')}</h2>
					</div>

					<!-- Sort Form - Updated to use URL navigation -->
					<div class="card bg-base-200/50 p-4">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Sort class="w-5 h-5" />
							{$t(`adventures.sort`)}
						</h3>

						<div class="space-y-4">
							<div>
								<!-- svelte-ignore a11y-label-has-associated-control -->
								<label class="label">
									<span class="label-text font-medium">{$t(`adventures.order_direction`)}</span>
								</label>
								<div class="join w-full">
									<button
										class="join-item btn btn-sm flex-1 {orderDirection === 'asc'
											? 'btn-active'
											: ''}"
										on:click={() => updateSort(orderBy, 'asc')}
									>
										{$t(`adventures.ascending`)}
									</button>
									<button
										class="join-item btn btn-sm flex-1 {orderDirection === 'desc'
											? 'btn-active'
											: ''}"
										on:click={() => updateSort(orderBy, 'desc')}
									>
										{$t(`adventures.descending`)}
									</button>
								</div>
							</div>

							<div>
								<!-- svelte-ignore a11y-label-has-associated-control -->
								<label class="label">
									<span class="label-text font-medium">{$t('adventures.order_by')}</span>
								</label>
								<div class="space-y-2">
									<label class="label cursor-pointer justify-start gap-3">
										<input
											type="radio"
											name="order_by_radio"
											class="radio radio-primary radio-sm"
											checked={orderBy === 'updated_at'}
											on:change={() => updateSort('updated_at', orderDirection)}
										/>
										<span class="label-text">{$t('adventures.updated')}</span>
									</label>
									<label class="label cursor-pointer justify-start gap-3">
										<input
											type="radio"
											name="order_by_radio"
											class="radio radio-primary radio-sm"
											checked={orderBy === 'start_date'}
											on:change={() => updateSort('start_date', orderDirection)}
										/>
										<span class="label-text">{$t('adventures.start_date')}</span>
									</label>
									<label class="label cursor-pointer justify-start gap-3">
										<input
											type="radio"
											name="order_by_radio"
											class="radio radio-primary radio-sm"
											checked={orderBy === 'name'}
											on:change={() => updateSort('name', orderDirection)}
										/>
										<span class="label-text">{$t('adventures.name')}</span>
									</label>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Floating Action Button -->
	{#if activeView === 'owned'}
		<div class="fixed bottom-6 right-6 z-50">
			<div class="dropdown dropdown-top dropdown-end">
				<div
					tabindex="0"
					role="button"
					class="btn btn-primary btn-circle w-16 h-16 shadow-2xl hover:shadow-primary/25 transition-all duration-200"
				>
					<Plus class="w-8 h-8" />
				</div>
				<ul
					class="dropdown-content z-[1] menu p-4 shadow-2xl bg-base-100 rounded-2xl w-64 border border-base-300"
				>
					<div class="text-center mb-4">
						<h3 class="font-bold text-lg">{$t(`adventures.create_new`)}</h3>
					</div>
					<button
						class="btn btn-primary gap-2 w-full"
						on:click={() => {
							collectionToEdit = null;
							isShowingCollectionModal = true;
							newType = 'visited';
						}}
					>
						<CollectionIcon class="w-5 h-5" />
						{$t(`adventures.collection`)}
					</button>
				</ul>
			</div>
		</div>
	{/if}
</div>
