<script lang="ts">
	import type { Category } from '$lib/types';
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	const dispatch = createEventDispatcher();
	let modal: HTMLDialogElement;

	export let categories: Category[] = [];

	let categoryToEdit: Category | null = null;
	let newCategory = { display_name: '', icon: '' };
	let showAddForm = false;
	let isChanged = false;
	let hasLoaded = false;
	let warningMessage: string | null = null;
	let showEmojiPickerAdd = false;
	let showEmojiPickerEdit = false;

	onMount(async () => {
		await import('emoji-picker-element');
		modal = document.querySelector('#category-modal') as HTMLDialogElement;
		modal.showModal();
		await loadCategories();
	});

	async function loadCategories() {
		try {
			const res = await fetch('/api/categories');
			if (res.ok) {
				categories = await res.json();
			}
		} catch (err) {
			console.error('Failed to load categories:', err);
		} finally {
			hasLoaded = true;
		}
	}

	function closeModal() {
		dispatch('close');
		modal.close();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			closeModal();
		}
	}

	function handleEmojiSelectAdd(event: CustomEvent) {
		newCategory.icon = event.detail.unicode;
		showEmojiPickerAdd = false;
	}

	function handleEmojiSelectEdit(event: CustomEvent) {
		if (categoryToEdit) {
			categoryToEdit.icon = event.detail.unicode;
		}
		showEmojiPickerEdit = false;
	}

	async function createCategory(event: Event) {
		event.preventDefault();

		const nameTrimmed = newCategory.display_name.trim();
		if (!nameTrimmed) {
			warningMessage = $t('categories.name_required');
			return;
		}
		warningMessage = null;

		const payload = {
			display_name: nameTrimmed,
			name: nameTrimmed
				.toLowerCase()
				.replace(/\s+/g, '_')
				.replace(/[^a-z0-9_]/g, ''),
			icon: newCategory.icon.trim() || '🌍'
		};

		try {
			const res = await fetch('/api/categories', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			if (res.ok) {
				const created = await res.json();
				categories = [...categories, created];
				isChanged = true;
				newCategory = { display_name: '', icon: '' };
				showAddForm = false;
				showEmojiPickerAdd = false;
			}
		} catch (err) {
			console.error('Failed to create category:', err);
		}
	}

	async function saveCategory(event: Event) {
		event.preventDefault();
		if (!categoryToEdit) return;

		const nameTrimmed = categoryToEdit.display_name.trim();
		if (!nameTrimmed) {
			warningMessage = $t('categories.name_required');
			return;
		}
		warningMessage = null;

		try {
			const res = await fetch(`/api/categories/${categoryToEdit.id}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ ...categoryToEdit, display_name: nameTrimmed })
			});
			if (res.ok) {
				const updated = await res.json();
				categories = categories.map((c) => (c.id === updated.id ? updated : c));
				categoryToEdit = null;
				isChanged = true;
				showEmojiPickerEdit = false;
			}
		} catch (err) {
			console.error('Failed to save category:', err);
		}
	}

	function startEdit(category: Category) {
		categoryToEdit = { ...category };
		showAddForm = false;
		showEmojiPickerAdd = false;
		showEmojiPickerEdit = false;
	}

	function cancelEdit() {
		categoryToEdit = null;
		showEmojiPickerEdit = false;
	}

	async function removeCategory(category: Category) {
		if (category.name === 'general') return;

		try {
			const res = await fetch(`/api/categories/${category.id}`, {
				method: 'DELETE'
			});
			if (res.ok) {
				categories = categories.filter((c) => c.id !== category.id);
				isChanged = true;
			}
		} catch (err) {
			console.error('Failed to delete category:', err);
		}
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<dialog id="category-modal" class="modal" on:keydown={handleKeydown}>
	<div class="modal-box max-w-2xl">
		<!-- Header -->
		<div class="flex items-center justify-between mb-6">
			<h2 class="text-xl font-bold">{$t('categories.manage_categories')}</h2>
			<button
				type="button"
				on:click={closeModal}
				class="btn btn-sm btn-circle btn-ghost"
				aria-label="Close"
			>
				✕
			</button>
		</div>

		<!-- Category List -->
		{#if hasLoaded}
			{#if categories.length > 0}
				<div class="space-y-2 mb-6">
					{#each categories as category (category.id)}
						<div class="flex items-center justify-between p-3 bg-base-200 rounded-lg">
							<div class="flex items-center gap-3">
								<span class="text-lg">{category.icon || '🌍'}</span>
								<span class="font-medium">{category.display_name}</span>
							</div>
							<div class="flex gap-2">
								<button
									type="button"
									on:click={() => startEdit(category)}
									class="btn btn-xs btn-neutral"
								>
									{$t('lodging.edit')}
								</button>
								{#if category.name !== 'general'}
									<button
										type="button"
										on:click={() => removeCategory(category)}
										class="btn btn-xs btn-error"
									>
										{$t('adventures.remove')}
									</button>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-center py-8 text-base-content/60">
					{$t('categories.no_categories_found')}
				</div>
			{/if}
		{:else}
			<div class="text-center py-8">
				<span class="loading loading-spinner loading-md"></span>
			</div>
		{/if}

		<!-- Edit Category Form -->
		{#if categoryToEdit}
			<div class="bg-base-100 border border-base-300 rounded-lg p-4 mb-4">
				<h3 class="font-medium mb-4">{$t('categories.edit_category')}</h3>
				<form on:submit={saveCategory} class="space-y-4">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div>
							<!-- svelte-ignore a11y-label-has-associated-control -->
							<label class="label">
								<span class="label-text">{$t('categories.category_name')}</span>
							</label>
							<input
								type="text"
								class="input input-bordered w-full"
								bind:value={categoryToEdit.display_name}
								required
							/>
						</div>
						<div>
							<!-- svelte-ignore a11y-label-has-associated-control -->
							<label class="label">
								<span class="label-text">{$t('categories.icon')}</span>
							</label>
							<div class="flex gap-2">
								<input
									type="text"
									class="input input-bordered flex-1"
									bind:value={categoryToEdit.icon}
								/>
								<button
									type="button"
									on:click={() => (showEmojiPickerEdit = !showEmojiPickerEdit)}
									class="btn btn-square btn-outline"
								>
									😀
								</button>
							</div>
						</div>
					</div>

					{#if showEmojiPickerEdit}
						<div class="p-2 border rounded-lg bg-base-100">
							<emoji-picker on:emoji-click={handleEmojiSelectEdit}></emoji-picker>
						</div>
					{/if}

					<div class="flex justify-end gap-2">
						<button type="button" class="btn btn-ghost" on:click={cancelEdit}>
							{$t('adventures.cancel')}
						</button>
						<button type="submit" class="btn btn-primary"> {$t('notes.save')} </button>
					</div>
				</form>
			</div>
		{/if}

		<!-- Add Category Section -->
		<div class="collapse collapse-plus bg-base-200 mb-4">
			<input type="checkbox" bind:checked={showAddForm} />
			<div class="collapse-title font-medium">{$t('categories.add_new_category')}</div>
			{#if showAddForm}
				<div class="collapse-content">
					<form on:submit={createCategory} class="space-y-4">
						<div>
							<!-- svelte-ignore a11y-label-has-associated-control -->
							<label class="label">
								<span class="label-text">{$t('categories.category_name')}</span>
							</label>
							<input
								type="text"
								class="input input-bordered w-full"
								bind:value={newCategory.display_name}
								required
							/>
						</div>

						<div>
							<!-- svelte-ignore a11y-label-has-associated-control -->
							<label class="label">
								<span class="label-text">{$t('categories.icon')}</span>
							</label>
							<div class="flex gap-2">
								<input
									type="text"
									class="input input-bordered flex-1"
									bind:value={newCategory.icon}
									placeholder="🌍"
								/>
								<button
									type="button"
									on:click={() => (showEmojiPickerAdd = !showEmojiPickerAdd)}
									class="btn btn-square btn-outline"
								>
									😀
								</button>
							</div>
							{#if showEmojiPickerAdd}
								<div class="mt-2 p-2 border rounded-lg bg-base-100">
									<emoji-picker on:emoji-click={handleEmojiSelectAdd}></emoji-picker>
								</div>
							{/if}
						</div>

						<button type="submit" class="btn btn-primary w-full">
							{$t('collection.create')}
						</button>
					</form>
				</div>
			{/if}
		</div>

		<!-- Messages -->
		{#if warningMessage}
			<div class="alert alert-warning mb-4">
				<span>{warningMessage}</span>
			</div>
		{/if}

		{#if isChanged}
			<div class="alert alert-success mb-4">
				<span>{$t('categories.location_update_after_refresh')}</span>
			</div>
		{/if}

		<!-- Footer -->
		<div class="flex justify-end">
			<button type="button" class="btn" on:click={closeModal}> {$t('about.close')} </button>
		</div>
	</div>
</dialog>

<style>
	.modal-box {
		max-height: 90vh;
		overflow-y: auto;
	}
</style>
