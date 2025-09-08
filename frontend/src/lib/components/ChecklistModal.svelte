<script lang="ts">
	import type { Collection, Checklist, User, ChecklistItem } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	import CheckboxIcon from '~icons/mdi/checkbox-multiple-marked-outline';

	export let checklist: Checklist | null = null;
	export let collection: Collection;
	export let user: User | null = null;

	let items: ChecklistItem[] = [];

	let constrainDates: boolean = true;

	items = checklist?.items || [];

	let warning: string | null = '';

	let isReadOnly =
		!(checklist && user?.uuid == checklist?.user) &&
		!(user && collection && collection.shared_with && collection.shared_with.includes(user.uuid)) &&
		!!checklist;
	let newStatus: boolean = false;
	let newItem: string = '';

	let initialName: string = checklist?.name || '';

	function addItem() {
		if (newItem.trim() == '') {
			warning = $t('checklist.item_cannot_be_empty');
			return;
		}
		if (newChecklist.items.find((item) => item.name.trim() == newItem)) {
			warning = $t('checklist.item_already_exists');
			return;
		}
		items = [
			...items,
			{
				name: newItem,
				is_checked: newStatus,
				id: '',
				user: '',
				checklist: 0,
				created_at: '',
				updated_at: ''
			}
		];

		newChecklist.items = items;

		newItem = '';
		newStatus = false;
		warning = '';
	}

	let newChecklist = {
		name: checklist?.name || '',
		date: checklist?.date || undefined || null,
		items: checklist?.items || [],
		collection: collection.id,
		is_public: collection.is_public
	};

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function close() {
		dispatch('close');
	}

	function removeItem(i: number) {
		items = items.filter((_, index) => index !== i);
		newChecklist.items = items;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	async function save() {
		// handles empty date
		if (newChecklist.date == '') {
			newChecklist.date = null;
		}

		if (checklist && checklist.id) {
			console.log('newChecklist', newChecklist);
			const res = await fetch(`/api/checklists/${checklist.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newChecklist)
			});
			if (res.ok) {
				let data = await res.json();
				if (data) {
					dispatch('save', data);
				}
			} else {
				console.error('Failed to save checklist');
			}
		} else {
			console.log('newChecklist', newChecklist);
			const res = await fetch(`/api/checklists/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newChecklist)
			});
			if (res.ok) {
				let data = await res.json();
				if (data) {
					dispatch('create', data);
				}
			} else {
				let data = await res.json();
				console.error('Failed to save checklist', data);
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section -->
		<div
			class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<CheckboxIcon class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{#if checklist?.id && !isReadOnly}
								{$t('checklist.editing_checklist')}
							{:else if !isReadOnly}
								{$t('checklist.checklist_editor')}
							{:else}
								{$t('checklist.checklist_viewer')}
							{/if}
						</h1>
						<p class="text-sm text-base-content/60">
							{#if checklist?.id && !isReadOnly}
								{$t('checklist.update_checklist_details')} "{initialName}"
							{:else if !isReadOnly}
								{$t('checklist.new_checklist')}
							{:else}
								{$t('checklist.viewing_checklist')} "{checklist?.name || ''}"
							{/if}
						</p>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={close}>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="px-2">
			<form method="post" style="width: 100%;" on:submit|preventDefault>
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
								<svg
									class="w-5 h-5 text-primary"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
									/>
								</svg>
							</div>
							{$t('adventures.basic_information')}
						</div>
					</div>
					<div class="collapse-content bg-base-100/50 pt-4 p-6 space-y-4">
						<!-- Dual Column Layout for Large Screens -->
						<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
							<!-- Left Column -->
							<div class="space-y-4">
								<!-- Name Field -->
								<div class="form-control">
									<label class="label" for="name">
										<span class="label-text font-medium"
											>{$t('adventures.name')}<span class="text-error ml-1">*</span></span
										>
									</label>
									<input
										type="text"
										id="name"
										name="name"
										readonly={isReadOnly}
										bind:value={newChecklist.name}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('checklist.enter_checklist_title')}
										required
									/>
								</div>
							</div>

							<!-- Right Column -->
							<div class="space-y-4">
								<!-- Date Field -->
								<div class="form-control">
									<label class="label" for="date">
										<span class="label-text font-medium">{$t('adventures.date')}</span>
									</label>
									{#if collection && collection.start_date && collection.end_date && !isReadOnly}
										<div class="flex items-center gap-2 mb-2">
											<input
												type="checkbox"
												class="toggle toggle-primary toggle-sm"
												id="constrain_dates"
												name="constrain_dates"
												bind:checked={constrainDates}
											/>
											<span class="text-sm text-base-content/70"
												>{$t('adventures.date_constrain')}</span
											>
										</div>
									{/if}
									<input
										type="date"
										id="date"
										name="date"
										readonly={isReadOnly}
										min={constrainDates ? collection.start_date : ''}
										max={constrainDates ? collection.end_date : ''}
										bind:value={newChecklist.date}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
									/>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Items Section -->
				<div
					class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
				>
					<input type="checkbox" checked />
					<div
						class="collapse-title text-xl font-semibold bg-gradient-to-r from-primary/10 to-primary/5"
					>
						<div class="flex items-center gap-3">
							<div class="p-2 bg-primary/10 rounded-lg">
								<CheckboxIcon class="w-5 h-5 text-primary" />
							</div>
							{$t('checklist.items')}
							{#if items.length > 0}
								<div class="badge badge-primary badge-sm ml-2">{items.length}</div>
							{/if}
						</div>
					</div>
					<div class="collapse-content bg-base-100/50 pt-4 p-6">
						<!-- Add New Item Section -->
						{#if !isReadOnly}
							<div class="form-control mb-6">
								<label class="label" for="new-item">
									<span class="label-text font-medium">{$t('checklist.add_new_item')}</span>
								</label>
								<div class="flex gap-3 items-center">
									<input
										type="checkbox"
										bind:checked={newStatus}
										class="checkbox checkbox-primary"
									/>
									<div class="join flex-1">
										<input
											type="text"
											id="new-item"
											placeholder={$t('checklist.new_item')}
											bind:value={newItem}
											class="input input-bordered join-item flex-1 bg-base-100/80 focus:bg-base-100"
											on:keydown={(e) => {
												if (e.key === 'Enter') {
													e.preventDefault();
													addItem();
												}
											}}
										/>
										<button type="button" class="btn btn-primary join-item" on:click={addItem}>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 6v6m0 0v6m0-6h6m-6 0H6"
												/>
											</svg>
											{$t('adventures.add')}
										</button>
									</div>
								</div>
							</div>
						{/if}

						<!-- Items List -->
						{#if items.length > 0}
							<div class="space-y-3">
								<div class="flex items-center justify-between">
									<h3 class="text-lg font-semibold text-base-content/80">
										{$t('checklist.current_items')}
									</h3>
									<div class="text-sm text-base-content/60">
										{items.filter((item) => item.is_checked).length} / {items.length}
										{$t('checklist.completed')}
									</div>
								</div>
								<div class="max-h-64 overflow-y-auto space-y-2">
									{#each items as item, i}
										<div
											class="flex items-center gap-3 p-4 bg-base-200/50 rounded-xl border border-base-300/50 group hover:bg-base-200/70 transition-colors"
										>
											<input
												type="checkbox"
												bind:checked={item.is_checked}
												class="checkbox checkbox-primary"
												readonly={isReadOnly}
											/>
											<input
												type="text"
												bind:value={item.name}
												class="input input-ghost flex-1 bg-transparent focus:bg-base-100/80 {item.is_checked
													? 'line-through text-base-content/50'
													: ''}"
												readonly={isReadOnly}
											/>
											{#if !isReadOnly}
												<button
													type="button"
													class="btn btn-ghost btn-sm text-error opacity-0 group-hover:opacity-100 transition-opacity"
													on:click={() => removeItem(i)}
												>
													<svg
														class="w-4 h-4"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
														/>
													</svg>
												</button>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{:else if !isReadOnly}
							<div class="text-center py-12 text-base-content/50">
								<svg
									class="w-16 h-16 mx-auto mb-4 opacity-50"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 5H7a2 2 0 00-2 2v6a2 2 0 002 2h6a2 2 0 002-2V7a2 2 0 00-2-2H9z"
									/>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 9l2 2 4-4"
									/>
								</svg>
								<p class="text-lg font-medium">{$t('checklist.no_items_yet')}</p>
								<p class="text-sm">{$t('checklist.add_your_first_item')}</p>
							</div>
						{/if}
					</div>
				</div>

				<!-- Warning Messages -->
				{#if warning}
					<div role="alert" class="alert alert-error mb-6 rounded-xl border border-error/20">
						<svg class="h-6 w-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<span class="font-medium">{warning}</span>
					</div>
				{/if}

				<!-- Public Checklist Alert -->
				{#if collection.is_public}
					<div role="alert" class="alert alert-info mb-6 rounded-xl border border-info/20">
						<svg class="h-6 w-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<span class="font-medium">{$t('checklist.checklist_public')}</span>
					</div>
				{/if}

				<!-- Action Buttons -->
				<div class="flex gap-3 justify-end pt-4 border-t border-base-300/50">
					<button type="button" class="btn btn-neutral-200" on:click={close}>
						<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
						{$t('about.close')}
					</button>
					{#if !isReadOnly}
						<button type="button" class="btn btn-primary" on:click={save}>
							<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
								/>
							</svg>
							{$t('notes.save')}
						</button>
					{/if}
				</div>
			</form>
		</div>
	</div>
</dialog>
