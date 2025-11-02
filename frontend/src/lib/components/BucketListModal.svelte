<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';

	// Icons
	import Plus from '~icons/mdi/plus';
	import Pencil from '~icons/mdi/pencil';
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
	$: submitLabel = isEditMode ? 'Update Item' : 'Create Item';

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
	$: if (!show) {
		hasInitialized = false;
		if (!editItem) {
			title = '';
			description = '';
			tags = '';
			status = 'planned';
			notes = '';
		}
		error = '';
	}

	function handleClose() {
		dispatch('close');
		isSubmitting = false;
		hasInitialized = false;
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
	<div class="modal modal-open">
		<div class="modal-box max-w-2xl">
			<h3 class="font-bold text-lg mb-4 flex items-center gap-2">
				{#if isEditMode}
					<Pencil class="w-5 h-5" />
				{:else}
					<Plus class="w-5 h-5" />
				{/if}
				{modalTitle}
			</h3>

			{#if error}
				<div class="alert alert-error mb-4">
					<span>{error}</span>
				</div>
			{/if}

			<form on:submit={handleSubmit}>
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
						bind:value={title}
						required
						disabled={isSubmitting}
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
						bind:value={description}
						disabled={isSubmitting}
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
						placeholder="e.g., adventure, nature, photography"
						class="input input-bordered w-full"
						bind:value={tags}
						disabled={isSubmitting}
					/>
					<label class="label">
						<span class="label-text-alt">Separate multiple tags with commas</span>
					</label>
				</div>

				<div class="form-control w-full mb-4">
					<label class="label" for="status">
						<span class="label-text">Status</span>
					</label>
					<select
						id="status"
						name="status"
						class="select select-bordered w-full"
						bind:value={status}
						disabled={isSubmitting}
					>
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
						bind:value={notes}
						disabled={isSubmitting}
					></textarea>
				</div>

				<div class="modal-action">
					<button type="button" class="btn" on:click={handleClose} disabled={isSubmitting}>
						Cancel
					</button>
					<button type="submit" class="btn btn-primary gap-2" disabled={isSubmitting}>
						{#if isSubmitting}
							<span class="loading loading-spinner loading-sm"></span>
							{isEditMode ? 'Updating...' : 'Creating...'}
						{:else}
							{#if isEditMode}
								<Pencil class="w-5 h-5" />
							{:else}
								<Plus class="w-5 h-5" />
							{/if}
							{submitLabel}
						{/if}
					</button>
				</div>
			</form>
		</div>
		<label class="modal-backdrop" on:click={handleClose}></label>
	</div>
{/if}
