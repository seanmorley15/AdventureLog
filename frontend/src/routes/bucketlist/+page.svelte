<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import { enhance } from '$app/forms';
	import { t } from 'svelte-i18n';
	import Plus from '~icons/mdi/plus';
	import CheckCircle from '~icons/mdi/check-circle';
	import ProgressClock from '~icons/mdi/progress-clock';
	import ClockOutline from '~icons/mdi/clock-outline';
	import Target from '~icons/mdi/target';
	import FormatListChecks from '~icons/mdi/format-list-checks';
	import Delete from '~icons/mdi/delete';

	export let data: any;
	export let form: any;

	let bucketItems = data.props?.bucketItems || [];
	let count = data.props?.count || 0;
	let currentPage = 1;
	let statusFilter = 'all';
	let showModal = false;
	let isSubmitting = false;
	
	// Form fields
	let title = '';
	let description = '';
	let tags = '';
	let status = 'planned';
	let notes = '';

	$: if (form?.success) {
		closeModal();
		// Reload to show new item
		invalidateAll();
	}

	$: if (form?.error) {
		alert('Error: ' + form.error);
		isSubmitting = false;
	}
	
	function handleFormSubmit() {
		return async ({ result, update }) => {
			isSubmitting = true;
			await update();
			isSubmitting = false;
		};
	}

	const statusOptions = [
		{ value: 'all', label: 'All', icon: FormatListChecks },
		{ value: 'planned', label: 'Planned', icon: ClockOutline },
		{ value: 'in_progress', label: 'In Progress', icon: ProgressClock },
		{ value: 'completed', label: 'Completed', icon: CheckCircle }
	];

	$: {
		if (data.props?.bucketItems) {
			bucketItems = data.props.bucketItems;
		}
		if (data.props?.count !== undefined) {
			count = data.props.count;
		}
	}

	$: {
		let url = new URL($page.url);
		let pageParam = url.searchParams.get('page');
		if (pageParam) {
			currentPage = parseInt(pageParam);
		}
		let statusParam = url.searchParams.get('status');
		if (statusParam) {
			statusFilter = statusParam;
		}
	}

	function changeStatus(newStatus: string) {
		statusFilter = newStatus;
		let url = new URL(window.location.href);
		if (newStatus === 'all') {
			url.searchParams.delete('status');
		} else {
			url.searchParams.set('status', newStatus);
		}
		url.searchParams.set('page', '1');
		goto(url.toString(), { invalidateAll: true });
	}

	function getStatusBadgeClass(status: string) {
		if (status === 'completed') return 'badge-success';
		if (status === 'in_progress') return 'badge-warning';
		return 'badge-info';
	}

	function getStatusLabel(status: string) {
		if (status === 'completed') return 'Completed';
		if (status === 'in_progress') return 'In Progress';
		return 'Planned';
	}

	const completedCount = bucketItems.filter(item => item.status === 'completed').length;
	const totalCount = bucketItems.length || 1;
	const completionPercentage = Math.round((completedCount / totalCount) * 100);
	
	function openModal() {
		showModal = true;
	}
	
	function closeModal() {
		showModal = false;
		// Reset form
		title = '';
		description = '';
		tags = '';
		status = 'planned';
		notes = '';
		isSubmitting = false;
	}
</script>

<div class="container mx-auto p-4 max-w-7xl">
	<!-- Header -->
	<div class="mb-8">
		<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
			<div>
				<h1 class="text-3xl font-bold flex items-center gap-3">
					<Target class="w-8 h-8" />
					Bucket List
				</h1>
				<p class="text-base-content/60 mt-2">
					Track your travel goals and dream experiences
				</p>
			</div>
			<button class="btn btn-primary gap-2" on:click={openModal}>
				<Plus class="w-5 h-5" />
				Add Item
			</button>
		</div>

		<!-- Progress Bar -->
		{#if bucketItems.length > 0}
			<div class="card bg-base-200 shadow-md p-6">
				<div class="flex items-center justify-between mb-2">
					<span class="text-sm font-semibold">Overall Progress</span>
					<span class="text-sm text-base-content/60"
						>{completedCount} of {totalCount} completed</span
					>
				</div>
				<progress class="progress progress-success w-full" value={completionPercentage} max="100"
				></progress>
				<div class="text-right mt-1 text-xs text-base-content/60">
					{completionPercentage}%
				</div>
			</div>
		{/if}
	</div>

	<!-- Status Filter -->
	<div class="flex flex-wrap gap-2 mb-6">
		{#each statusOptions as option}
			<button
				class="btn btn-sm gap-2"
				class:btn-active={statusFilter === option.value}
				on:click={() => changeStatus(option.value)}
			>
				<svelte:component this={option.icon} class="w-4 h-4" />
				{option.label}
				{#if option.value !== 'all'}
					<span class="badge badge-sm">
						{bucketItems.filter(item => item.status === option.value).length}
					</span>
				{/if}
			</button>
		{/each}
	</div>

	<!-- Items List -->
	{#if bucketItems.length === 0}
		<div class="text-center py-16">
			<Target class="w-16 h-16 mx-auto text-base-content/20 mb-4" />
			<h3 class="text-xl font-semibold mb-2">No bucket list items yet</h3>
			<p class="text-base-content/60 mb-6">Start tracking your travel dreams and goals!</p>
			<button class="btn btn-primary gap-2" on:click={openModal}>
				<Plus class="w-5 h-5" />
				Add Your First Item
			</button>
		</div>
	{:else}
		<div class="grid gap-4">
			{#each bucketItems as item (item.id)}
				<div class="card bg-base-100 shadow hover:shadow-lg transition-all border border-base-300">
					<div class="card-body">
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1">
								<h3 class="card-title text-lg">{item.title}</h3>
								{#if item.description}
									<p class="text-sm text-base-content/70 mt-2">{item.description}</p>
								{/if}
								{#if item.tags && item.tags.length > 0}
									<div class="flex flex-wrap gap-2 mt-3">
										{#each item.tags as tag}
											<span class="badge badge-sm badge-ghost">{tag}</span>
										{/each}
									</div>
								{/if}
								{#if item.notes}
									<div class="text-xs text-base-content/60 mt-2 italic">
										Note: {item.notes}
									</div>
								{/if}
							</div>
							<div class="flex flex-col items-end gap-2">
								<span class="badge {getStatusBadgeClass(item.status)} badge-sm">
									{getStatusLabel(item.status)}
								</span>
								{#if item.location}
									<span class="text-xs text-base-content/60">Linked to location</span>
								{/if}
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Add Item Modal -->
{#if showModal}
	<div class="modal modal-open">
		<div class="modal-box max-w-2xl">
			<h3 class="font-bold text-lg mb-4">Add Bucket List Item</h3>
			<form method="POST" action="?/create" use:enhance={handleFormSubmit}>
				<div class="form-control w-full mb-4">
					<label class="label" for="title">
						<span class="label-text">Title <span class="text-error">*</span></span>
					</label>
					<input
						id="title"
						name="title"
						type="text"
						placeholder="e.g., Visit the Northern Lights"
						class="input input-bordered w-full"
						value={title}
						required
					/>
				</div>

				<div class="form-control w-full mb-4">
					<label class="label" for="description">
						<span class="label-text">Description</span>
					</label>
					<textarea
						id="description"
						name="description"
						placeholder="Describe your travel goal..."
						class="textarea textarea-bordered h-24"
						value={description}
					></textarea>
				</div>

				<div class="form-control w-full mb-4">
					<label class="label" for="tags">
						<span class="label-text">Tags</span>
					</label>
					<input
						id="tags"
						name="tags"
						type="text"
						placeholder="e.g., adventure, nature, photography (comma-separated)"
						class="input input-bordered w-full"
						value={tags}
					/>
					<label class="label">
						<span class="label-text-alt">Separate multiple tags with commas</span>
					</label>
				</div>

				<div class="form-control w-full mb-4">
					<label class="label" for="status">
						<span class="label-text">Status</span>
					</label>
					<select id="status" name="status" class="select select-bordered w-full" value={status}>
						<option value="planned">Planned</option>
						<option value="in_progress">In Progress</option>
						<option value="completed">Completed</option>
					</select>
				</div>

				<div class="form-control w-full mb-4">
					<label class="label" for="notes">
						<span class="label-text">Notes</span>
					</label>
					<textarea
						id="notes"
						name="notes"
						placeholder="Any additional notes or details..."
						class="textarea textarea-bordered h-20"
						value={notes}
					></textarea>
				</div>

				<div class="modal-action">
					<button type="button" class="btn" on:click={closeModal} disabled={isSubmitting}>
						Cancel
					</button>
					<button type="submit" class="btn btn-primary" disabled={isSubmitting}>
						{#if isSubmitting}
							<span class="loading loading-spinner loading-sm"></span>
							Creating...
						{:else}
							<Plus class="w-5 h-5" />
							Create Item
						{/if}
					</button>
				</div>
			</form>
		</div>
		<div class="modal-backdrop" on:click={closeModal}></div>
	</div>
{/if}
