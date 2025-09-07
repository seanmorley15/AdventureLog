<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import type { Collection, Lodging, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import DeleteWarning from './DeleteWarning.svelte';
	import { LODGING_TYPES_ICONS } from '$lib';
	import { formatDateInTimezone, isEntityOutsideCollectionDateRange } from '$lib/dateUtils';
	import { formatAllDayDate } from '$lib/dateUtils';
	import { isAllDay } from '$lib';
	import CardCarousel from './CardCarousel.svelte';

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

	let outsideCollectionRange: boolean = false;

	$: {
		if (collection) {
			outsideCollectionRange = isEntityOutsideCollectionDateRange(lodging, collection);
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
	<!-- Image Section with Overlay -->
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel images={lodging.images} icon={getLodgingIcon(lodging.type)} name={lodging.name} />

		<!-- Category Badge -->
		{#if lodging.type}
			<div class="absolute bottom-4 left-4">
				<div class="badge badge-primary shadow-lg font-medium">
					{$t(`lodging.${lodging.type}`)}
					{getLodgingIcon(lodging.type)}
				</div>
			</div>
		{/if}
	</div>
	<div class="card-body p-6 space-y-4">
		<!-- Header -->
		<div class="flex flex-col gap-3">
			<h2 class="text-xl font-bold break-words">{lodging.name}</h2>
			<div class="flex flex-wrap gap-2">
				<div class="badge badge-secondary">
					{$t(`lodging.${lodging.type}`)}
					{getLodgingIcon(lodging.type)}
				</div>
				{#if outsideCollectionRange}
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

			<div class="space-y-3">
				{#if lodging.check_in}
					<div class="flex gap-2 text-sm">
						<span class="font-medium whitespace-nowrap">{$t('adventures.check_in')}:</span>
						<span>
							{#if isAllDay(lodging.check_in)}
								{formatAllDayDate(lodging.check_in)}
							{:else}
								{formatDateInTimezone(lodging.check_in, lodging.timezone)}
								{#if lodging.timezone}
									<span class="ml-1 text-xs opacity-60">({lodging.timezone})</span>
								{/if}
							{/if}
						</span>
					</div>
				{/if}

				{#if lodging.check_out}
					<div class="flex gap-2 text-sm">
						<span class="font-medium whitespace-nowrap">{$t('adventures.check_out')}:</span>
						<span>
							{#if isAllDay(lodging.check_out)}
								{formatAllDayDate(lodging.check_out)}
							{:else}
								{formatDateInTimezone(lodging.check_out, lodging.timezone)}
								{#if lodging.timezone}
									<span class="ml-1 text-xs opacity-60">({lodging.timezone})</span>
								{/if}
							{/if}
						</span>
					</div>
				{/if}
			</div>
		</div>

		<!-- Reservation Info -->
		{#if lodging.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
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
		{#if lodging.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
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
