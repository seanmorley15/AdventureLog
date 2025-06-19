<script lang="ts">
	import type { Collection, Checklist, User, ChecklistItem } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	export let checklist: Checklist | null = null;
	export let collection: Collection;
	export let user: User | null = null;

	let items: ChecklistItem[] = [];

	let constrainDates: boolean = false;

	items = checklist?.items || [];

	let warning: string | null = '';

	let isReadOnly =
		!(checklist && user?.uuid == checklist?.user) &&
		!(user && collection && collection.shared_with && collection.shared_with.includes(user.uuid)) &&
		!!checklist;
	let newStatus: boolean = false;
	let newItem: string = '';

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
			console.log('newNote', newChecklist);
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
			console.log('newNote', newChecklist);
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
				console.error('Failed to save checklist');
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box w-11/12 max-w-3xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-2xl">
			{#if checklist?.id}
				<p class="font-semibold text-md mb-2">
					{$t('checklist.checklist_editor')}
				</p>
			{:else}
				{$t('checklist.new_checklist')}
			{/if}
		</h3>
		<div class="modal-action items-center">
			<form method="post" style="width: 100%;" on:submit|preventDefault>
				<!-- Basic Information Section -->
				<div class="collapse collapse-plus bg-base-200 mb-4">
					<input type="checkbox" id="collapse-plus-1" checked />
					<div class="collapse-title text-lg font-bold">
						{$t('adventures.basic_information')}
					</div>
					<div class="collapse-content">
						<div class="form-control mb-2">
							<label for="name">{$t('adventures.name')}</label>
							<input
								type="text"
								id="name"
								class="input input-bordered w-full max-w-xs"
								bind:value={newChecklist.name}
								readonly={isReadOnly}
							/>
						</div>
						<div class="form-control mb-2">
							<label for="content">{$t('adventures.date')}</label>
							{#if collection && collection.start_date && collection.end_date && !isReadOnly}<label
									class="label cursor-pointer flex items-start space-x-2"
								>
									<span class="label-text">{$t('adventures.date_constrain')}</span>
									<input
										type="checkbox"
										class="toggle toggle-primary"
										id="constrain_dates"
										name="constrain_dates"
										on:change={() => (constrainDates = !constrainDates)}
									/></label
								>
							{/if}
							<input
								type="date"
								id="date"
								name="date"
								min={constrainDates ? collection.start_date : ''}
								max={constrainDates ? collection.end_date : ''}
								bind:value={newChecklist.date}
								class="input input-bordered w-full max-w-xs mt-1"
								readonly={isReadOnly}
							/>
						</div>
					</div>
				</div>
				<!-- Items Section -->
				<div class="collapse collapse-plus bg-base-200 mb-4">
					<input type="checkbox" id="collapse-plus-2" checked />
					<div class="collapse-title text-lg font-bold">
						{$t('checklist.items')}
					</div>
					<div class="collapse-content">
						{#if !isReadOnly}
							<div class="form-control mb-2 flex flex-row">
								<input type="checkbox" bind:checked={newStatus} class="checkbox mt-4 mr-2" />
								<input
									type="text"
									id="new_item"
									placeholder={$t('checklist.new_item')}
									name="new_item"
									bind:value={newItem}
									class="input input-bordered w-full max-w-xs mt-1"
									on:keydown={(e) => {
										if (e.key === 'Enter') {
											e.preventDefault();
											addItem();
										}
									}}
								/>
								<button
									type="button"
									class="btn btn-sm btn-primary absolute right-0 mt-2.5 mr-4"
									on:click={addItem}
								>
									{$t('adventures.add')}
								</button>
							</div>
						{/if}
						{#if items.length > 0}
							<div class="divider"></div>
							<h2 class=" text-xl font-semibold mb-4 -mt-3">{$t('checklist.items')}</h2>
						{/if}
						{#each items as item, i}
							<div class="form-control mb-2 flex flex-row">
								<input
									type="checkbox"
									bind:checked={item.is_checked}
									class="checkbox mt-4 mr-2"
									readonly={isReadOnly}
								/>
								<input
									type="text"
									id="item_{i}"
									name="item_{i}"
									bind:value={item.name}
									class="input input-bordered w-full max-w-xs mt-1"
									readonly={isReadOnly}
								/>
								<button
									type="button"
									class="btn btn-sm btn-error absolute right-0 mt-2.5 mr-4"
									on:click={() => removeItem(i)}
									disabled={isReadOnly}
								>
									{$t('adventures.remove')}
								</button>
							</div>
						{/each}
					</div>
				</div>
				{#if warning}
					<div role="alert" class="alert alert-error">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-6 w-6 shrink-0 stroke-current"
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
						<span>{warning}</span>
					</div>
				{/if}
				{#if collection.is_public}
					<div role="alert" class="alert mt-4">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							class="h-6 w-6 shrink-0 stroke-current"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							></path>
						</svg>
						<span>{$t('checklist.checklist_public')}</span>
					</div>
				{/if}

				<div class="mt-4">
					<button class="btn btn-primary mr-1" disabled={isReadOnly} on:click={save}
						>{$t('notes.save')}</button
					><button class="btn btn-neutral" on:click={close}>{$t('about.close')}</button>
				</div>
			</form>
		</div>
	</div>
</dialog>
