<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import type { Collection, Transportation, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import DeleteWarning from './DeleteWarning.svelte';
	// import ArrowDownThick from '~icons/mdi/arrow-down-thick';

	const dispatch = createEventDispatcher();

	export let transportation: Transportation;
	export let user: User | null = null;
	export let collection: Collection | null = null;

	let isWarningModalOpen: boolean = false;

	function editTransportation() {
		dispatch('edit', transportation);
	}

	let unlinked: boolean = false;

	$: {
		if (collection?.start_date && collection.end_date) {
			// Parse transportation dates
			let transportationStartDate = transportation.date
				? new Date(transportation.date.split('T')[0]) // Ensure proper date parsing
				: null;
			let transportationEndDate = transportation.end_date
				? new Date(transportation.end_date.split('T')[0])
				: null;

			// Parse collection dates
			let collectionStartDate = new Date(collection.start_date);
			let collectionEndDate = new Date(collection.end_date);

			// // Debugging outputs
			// console.log(
			// 	'Transportation Start Date:',
			// 	transportationStartDate,
			// 	'Transportation End Date:',
			// 	transportationEndDate
			// );
			// console.log(
			// 	'Collection Start Date:',
			// 	collectionStartDate,
			// 	'Collection End Date:',
			// 	collectionEndDate
			// );

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
		let res = await fetch(`/api/transportations/${transportation.id}`, {
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
			dispatch('delete', transportation.id);
		}
	}
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_transportation')}
		button_text="Delete"
		description={$t('adventures.transportation_delete_confirm')}
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
		<div class="flex items-center justify-between">
			<h2 class="card-title text-lg font-semibold truncate">{transportation.name}</h2>
			<div class="flex items-center gap-2">
				<div class="badge badge-secondary">
					{$t(`transportation.modes.${transportation.type}`)}
				</div>
				{#if transportation.type == 'plane' && transportation.flight_number}
					<div class="badge badge-neutral-200">{transportation.flight_number}</div>
				{/if}
			</div>
		</div>
		{#if unlinked}
			<div class="badge badge-error">{$t('adventures.out_of_range')}</div>
		{/if}

		<!-- Locations -->
		<div class="space-y-2">
			{#if transportation.from_location}
				<div class="flex items-center gap-2">
					<span class="font-medium text-sm">{$t('adventures.from')}:</span>
					<p class="break-words">{transportation.from_location}</p>
				</div>
			{/if}
			{#if transportation.date}
				<div class="flex items-center gap-2">
					<span class="font-medium text-sm">{$t('adventures.start')}:</span>
					<p>{new Date(transportation.date).toLocaleString(undefined, { timeZone: 'UTC' })}</p>
				</div>
			{/if}
		</div>

		<!-- Dates -->
		<div class="space-y-2">
			{#if transportation.to_location}
				<!-- <ArrowDownThick class="w-4 h-4" /> -->
				<div class="flex items-center gap-2">
					<span class="font-medium text-sm">{$t('adventures.to')}:</span>

					<p class="break-words">{transportation.to_location}</p>
				</div>
			{/if}
			{#if transportation.end_date}
				<div class="flex items-center gap-2">
					<span class="font-medium text-sm">{$t('adventures.end')}:</span>
					<p>{new Date(transportation.end_date).toLocaleString(undefined, { timeZone: 'UTC' })}</p>
				</div>
			{/if}
		</div>

		<!-- Actions -->
		{#if transportation.user_id == user?.uuid || (collection && user && collection.shared_with && collection.shared_with.includes(user.uuid))}
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
