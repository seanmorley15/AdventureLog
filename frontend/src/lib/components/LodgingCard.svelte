<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import type { Collection, Lodging, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import DeleteWarning from './DeleteWarning.svelte';
	import { LODGING_TYPES_ICONS } from '$lib';

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
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-neutral text-neutral-content shadow-xl"
>
	<div class="card-body space-y-4">
		<!-- Title and Type -->
		<h2 class="text-2xl font-semibold">{lodging.name}</h2>
		<div>
			<div class="badge badge-secondary">
				{$t(`lodging.${lodging.type}`) + ' ' + getLodgingIcon(lodging.type)}
			</div>
			{#if unlinked}
				<div class="badge badge-error">{$t('adventures.out_of_range')}</div>
			{/if}
		</div>

		<!-- Location -->
		<div class="space-y-2">
			{#if lodging.location}
				<div class="flex items-center gap-2">
					<span class="font-medium text-sm">{$t('adventures.location')}:</span>
					<p>{lodging.location}</p>
				</div>
			{/if}

			{#if lodging.check_in && lodging.check_out}
				<div class="flex items-center gap-2">
					<span class="font-medium text-sm">{$t('adventures.dates')}:</span>
					<p>
						{new Date(lodging.check_in).toLocaleString(undefined, {
							month: 'short',
							day: 'numeric',
							year: 'numeric',
							hour: 'numeric',
							minute: 'numeric'
						})}
						-
						{new Date(lodging.check_out).toLocaleString(undefined, {
							month: 'short',
							day: 'numeric',
							year: 'numeric',
							hour: 'numeric',
							minute: 'numeric'
						})}
					</p>
				</div>
			{/if}
			{#if lodging.user_id == user?.uuid || (collection && user && collection.shared_with && collection.shared_with.includes(user.uuid))}
				{#if lodging.reservation_number}
					<div class="flex items-center gap-2">
						<span class="font-medium text-sm">{$t('adventures.reservation_number')}:</span>
						<p>{lodging.reservation_number}</p>
					</div>
				{/if}
				{#if lodging.price}
					<div class="flex items-center gap-2">
						<span class="font-medium text-sm">{$t('adventures.price')}:</span>
						<p>{lodging.price}</p>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Actions -->
		{#if lodging.user_id == user?.uuid || (collection && user && collection.shared_with && collection.shared_with.includes(user.uuid))}
			<div class="card-actions justify-end">
				<button
					class="btn btn-primary btn-sm flex items-center gap-1"
					on:click={editTransportation}
					title="Edit"
				>
					<FileDocumentEdit class="w-5 h-5" />
					<span>{$t('transportation.edit')}</span>
				</button>
				<button
					on:click={() => (isWarningModalOpen = true)}
					class="btn btn-secondary btn-sm flex items-center gap-1"
					title="Delete"
				>
					<TrashCanOutline class="w-5 h-5" />
					<span>{$t('adventures.delete')}</span>
				</button>
			</div>
		{/if}
	</div>
</div>
