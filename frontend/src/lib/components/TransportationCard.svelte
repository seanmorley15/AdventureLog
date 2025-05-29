<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import type { Collection, Transportation, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import DeleteWarning from './DeleteWarning.svelte';
	// import ArrowDownThick from '~icons/mdi/arrow-down-thick';
	import { TRANSPORTATION_TYPES_ICONS } from '$lib';
	import { formatDateInTimezone } from '$lib/dateUtils';

	function getTransportationIcon(type: string) {
		if (type in TRANSPORTATION_TYPES_ICONS) {
			return TRANSPORTATION_TYPES_ICONS[type as keyof typeof TRANSPORTATION_TYPES_ICONS];
		} else {
			return '🚗';
		}
	}
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
	class="card w-full max-w-md bg-base-300 text-base-content shadow-2xl hover:shadow-3xl transition-all duration-300 border border-base-300 hover:border-primary/20 group"
>
	<div class="card-body p-6 space-y-4">
		<!-- Title & Mode -->
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
			<h2 class="card-title text-xl font-semibold truncate">{transportation.name}</h2>
			<div class="flex flex-wrap gap-2">
				<div class="badge badge-secondary">
					{$t(`transportation.modes.${transportation.type}`)}
					{' '}{getTransportationIcon(transportation.type)}
				</div>
				{#if transportation.type === 'plane' && transportation.flight_number}
					<div class="badge badge-neutral">{transportation.flight_number}</div>
				{/if}
				{#if unlinked}
					<div class="badge badge-error">{$t('adventures.out_of_range')}</div>
				{/if}
			</div>
		</div>

		<!-- Start Section -->
		<div class="space-y-2">
			{#if transportation.from_location}
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium">{$t('adventures.from')}:</span>
					<p class="text-sm break-words">{transportation.from_location}</p>
				</div>
			{/if}
			{#if transportation.date}
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium">{$t('adventures.start')}:</span>
					<p class="text-sm">
						{formatDateInTimezone(transportation.date, transportation.start_timezone)}
						{#if transportation.start_timezone}
							<span class="ml-1 text-xs opacity-60">({transportation.start_timezone})</span>
						{/if}
					</p>
				</div>
			{/if}
		</div>

		<!-- End Section -->
		<div class="space-y-2">
			{#if transportation.to_location}
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium">{$t('adventures.to')}:</span>
					<p class="text-sm break-words">{transportation.to_location}</p>
				</div>
			{/if}
			{#if transportation.end_date}
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium">{$t('adventures.end')}:</span>
					<p class="text-sm">
						{formatDateInTimezone(transportation.end_date, transportation.end_timezone)}
						{#if transportation.end_timezone}
							<span class="ml-1 text-xs opacity-60">({transportation.end_timezone})</span>
						{/if}
					</p>
				</div>
			{/if}
		</div>

		<!-- Actions -->
		{#if transportation.user_id == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
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
					class="btn btn-secondary btn-sm flex items-center gap-1"
					on:click={() => (isWarningModalOpen = true)}
					title={$t('adventures.delete')}
				>
					<TrashCanOutline class="w-5 h-5" />
					<span>{$t('adventures.delete')}</span>
				</button>
			</div>
		{/if}
	</div>
</div>
