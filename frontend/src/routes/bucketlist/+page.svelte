<script lang="ts">
	// Icons
	import Plus from '~icons/mdi/plus';
	import CheckCircle from '~icons/mdi/check-circle';
	import ProgressClock from '~icons/mdi/progress-clock';
	import ClockOutline from '~icons/mdi/clock-outline';
	import Target from '~icons/mdi/target';
	import FormatListChecks from '~icons/mdi/format-list-checks';
	import Delete from '~icons/mdi/delete';
	import Pencil from '~icons/mdi/pencil';
	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Filter from '~icons/mdi/filter-variant';
	import Trophy from '~icons/mdi/trophy';
	import Tag from '~icons/mdi/tag';
	import type { BucketListItem } from '$lib/types';
	import BucketListModal from '$lib/components/BucketListModal.svelte';

	export let data: any;

	let bucketItems: BucketListItem[] = data.props?.bucketItems || [];
	let statusFilter = 'all';
	let searchQuery = '';
	let sidebarOpen = false;
	let showModal = false;
	let editingItem: BucketListItem | null = null;

	$: filteredItems = filterItems(bucketItems, searchQuery, statusFilter);
	$: completedCount = bucketItems.filter((item) => item.status === 'completed').length;
	$: inProgressCount = bucketItems.filter((item) => item.status === 'in_progress').length;
	$: plannedCount = bucketItems.filter((item) => item.status === 'planned').length;
	$: totalCount = bucketItems.length || 1;
	$: completionPercentage = Math.round((completedCount / totalCount) * 100);

	const statusOptions = [
		{ value: 'all', label: 'All', icon: FormatListChecks },
		{ value: 'planned', label: 'Planned', icon: ClockOutline },
		{ value: 'in_progress', label: 'In Progress', icon: ProgressClock },
		{ value: 'completed', label: 'Completed', icon: CheckCircle }
	];

	function filterItems(items: BucketListItem[], query: string, status: string): BucketListItem[] {
		let filtered = items;

		if (query) {
			const lowerQuery = query.toLowerCase();
			filtered = filtered.filter(
				(item) =>
					item.title.toLowerCase().includes(lowerQuery) ||
					item.description?.toLowerCase().includes(lowerQuery) ||
					item.tags?.some((tag) => tag.toLowerCase().includes(lowerQuery))
			);
		}

		if (status !== 'all') {
			filtered = filtered.filter((item) => item.status === status);
		}

		return filtered;
	}

	function clearFilters() {
		searchQuery = '';
		statusFilter = 'all';
	}

	function getStatusBadgeClass(status: string): string {
		switch (status) {
			case 'completed':
				return 'badge-success';
			case 'in_progress':
				return 'badge-warning';
			default:
				return 'badge-info';
		}
	}

	function getStatusLabel(status: string): string {
		switch (status) {
			case 'completed':
				return 'Completed';
			case 'in_progress':
				return 'In Progress';
			default:
				return 'Planned';
		}
	}

	function openCreateModal() {
		editingItem = null;
		showModal = true;
	}

	function openEditModal(item: BucketListItem) {
		editingItem = item;
		showModal = true;
	}

	function handleModalClose() {
		showModal = false;
		editingItem = null;
	}

	async function handleDelete(itemId: string) {
		if (!confirm('Are you sure you want to delete this item?')) {
			return;
		}

		try {
			const response = await fetch(`/api/bucketlist/items/${itemId}`, {
				method: 'DELETE'
			});

			if (!response.ok) {
				throw new Error('Failed to delete item');
			}

			// Remove item from list
			bucketItems = bucketItems.filter((item) => item.id !== itemId);
		} catch (err) {
			alert(err instanceof Error ? err.message : 'Failed to delete item');
		}
	}
</script>

<svelte:head>
	<title>Bucket List - Track Your Travel Goals</title>
	<meta
		name="description"
		content="Track your travel goals and dream experiences with your bucket list."
	/>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="bucket-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<!-- Header Section -->
			<div class="sticky top-0 z-40 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4">
							<button
								class="btn btn-ghost btn-square lg:hidden"
								on:click={() => (sidebarOpen = !sidebarOpen)}
							>
								<Filter class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-xl">
									<Target class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-primary">Bucket List</h1>
									<p class="text-sm text-base-content/60">
										{filteredItems.length} of {bucketItems.length} items
									</p>
								</div>
							</div>
						</div>

						<!-- Completion Badge & Add Button -->
						<div class="hidden md:flex items-center gap-3">
							{#if completionPercentage === 100 && bucketItems.length > 0}
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
							<button class="btn btn-primary gap-2" on:click={openCreateModal}>
								<Plus class="w-5 h-5" />
								Add Item
							</button>
						</div>
					</div>

					<!-- Search and Filters -->
					<div class="mt-4 flex items-center gap-4">
						<div class="relative flex-1 max-w-md">
							<Search
								class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-base-content/40"
							/>
							<input
								type="text"
								placeholder="Search bucket list..."
								class="input input-bordered w-full pl-10 pr-10 bg-base-100/80"
								bind:value={searchQuery}
							/>
							{#if searchQuery}
								<button
									class="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content"
									on:click={() => (searchQuery = '')}
								>
									<Clear class="w-4 h-4" />
								</button>
							{/if}
						</div>
						<button class="btn btn-primary gap-2 md:hidden" on:click={openCreateModal}>
							<Plus class="w-5 h-5" />
						</button>
					</div>

					<!-- Filter Chips -->
					<div class="mt-4 flex flex-wrap items-center gap-2">
						<span class="text-sm font-medium text-base-content/60">Filter by:</span>
						<div class="tabs tabs-boxed bg-base-200">
							{#each statusOptions as option}
								<button
									class="tab tab-sm gap-2 {statusFilter === option.value ? 'tab-active' : ''}"
									on:click={() => (statusFilter = option.value)}
								>
									<svelte:component this={option.icon} class="w-3 h-3" />
									{option.label}
									{#if option.value !== 'all'}
										<span class="badge badge-xs">
											{bucketItems.filter((item) => item.status === option.value).length}
										</span>
									{/if}
								</button>
							{/each}
						</div>

						{#if searchQuery || statusFilter !== 'all'}
							<button class="btn btn-ghost btn-xs gap-1" on:click={clearFilters}>
								<Clear class="w-3 h-3" />
								Clear all
							</button>
						{/if}
					</div>
				</div>
			</div>

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-8">
				{#if filteredItems.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							<Target class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{bucketItems.length === 0 ? 'No bucket list items yet' : 'No items found'}
						</h3>
						<p class="text-base-content/50 text-center max-w-md mb-6">
							{bucketItems.length === 0
								? 'Start tracking your travel dreams and goals!'
								: 'Try adjusting your filters or search query.'}
						</p>
						{#if bucketItems.length === 0}
							<button class="btn btn-primary gap-2" on:click={openCreateModal}>
								<Plus class="w-4 h-4" />
								Add Your First Item
							</button>
						{:else}
							<button class="btn btn-primary gap-2" on:click={clearFilters}>
								<Clear class="w-4 h-4" />
								Clear Filters
							</button>
						{/if}
					</div>
				{:else}
					<!-- Items Grid -->
					<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
						{#each filteredItems as item (item.id)}
							<div
								class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all border border-base-300"
							>
								<div class="card-body">
									<div class="flex items-start justify-between gap-2 mb-2">
										<h3 class="card-title text-lg flex-1">{item.title}</h3>
										<span class="badge {getStatusBadgeClass(item.status)} badge-sm">
											{getStatusLabel(item.status)}
										</span>
									</div>

									{#if item.description}
										<p class="text-sm text-base-content/70 line-clamp-3">{item.description}</p>
									{/if}

									{#if item.tags && item.tags.length > 0}
										<div class="flex flex-wrap gap-2 mt-2">
											{#each item.tags as tag}
												<span class="badge badge-sm badge-ghost gap-1">
													<Tag class="w-3 h-3" />
													{tag}
												</span>
											{/each}
										</div>
									{/if}

									{#if item.notes}
										<div
											class="mt-2 p-2 bg-base-200/50 rounded text-xs text-base-content/60 italic"
										>
											{item.notes}
										</div>
									{/if}

									<div class="card-actions justify-end mt-4 pt-4 border-t border-base-300">
										<button
											class="btn btn-sm btn-ghost gap-1"
											on:click={() => openEditModal(item)}
											title="Edit item"
										>
											<Pencil class="w-4 h-4" />
											Edit
										</button>
										<button
											class="btn btn-sm btn-ghost text-error gap-1"
											on:click={() => handleDelete(item.id)}
											title="Delete item"
										>
											<Delete class="w-4 h-4" />
											Delete
										</button>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label for="bucket-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<!-- Sidebar Header -->
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Target class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">Progress & Stats</h2>
					</div>

					<!-- Overall Progress -->
					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Trophy class="w-5 h-5" />
							Overall Progress
						</h3>

						<div class="space-y-4">
							<div class="stat p-0">
								<div class="stat-title text-sm">Total Items</div>
								<div class="stat-value text-2xl">{bucketItems.length}</div>
								<div class="stat-desc">Travel goals & dreams</div>
							</div>

							<div class="grid grid-cols-3 gap-2">
								<div class="stat p-0">
									<div class="stat-title text-xs">Planned</div>
									<div class="stat-value text-lg text-info">{plannedCount}</div>
								</div>
								<div class="stat p-0">
									<div class="stat-title text-xs">In Progress</div>
									<div class="stat-value text-lg text-warning">{inProgressCount}</div>
								</div>
								<div class="stat p-0">
									<div class="stat-title text-xs">Done</div>
									<div class="stat-value text-lg text-success">{completedCount}</div>
								</div>
							</div>

							<!-- Progress Bar -->
							<div class="space-y-2">
								<div class="flex justify-between text-sm">
									<span>Completion</span>
									<span class="font-semibold">{completionPercentage}%</span>
								</div>
								<progress
									class="progress progress-success w-full"
									value={completedCount}
									max={bucketItems.length || 1}
								></progress>
							</div>

							{#if completionPercentage === 100 && bucketItems.length > 0}
								<div class="alert alert-success">
									<Trophy class="w-4 h-4" />
									<span class="text-sm">All goals completed! 🎉</span>
								</div>
							{/if}
						</div>
					</div>

					<!-- Quick Stats -->
					<div class="space-y-3">
						<h3 class="font-semibold text-sm text-base-content/60 uppercase tracking-wide">
							Quick Actions
						</h3>
						<button class="btn btn-outline w-full gap-2" on:click={openCreateModal}>
							<Plus class="w-4 h-4" />
							Add New Item
						</button>
						{#if searchQuery || statusFilter !== 'all'}
							<button class="btn btn-ghost w-full gap-2" on:click={clearFilters}>
								<Clear class="w-4 h-4" />
								Clear All Filters
							</button>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<!-- Modal Component -->
<BucketListModal
	bind:show={showModal}
	bind:editItem={editingItem}
	bind:items={bucketItems}
	on:close={handleModalClose}
/>
