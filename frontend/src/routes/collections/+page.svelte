<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import CollectionCard from '$lib/components/cards/CollectionCard.svelte';
	import CollectionLink from '$lib/components/CollectionLink.svelte';
	import CollectionModal from '$lib/components/CollectionModal.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Collection, CollectionInvite, SlimCollection } from '$lib/types';
	import { t } from 'svelte-i18n';

	import Plus from '~icons/mdi/plus';
	import Filter from '~icons/mdi/filter-variant';
	import Sort from '~icons/mdi/sort';
	import Archive from '~icons/mdi/archive';
	import Share from '~icons/mdi/share-variant';
	import CollectionIcon from '~icons/mdi/folder-multiple';
	import MailIcon from '~icons/mdi/email';
	import CheckIcon from '~icons/mdi/check';
	import CloseIcon from '~icons/mdi/close';
	import { addToast } from '$lib/toasts';
	import DeleteWarning from '$lib/components/DeleteWarning.svelte';

	export let data: any;
	console.log('Collections page data:', data);

	let collections: SlimCollection[] = data.props.adventures || [];
	let sharedCollections: SlimCollection[] = data.props.sharedCollections || [];
	let archivedCollections: SlimCollection[] = data.props.archivedCollections || [];

	let newType: string = '';
	let resultsPerPage: number = 25;
	let isShowingCollectionModal: boolean = false;
	let activeView: 'owned' | 'shared' | 'archived' | 'invites' = 'owned';

	let next: string | null = data.props.next || null;
	let previous: string | null = data.props.previous || null;
	let count = data.props.count || 0;
	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = data.props.currentPage || 1;
	let orderBy = data.props.order_by || 'updated_at';
	let orderDirection = data.props.order_direction || 'asc';
	let statusFilter = data.props.status || '';

	let invites: CollectionInvite[] = data.props.invites || [];

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
					: activeView === 'invites'
						? invites.length
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

	async function updateStatusFilter(status: string) {
		const url = new URL($page.url);
		if (status) {
			url.searchParams.set('status', status);
		} else {
			url.searchParams.delete('status');
		}
		url.searchParams.set('page', '1'); // Reset to first page when filter changes
		currentPage = 1;
		statusFilter = status;
		await goto(url.toString(), { invalidateAll: true, replaceState: true });
		if (data.props.adventures) {
			collections = data.props.adventures;
		}
	}

	let importInputEl: HTMLInputElement | null = null;
	let importFormEl: HTMLFormElement | null = null;
	let isImporting: boolean = false;

	function triggerImport() {
		importInputEl?.click();
	}

	async function handleImportFileChange(event: Event) {
		const target = event.currentTarget as HTMLInputElement;
		const file = target.files && target.files[0];
		if (!file) return;
		isImporting = true;
		// Submit the hidden form to server action
		importFormEl?.requestSubmit();
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

	function saveOrCreate(event: CustomEvent<SlimCollection>) {
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

	function duplicateCollectionInList(event: CustomEvent<SlimCollection | Collection>) {
		const duplicatedCollection = event.detail as SlimCollection;

		collections = [
			duplicatedCollection,
			...collections.filter((collection) => collection.id !== duplicatedCollection.id)
		];

		archivedCollections = archivedCollections.filter(
			(collection) => collection.id !== duplicatedCollection.id
		);

		activeView = 'owned';
	}

	async function editCollection(event: CustomEvent<SlimCollection>) {
		const slim = event.detail;
		try {
			const res = await fetch(`/api/collections/${slim.id}?nested=true`);
			if (res.ok) {
				collectionToEdit = (await res.json()) as Collection;
			} else {
				collectionToEdit = slim as unknown as Collection;
			}
		} catch (e) {
			collectionToEdit = slim as unknown as Collection;
		}
		isShowingCollectionModal = true;
	}

	let isShowingConfirmLeaveModal: boolean = false;
	let collectionIdToLeave: string | null = null;

	async function leaveCollection() {
		let res = await fetch(`/api/collections/${collectionIdToLeave}/leave`, {
			method: 'POST'
		});
		if (res.ok) {
			addToast('info', $t('adventures.left_collection_message'));
			// Remove from shared collections
			sharedCollections = sharedCollections.filter(
				(collection) => collection.id !== collectionIdToLeave
			);
			// Optionally, you can also remove from owned collections if needed
			collections = collections.filter((collection) => collection.id !== collectionIdToLeave);
		} else {
			console.log('Error leaving collection');
		}
	}

	function saveEdit(event: CustomEvent<SlimCollection>) {
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

	function switchView(view: 'owned' | 'shared' | 'archived' | 'invites') {
		activeView = view;
	}

	// Invite functions
	async function acceptInvite(invite: CollectionInvite) {
		try {
			const res = await fetch(`/api/collections/${invite.collection}/accept-invite/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			if (res.ok) {
				// Try to parse returned collection data
				let data: any = null;
				try {
					data = await res.json();
				} catch (e) {
					data = null;
				}

				// Remove invite from list
				invites = invites.filter((i) => i.id !== invite.id);
				addToast('success', `${$t('invites.accepted')} "${invite.name}"`);

				// If API returned the accepted collection, add it to sharedCollections immediately
				if (data && (data.collection || data.result || data.id)) {
					// Normalize expected shapes: {collection: {...}} or collection object directly
					const newCollection = data.collection ? data.collection : data;
					// Prepend so it's visible at top
					sharedCollections = [newCollection as SlimCollection, ...sharedCollections];
				} else {
					// Fallback: refresh shared collections from API
					try {
						const sharedRes = await fetch(`/api/collections/shared/?nested=true`);
						if (sharedRes.ok) {
							const sharedData = await sharedRes.json();
							// Prefer results if paginated
							sharedCollections = sharedData.results ? sharedData.results : sharedData;
						}
					} catch (e) {
						// ignore fallback errors; user already got success toast
					}
				}
			} else {
				const error = await res.json();
				addToast('error', error.error || $t('invites.accept_failed'));
			}
		} catch (error) {
			addToast('error', $t('invites.accept_failed'));
		}
	}

	async function declineInvite(invite: CollectionInvite) {
		try {
			const res = await fetch(`/api/collections/${invite.collection}/decline-invite/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			if (res.ok) {
				// Remove invite from list
				invites = invites.filter((i) => i.id !== invite.id);
				addToast('success', `${$t('invites.declined')} "${invite.name}"`);
			} else {
				const error = await res.json();
				addToast('error', error.error || $t('invites.decline_failed'));
			}
		} catch (error) {
			addToast('error', $t('invites.decline_failed'));
		}
	}

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString();
	}
</script>

<svelte:head>
	<title>Collections</title>
	<meta name="description" content="View your adventure collections." />
</svelte:head>

{#if isShowingConfirmLeaveModal}
	<DeleteWarning
		title={$t('adventures.leave_collection')}
		button_text={$t('adventures.leave')}
		description={$t('adventures.leave_collection_warning')}
		is_warning={true}
		on:close={() => (isShowingConfirmLeaveModal = false)}
		on:confirm={leaveCollection}
	/>
{/if}

{#if isShowingCollectionModal}
	<CollectionModal
		{collectionToEdit}
		on:close={() => (isShowingCollectionModal = false)}
		on:saveEdit={saveEdit}
		on:save={saveOrCreate}
	/>
{/if}

<!-- Import progress modal -->
{#if isImporting}
	<dialog id="import_modal" class="modal modal-open">
		<div class="modal-box">
			<h3 class="font-bold text-lg">{$t('adventures.importing') || 'Importing collection...'}</h3>
			<div class="mt-4 flex items-center gap-3">
				<span class="loading loading-dots loading-md"></span>
				<span class="text-sm text-base-content/70"
					>{$t('adventures.in_progress') || 'In progress'}</span
				>
			</div>
		</div>
	</dialog>
{/if}

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="my-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

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
									<CollectionIcon class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-primary">
										{activeView === 'invites'
											? $t('invites.title')
											: $t(`adventures.my_collections`)}
									</h1>
									<p class="text-sm text-base-content/60">
										{currentCount}
										{activeView === 'owned'
											? $t('navbar.collections')
											: activeView === 'shared'
												? $t('collection.shared_collections')
												: activeView === 'archived'
													? $t('adventures.archived_collections')
													: $t('invites.pending_invites')}
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
							<button
								class="tab gap-2 {activeView === 'invites' ? 'tab-active' : ''}"
								on:click={() => switchView('invites')}
							>
								<div class="indicator">
									<MailIcon class="w-4 h-4" />
									{#if invites.length > 0}
										<span class="indicator-item badge badge-xs badge-error"></span>
									{/if}
								</div>
								<span class="hidden sm:inline">{$t('invites.title')}</span>
								<div
									class="badge badge-sm {activeView === 'invites'
										? 'badge-primary'
										: invites.length > 0
											? 'badge-error'
											: 'badge-ghost'}"
								>
									{invites.length}
								</div>
							</button>
						</div>
					</div>
				</div>
			</div>

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-8">
				{#if activeView === 'invites'}
					<!-- Invites Content -->
					{#if invites.length === 0}
						<div class="flex flex-col items-center justify-center py-16">
							<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
								<MailIcon class="w-16 h-16 text-base-content/30" />
							</div>
							<h3 class="text-xl font-semibold text-base-content/70 mb-2">
								{$t('invites.no_invites')}
							</h3>
							<p class="text-base-content/50 text-center max-w-md">
								{$t('invites.no_invites_desc')}
							</p>
						</div>
					{:else}
						<div class="space-y-4">
							{#each invites as invite}
								<div
									class="card bg-base-100 shadow-lg border border-base-300 hover:shadow-xl transition-shadow"
								>
									<div class="card-body p-6">
										<div class="flex items-start justify-between">
											<div class="flex-1">
												<div class="flex items-center gap-3 mb-2">
													<div class="p-2 bg-primary/10 rounded-lg">
														<CollectionIcon class="w-5 h-5 text-primary" />
													</div>
													<div>
														<h3 class="font-semibold text-lg">
															{invite.name}
														</h3>
														<p class="text-xs text-base-content/50">
															{$t('invites.invited_on')}
															{formatDate(invite.created_at)}
															{$t('invites.by')}
															{invite.collection_owner_username || ''}
															({invite.collection_user_first_name || ''}
															{invite.collection_user_last_name || ''})
														</p>
													</div>
												</div>
											</div>
											<div class="flex gap-2 ml-4">
												<button
													class="btn btn-success btn-sm gap-2"
													on:click={() => acceptInvite(invite)}
												>
													<CheckIcon class="w-4 h-4" />
													{$t('invites.accept')}
												</button>
												<button
													class="btn btn-error btn-sm btn-outline gap-2"
													on:click={() => declineInvite(invite)}
												>
													<CloseIcon class="w-4 h-4" />
													{$t('invites.decline')}
												</button>
											</div>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				{:else if currentCollections.length === 0}
					<!-- Empty State for Collections -->
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
						class="grid grid-cols-1 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6"
					>
						{#each currentCollections as collection (collection.id)}
							<CollectionCard
								type=""
								{collection}
								on:delete={deleteCollection}
								on:edit={editCollection}
								on:archive={archiveCollection}
								on:unarchive={unarchiveCollection}
								on:duplicate={duplicateCollectionInList}
								user={data.user}
								on:leave={(e) => {
									collectionIdToLeave = e.detail;
									isShowingConfirmLeaveModal = true;
								}}
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

					<!-- Only show sort options for collection views, not invites -->
					{#if activeView !== 'invites'}
						<!-- Status Filter -->
						<div class="card bg-base-200/50 p-4 mb-4">
							<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
								<Filter class="w-5 h-5" />
								{$t('adventures.status_filter')}
							</h3>

							<div class="space-y-2">
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="radio"
										name="status_filter"
										class="radio radio-primary radio-sm"
										checked={statusFilter === ''}
										on:change={() => updateStatusFilter('')}
									/>
									<span class="label-text">{$t('adventures.all')}</span>
								</label>
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="radio"
										name="status_filter"
										class="radio radio-primary radio-sm"
										checked={statusFilter === 'folder'}
										on:change={() => updateStatusFilter('folder')}
									/>
									<span class="label-text">📁 {$t('adventures.folder')}</span>
								</label>
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="radio"
										name="status_filter"
										class="radio radio-primary radio-sm"
										checked={statusFilter === 'upcoming'}
										on:change={() => updateStatusFilter('upcoming')}
									/>
									<span class="label-text">🚀 {$t('adventures.upcoming')}</span>
								</label>
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="radio"
										name="status_filter"
										class="radio radio-primary radio-sm"
										checked={statusFilter === 'in_progress'}
										on:change={() => updateStatusFilter('in_progress')}
									/>
									<span class="label-text">🎯 {$t('adventures.in_progress')}</span>
								</label>
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="radio"
										name="status_filter"
										class="radio radio-primary radio-sm"
										checked={statusFilter === 'completed'}
										on:change={() => updateStatusFilter('completed')}
									/>
									<span class="label-text">✓ {$t('adventures.completed')}</span>
								</label>
							</div>
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
					{/if}
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
					<div class="divider my-2"></div>
					<button class="btn btn-neutral gap-2 w-full" on:click={triggerImport}>
						<Archive class="w-5 h-5" />
						{$t('adventures.import_from_file')}
					</button>
					<form
						bind:this={importFormEl}
						method="POST"
						action="?/restoreData"
						enctype="multipart/form-data"
						use:enhance={({}) => {
							return ({ result }) => {
								isImporting = false;
								if (result?.type === 'success') {
									addToast('success', $t('adventures.import_success') || 'Imported collection');
									// Delay refresh by 1 second to let the success state be visible
									setTimeout(() => {
										window.location.reload();
									}, 1000);
								} else if (result?.type === 'failure') {
									addToast('error', $t('adventures.import_failed') || 'Import failed');
								}
							};
						}}
					>
						<input
							bind:this={importInputEl}
							type="file"
							name="file"
							accept=".zip"
							class="hidden"
							on:change={handleImportFileChange}
						/>
					</form>
				</ul>
			</div>
		</div>
	{/if}
</div>
