<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	// Icons
	import Plus from '~icons/mdi/plus';
	import Pencil from '~icons/mdi/pencil';
	import Target from '~icons/mdi/target';
	import Close from '~icons/mdi/close';
	import ContentSave from '~icons/mdi/content-save';
	import InformationOutline from '~icons/mdi/information-outline';
	import TagMultiple from '~icons/mdi/tag-multiple';
	import type { BucketListItem } from '$lib/types';

	export let show = false;
	export let editItem: BucketListItem | null = null;
	export let items: BucketListItem[] = [];

	const dispatch = createEventDispatcher<{
		close: void;
	}>();

	let isSubmitting = false;
	let title = '';
	let description = '';
	let tags = '';
	let status = 'planned';
	let notes = '';
	let error = '';
	let hasInitialized = false;

	$: isEditMode = editItem !== null;
	$: modalTitle = isEditMode ? 'Edit Bucket List Item' : 'Add Bucket List Item';
	$: modalSubtitle = isEditMode ? 'Update your travel goal details' : 'Create a new travel dream';

	// Populate form ONLY when modal first opens
	$: if (show && !hasInitialized) {
		if (editItem) {
			title = editItem.title;
			description = editItem.description || '';
			tags = editItem.tags ? editItem.tags.join(', ') : '';
			status = editItem.status;
			notes = editItem.notes || '';
		} else {
			title = '';
			description = '';
			tags = '';
			status = 'planned';
			notes = '';
		}
		error = '';
		hasInitialized = true;
	}

	// Reset initialization flag when modal closes
	$: if (!show && hasInitialized) {
		hasInitialized = false;
		error = '';
	}

	function handleClose() {
		dispatch('close');
		isSubmitting = false;
		hasInitialized = false;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleClose();
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		isSubmitting = true;
		error = '';

		try {
			const payload = {
				title,
				description: description || null,
				tags: tags
					? tags
							.split(',')
							.map((t) => t.trim())
							.filter(Boolean)
					: null,
				status,
				notes: notes || null
			};

			let response: Response;

			if (isEditMode && editItem) {
				// PATCH for update
				response = await fetch(`/api/bucketlist/items/${editItem.id}`, {
					method: 'PATCH',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(payload)
				});
			} else {
				// POST for create
				response = await fetch('/api/bucketlist/items', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(payload)
				});
			}

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ error: 'An error occurred' }));
				throw new Error(errorData.error || `Failed to ${isEditMode ? 'update' : 'create'} item`);
			}

			const savedItem: BucketListItem = await response.json();

			// Update the items array directly
			const existingIndex = items.findIndex((item) => item.id === savedItem.id);

			if (existingIndex !== -1) {
				// Update existing item
				items[existingIndex] = savedItem;
				items = items; // Trigger reactivity
			} else {
				// Add new item at the beginning
				items = [savedItem, ...items];
			}

			handleClose();
		} catch (err) {
			error = err instanceof Error ? err.message : 'An unexpected error occurred';
		} finally {
			isSubmitting = false;
		}
	}
</script>

{#if show}
	<div class="modal modal-open backdrop-blur-sm">
		<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
		<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
		<div
			class="modal-box w-11/12 max-w-4xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
			role="dialog"
			on:keydown={handleKeydown}
			tabindex="0"
		>
			<!-- Header Section -->
			<div
				class=" top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
			>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<div class="p-2 bg-primary/10 rounded-xl">
							<Target class="w-8 h-8 text-primary" />
						</div>
						<div>
							<h1 class="text-3xl font-bold text-primary bg-clip-text">
								{modalTitle}
							</h1>
							<p class="text-sm text-base-content/60">
								{modalSubtitle}
							</p>
						</div>
					</div>

					<!-- Close Button -->
					<button class="btn btn-ghost btn-square" on:click={handleClose}>
						<Close class="w-5 h-5" />
					</button>
				</div>
			</div>

			<!-- Main Content -->
			<div class="px-2">
				{#if error}
					<div class="alert alert-error mb-6">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="stroke-current shrink-0 h-6 w-6"
							fill="none"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<span>{error}</span>
					</div>
				{/if}

				<form method="post" style="width: 100%;" on:submit={handleSubmit}>
					<!-- Basic Information Section -->
					<div
						class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
					>
						<input type="checkbox" checked />
						<div
							class="collapse-title text-xl font-semibold bg-gradient-to-r from-primary/10 to-primary/5"
						>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-lg">
									<InformationOutline class="w-5 h-5 text-primary" />
								</div>
								Basic Information
							</div>
						</div>
						<div class="collapse-content bg-base-100/50 pt-4 p-6 space-y-4">
							<!-- Title Field -->
							<div class="form-control">
								<label class="label" for="title">
									<span class="label-text font-medium"
										>Title<span class="text-error ml-1">*</span></span
									>
								</label>
								<input
									id="title"
									type="text"
									placeholder="e.g., Visit the Northern Lights"
									class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
									bind:value={title}
									required
									disabled={isSubmitting}
								/>
							</div>

							<!-- Description Field -->
							<div class="form-control">
								<label class="label" for="description">
									<span class="label-text font-medium">Description</span>
								</label>
								<textarea
									id="description"
									placeholder="Describe your travel goal..."
									class="textarea textarea-bordered h-32 bg-base-100/80 focus:bg-base-100"
									bind:value={description}
									disabled={isSubmitting}
								></textarea>
							</div>

							<!-- Status Selection -->
							<div class="form-control">
								<label class="label" for="status">
									<span class="label-text font-medium"
										>Status<span class="text-error ml-1">*</span></span
									>
								</label>
								<select
									id="status"
									class="select select-bordered w-full bg-base-100/80 focus:bg-base-100"
									bind:value={status}
									disabled={isSubmitting}
								>
									<option value="planned">Planned</option>
									<option value="in_progress">In Progress</option>
									<option value="completed">Completed</option>
								</select>
							</div>
						</div>
					</div>

					<!-- Additional Details Section -->
					<div
						class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
					>
						<input type="checkbox" checked />
						<div
							class="collapse-title text-xl font-semibold bg-gradient-to-r from-primary/10 to-primary/5"
						>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-lg">
									<TagMultiple class="w-5 h-5 text-primary" />
								</div>
								Additional Details
							</div>
						</div>
						<div class="collapse-content bg-base-100/50 pt-4 p-6 space-y-4">
							<!-- Tags Field -->
							<div class="form-control">
								<label class="label" for="tags">
									<span class="label-text font-medium">Tags</span>
								</label>
								<input
									id="tags"
									type="text"
									placeholder="e.g., adventure, nature, photography"
									class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
									bind:value={tags}
									disabled={isSubmitting}
								/>
								<label class="label">
									<span class="label-text-alt">Separate multiple tags with commas</span>
								</label>
							</div>

							<!-- Notes Field -->
							<div class="form-control">
								<label class="label" for="notes">
									<span class="label-text font-medium">Notes</span>
								</label>
								<textarea
									id="notes"
									placeholder="Any additional notes or details..."
									class="textarea textarea-bordered h-24 bg-base-100/80 focus:bg-base-100"
									bind:value={notes}
									disabled={isSubmitting}
								></textarea>
							</div>
						</div>
					</div>

					<!-- Form Actions -->
					<div class="flex justify-end gap-3 mt-8 pt-6 border-t border-base-300">
						<button
							type="button"
							class="btn btn-neutral-200"
							on:click={handleClose}
							disabled={isSubmitting}
						>
							Cancel
						</button>
						<button type="submit" class="btn btn-primary gap-2" disabled={isSubmitting}>
							{#if isSubmitting}
								<span class="loading loading-spinner loading-sm"></span>
								{isEditMode ? 'Updating...' : 'Creating...'}
							{:else}
								<ContentSave class="w-4 h-4" />
								Save
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
		<label class="modal-backdrop" on:click={handleClose}></label>
	</div>
{/if}
