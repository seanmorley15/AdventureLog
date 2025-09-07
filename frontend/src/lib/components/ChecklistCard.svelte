<script lang="ts">
	import { addToast } from '$lib/toasts';
	import type { Checklist, Collection, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';

	import Launch from '~icons/mdi/launch';
	import TrashCan from '~icons/mdi/trash-can';
	import Calendar from '~icons/mdi/calendar';
	import DeleteWarning from './DeleteWarning.svelte';
	import { isEntityOutsideCollectionDateRange } from '$lib/dateUtils';

	export let checklist: Checklist;
	export let user: User | null = null;
	export let collection: Collection;

	let isWarningModalOpen: boolean = false;

	let outsideCollectionRange: boolean = false;

	$: {
		outsideCollectionRange = isEntityOutsideCollectionDateRange(checklist, collection);
	}

	function editChecklist() {
		dispatch('edit', checklist);
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
<div
	class="card w-full max-w-md bg-base-300 text-base-content shadow-2xl hover:shadow-3xl transition-all duration-300 border border-base-300 hover:border-primary/20 group"
>
	<div class="card-body p-6 space-y-4">
		<!-- Header -->
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
			<h2 class="text-xl font-bold break-words">{checklist.name}</h2>
			<div class="flex flex-wrap gap-2">
				<div class="badge badge-primary">{$t('adventures.checklist')}</div>
				{#if outsideCollectionRange}
					<div class="badge badge-error">{$t('adventures.out_of_range')}</div>
				{/if}
			</div>
		</div>

		<!-- Checklist Stats -->
		{#if checklist.items.length > 0}
			<p class="text-sm">
				{checklist.items.length}
				{checklist.items.length > 1 ? $t('checklist.items') : $t('checklist.item')}
			</p>
		{/if}

		<!-- Date -->
		{#if checklist.date && checklist.date !== ''}
			<div class="inline-flex items-center gap-2 text-sm">
				<Calendar class="w-5 h-5 text-primary" />
				<p>{new Date(checklist.date).toLocaleDateString(undefined, { timeZone: 'UTC' })}</p>
			</div>
		{/if}

		<!-- Actions -->
		<div class="pt-4 border-t border-base-300 flex justify-end gap-2">
			<button class="btn btn-neutral btn-sm flex items-center gap-1" on:click={editChecklist}>
				<Launch class="w-5 h-5" />
				{$t('notes.open')}
			</button>
			{#if checklist.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
				<button
					id="delete_adventure"
					data-umami-event="Delete Checklist"
					class="btn btn-secondary btn-sm flex items-center gap-1"
					on:click={() => (isWarningModalOpen = true)}
				>
					<TrashCan class="w-5 h-5" />
					{$t('adventures.delete')}
				</button>
			{/if}
		</div>
	</div>
</div>
