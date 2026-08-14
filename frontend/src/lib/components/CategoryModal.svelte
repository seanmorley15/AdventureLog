<script lang="ts">
	import type { Category } from '$lib/types';
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	import TagIcon from '~icons/mdi/tag-multiple';
	import CloseIcon from '~icons/mdi/close';
	import PlusIcon from '~icons/mdi/plus';
	import PencilIcon from '~icons/mdi/pencil';
	import DeleteIcon from '~icons/mdi/delete';
	import SaveIcon from '~icons/mdi/content-save';
	import SearchIcon from '~icons/mdi/magnify';
	import InfoIcon from '~icons/mdi/information';
	import EmojiIcon from '~icons/mdi/emoticon-happy-outline';

	const dispatch = createEventDispatcher();
	let modal: HTMLDialogElement | undefined = $state();

	interface Props {
		categories?: Category[];
	}

	let { categories = $bindable([]) }: Props = $props();

	let categoryToEdit: Category | null = $state(null);
	let categoryToDelete: Category | null = $state(null);
	let newCategory = $state({ display_name: '', icon: '' });
	let isChanged = $state(false);
	let hasLoaded = $state(false);
	let warningMessage: string | null = $state(null);
	let showEmojiPickerAdd = $state(false);
	let showEmojiPickerEdit = $state(false);
	let searchTerm = $state('');

	let filteredCategories = $derived(categories
		.filter((category) => {
			if (!searchTerm.trim()) return true;
			return category.display_name.toLowerCase().includes(searchTerm.toLowerCase());
		})
		.sort((a, b) => {
			const usageDiff = (b.num_locations || 0) - (a.num_locations || 0);
			if (usageDiff !== 0) return usageDiff;
			return a.display_name.localeCompare(b.display_name);
		}));

	onMount(async () => {
		await import('emoji-picker-element');
		modal?.showModal();
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
		modal?.close();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			if (categoryToEdit) {
				cancelEdit();
				return;
			}
			if (categoryToDelete) {
				cancelDelete();
				return;
			}
			closeModal();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === modal) {
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
		categoryToDelete = null;
		showEmojiPickerAdd = false;
		showEmojiPickerEdit = false;
	}

	function cancelEdit() {
		categoryToEdit = null;
		showEmojiPickerEdit = false;
	}

	function requestDelete(category: Category) {
		if (category.name === 'general') return;
		categoryToDelete = category;
		categoryToEdit = null;
	}

	function cancelDelete() {
		categoryToDelete = null;
	}

	async function confirmDelete(category: Category) {
		if (category.name === 'general') return;

		try {
			const res = await fetch(`/api/categories/${category.id}`, {
				method: 'DELETE'
			});
			if (res.ok) {
				categories = categories.filter((c) => c.id !== category.id);
				isChanged = true;
				categoryToDelete = null;
			}
		} catch (err) {
			console.error('Failed to delete category:', err);
		}
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<dialog
	id="category-modal"
	bind:this={modal}
	class="modal modal-bottom md:modal-middle backdrop-blur-xs"
	onclick={handleBackdropClick}
	onkeydown={handleKeydown}
>
	<div
		class="modal-box category-modal-box w-full max-w-none bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl flex flex-col p-0 overflow-hidden rounded-t-2xl md:rounded-2xl"
		role="dialog"
		aria-labelledby="category-modal-title"
	>
		<!-- Header -->
		<div
			class="shrink-0 bg-base-100/90 backdrop-blur-lg border-b border-base-300 px-4 md:px-6 py-3 md:py-4"
		>
			<div class="flex items-center justify-between gap-3 md:gap-4">
				<div class="flex items-center gap-2.5 md:gap-3 min-w-0">
					<div class="p-1.5 md:p-2 bg-primary/10 rounded-xl shrink-0">
						<TagIcon class="w-5 h-5 md:w-7 md:h-7 text-primary" />
					</div>
					<div class="min-w-0">
						<h2
							id="category-modal-title"
							class="text-lg md:text-2xl font-bold text-primary truncate"
						>
							{$t('categories.manage_categories')}
						</h2>
					</div>
				</div>
				<button
					type="button"
					onclick={closeModal}
					class="btn btn-ghost btn-sm md:btn-md btn-square shrink-0"
					aria-label={$t('about.close')}
				>
					<CloseIcon class="w-5 h-5" />
				</button>
			</div>
		</div>

		<!-- Body -->
		<div
			class="flex-1 min-h-0 overflow-y-auto md:overflow-hidden flex flex-col px-4 md:px-6 py-4 md:py-5"
		>
			{#if warningMessage}
				<div role="alert" class="alert alert-warning shadow-xs mb-4 shrink-0">
					<InfoIcon class="w-5 h-5 shrink-0" />
					<span class="text-sm md:text-base">{warningMessage}</span>
				</div>
			{/if}

			<div
				class="category-modal-panels flex flex-col md:grid md:grid-cols-[minmax(0,1fr)_20rem] lg:grid-cols-[minmax(0,1fr)_22rem] gap-4 md:gap-6 flex-1 min-h-0 w-full min-w-0 md:overflow-hidden"
			>
				<!-- Existing categories -->
				<section
					class="order-2 md:order-1 min-w-0 w-full flex flex-col rounded-xl border border-base-300 bg-base-100 shadow-lg md:min-h-0 md:overflow-hidden"
					aria-labelledby="existing-categories-heading"
				>
					<div
						class="shrink-0 px-4 py-3 border-b border-base-300 bg-base-200/40 rounded-t-xl flex flex-col md:flex-row md:items-center md:justify-between gap-3"
					>
						<h3
							id="existing-categories-heading"
							class="flex items-center gap-2 text-sm md:text-base font-semibold min-w-0"
						>
							<span class="p-1.5 bg-primary/10 rounded-lg shrink-0">
								<TagIcon class="w-4 h-4 text-primary" />
							</span>
							<span class="truncate">{$t('adventures.categories')}</span>
							{#if hasLoaded}
								<span class="badge badge-neutral badge-sm shrink-0">{categories.length}</span>
							{/if}
						</h3>

						{#if hasLoaded && categories.length > 0}
							<label
								class="input input-sm flex items-center gap-2 w-full md:w-56 md:shrink-0"
							>
								<SearchIcon class="w-4 h-4 opacity-50 shrink-0" />
								<input
									type="search"
									class="grow min-w-0"
									placeholder={$t('navbar.search')}
									bind:value={searchTerm}
								/>
							</label>
						{/if}
					</div>

					<div
						class="p-3 md:p-4 md:flex-1 md:min-h-0 md:overflow-y-auto md:overflow-x-hidden md:overscroll-contain"
					>
						{#if !hasLoaded}
							<div class="flex justify-center items-center py-16">
								<span class="loading loading-spinner loading-md text-primary"></span>
							</div>
						{:else if categories.length === 0}
							<div
								class="flex flex-col items-center justify-center py-16 text-base-content/60 px-4 text-center"
							>
								<TagIcon class="w-10 h-10 opacity-40 mb-3" />
								<p>{$t('categories.no_categories_found')}</p>
							</div>
						{:else if filteredCategories.length === 0}
							<div
								class="flex items-center justify-center py-12 text-base-content/60 px-4 text-center"
							>
								<p>{$t('categories.no_categories_found')}</p>
							</div>
						{:else}
							<ul class="space-y-2 min-w-0">
								{#each filteredCategories as category (category.id)}
									<li class="min-w-0">
										{#if categoryToEdit?.id === category.id}
											<div
												class="rounded-xl border-2 border-primary/30 bg-primary/5 p-4 space-y-3 min-w-0 overflow-hidden"
											>
												<p class="text-sm font-medium text-primary">
													{$t('categories.edit_category')}
												</p>
												<form onsubmit={saveCategory} class="space-y-3 min-w-0">
													<div class="space-y-3">
														<div class="flex flex-col min-w-0">
															<label class="field-label" for="edit-category-name">{$t('categories.category_name')}</label>
															<input
																id="edit-category-name"
																type="text"
																class="input w-full min-w-0 bg-base-100"
																bind:value={categoryToEdit.display_name}
																required
															/>
														</div>
														<div class="flex flex-col min-w-0">
															<label class="field-label" for="edit-category-icon">{$t('categories.icon')}</label>
															<div class="join w-full min-w-0">
																<input
																	id="edit-category-icon"
																	type="text"
																	class="input join-item flex-1 min-w-0 w-0 bg-base-100"
																	bind:value={categoryToEdit.icon}
																/>
																<button
																	type="button"
																	onclick={() => {
																		showEmojiPickerEdit = !showEmojiPickerEdit;
																		showEmojiPickerAdd = false;
																	}}
																	class="icon-join-btn btn join-item btn-square shrink-0"
																	aria-pressed={showEmojiPickerEdit}
																	aria-label={$t('categories.icon')}
																>
																	<EmojiIcon class="w-5 h-5" />
																</button>
															</div>
														</div>
													</div>

													{#if showEmojiPickerEdit}
														<div
															class="rounded-xl border border-base-300 bg-base-100 overflow-y-auto max-h-64 max-w-full"
														>
															<emoji-picker onemoji-click={handleEmojiSelectEdit}></emoji-picker>
														</div>
													{/if}

													<div class="flex flex-wrap justify-end gap-2">
														<button
															type="button"
															class="btn btn-ghost btn-sm"
															onclick={cancelEdit}
														>
															{$t('adventures.cancel')}
														</button>
														<button type="submit" class="btn btn-primary btn-sm gap-2">
															<SaveIcon class="w-4 h-4" />
															{$t('notes.save')}
														</button>
													</div>
												</form>
											</div>
										{:else if categoryToDelete?.id === category.id}
											<div
												class="rounded-xl border border-error/30 bg-error/5 p-4 flex flex-col gap-3 min-w-0 overflow-hidden"
											>
												<p class="text-sm">
													{$t('adventures.remove')}
													<span class="font-semibold">{category.display_name}</span>?
												</p>
												<div class="flex flex-wrap gap-2 shrink-0 justify-end">
													<button
														type="button"
														class="btn btn-ghost btn-sm"
														onclick={cancelDelete}
													>
														{$t('adventures.cancel')}
													</button>
													<button
														type="button"
														class="btn btn-error btn-sm gap-2"
														onclick={() => confirmDelete(category)}
													>
														<DeleteIcon class="w-4 h-4" />
														{$t('adventures.remove')}
													</button>
												</div>
											</div>
										{:else}
											<div
												class="group flex items-center gap-3 p-3 rounded-xl border border-base-300 bg-base-200/30 hover:border-primary/40 hover:bg-primary/5 transition-colors"
											>
												<span
													class="flex items-center justify-center w-11 h-11 rounded-xl bg-base-100 border border-base-300 text-xl shrink-0"
												>
													{category.icon || '🌍'}
												</span>
												<div class="flex-1 min-w-0">
													<div class="font-medium truncate">{category.display_name}</div>
													<div class="text-sm text-base-content/60">
														{category.num_locations || 0}
														{$t('locations.locations')}
													</div>
												</div>
												<div class="flex gap-1 shrink-0">
													<button
														type="button"
														onclick={() => startEdit(category)}
														class="btn btn-ghost btn-sm btn-square"
														aria-label={$t('lodging.edit')}
													>
														<PencilIcon class="w-4 h-4" />
													</button>
													{#if category.name !== 'general'}
														<button
															type="button"
															onclick={() => requestDelete(category)}
															class="btn btn-ghost btn-sm btn-square text-error hover:bg-error/10"
															aria-label={$t('adventures.remove')}
														>
															<DeleteIcon class="w-4 h-4" />
														</button>
													{/if}
												</div>
											</div>
										{/if}
									</li>
								{/each}
							</ul>
						{/if}
					</div>
				</section>

				<!-- Add new category -->
				<section
					class="order-1 md:order-2 min-w-0 w-full flex flex-col rounded-xl border border-base-300 bg-base-100 shadow-lg md:min-h-0 md:overflow-hidden"
					aria-labelledby="add-category-heading"
				>
					<div
						class="shrink-0 px-4 py-3 border-b border-base-300 bg-base-200/40 rounded-t-xl flex items-center gap-2 min-w-0"
					>
						<span class="p-1.5 bg-primary/10 rounded-lg shrink-0">
							<PlusIcon class="w-4 h-4 text-primary" />
						</span>
						<h3 id="add-category-heading" class="text-sm md:text-base font-semibold truncate">
							{$t('categories.add_new_category')}
						</h3>
					</div>

					<div class="md:flex-1 md:min-h-0 md:overflow-y-auto md:overscroll-contain">
						<form onsubmit={createCategory} class="p-4 md:p-5 space-y-4 w-full min-w-0 box-border">
							<div class="flex flex-col min-w-0 w-full">
								<label class="field-label" for="new-category-name">{$t('categories.category_name')}</label>
								<input
									id="new-category-name"
									type="text"
									class="input w-full min-w-0 bg-base-100"
									bind:value={newCategory.display_name}
									placeholder={$t('categories.category_name')}
									required
								/>
							</div>

							<div class="flex flex-col min-w-0 w-full">
								<label class="field-label" for="new-category-icon">{$t('categories.icon')}</label>
								<div class="join w-full min-w-0">
									<input
										id="new-category-icon"
										type="text"
										class="input join-item flex-1 min-w-0 w-0 bg-base-100"
										bind:value={newCategory.icon}
										placeholder="🌍"
									/>
									<button
										type="button"
										onclick={() => {
											showEmojiPickerAdd = !showEmojiPickerAdd;
											showEmojiPickerEdit = false;
										}}
										class="icon-join-btn btn join-item btn-square shrink-0"
										aria-pressed={showEmojiPickerAdd}
										aria-label={$t('categories.icon')}
									>
										<EmojiIcon class="w-5 h-5" />
									</button>
								</div>
							</div>

							{#if showEmojiPickerAdd}
								<div
									class="emoji-picker-shell rounded-xl border border-base-300 bg-base-200/30 overflow-y-auto overflow-x-hidden w-full"
								>
									<emoji-picker onemoji-click={handleEmojiSelectAdd}></emoji-picker>
								</div>
							{/if}

							<button
								type="submit"
								class="btn btn-primary w-full gap-2"
								disabled={!newCategory.display_name.trim()}
							>
								<PlusIcon class="w-4 h-4" />
								{$t('collection.create')}
							</button>
						</form>
					</div>
				</section>
			</div>
		</div>

		<!-- Footer -->
		<div
			class="shrink-0 border-t border-base-300 bg-base-100/90 backdrop-blur-lg px-4 md:px-6 py-3 md:py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
		>
			{#if isChanged}
				<p
					class="text-xs md:text-sm text-base-content/60 flex items-start md:items-center gap-2 min-w-0 md:flex-1"
				>
					<InfoIcon class="w-4 h-4 shrink-0 text-info mt-0.5 md:mt-0" />
					<span>{$t('categories.location_update_after_refresh')}</span>
				</p>
			{:else}
				<span class="hidden md:block md:flex-1"></span>
			{/if}
			<button
				type="button"
				class="btn btn-neutral w-full md:w-auto gap-2 shrink-0"
				onclick={closeModal}
			>
				<CloseIcon class="w-4 h-4" />
				{$t('about.close')}
			</button>
		</div>
	</div>
</dialog>

<style>
	dialog::backdrop {
		backdrop-filter: blur(8px);
		background: rgba(0, 0, 0, 0.3);
	}

	/* DaisyUI .btn fill uses --btn-bg (base-200). bg-base-100 only wins on hover. */
	.icon-join-btn,
	.icon-join-btn:hover,
	.icon-join-btn:active,
	.icon-join-btn:focus-visible {
		--btn-bg: var(--color-base-100);
		--btn-border: color-mix(in oklab, var(--color-base-content) 20%, #0000);
		--btn-fg: var(--color-base-content);
	}

	.category-modal-box {
		width: 100%;
		max-width: 100%;
		max-height: 92dvh;
	}

	@media (min-width: 768px) {
		.category-modal-box {
			width: min(92vw, 72rem);
			max-width: 72rem;
			max-height: min(85vh, 760px);
			min-height: min(34rem, 85vh);
		}

		.category-modal-panels {
			grid-template-rows: minmax(0, 1fr);
		}

		.category-modal-panels > section {
			min-height: 0;
		}
	}

	.emoji-picker-shell {
		max-height: 14rem;
	}

	@media (min-width: 768px) {
		.emoji-picker-shell {
			max-height: 16rem;
		}
	}

	emoji-picker {
		width: 100%;
		max-width: 100%;
		box-sizing: border-box;
		--num-columns: 7;
	}

	@media (min-width: 768px) {
		emoji-picker {
			--num-columns: 8;
		}
	}
</style>
