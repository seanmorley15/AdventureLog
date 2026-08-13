<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import type { Collection, Lodging, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import DeleteWarning from '../DeleteWarning.svelte';
	import { LODGING_TYPES_ICONS } from '$lib';
	import { formatDateInTimezone } from '$lib/dateUtils';
	import { formatAllDayDate } from '$lib/dateUtils';
	import { isAllDay } from '$lib';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '$lib/money';
	import CardCarousel from '../CardCarousel.svelte';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Launch from '~icons/mdi/launch';
	import Globe from '~icons/mdi/globe';
	import { goto } from '$app/navigation';
	import Calendar from '~icons/mdi/calendar';
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

	function closeAllLodgingMenus() {
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

	const dispatch = createEventDispatcher();

	function getLodgingIcon(type: string) {
		if (type in LODGING_TYPES_ICONS) {
			return LODGING_TYPES_ICONS[type as keyof typeof LODGING_TYPES_ICONS];
		} else {
			return '🏨';
		}
	}

	function renderStars(rating: number) {
		const stars = [];
		for (let i = 1; i <= 5; i++) {
			stars.push(i <= rating);
		}
		return stars;
	}

	const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';
	const getTimezoneLabel = (zone?: string | null) => zone ?? localTimeZone;
	const getTimezoneTip = (zone?: string | null) => {
		const label = getTimezoneLabel(zone);
		return label === localTimeZone
			? null
			: `${$t('adventures.trip_timezone') ?? 'Trip TZ'}: ${label}. ${
					$t('adventures.your_time') ?? 'Your time'
				}: ${localTimeZone}.`;
	};
	const shouldShowTzBadge = (zone?: string | null) => {
		if (!zone) return false;
		return getTimezoneLabel(zone) !== localTimeZone;
	};
	const hasTimePortion = (date: string | null) => !!date && !isAllDay(date);
	const isTimedStay = (date: string | null) => hasTimePortion(date);
	$: lodgingPriceLabel = formatMoney(
		toMoneyValue(lodging.price, lodging.price_currency, DEFAULT_CURRENCY)
	);

	let showMoreDetails = false;
	$: hasExpandableDetails = Boolean(
		lodging.check_out && (isTimedStay(lodging.check_out) || isTimedStay(lodging.check_in))
	);
	$: if (!hasExpandableDetails) showMoreDetails = false;

	export let lodging: Lodging;
	export let user: User | null = null;
	export let collection: Collection | null = null;
	export let readOnly: boolean = false;
	export let itineraryItem: CollectionItineraryItem | null = null;
	export let isMultiDay: boolean = false;

	let isWarningModalOpen: boolean = false;

	function editTransportation() {
		dispatch('edit', lodging);
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

	function changeDay() {
		dispatch('changeDay', { type: 'lodging', item: lodging, forcePicker: true });
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
	class="card w-full max-w-md bg-base-300 shadow hover:shadow-md transition-all duration-200 border border-base-300 group"
	aria-label="lodging-card"
>
	<!-- Image Section with Overlay -->
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel images={lodging.images} icon={getLodgingIcon(lodging.type)} name={lodging.name} />

		<!-- Privacy Indicator -->
		<div class="absolute top-2 right-4">
			<div
				class="tooltip tooltip-left"
				data-tip={lodging.is_public ? $t('adventures.public') : $t('adventures.private')}
			>
				<div
					class="badge badge-sm p-1 rounded-full text-base-content shadow-sm"
					role="img"
					aria-label={lodging.is_public ? $t('adventures.public') : $t('adventures.private')}
				>
					{#if lodging.is_public}
						<Eye class="w-4 h-4" />
					{:else}
						<EyeOff class="w-4 h-4" />
					{/if}
				</div>
			</div>
		</div>

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
	<div class="card-body p-4 space-y-3 min-w-0">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<a
				href="/lodging/{lodging.id}"
				class="hover:text-primary transition-colors duration-200 line-clamp-2 text-lg font-semibold"
			>
				{lodging.name}
			</a>

			<div class="flex items-center gap-2">
				<button
					class="btn btn-sm p-1 text-base-content"
					aria-label="open-details"
					on:click={() => goto(`/lodging/${lodging.id}`)}
				>
					<Launch class="w-4 h-4" />
				</button>

				{#if !readOnly && (lodging.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid)))}
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
								closeAllLodgingMenus();
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
										editTransportation();
									}}
									class="flex items-center gap-2"
								>
									<FileDocumentEdit class="w-4 h-4" />
									{$t('transportation.edit')}
								</button>
							</li>
							{#if itineraryItem && itineraryItem.id}
								<div class="divider my-1"></div>
								{#if !itineraryItem.is_global}
									<li>
										<button
											on:click={() => {
												isActionsMenuOpen = false;
												dispatch('moveToGlobal', { type: 'lodging', id: lodging.id });
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
									<TrashCanOutline class="w-4 h-4" />
									{$t('adventures.delete')}
								</button>
							</li>
						</ul>
					</div>
				{/if}
			</div>
		</div>

		<!-- Location -->
		{#if lodging.location}
			<div class="flex items-center gap-2 text-sm text-base-content/70 min-w-0">
				<MapMarker class="w-4 h-4 text-primary flex-shrink-0" />
				<span class="truncate">{lodging.location}</span>
			</div>
		{/if}

		<!-- Check-in & Check-out Section -->
		{#if lodging.check_in || lodging.check_out}
			<div class="flex flex-col gap-1.5">
				{#if lodging.check_in && lodging.check_out}
					<!-- Both dates present -->
					{#if isAllDay(lodging.check_in) && isAllDay(lodging.check_out)}
						<!-- All-day dates -->
						<div class="flex items-center gap-2 text-sm">
							<span class="font-medium text-base-content">{formatAllDayDate(lodging.check_in)}</span
							>
							<span class="text-primary">→</span>
							<span class="font-medium text-base-content"
								>{formatAllDayDate(lodging.check_out)}</span
							>
						</div>
					{:else}
						<!-- Timed dates with tidy mini cards and toggle -->
						<div class="flex flex-col gap-2">
							<!-- Check-in Card (always shown) -->
							<div class="bg-base-200 rounded-lg px-3 py-2 flex flex-col gap-2">
								<div class="flex items-start justify-between gap-2">
									<div class="flex flex-col gap-0.5 min-w-0">
										<span class="text-xs text-base-content/60">Check-in</span>
										<span class="text-sm font-semibold text-base-content">
											{#if isAllDay(lodging.check_in)}
												{formatAllDayDate(lodging.check_in)}
											{:else}
												{formatDateInTimezone(lodging.check_in, lodging.timezone)}
											{/if}
										</span>
									</div>
								</div>

								{#if hasTimePortion(lodging.check_in) && shouldShowTzBadge(lodging.timezone)}
									<div class="flex items-center gap-2 text-xs text-base-content/70">
										<div class="tooltip" data-tip={getTimezoneTip(lodging.timezone) ?? undefined}>
											<span class="badge badge-ghost badge-sm">
												{getTimezoneLabel(lodging.timezone)}
											</span>
										</div>
									</div>
								{/if}
							</div>

							{#if hasExpandableDetails}
								<div class="flex justify-end">
									<button
										class="btn btn-neutral-200 btn-xs"
										aria-expanded={showMoreDetails}
										on:click={() => (showMoreDetails = !showMoreDetails)}
										type="button"
									>
										{showMoreDetails
											? ($t('common.show_less') ?? 'Hide details')
											: ($t('common.show_more') ?? 'Show more')}
									</button>
								</div>
							{/if}

							{#if showMoreDetails && hasExpandableDetails}
								<!-- Check-out Card (expandable) -->
								<div class="bg-base-200 rounded-lg px-3 py-2 flex flex-col gap-2">
									<div class="flex items-start justify-between gap-2">
										<div class="flex flex-col gap-0.5 min-w-0">
											<span class="text-xs text-base-content/60">Check-out</span>
											<span class="text-sm font-semibold text-base-content">
												{#if isAllDay(lodging.check_out)}
													{formatAllDayDate(lodging.check_out)}
												{:else}
													{formatDateInTimezone(lodging.check_out, lodging.timezone)}
												{/if}
											</span>
										</div>
									</div>

									{#if hasTimePortion(lodging.check_out) && shouldShowTzBadge(lodging.timezone)}
										<div class="flex items-center gap-2 text-xs text-base-content/70">
											<div class="tooltip" data-tip={getTimezoneTip(lodging.timezone) ?? undefined}>
												<span class="badge badge-ghost badge-sm">
													{getTimezoneLabel(lodging.timezone)}
												</span>
											</div>
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/if}
				{:else if lodging.check_in}
					<!-- Check-in only -->
					<div class="bg-base-200 rounded-lg px-3 py-2 flex flex-col gap-2">
						<div class="flex items-start justify-between gap-2">
							<div class="flex flex-col gap-0.5">
								<span class="text-xs text-base-content/60">Check-in</span>
								<span class="text-sm font-semibold text-base-content">
									{#if isAllDay(lodging.check_in)}
										{formatAllDayDate(lodging.check_in)}
									{:else}
										{formatDateInTimezone(lodging.check_in, lodging.timezone)}
									{/if}
								</span>
							</div>
						</div>

						{#if hasTimePortion(lodging.check_in) && shouldShowTzBadge(lodging.timezone)}
							<div class="flex items-center gap-2 text-xs text-base-content/70">
								<div class="tooltip" data-tip={getTimezoneTip(lodging.timezone) ?? undefined}>
									<span class="badge badge-ghost badge-sm">
										{getTimezoneLabel(lodging.timezone)}
									</span>
								</div>
							</div>
						{/if}
					</div>
				{:else if lodging.check_out}
					<!-- Check-out only -->
					<div class="bg-base-200 rounded-lg px-3 py-2 flex flex-col gap-2">
						<div class="flex items-start justify-between gap-2">
							<div class="flex flex-col gap-0.5">
								<span class="text-xs text-base-content/60">Check-out</span>
								<span class="text-sm font-semibold text-base-content">
									{#if isAllDay(lodging.check_out)}
										{formatAllDayDate(lodging.check_out)}
									{:else}
										{formatDateInTimezone(lodging.check_out, lodging.timezone)}
									{/if}
								</span>
							</div>
						</div>

						{#if hasTimePortion(lodging.check_out) && shouldShowTzBadge(lodging.timezone)}
							<div class="flex items-center gap-2 text-xs text-base-content/70">
								<div class="tooltip" data-tip={getTimezoneTip(lodging.timezone) ?? undefined}>
									<span class="badge badge-ghost badge-sm">
										{getTimezoneLabel(lodging.timezone)}
									</span>
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Rating & Info Badges -->
		<div class="flex flex-wrap items-center gap-2 text-sm">
			{#if isMultiDay}
				<span class="badge badge-info badge-sm gap-1">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-3 w-3"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
						/>
					</svg>
					{$t('itinerary.multi_day')}
				</span>
			{/if}

			{#if lodging.rating}
				<div class="flex items-center gap-1">
					<div class="flex -ml-1">
						{#each renderStars(lodging.rating) as filled}
							{#if filled}
								<Star class="w-4 h-4 text-warning fill-current" />
							{:else}
								<StarOutline class="w-4 h-4 text-base-content/30" />
							{/if}
						{/each}
					</div>
					<span class="text-xs text-base-content/60">({lodging.rating}/5)</span>
				</div>
			{/if}

			{#if lodging.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
				{#if lodging.reservation_number}
					<span class="badge badge-primary badge-sm font-medium">
						{$t('adventures.reservation')}: {lodging.reservation_number}
					</span>
				{/if}
				{#if lodgingPriceLabel}
					<span class="badge badge-ghost badge-sm">💰 {lodgingPriceLabel}</span>
				{/if}
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
