<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from 'svelte-i18n';
	import type { Collection, CollectionItineraryItem, Transportation, User } from '#lib/types.js';
	import { addToast } from '#lib/toasts.js';
	import { dateFormatFromUser } from '#lib/dateFormat.js';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '#lib/money.js';
	import { getTransportationTypeIcon } from '#lib/typeIcons.js';

	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Calendar from '~icons/mdi/calendar';
	import Launch from '~icons/mdi/launch';
	import Globe from '~icons/mdi/globe';
	import Cash from '~icons/mdi/cash';
	import TimerOutline from '~icons/mdi/timer-outline';
	import MapMarkerDistance from '~icons/mdi/map-marker-distance';

	import DeleteWarning from '../DeleteWarning.svelte';
	import CardCarousel from '../CardCarousel.svelte';
	import TransportationRoutePreview from './TransportationRoutePreview.svelte';
	import CardActionsMenu from './parts/CardActionsMenu.svelte';
	import CardEndpoints from './parts/CardEndpoints.svelte';
	import CardRating from './parts/CardRating.svelte';
	import CardVisibility from './parts/CardVisibility.svelte';

	const dispatch = createEventDispatcher();

	interface Props {
		transportation: Transportation;
		user?: User | null;
		collection?: Collection | null;
		readOnly?: boolean;
		itineraryItem?: CollectionItineraryItem | null;
	}

	let {
		transportation,
		user = null,
		collection = null,
		readOnly = false,
		itineraryItem = null
	}: Props = $props();

	const dateFormat = $derived(dateFormatFromUser(user));
	let isWarningModalOpen: boolean = $state(false);

	const toMiles = (km: any) => (Number(km) * 0.621371).toFixed(1);

	const formatTravelDuration = (minutes: number | null | undefined) => {
		if (minutes === null || minutes === undefined || Number.isNaN(minutes)) return null;
		const safeMinutes = Math.max(0, Math.floor(minutes));
		const hours = Math.floor(safeMinutes / 60);
		const mins = safeMinutes % 60;
		const parts = [] as string[];
		if (hours) parts.push(`${hours}h`);
		parts.push(`${mins}m`);
		return parts.join(' ');
	};

	let ModeIcon = $derived(getTransportationTypeIcon(transportation.type));
	let durationLabel = $derived(formatTravelDuration(transportation.travel_duration_minutes));
	let distanceLabel = $derived(
		transportation.distance && !isNaN(+transportation.distance)
			? user?.measurement_system === 'imperial'
				? `${toMiles(transportation.distance)} mi`
				: `${(+transportation.distance).toFixed(1)} km`
			: null
	);
	let priceLabel = $derived(
		formatMoney(toMoneyValue(transportation.price, transportation.price_currency, DEFAULT_CURRENCY))
	);

	let routeGeojson = $derived(
		transportation?.attachments?.find((attachment) => attachment?.geojson)?.geojson ?? null
	);
	let hasPhotos = $derived((transportation.images?.length ?? 0) > 0);
	let hasMedia = $derived(!!routeGeojson || hasPhotos);

	let isOwnerOrCollaborator = $derived(
		transportation.user === user?.uuid ||
			!!(collection && user && collection.shared_with?.includes(user.uuid))
	);

	// Codes (JFK → LHR) read faster than names, so use them when both ends have one.
	let hasCodePair = $derived(Boolean(transportation.start_code && transportation.end_code));
	let start = $derived({
		label: $t('cards.departs'),
		code: hasCodePair ? transportation.start_code : null,
		place: hasCodePair ? null : (transportation.from_location ?? transportation.start_code),
		value: transportation.date,
		timezone: transportation.start_timezone
	});
	let hasEnd = $derived(
		Boolean(
			transportation.end_date ||
			transportation.to_location ||
			transportation.end_code ||
			hasCodePair
		)
	);
	let end = $derived(
		hasEnd
			? {
					label: $t('cards.arrives'),
					code: hasCodePair ? transportation.end_code : null,
					place: hasCodePair ? null : (transportation.to_location ?? transportation.end_code),
					value: transportation.end_date,
					timezone: transportation.end_timezone ?? transportation.start_timezone
				}
			: null
	);
	let showRoute = $derived(
		Boolean(transportation.date || transportation.from_location || transportation.start_code)
	);

	function editTransportation() {
		dispatch('edit', transportation);
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

	function changeDay() {
		dispatch('changeDay', { type: 'transportation', item: transportation, forcePicker: true });
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
		title={$t('adventures.delete_transportation')}
		button_text={$t('adventures.delete')}
		description={$t('adventures.transportation_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteTransportation}
	/>
{/if}

<div
	class="card h-full flex flex-col rounded-2xl border border-base-300/60 bg-base-100 shadow-xs transition-colors hover:border-base-300"
	aria-label="transportation-card"
>
	<!-- A GPX route or photos get a media band; otherwise the card opens on the journey itself. -->
	{#if hasMedia}
		<div class="relative overflow-hidden rounded-t-2xl">
			{#if routeGeojson}
				<TransportationRoutePreview
					geojson={routeGeojson}
					name={transportation.name}
					images={transportation.images}
				/>
			{:else}
				<CardCarousel images={transportation.images} icon={ModeIcon} name={transportation.name} />
			{/if}
			<div class="absolute right-2 top-2">
				<CardVisibility visibility={transportation.is_public ? 'public' : 'private'} />
			</div>
		</div>
	{/if}

	<div class="flex min-w-0 flex-1 flex-col gap-3 p-4">
		<div class="flex items-start gap-3">
			<div
				class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10"
				aria-hidden="true"
			>
				<ModeIcon class="h-5 w-5 text-primary" />
			</div>
			<div class="min-w-0 flex-1">
				<a
					href="/transportations/{transportation.id}"
					class="line-clamp-2 text-lg font-semibold leading-snug transition-colors hover:text-primary"
				>
					{transportation.name}
				</a>
				<p class="flex flex-wrap items-center gap-x-2 text-sm text-base-content/60">
					{$t(`transportation.modes.${transportation.type}`)}
					{#if transportation.type === 'plane' && transportation.flight_number}
						<span class="badge badge-primary badge-sm font-medium">
							{transportation.flight_number}
						</span>
					{/if}
				</p>
			</div>

			<div class="-mr-1 -mt-1 flex shrink-0 items-center">
				{#if !hasMedia}
					<CardVisibility
						visibility={transportation.is_public ? 'public' : 'private'}
						onPhoto={false}
					/>
				{/if}
				<button
					class="btn btn-ghost btn-square btn-sm"
					aria-label={$t('adventures.open_details')}
					onclick={() => goto(`/transportations/${transportation.id}`)}
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
										editTransportation();
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
												dispatch('moveToGlobal', { type: 'transportation', id: transportation.id });
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

		{#if showRoute}
			<CardEndpoints {start} {end} {dateFormat}>
				{#snippet between()}
					<ModeIcon class="h-4 w-4 text-primary" />
					{#if durationLabel}
						<span class="inline-flex items-center gap-1 whitespace-nowrap font-medium">
							<TimerOutline class="h-3.5 w-3.5" />
							{durationLabel}
						</span>
					{/if}
					{#if distanceLabel}
						<span class="inline-flex items-center gap-1 whitespace-nowrap">
							<MapMarkerDistance class="h-3.5 w-3.5" />
							{distanceLabel}
						</span>
					{/if}
				{/snippet}
			</CardEndpoints>
		{/if}

		{#if transportation.rating || priceLabel || (!end && (durationLabel || distanceLabel))}
			<div class="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1.5 pt-1 text-sm">
				<CardRating rating={transportation.rating} />
				{#if priceLabel}
					<span class="inline-flex items-center gap-1 text-base-content/70">
						<Cash class="h-4 w-4" />
						{priceLabel}
					</span>
				{/if}
				<!-- With no far end there's no connecting line, so duration and distance go here. -->
				{#if !end}
					{#if durationLabel}
						<span class="inline-flex items-center gap-1 text-base-content/70">
							<TimerOutline class="h-4 w-4" />
							{durationLabel}
						</span>
					{/if}
					{#if distanceLabel}
						<span class="inline-flex items-center gap-1 text-base-content/70">
							<MapMarkerDistance class="h-4 w-4" />
							{distanceLabel}
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
