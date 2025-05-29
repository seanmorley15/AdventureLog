<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import type { Collection, Lodging, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import DeleteWarning from './DeleteWarning.svelte';
	import { LODGING_TYPES_ICONS } from '$lib';
	import { formatDateInTimezone } from '$lib/dateUtils';

	const dispatch = createEventDispatcher();

	function getLodgingIcon(type: string) {
		if (type in LODGING_TYPES_ICONS) {
			return LODGING_TYPES_ICONS[type as keyof typeof LODGING_TYPES_ICONS];
		} else {
			return '🏨';
		}
	}
	export let lodging: Lodging;
	export let user: User | null = null;
	export let collection: Collection | null = null;

	let isWarningModalOpen: boolean = false;

	function editTransportation() {
		dispatch('edit', lodging);
	}

	let unlinked: boolean = false;

	$: {
		if (collection?.start_date && collection.end_date) {
			// Parse transportation dates
			let transportationStartDate = lodging.check_in
				? new Date(lodging.check_in.split('T')[0]) // Ensure proper date parsing
				: null;
			let transportationEndDate = lodging.check_out
				? new Date(lodging.check_out.split('T')[0])
				: null;

			// Parse collection dates
			let collectionStartDate = new Date(collection.start_date);
			let collectionEndDate = new Date(collection.end_date);

			// Check if the collection range is outside the transportation range
			const startOutsideRange =
				transportationStartDate &&
				collectionStartDate < transportationStartDate &&
				collectionEndDate < transportationStartDate;

			const endOutsideRange =
				transportationEndDate &&
				collectionStartDate > transportationEndDate &&
				collectionEndDate > transportationEndDate;

			unlinked = !!(
				startOutsideRange ||
				endOutsideRange ||
				(!transportationStartDate && !transportationEndDate)
			);
		}
	}

	async function deleteTransportation() {
		let res = await fetch(`/api/lodging/${lodging.id}`, {
			method: 'DELETE',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (!res.ok) {
			console.log($t('transportation.transportation_delete_error'));
		} else {
			addToast('info', $t('transportation.transportation_deleted'));
			isWarningModalOpen = false;
			dispatch('delete', lodging.id);
		}
	}
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_lodging')}
		button_text="Delete"
		description={$t('adventures.lodging_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteTransportation}
	/>
{/if}

<div
	class="card w-full max-w-md bg-base-300 text-base-content shadow-2xl hover:shadow-3xl transition-all duration-300 border border-base-300 hover:border-primary/20 group"
>
	<div class="card-body p-6 space-y-4">
		<!-- Header -->
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
			<h2 class="text-xl font-bold truncate">{lodging.name}</h2>
			<div class="flex flex-wrap gap-2">
				<div class="badge badge-secondary">
					{$t(`lodging.${lodging.type}`)}
					{getLodgingIcon(lodging.type)}
				</div>
				{#if unlinked}
					<div class="badge badge-error">{$t('adventures.out_of_range')}</div>
				{/if}
			</div>
		</div>

		<!-- Location Info -->
		<div class="space-y-2">
			{#if lodging.location}
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium">{$t('adventures.location')}:</span>
					<p class="text-sm break-words">{lodging.location}</p>
				</div>
			{/if}

			{#if lodging.check_in && lodging.check_out}
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium">{$t('adventures.dates')}:</span>
					<p class="text-sm">
						{formatDateInTimezone(lodging.check_in, lodging.timezone)} –
						{formatDateInTimezone(lodging.check_out, lodging.timezone)}
						{#if lodging.timezone}
							<span class="ml-1 text-xs opacity-60">({lodging.timezone})</span>
						{/if}
					</p>
				</div>
			{/if}
		</div>

		<!-- Reservation Info -->
		{#if lodging.user_id == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
			<div class="space-y-2">
				{#if lodging.reservation_number}
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium">{$t('adventures.reservation_number')}:</span>
						<p class="text-sm break-all">{lodging.reservation_number}</p>
					</div>
				{/if}
				{#if lodging.price}
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium">{$t('adventures.price')}:</span>
						<p class="text-sm">{lodging.price}</p>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Actions -->
		{#if lodging.user_id == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
			<div class="pt-4 border-t border-base-300 flex justify-end gap-2">
				<button
					class="btn btn-neutral btn-sm flex items-center gap-1"
					on:click={editTransportation}
					title={$t('transportation.edit')}
				>
					<FileDocumentEdit class="w-5 h-5" />
					<span>{$t('transportation.edit')}</span>
				</button>
				<button
					on:click={() => (isWarningModalOpen = true)}
					class="btn btn-secondary btn-sm flex items-center gap-1"
					title={$t('adventures.delete')}
				>
					<TrashCanOutline class="w-5 h-5" />
					<span>{$t('adventures.delete')}</span>
				</button>
			</div>
		{/if}
	</div>
</div>
