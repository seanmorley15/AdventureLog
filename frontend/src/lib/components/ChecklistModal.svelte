<script lang="ts">
	import { createBubbler, preventDefault } from 'svelte/legacy';

	const bubble = createBubbler();
	import type { Collection, Checklist, User, ChecklistItem } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	import CheckboxIcon from '~icons/mdi/checkbox-multiple-marked-outline';
	import DateInput from './shared/DateInput.svelte';
	import InfoIcon from '~icons/mdi/information';
	import CalendarIcon from '~icons/mdi/calendar';
	import SaveIcon from '~icons/mdi/content-save';
	import CloseIcon from '~icons/mdi/close';
	import PlusIcon from '~icons/mdi/plus';
	import DeleteIcon from '~icons/mdi/delete-outline';

	interface Props {
		checklist?: Checklist | null;
		collection: Collection;
		user?: User | null;
		initialVisitDate?: string | null;
	}

	let { checklist = null, collection, user = null, initialVisitDate = null }: Props = $props();

	let items: ChecklistItem[] = $state([]);

	let constrainDates: boolean = $state(true);

	let warning: string | null = $state('');

	let isReadOnly = $derived(
		!(checklist && user?.uuid == checklist?.user) &&
			!(
				user &&
				collection &&
				collection.shared_with &&
				collection.shared_with.includes(user.uuid)
			) &&
			!!checklist
	);
	let newStatus: boolean = $state(false);
	let newItem: string = $state('');

	let initialName = $derived(checklist?.name || '');

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

	const getSeedDate = (): string | null => {
		if (checklist?.date) return checklist.date;
		if (initialVisitDate) return initialVisitDate;
		return null;
	};

	let newChecklist = $state({
		name: '',
		date: null as string | null | undefined,
		items: [] as ChecklistItem[],
		collection: '',
		is_public: false
	});
	let previousChecklistId: string | null | undefined = undefined;

	$effect.pre(() => {
		const sourceId = checklist?.id ?? null;
		if (sourceId === previousChecklistId) return;

		previousChecklistId = sourceId;
		items = checklist?.items || [];
		newChecklist = {
			name: checklist?.name || '',
			date: getSeedDate() || null,
			items: checklist?.items || [],
			collection: collection.id,
			is_public: collection.is_public
		};
	});

	const hasVisitDateSuggestion = $derived(!!initialVisitDate && !checklist?.date);

	function useVisitDate() {
		if (isReadOnly) return;
		if (initialVisitDate) {
			newChecklist = { ...newChecklist, date: initialVisitDate };
		}
	}

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

<dialog id="my_modal_1" class="modal modal-bottom md:modal-middle backdrop-blur-xs">
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="modal-box checklist-modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl flex flex-col p-0 overflow-hidden rounded-none md:rounded-2xl"
		role="dialog"
		onkeydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section -->
		<div
			class="shrink-0 bg-base-100/90 backdrop-blur-lg border-b border-base-300 px-4 md:px-6 py-3 md:py-4"
		>
			<div class="flex items-center justify-between gap-3">
				<div class="flex items-center gap-3 min-w-0">
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
						<p class="text-sm text-base-content/80">
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
				<button
					type="button"
					class="btn btn-ghost btn-square shrink-0"
					aria-label={$t('about.close')}
					title={$t('about.close')}
					onclick={close}
				>
					<CloseIcon class="w-5 h-5" />
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="flex-1 min-h-0 overflow-hidden flex flex-col">
			<form
				class="h-full min-h-0 flex flex-col"
				method="post"
				onsubmit={preventDefault(bubble('submit'))}
			>
				<div
					class="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-4 md:py-5 bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5"
				>
					<div class="max-w-full mx-auto space-y-6">
						<div class="card bg-base-100 border border-base-300 shadow-lg">
							<div class="card-body p-6">
								<div class="flex items-center gap-3 mb-6">
									<div class="p-2 bg-primary/10 rounded-lg">
										<InfoIcon class="w-5 h-5 text-primary" />
									</div>
									<h2 class="text-xl font-bold">{$t('adventures.basic_information')}</h2>
								</div>

								<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
									<div class="space-y-4">
										<div class="flex flex-col">
											<label class="field-label" for="name">
												{$t('adventures.name')}<span class="text-error ml-1">*</span>
											</label>
											<input
												type="text"
												id="name"
												name="name"
												readonly={isReadOnly}
												bind:value={newChecklist.name}
												class="input w-full bg-base-100/80 focus:bg-base-100"
												placeholder={$t('checklist.enter_checklist_title')}
												required
											/>
										</div>
									</div>

									<div class="space-y-4">
										<div class="flex flex-col">
											<label class="field-label flex items-center gap-2" for="date">
												<CalendarIcon class="w-4 h-4" />
												{$t('adventures.date')}
											</label>
											{#if !isReadOnly && hasVisitDateSuggestion}
												<div
													class="flex flex-wrap items-center gap-2 mb-2 text-xs text-base-content/70"
												>
													<span class="badge badge-primary badge-soft">Itinerary day</span>
													<span>Prefilled to match your selected day.</span>
													<button type="button" class="btn btn-ghost btn-xs" onclick={useVisitDate}>
														Reapply date
													</button>
												</div>
											{/if}
											{#if collection && collection.start_date && collection.end_date && !isReadOnly}
												<label class="field-toggle mb-2">
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
												</label>
											{/if}
											<DateInput
												id="date"
												name="date"
												readonly={isReadOnly}
												min={constrainDates ? collection.start_date || undefined : undefined}
												max={constrainDates ? collection.end_date || undefined : undefined}
												bind:value={newChecklist.date}
												clearable={!isReadOnly}
											/>
										</div>
									</div>
								</div>
							</div>
						</div>

						<div class="card bg-base-100 border border-base-300 shadow-lg">
							<div class="card-body p-6">
								<div class="flex items-center gap-3 mb-6">
									<div class="p-2 bg-primary/10 rounded-lg">
										<CheckboxIcon class="w-5 h-5 text-primary" />
									</div>
									<h2 class="text-xl font-bold">{$t('checklist.items')}</h2>
									{#if items.length > 0}
										<div class="badge badge-primary badge-sm">{items.length}</div>
									{/if}
								</div>

								{#if !isReadOnly}
									<div class="flex flex-col mb-6">
										<label class="field-label" for="new-item">{$t('checklist.add_new_item')}</label>
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
													class="input join-item flex-1 bg-base-100/80 focus:bg-base-100"
													onkeydown={(e) => {
														if (e.key === 'Enter') {
															e.preventDefault();
															addItem();
														}
													}}
												/>
												<button
													type="button"
													class="btn btn-primary join-item gap-1"
													onclick={addItem}
												>
													<PlusIcon class="w-4 h-4" />
													{$t('adventures.add')}
												</button>
											</div>
										</div>
									</div>
								{/if}

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
										<div class="space-y-2">
											{#each items as item, i (item.id || `${item.name}-${i}`)}
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
															aria-label={$t('adventures.remove')}
															title={$t('adventures.remove')}
															onclick={() => removeItem(i)}
														>
															<DeleteIcon class="w-4 h-4" />
														</button>
													{/if}
												</div>
											{/each}
										</div>
									</div>
								{:else if !isReadOnly}
									<div class="text-center py-12 text-base-content/50">
										<CheckboxIcon class="w-16 h-16 mx-auto mb-4 opacity-50" />
										<p class="text-lg font-medium">{$t('checklist.no_items_yet')}</p>
										<p class="text-sm">{$t('checklist.add_your_first_item')}</p>
									</div>
								{/if}
							</div>
						</div>

						{#if warning}
							<div role="alert" class="alert alert-error rounded-xl border border-error/20">
								<InfoIcon class="h-6 w-6 shrink-0" />
								<span class="font-medium">{warning}</span>
							</div>
						{/if}

						{#if collection.is_public}
							<div role="alert" class="alert alert-info rounded-xl border border-info/20">
								<InfoIcon class="h-6 w-6 shrink-0" />
								<span class="font-medium">{$t('checklist.checklist_public')}</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Action Buttons -->
				<div
					class="shrink-0 border-t border-base-300 bg-base-100/90 backdrop-blur-lg px-4 md:px-6 py-3 md:py-4 flex gap-3 justify-end"
				>
					<button type="button" class="btn btn-ghost gap-2" onclick={close}>
						<CloseIcon class="w-4 h-4" />
						{$t('about.close')}
					</button>
					{#if !isReadOnly}
						<button type="button" class="btn btn-primary gap-2" onclick={save}>
							<SaveIcon class="w-5 h-5" />
							{$t('notes.save')}
						</button>
					{/if}
				</div>
			</form>
		</div>
	</div>
</dialog>

<style>
	.checklist-modal-box {
		width: 100%;
		max-width: 100%;
		height: 100dvh;
		max-height: 100dvh;
	}

	@media (min-width: 768px) {
		.checklist-modal-box {
			width: min(96vw, 72rem);
			max-width: 72rem;
			height: min(90dvh, 56rem);
			max-height: 90dvh;
		}
	}
</style>
