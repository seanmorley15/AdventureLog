<script lang="ts">
	import { addToast } from '$lib/toasts';
	import type { Checklist, Collection, User } from '$lib/types';
	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';

	import Launch from '~icons/mdi/launch';
	import TrashCan from '~icons/mdi/trash-can';
	import Calendar from '~icons/mdi/calendar';
	import DeleteWarning from '../DeleteWarning.svelte';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import CheckCircle from '~icons/mdi/check-circle';
	import CheckboxBlankCircleOutline from '~icons/mdi/checkbox-blank-circle-outline';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Close from '~icons/mdi/close';
	import Globe from '~icons/mdi/globe';
	import type { CollectionItineraryItem } from '$lib/types';
	import { shouldFlipDropdownUp } from '$lib/utils/flipDropdown';

	let isActionsMenuOpen = false;
	let openUpward = false;
	let actionsMenuRef: HTMLDivElement | null = null;
	const ACTIONS_CLOSE_EVENT = 'card-actions-close';
	const handleCloseEvent = () => (isActionsMenuOpen = false);

	function handleDocumentClick(event: MouseEvent) {
		if (!isActionsMenuOpen) return;
		const target = event.target as Node | null;
		if (actionsMenuRef && target && !actionsMenuRef.contains(target)) {
			isActionsMenuOpen = false;
		}
	}

	function closeAllChecklistMenus() {
		window.dispatchEvent(new CustomEvent(ACTIONS_CLOSE_EVENT));
	}

	onMount(() => {
		document.addEventListener('click', handleDocumentClick);
		window.addEventListener(ACTIONS_CLOSE_EVENT, handleCloseEvent);
		return () => {
			document.removeEventListener('click', handleDocumentClick);
			window.removeEventListener(ACTIONS_CLOSE_EVENT, handleCloseEvent);
		};
	});

	export let checklist: Checklist;
	export let user: User | null = null;
	export let collection: Collection;
	export let readOnly: boolean = false;
	export let itineraryItem: CollectionItineraryItem | null = null;

	let isWarningModalOpen: boolean = false;
	let isDetailsOpen: boolean = false;
	let updatingItemId: string | null = null;

	$: canEdit =
		!readOnly &&
		(checklist.user == user?.uuid ||
			(collection && user && collection.shared_with?.includes(user.uuid)));

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
		let res = await fetch(`/api/itineraries/${itineraryItemId}`, {
			method: 'DELETE'
		});
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
		button_text="Delete"
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
									{new Date(checklist.date).toLocaleDateString(undefined, { timeZone: 'UTC' })}
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
					on:click={() => (isDetailsOpen = false)}
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
								on:click={() => toggleItemStatus(item.id)}
								disabled={updatingItemId === item.id}
								class="flex w-full items-center gap-3 rounded-lg bg-base-200/60 p-2 text-left transition-colors hover:bg-base-200 disabled:opacity-70"
							>
								{#if updatingItemId === item.id}
									<span class="loading loading-spinner loading-xs text-primary flex-shrink-0"
									></span>
								{:else if item.is_checked}
									<CheckCircle class="w-5 h-5 text-success flex-shrink-0" />
								{:else}
									<CheckboxBlankCircleOutline class="w-5 h-5 flex-shrink-0" />
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
									<CheckCircle class="w-5 h-5 text-success flex-shrink-0" />
								{:else}
									<CheckboxBlankCircleOutline class="w-5 h-5 flex-shrink-0" />
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
				<button class="btn" on:click={() => (isDetailsOpen = false)}>Close</button>
			</div>
		</div>
		<form method="dialog" class="modal-backdrop">
			<button aria-label="close" on:click={() => (isDetailsOpen = false)}>Close</button>
		</form>
	</dialog>
{/if}
<div
	class="card w-full max-w-md bg-base-300 shadow hover:shadow-md transition-all duration-200 border border-base-300 group"
	aria-label="checklist-card"
>
	<div class="card-body p-4 space-y-3">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<div class="flex-1 min-w-0">
				<h2 class="text-lg font-semibold line-clamp-2">{checklist.name}</h2>
				<div class="flex flex-wrap items-center gap-2 mt-2">
					<div class="badge badge-primary badge-sm">{$t('adventures.checklist')}</div>
				</div>
			</div>

			<div class="flex items-center gap-2">
				<button
					class="btn btn-square btn-sm p-1 text-base-content"
					on:click={() => (isDetailsOpen = true)}
					aria-label={$t('adventures.view')}
					type="button"
				>
					<Launch class="w-5 h-5" />
				</button>

				{#if canEdit}
					<div
						class="dropdown dropdown-end relative z-50"
						class:dropdown-open={isActionsMenuOpen}
						class:dropdown-top={openUpward}
						bind:this={actionsMenuRef}
					>
						<button
							type="button"
							class="btn btn-square btn-sm p-1 text-base-content"
							aria-haspopup="menu"
							on:click|stopPropagation={() => {
								if (isActionsMenuOpen) {
									isActionsMenuOpen = false;
									return;
								}
								closeAllChecklistMenus();
								openUpward = shouldFlipDropdownUp(actionsMenuRef);
								isActionsMenuOpen = true;
							}}
						>
							<DotsHorizontal class="w-5 h-5" />
						</button>
						<ul
							tabindex="-1"
							class="dropdown-content menu bg-base-100 rounded-box z-[9999] w-52 p-2 shadow-lg border border-base-300 max-h-[min(24rem,calc(100vh-2rem))] overflow-y-auto"
						>
							<li>
								<button
									on:click={() => {
										isActionsMenuOpen = false;
										editChecklist();
									}}
									class="flex items-center gap-2"
								>
									<FileDocumentEdit class="w-4 h-4" />
									{$t('lodging.edit')}
								</button>
							</li>
							{#if itineraryItem && itineraryItem.id}
								<div class="divider my-1"></div>
								{#if !itineraryItem.is_global}
									<li>
										<button
											on:click={() => {
												isActionsMenuOpen = false;
												dispatch('moveToGlobal', { type: 'checklist', id: checklist.id });
											}}
											class="flex items-center gap-2"
										>
											<Globe class="w-4 h-4" />
											{$t('itinerary.move_to_trip_context') || 'Move to Trip Context'}
										</button>
									</li>
									<li>
										<button
											on:click={() => {
												isActionsMenuOpen = false;
												changeDay();
											}}
											class=" flex items-center gap-2"
										>
											<Calendar class="w-4 h-4 text" />
											{$t('itinerary.change_day')}
										</button>
									</li>
								{/if}
								<li>
									<button
										on:click={() => {
											isActionsMenuOpen = false;
											removeFromItinerary();
										}}
										class="text-error flex items-center gap-2"
									>
										<CalendarRemove class="w-4 h-4 text-error" />
										{#if itineraryItem.is_global}
											{$t('itinerary.remove_from_trip_context') || 'Remove from Trip Context'}
										{:else}
											{$t('itinerary.remove_from_itinerary')}
										{/if}
									</button>
								</li>
							{/if}
							<div class="divider my-1"></div>
							<li>
								<button
									class="text-error flex items-center gap-2"
									on:click={() => {
										isActionsMenuOpen = false;
										isWarningModalOpen = true;
									}}
								>
									<TrashCan class="w-4 h-4" />
									{$t('adventures.delete')}
								</button>
							</li>
						</ul>
					</div>
				{/if}
			</div>
		</div>

		<!-- Checklist Items Preview -->
		{#if checklist.items.length > 0}
			<div class="space-y-1.5">
				{#each checklist.items.slice(0, 3) as item}
					{#if canEdit}
						<button
							type="button"
							on:click={() => toggleItemStatus(item.id)}
							disabled={updatingItemId === item.id}
							class="flex w-full items-center gap-1.5 rounded-lg px-2 py-0.5 text-left text-sm text-base-content/80 transition-colors hover:bg-base-200/80 disabled:opacity-60"
						>
							{#if updatingItemId === item.id}
								<span class="loading loading-spinner loading-xs text-primary"></span>
							{:else if item.is_checked}
								<CheckCircle class="w-4 h-4 text-success flex-shrink-0" />
							{:else}
								<CheckboxBlankCircleOutline class="w-4 h-4 flex-shrink-0" />
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
						<div class="flex items-center gap-1.5 text-sm text-base-content/70">
							{#if item.is_checked}
								<CheckCircle class="w-4 h-4 text-success flex-shrink-0" />
							{:else}
								<CheckboxBlankCircleOutline class="w-4 h-4 flex-shrink-0" />
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
					<div class="text-sm text-base-content/60 pl-6">
						+{checklist.items.length - 3}
						{$t('checklist.more_items')}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Inline Stats -->
		<div class="flex flex-wrap items-center gap-3 text-sm text-base-content/70">
			{#if checklist.date && checklist.date !== ''}
				<div class="flex items-center gap-1">
					<Calendar class="w-4 h-4 text-primary" />
					<span>{new Date(checklist.date).toLocaleDateString(undefined, { timeZone: 'UTC' })}</span>
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
