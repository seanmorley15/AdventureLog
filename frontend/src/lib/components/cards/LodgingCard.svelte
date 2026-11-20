<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from 'svelte-i18n';
	import type { Collection, CollectionItineraryItem, Lodging, User } from '#lib/types.js';
	import { addToast } from '#lib/toasts.js';
	import { dateFormatFromUser } from '#lib/dateFormat.js';
	import { nightsBetween } from '#lib/dateUtils.js';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '#lib/money.js';
	import { getLodgingTypeIcon } from '#lib/typeIcons.js';

	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Calendar from '~icons/mdi/calendar';
	import CalendarRange from '~icons/mdi/calendar-range';
	import Launch from '~icons/mdi/launch';
	import Globe from '~icons/mdi/globe';
	import MapMarkerOutline from '~icons/mdi/map-marker-outline';
	import WeatherNight from '~icons/mdi/weather-night';
	import TicketConfirmationOutline from '~icons/mdi/ticket-confirmation-outline';
	import Cash from '~icons/mdi/cash';

	import DeleteWarning from '../DeleteWarning.svelte';
	import CardCarousel from '../CardCarousel.svelte';
	import CardActionsMenu from './parts/CardActionsMenu.svelte';
	import CardEndpoints from './parts/CardEndpoints.svelte';
	import CardRating from './parts/CardRating.svelte';
	import CardVisibility from './parts/CardVisibility.svelte';

	const dispatch = createEventDispatcher();

	interface Props {
		lodging: Lodging;
		user?: User | null;
		collection?: Collection | null;
		readOnly?: boolean;
		itineraryItem?: CollectionItineraryItem | null;
		isMultiDay?: boolean;
	}

	let {
		lodging,
		user = null,
		collection = null,
		readOnly = false,
		itineraryItem = null,
		isMultiDay = false
	}: Props = $props();

	const dateFormat = $derived(dateFormatFromUser(user));
	let isWarningModalOpen: boolean = $state(false);

	let TypeIcon = $derived(getLodgingTypeIcon(lodging.type));
	let hasPhotos = $derived((lodging.images?.length ?? 0) > 0);
	let isOwnerOrCollaborator = $derived(
		lodging.user == user?.uuid ||
			!!(collection && user && collection.shared_with?.includes(user.uuid))
	);
	let nights = $derived(nightsBetween(lodging.check_in, lodging.check_out, lodging.timezone));
	let priceLabel = $derived(
		formatMoney(toMoneyValue(lodging.price, lodging.price_currency, DEFAULT_CURRENCY))
	);

	// With both dates it's a stay; with one it's just that day, so show only what exists.
	let start = $derived(
		lodging.check_in
			? { label: $t('adventures.check_in'), value: lodging.check_in, timezone: lodging.timezone }
			: { label: $t('adventures.check_out'), value: lodging.check_out, timezone: lodging.timezone }
	);
	let end = $derived(
		lodging.check_in && lodging.check_out
			? { label: $t('adventures.check_out'), value: lodging.check_out, timezone: lodging.timezone }
			: null
	);

	function editLodging() {
		dispatch('edit', lodging);
	}

	async function deleteLodging() {
		let res = await fetch(`/api/lodgings/${lodging.id}`, {
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

	function changeDay() {
		dispatch('changeDay', { type: 'lodging', item: lodging, forcePicker: true });
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
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_lodging')}
		button_text={$t('adventures.delete')}
		description={$t('adventures.lodging_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteLodging}
	/>
{/if}

<div
	class="card h-full flex flex-col rounded-2xl border border-base-300/60 bg-base-100 shadow-xs transition-colors hover:border-base-300"
	aria-label="lodging-card"
>
	<!-- No photos means no empty image block: the card opens straight on the details. -->
	{#if hasPhotos}
		<div class="relative overflow-hidden rounded-t-2xl">
			<CardCarousel images={lodging.images} icon={TypeIcon} name={lodging.name} />
			<div class="absolute right-2 top-2">
				<CardVisibility visibility={lodging.is_public ? 'public' : 'private'} />
			</div>
		</div>
	{/if}

	<div class="flex min-w-0 flex-1 flex-col gap-3 p-4">
		<div class="flex items-start gap-3">
			<div
				class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10"
				aria-hidden="true"
			>
				<TypeIcon class="h-5 w-5 text-primary" />
			</div>
			<div class="min-w-0 flex-1">
				<a
					href="/lodging/{lodging.id}"
					class="line-clamp-2 text-lg font-semibold leading-snug transition-colors hover:text-primary"
				>
					{lodging.name}
				</a>
				<p class="text-sm text-base-content/60">{$t(`lodging.${lodging.type}`)}</p>
			</div>

			<div class="-mr-1 -mt-1 flex shrink-0 items-center">
				{#if !hasPhotos}
					<CardVisibility visibility={lodging.is_public ? 'public' : 'private'} onPhoto={false} />
				{/if}
				<button
					class="btn btn-ghost btn-square btn-sm"
					aria-label={$t('adventures.open_details')}
					onclick={() => goto(`/lodging/${lodging.id}`)}
				>
					<Launch class="h-5 w-5" />
				</button>
				{#if !readOnly && isOwnerOrCollaborator}
					<CardActionsMenu label={$t('cards.item_actions')}>
						{#snippet children({ close })}
							<li>
								<button
									onclick={() => {
										close();
										editLodging();
									}}
								>
									<FileDocumentEdit class="h-4 w-4" />
									{$t('transportation.edit')}
								</button>
							</li>
							{#if itineraryItem && itineraryItem.id}
								<div class="divider my-1"></div>
								{#if !itineraryItem.is_global}
									<li>
										<button
											onclick={() => {
												close();
												dispatch('moveToGlobal', { type: 'lodging', id: lodging.id });
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
									<TrashCanOutline class="h-4 w-4" />
									{$t('adventures.delete')}
								</button>
							</li>
						{/snippet}
					</CardActionsMenu>
				{/if}
			</div>
		</div>

		{#if lodging.location}
			<p class="flex min-w-0 items-center gap-1.5 text-sm text-base-content/70">
				<MapMarkerOutline class="h-4 w-4 shrink-0 text-primary" />
				<span class="truncate">{lodging.location}</span>
			</p>
		{/if}

		{#if lodging.check_in || lodging.check_out}
			<CardEndpoints {start} {end} {dateFormat}>
				{#snippet between()}
					<WeatherNight class="h-4 w-4 text-primary" />
					{#if nights}
						<span class="whitespace-nowrap font-medium">
							{$t('detail.nights', { values: { count: nights } })}
						</span>
					{/if}
				{/snippet}
			</CardEndpoints>
		{/if}

		{#if isMultiDay || lodging.rating || (isOwnerOrCollaborator && (lodging.reservation_number || priceLabel))}
			<div class="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1.5 pt-1 text-sm">
				{#if isMultiDay}
					<span class="badge badge-info badge-sm gap-1">
						<CalendarRange class="h-3.5 w-3.5" />
						{$t('itinerary.multi_day')}
					</span>
				{/if}
				<CardRating rating={lodging.rating} />
				{#if isOwnerOrCollaborator}
					{#if lodging.reservation_number}
						<span class="inline-flex min-w-0 items-center gap-1 text-base-content/70">
							<TicketConfirmationOutline class="h-4 w-4 shrink-0" />
							<span class="truncate font-mono text-xs">
								{$t('cards.confirmation', { values: { code: lodging.reservation_number } })}
							</span>
						</span>
					{/if}
					{#if priceLabel}
						<span class="inline-flex items-center gap-1 text-base-content/70">
							<Cash class="h-4 w-4" />
							{priceLabel}
						</span>
					{/if}
				{/if}
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
