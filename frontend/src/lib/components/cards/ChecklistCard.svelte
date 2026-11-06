<script lang="ts">
	import { addToast } from '#lib/toasts.js';
	import type { Checklist, Collection, User } from '#lib/types.js';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';

	import Launch from '~icons/mdi/launch';
	import TrashCan from '~icons/mdi/trash-can';
	import Calendar from '~icons/mdi/calendar';
	import DeleteWarning from '../DeleteWarning.svelte';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import CheckCircle from '~icons/mdi/check-circle';
	import CheckboxBlankCircleOutline from '~icons/mdi/checkbox-blank-circle-outline';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Close from '~icons/mdi/close';
	import Globe from '~icons/mdi/globe';
	import type { CollectionItineraryItem } from '#lib/types.js';
	import CardActionsMenu from './parts/CardActionsMenu.svelte';
	import ClipboardListOutline from '~icons/mdi/clipboard-list-outline';
	import { dateFormatFromUser, formatDisplayDate } from '#lib/dateFormat.js';

	interface Props {
		checklist: Checklist;
		user?: User | null;
		collection: Collection;
		readOnly?: boolean;
		itineraryItem?: CollectionItineraryItem | null;
	}

	let {
		checklist = $bindable(),
		user = null,
		collection,
		readOnly = false,
		itineraryItem = null
	}: Props = $props();

	let isWarningModalOpen: boolean = $state(false);
	let isDetailsOpen: boolean = $state(false);
	let updatingItemId: string | null = $state(null);

	let canEdit = $derived(
		!readOnly &&
			(checklist.user == user?.uuid ||
				(collection && user && collection.shared_with?.includes(user.uuid)))
	);

	const dateFormat = $derived(dateFormatFromUser(user));

	let doneCount = $derived(checklist.items.filter((item) => item.is_checked).length);

	const normalizeDateForApi = (date: string | Date | null | undefined): string | null => {
		if (!date) return null;
		if (date instanceof Date && !isNaN(date.getTime())) {
			return date.toISOString().slice(0, 10);
		}
		if (typeof date === 'string') {
			const match = date.match(/^\d{4}-\d{2}-\d{2}/);
			return match ? match[0] : null;
		}
		return null;
	};

	function editChecklist() {
		dispatch('edit', checklist);
	}

	function changeDay() {
		dispatch('changeDay', { type: 'checklist', item: checklist, forcePicker: true });
	}

	async function deleteChecklist() {
		const res = await fetch(`/api/checklists/${checklist.id}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('success', $t('checklist.checklist_deleted'));
			isWarningModalOpen = false;
			dispatch('delete', checklist.id);
		} else {
			addToast($t('checklist.checklist_delete_error'), 'error');
		}
	}

	async function removeFromItinerary() {
		let itineraryItemId = itineraryItem?.id;
		let res = await fetch(
			`/api/collections/${itineraryItem?.collection}/itinerary-items/${itineraryItemId}/`,
			{
				method: 'DELETE'
			}
		);
		if (res.ok) {
			addToast('info', $t('itinerary.item_remove_success'));
			dispatch('removeFromItinerary', itineraryItem);
		} else {
			addToast('error', $t('itinerary.item_remove_error'));
		}
	}

	async function toggleItemStatus(itemId: string) {
		if (!canEdit || !itemId) return;

		const previousItems = checklist.items.map((item) => ({ ...item }));
		const updatedItems = checklist.items.map((item) =>
			item.id === itemId ? { ...item, is_checked: !item.is_checked } : item
		);
		const dateForApi = normalizeDateForApi(checklist.date);

		updatingItemId = itemId;
		checklist = { ...checklist, items: updatedItems };

		try {
			const res = await fetch(`/api/checklists/${checklist.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					name: checklist.name,
					date: dateForApi,
					items: updatedItems,
					collection: checklist.collection,
					is_public: checklist.is_public
				})
			});

			if (res.ok) {
				const data = await res.json();
				if (data) {
					checklist = data;
					dispatch('update', data);
				}
			} else {
				checklist = { ...checklist, items: previousItems };
				addToast('error', 'Unable to update checklist item');
			}
		} catch (error) {
			checklist = { ...checklist, items: previousItems };
			addToast('error', 'Unable to update checklist item');
			console.error(error);
		} finally {
			updatingItemId = null;
		}
	}
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_checklist')}
		button_text={$t('adventures.delete')}
		description={$t('adventures.checklist_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteChecklist}
	/>
{/if}

{#if isDetailsOpen}
	<dialog class="modal modal-open" open>
		<div class="modal-box max-w-3xl space-y-4">
			<div class="flex items-start justify-between gap-3">
				<div class="space-y-2">
					<div class="flex items-center gap-2">
						<h3 class="text-xl font-semibold leading-tight">{checklist.name}</h3>
						<div class="badge badge-primary badge-sm">{$t('adventures.checklist')}</div>
					</div>

					<div class="flex flex-wrap items-center gap-3 text-sm text-base-content/70">
						{#if checklist.date && checklist.date !== ''}
							<div class="flex items-center gap-2">
								<Calendar class="w-4 h-4 text-primary" />
								<span>
									{formatDisplayDate(checklist.date, dateFormat, { timeZone: 'UTC' })}
								</span>
							</div>
						{/if}
						{#if checklist.items.length > 0}
							{@const completedCount = checklist.items.filter((item) => item.is_checked).length}
							<div class="badge badge-ghost badge-sm">
								{completedCount}/{checklist.items.length}
								{$t('checklist.completed')}
							</div>
						{/if}
					</div>
				</div>
				<button
					type="button"
					class="btn btn-circle btn-ghost btn-sm"
					onclick={() => (isDetailsOpen = false)}
					aria-label={$t('about.close')}
				>
					<Close class="w-4 h-4" />
				</button>
			</div>

			{#if checklist.items.length > 0}
				<div class="space-y-2 max-h-96 overflow-y-auto pr-1">
					{#each checklist.items as item}
						{#if canEdit}
							<button
								type="button"
								onclick={() => toggleItemStatus(item.id)}
								disabled={updatingItemId === item.id}
								class="flex w-full items-center gap-3 rounded-lg bg-base-200/60 p-2 text-left transition-colors hover:bg-base-200 disabled:opacity-70"
							>
								{#if updatingItemId === item.id}
									<span class="loading loading-spinner loading-xs text-primary shrink-0"></span>
								{:else if item.is_checked}
									<CheckCircle class="w-5 h-5 text-success shrink-0" />
								{:else}
									<CheckboxBlankCircleOutline class="w-5 h-5 shrink-0" />
								{/if}
								<span
									class="flex-1 text-sm"
									class:line-through={item.is_checked}
									class:opacity-60={item.is_checked}
								>
									{item.name}
								</span>
							</button>
						{:else}
							<div class="flex items-center gap-3 rounded-lg bg-base-200/60 p-2">
								{#if item.is_checked}
									<CheckCircle class="w-5 h-5 text-success shrink-0" />
								{:else}
									<CheckboxBlankCircleOutline class="w-5 h-5 shrink-0" />
								{/if}
								<span
									class="flex-1 text-sm"
									class:line-through={item.is_checked}
									class:opacity-60={item.is_checked}
								>
									{item.name}
								</span>
							</div>
						{/if}
					{/each}
				</div>
			{:else}
				<p class="text-sm text-base-content/70">No items added yet.</p>
			{/if}

			<div class="modal-action">
				<button class="btn" onclick={() => (isDetailsOpen = false)}>Close</button>
			</div>
		</div>
		<form method="dialog" class="modal-backdrop">
			<button aria-label="close" onclick={() => (isDetailsOpen = false)}>Close</button>
		</form>
	</dialog>
{/if}
<div
	class="card h-full flex flex-col rounded-2xl border border-base-300/60 bg-base-100 shadow-xs transition-colors hover:border-base-300"
	aria-label="checklist-card"
>
	<div class="flex flex-1 flex-col gap-3 p-4">
		<div class="flex items-start gap-3">
			<div
				class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10"
				aria-hidden="true"
			>
				<ClipboardListOutline class="h-5 w-5 text-primary" />
			</div>
			<div class="min-w-0 flex-1">
				<h2 class="line-clamp-2 text-lg font-semibold leading-snug">{checklist.name}</h2>
				<p class="text-sm text-base-content/60">{$t('adventures.checklist')}</p>
			</div>

			<div class="-mr-1 -mt-1 flex shrink-0 items-center">
				<button
					class="btn btn-ghost btn-square btn-sm"
					onclick={() => (isDetailsOpen = true)}
					aria-label={$t('adventures.view')}
					type="button"
				>
					<Launch class="h-5 w-5" />
				</button>
				{#if canEdit}
					<CardActionsMenu label={$t('cards.item_actions')}>
						{#snippet children({ close })}
							<li>
								<button
									onclick={() => {
										close();
										editChecklist();
									}}
								>
									<FileDocumentEdit class="h-4 w-4" />
									{$t('lodging.edit')}
								</button>
							</li>
							{#if itineraryItem && itineraryItem.id}
								<div class="divider my-1"></div>
								{#if !itineraryItem.is_global}
									<li>
										<button
											onclick={() => {
												close();
												dispatch('moveToGlobal', { type: 'checklist', id: checklist.id });
											}}
										>
											<Globe class="h-4 w-4" />
											{$t('itinerary.move_to_trip_context')}
										</button>
									</li>
									<li>
										<button
											onclick={() => {
												close();
												changeDay();
											}}
										>
											<Calendar class="h-4 w-4" />
											{$t('itinerary.change_day')}
										</button>
									</li>
								{/if}
								<li>
									<button
										class="text-error"
										onclick={() => {
											close();
											removeFromItinerary();
										}}
									>
										<CalendarRemove class="h-4 w-4" />
										{itineraryItem.is_global
											? $t('itinerary.remove_from_trip_context')
											: $t('itinerary.remove_from_itinerary')}
									</button>
								</li>
							{/if}
							<div class="divider my-1"></div>
							<li>
								<button
									class="text-error"
									onclick={() => {
										close();
										isWarningModalOpen = true;
									}}
								>
									<TrashCan class="h-4 w-4" />
									{$t('adventures.delete')}
								</button>
							</li>
						{/snippet}
					</CardActionsMenu>
				{/if}
			</div>
		</div>

		{#if checklist.items.length > 0}
			<div class="space-y-1.5">
				<div class="flex items-center gap-2">
					<progress
						class="progress progress-primary h-1.5 flex-1"
						value={doneCount}
						max={checklist.items.length}
						aria-label={$t('cards.items_done', {
							values: { done: doneCount, total: checklist.items.length }
						})}
					></progress>
					<span class="shrink-0 text-xs text-base-content/60">
						{$t('cards.items_done', {
							values: { done: doneCount, total: checklist.items.length }
						})}
					</span>
				</div>

				<div class="space-y-0.5">
					{#each checklist.items.slice(0, 3) as item}
						{#if canEdit}
							<button
								type="button"
								onclick={() => toggleItemStatus(item.id)}
								disabled={updatingItemId === item.id}
								class="flex w-full items-center gap-2 rounded-lg px-2 py-1 text-left text-sm text-base-content/80 transition-colors hover:bg-base-200 disabled:opacity-60"
							>
								{#if updatingItemId === item.id}
									<span class="loading loading-spinner loading-xs text-primary"></span>
								{:else if item.is_checked}
									<CheckCircle class="h-4 w-4 shrink-0 text-success" />
								{:else}
									<CheckboxBlankCircleOutline class="h-4 w-4 shrink-0" />
								{/if}
								<span
									class="truncate"
									class:line-through={item.is_checked}
									class:opacity-60={item.is_checked}
								>
									{item.name}
								</span>
							</button>
						{:else}
							<div class="flex items-center gap-2 px-2 py-1 text-sm text-base-content/70">
								{#if item.is_checked}
									<CheckCircle class="h-4 w-4 shrink-0 text-success" />
								{:else}
									<CheckboxBlankCircleOutline class="h-4 w-4 shrink-0" />
								{/if}
								<span
									class="truncate"
									class:line-through={item.is_checked}
									class:opacity-60={item.is_checked}
								>
									{item.name}
								</span>
							</div>
						{/if}
					{/each}
					{#if checklist.items.length > 3}
						<p class="pl-8 text-sm text-base-content/60">
							+{checklist.items.length - 3}
							{$t('checklist.more_items')}
						</p>
					{/if}
				</div>
			</div>
		{/if}

		{#if checklist.date && checklist.date !== ''}
			<div class="mt-auto flex items-center gap-1.5 pt-1 text-sm text-base-content/70">
				<Calendar class="h-4 w-4 text-primary" />
				{formatDisplayDate(checklist.date, dateFormat, { timeZone: 'UTC' })}
			</div>
		{/if}
	</div>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
