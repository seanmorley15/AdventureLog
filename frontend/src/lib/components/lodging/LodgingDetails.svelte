<script lang="ts">
	import { run } from 'svelte/legacy';

	import { createEventDispatcher, onMount } from 'svelte';
	import { t, locale } from 'svelte-i18n';
	import {
		updateLocalDate,
		updateUTCDate,
		validateDateRange,
		toDateOnlyLocal,
		toTimedLocalDefault
	} from '$lib/dateUtils';
	import type { Collection, Lodging, MoneyValue } from '$lib/types';
	import LocationSearchMap from '../shared/LocationSearchMap.svelte';

	// Icons
	import MapIcon from '~icons/mdi/map';
	import ClearIcon from '~icons/mdi/close';
	import InfoIcon from '~icons/mdi/information';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import SaveIcon from '~icons/mdi/content-save';
	import type { Category, User } from '$lib/types';
	import MarkdownEditor from '../MarkdownEditor.svelte';
	import TimezoneSelector from '../TimezoneSelector.svelte';
	import MoneyInput from '../shared/MoneyInput.svelte';
	import { DEFAULT_CURRENCY, normalizeMoneyPayload, toMoneyValue } from '$lib/money';
	import { normalizeBasemapType } from '$lib';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import { isAllDay } from '$lib';
	import { addToast } from '$lib/toasts';

	const dispatch = createEventDispatcher();

	let isSaving = $state(false);
	let isReverseGeocoding = $state(false);

	let initialSelection: {
		name: string;
		lat: number;
		lng: number;
		location: string;
		category?: any;
	} | null = $state(null);

	
	interface Props {
		// Props (would be passed in from parent component)
		initialLodging?: any;
		currentUser?: any;
		editingLodging?: any;
		collection?: Collection | null;
		initialVisitDate?: string | null; // Used to pre-fill visit date when adding from itinerary planner
	}

	let {
		initialLodging = null,
		currentUser = null,
		editingLodging = $bindable(null),
		collection = null,
		initialVisitDate = null
	}: Props = $props();

	// Form data properties
	let lodging: {
		name: string;
		type: string;
		description: string;
		rating: number;
		link: string;
		check_in: string | null;
		check_out: string | null;
		timezone: string | null;
		reservation_number: string | null;
		price: number | null;
		price_currency: string | null;
		latitude: number | null;
		longitude: number | null;
		location: string;
		category?: Category | null;
		collection?: string;
		is_public?: boolean;
	} = $state({
		name: '',
		type: '',
		description: '',
		rating: NaN,
		link: '',
		check_in: null,
		check_out: null,
		timezone: null,
		reservation_number: null,
		price: null,
		price_currency: DEFAULT_CURRENCY,
		latitude: null,
		longitude: null,
		location: '',
		category: null,
		collection: undefined,
		is_public: true
	});

	let collectionId = $derived(collection?.id);

	let selectedTimezone: string = $state(Intl.DateTimeFormat().resolvedOptions().timeZone);
	let localStartDate: string = $state('');
	let localEndDate: string = $state('');
	let allDay: boolean = $state(true);
	let constrainDates: boolean = $state(true);
	let fullStartDate: string = $state('');
	let fullEndDate: string = $state('');

	let user: User | null = $state(null);
	let lodgingToEdit: Lodging | null = $state(null);
	let ownerUser: User | null = null;
	let dateError = $state('');
	let moneyValue: MoneyValue = $state({ amount: null, currency: DEFAULT_CURRENCY });
	let preferredCurrency: string = $state(DEFAULT_CURRENCY);

	run(() => {
		user = currentUser;
	});
	run(() => {
		lodgingToEdit = editingLodging;
	});
	// Only assign a timezone when this is a timed stay. Keep timezone null for all-day entries.
	run(() => {
		lodging.timezone = allDay ? null : selectedTimezone;
	});
	run(() => {
		preferredCurrency = user?.default_currency || DEFAULT_CURRENCY;
	});
	run(() => {
		const isNewLodging = !(initialLodging && initialLodging.id);
		const isEditing = Boolean(editingLodging && editingLodging.id);
		if (isNewLodging && !isEditing && lodging.price_currency === DEFAULT_CURRENCY) {
			lodging.price_currency = preferredCurrency;
		}
	});
	run(() => {
		moneyValue =
			lodging.price === null
				? { amount: null, currency: lodging.price_currency || preferredCurrency }
				: toMoneyValue(lodging.price, lodging.price_currency, preferredCurrency);
	});
	run(() => {
		initialSelection =
			initialLodging && initialLodging.latitude && initialLodging.longitude
				? {
						name: initialLodging.name || '',
						lat: Number(initialLodging.latitude),
						lng: Number(initialLodging.longitude),
						location: initialLodging.location || ''
					}
				: null;
	});

	// Set the full date range for constraining purposes
	run(() => {
		if (collection && collection.start_date && collection.end_date) {
			fullStartDate = `${collection.start_date}T00:00`;
			fullEndDate = `${collection.end_date}T23:59`;
		}
	});

	// Reactive constraints
	let constraintStartDate = $derived(allDay
		? fullStartDate && fullStartDate.includes('T')
			? fullStartDate.split('T')[0]
			: ''
		: fullStartDate || '');
	let constraintEndDate = $derived(allDay
		? fullEndDate && fullEndDate.includes('T')
			? fullEndDate.split('T')[0]
			: ''
		: fullEndDate || '');

	function handleLocationUpdate(
		event: CustomEvent<{ name?: string; lat: number; lng: number; location: string }>
	) {
		const { name, lat, lng, location } = event.detail;
		if (!lodging.name && name) lodging.name = name;
		lodging.latitude = lat;
		lodging.longitude = lng;
		lodging.location = location;
	}

	function handleLocationClear() {
		lodging.latitude = null;
		lodging.longitude = null;
		lodging.location = '';
	}

	function handleAllDayToggle(event: Event) {
		const nextAllDay = (event.currentTarget as HTMLInputElement).checked;

		if (nextAllDay) {
			localStartDate = toDateOnlyLocal(localStartDate);
			localEndDate = toDateOnlyLocal(localEndDate);
			lodging.timezone = null;
		} else {
			localStartDate = toTimedLocalDefault(localStartDate);
			localEndDate = toTimedLocalDefault(localEndDate, true);
			lodging.timezone = selectedTimezone;
		}

		allDay = nextAllDay;
		syncAndValidateDates(false);
	}

	function handleLocalDateChange() {
		syncAndValidateDates(false);
	}

	function syncAndValidateDates(autoFillEnd: boolean): boolean {
		dateError = '';

		if (localEndDate && !localStartDate) {
			dateError = 'Start date is required when end date is provided';
			localEndDate = '';
			lodging.check_out = null;
		}

		lodging.check_in = localStartDate
			? updateUTCDate({ localDate: localStartDate, timezone: selectedTimezone, allDay }).utcDate
			: null;
		lodging.check_out = localEndDate
			? updateUTCDate({ localDate: localEndDate, timezone: selectedTimezone, allDay }).utcDate
			: null;

		if (!localEndDate && localStartDate && autoFillEnd) {
			const start = allDay
				? DateTime.fromISO(localStartDate, { zone: 'UTC' })
				: DateTime.fromISO(localStartDate, { zone: selectedTimezone });
			if (start.isValid) {
				if (allDay) {
					const defaultEnd = start.plus({ days: 1 }).toISODate();
					if (defaultEnd) {
						localEndDate = defaultEnd;
						lodging.check_out = updateUTCDate({
							localDate: defaultEnd,
							timezone: selectedTimezone,
							allDay
						}).utcDate;
					}
				} else {
					const defaultEnd = start
						.plus({ days: 1 })
						.set({ hour: 9, minute: 0, second: 0, millisecond: 0 });
					const defaultEndLocal = defaultEnd.toISO({
						suppressSeconds: true,
						suppressMilliseconds: true,
						includeOffset: false
					});
					if (defaultEndLocal) {
						localEndDate = defaultEndLocal.slice(0, 16);
						lodging.check_out = updateUTCDate({
							localDate: localEndDate,
							timezone: selectedTimezone,
							allDay
						}).utcDate;
					}
				}
			}
		}

		if (lodging.check_in || lodging.check_out) {
			const validation = validateDateRange(lodging.check_in || '', lodging.check_out || '');
			if (!validation.valid) {
				dateError = validation.error || 'Invalid date range';
				lodging.check_out = null;
				localEndDate = '';
				return false;
			}
		}

		return true;
	}

	async function handleSave() {
		if (!lodging.name || !lodging.type) {
			return;
		}

		// Prevent double-clicks while saving
		if (isSaving) return;

		// Ensure timezone is only persisted for timed stays
		lodging.timezone = allDay ? null : selectedTimezone;

		if (!syncAndValidateDates(true)) {
			return;
		}

		// round latitude and longitude to 6 decimal places
		if (lodging.latitude !== null && typeof lodging.latitude === 'number') {
			lodging.latitude = parseFloat(lodging.latitude.toFixed(6));
		}
		if (lodging.longitude !== null && typeof lodging.longitude === 'number') {
			lodging.longitude = parseFloat(lodging.longitude.toFixed(6));
		}
		if (collectionId) {
			lodging.collection = collectionId;
		}

		// Build payload and avoid sending an empty `collection` array when editing
		let payload: any = { ...lodging };

		// Normalize price and currency consistently, but send explicit nulls when cleared
		if (lodging.price === null) {
			payload.price = null;
			payload.price_currency = null;
		} else {
			payload = normalizeMoneyPayload(payload, 'price', 'price_currency', preferredCurrency);
		}

		// Clean up link: empty/whitespace → null, invalid URL → null
		if (!payload.link || !payload.link.trim()) {
			payload.link = null;
		} else {
			try {
				new URL(payload.link);
			} catch {
				// Not a valid URL — clear it so Django doesn't reject it
				payload.link = null;
			}
		}

		isSaving = true;

		try {
			const persistedId =
				(lodgingToEdit && lodgingToEdit.id) || (lodging as { id?: string }).id || null;

			// If we're editing and the original location had collection, but the form's collection
			// is empty (i.e. user didn't modify collection), omit collection from payload so the
			// server doesn't clear them unintentionally.
			if (persistedId) {
				if (
					(!payload.collection || payload.collection.length === 0) &&
					lodgingToEdit?.collection &&
					lodgingToEdit.collection.length > 0
				) {
					delete payload.collection;
				}

				let res = await fetch(`/api/lodging/${persistedId}`, {
					method: 'PATCH',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(payload)
				});

				if (!res.ok) {
					const errorData = await res.json().catch(() => null);
					const errorMsg = errorData
						? Object.values(errorData).flat().join(', ')
						: `Server error (${res.status})`;
					addToast('error', errorMsg);
					return;
				}

				let updatedLocation = await res.json();
				lodging = updatedLocation;
			} else {
				let res = await fetch(`/api/lodging`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(payload)
				});

				if (!res.ok) {
					const errorData = await res.json().catch(() => null);
					const errorMsg = errorData
						? Object.values(errorData).flat().join(', ')
						: `Server error (${res.status})`;
					addToast('error', errorMsg);
					return;
				}

				let newLodging = await res.json();
				lodging = newLodging;
			}

			dispatch('save', {
				...lodging
			});
		} catch (err) {
			console.error('Error saving lodging:', err);
			addToast('error', $t('lodging.save_failed') || 'Failed to save lodging. Please try again.');
		} finally {
			isSaving = false;
		}
	}

	function handleBack() {
		dispatch('back');
	}

	onMount(() => {
		if (initialLodging && initialLodging.latitude && initialLodging.longitude) {
			lodging.latitude = initialLodging.latitude;
			lodging.longitude = initialLodging.longitude;
			if (!lodging.name) lodging.name = initialLodging.name || '';
			if (initialLodging.location) lodging.location = initialLodging.location;
		}
	});

	onMount(() => {
		// Prefer lodging timezone if present, otherwise keep current selection
		if (initialLodging?.timezone) {
			selectedTimezone = initialLodging.timezone;
		}

		// Determine if existing dates are all-day using shared helper
		if (initialLodging?.check_in) {
			allDay = isAllDay(initialLodging.check_in);
		}

		// Keep lodging.timezone null for all-day entries, otherwise use selectedTimezone
		lodging.timezone = allDay ? null : selectedTimezone;

		// Convert UTC dates to local display, respecting all-day formatting
		if (initialLodging?.check_in) {
			if (allDay) {
				localStartDate = initialLodging.check_in.split('T')[0];
			} else {
				const result = updateLocalDate({
					utcDate: initialLodging.check_in,
					timezone: selectedTimezone
				});
				localStartDate = result.localDate;
			}
		}
		if (initialLodging?.check_out) {
			if (allDay) {
				localEndDate = initialLodging.check_out.split('T')[0];
			} else {
				const result = updateLocalDate({
					utcDate: initialLodging.check_out,
					timezone: selectedTimezone
				});
				localEndDate = result.localDate;
			}
		}

		if (initialLodging && typeof initialLodging === 'object') {
			// Populate all fields from initialLodging
			lodging.name = initialLodging.name || '';
			lodging.type = initialLodging.type || '';
			lodging.link = initialLodging.link || '';
			lodging.description = initialLodging.description || '';
			lodging.rating = initialLodging.rating ?? NaN;
			lodging.is_public = initialLodging.is_public ?? true;
			lodging.reservation_number = initialLodging.reservation_number || null;
			const money = toMoneyValue(
				initialLodging.price,
				initialLodging.price_currency,
				preferredCurrency
			);
			lodging.price = money.amount;
			lodging.price_currency = money.currency || preferredCurrency;

			if (initialLodging.location) {
				lodging.location = initialLodging.location;
			}

			if (initialLodging.user) {
				ownerUser = initialLodging.user;
			}
		}

		// If adding from itinerary, pre-fill all-day stay with next-day checkout
		if (!initialLodging?.check_in && initialVisitDate && !localStartDate) {
			const start = DateTime.fromISO(initialVisitDate, { zone: 'UTC' });
			if (start.isValid) {
				allDay = true;
				localStartDate = start.toISODate() || '';
				const nextDay = start.plus({ days: 1 }).toISODate();
				localEndDate = nextDay || '';

				syncAndValidateDates(false);
			}
		}

		return () => {
			// no-op
		};
	});
</script>

<div class="h-full min-h-0 flex flex-col bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5">
	<div class="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-4 md:py-5">
	<div class="max-w-full mx-auto space-y-6">
		<!-- Location Search & Map Section - FIRST! -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-secondary/10 rounded-lg">
						<MapIcon class="w-5 h-5 text-secondary" />
					</div>
					<div>
						<h2 class="text-xl font-bold">{$t('adventures.location_map')}</h2>
					</div>
				</div>

				<LocationSearchMap
					{initialSelection}
					bind:isReverseGeocoding
					bind:displayName={lodging.location}
					basemapType={normalizeBasemapType(user?.map_style)}
					displayNamePosition="after"
					on:update={handleLocationUpdate}
					on:clear={handleLocationClear}
				/>
			</div>
		</div>

		<!-- Basic Information Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-primary/10 rounded-lg">
						<InfoIcon class="w-5 h-5 text-primary" />
					</div>
					<h2 class="text-xl font-bold">{$t('adventures.basic_information')}</h2>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
					<!-- Left Column -->
					<div class="space-y-4">
						<!-- Name Field -->
						<div class="flex flex-col">
							<label class="field-label" for="name">{$t('adventures.name')} <span class="text-error">*</span></label>
							<input
								type="text"
								id="name"
								bind:value={lodging.name}
								class="input bg-base-100/80 focus:bg-base-100"
								placeholder={$t('lodging.enter_lodging_name')}
								required
							/>
						</div>

						<!-- Type Field -->
						<div class="flex flex-col">
							<label class="field-label" for="type">
								{$t('transportation.type')} <span class="text-error">*</span>
							</label>
							<select
								class="select w-full bg-base-100 text-base-content"
								name="type"
								id="type"
								required
								bind:value={lodging.type}
							>
								<option disabled value="">{$t('transportation.select_type')}</option>
								<option value="hotel">{$t('lodging.hotel')}</option>
								<option value="hostel">{$t('lodging.hostel')}</option>
								<option value="resort">{$t('lodging.resort')}</option>
								<option value="bnb">{$t('lodging.bnb')}</option>
								<option value="campground">{$t('lodging.campground')}</option>
								<option value="cabin">{$t('lodging.cabin')}</option>
								<option value="apartment">{$t('lodging.apartment')}</option>
								<option value="house">{$t('lodging.house')}</option>
								<option value="villa">{$t('lodging.villa')}</option>
								<option value="motel">{$t('lodging.motel')}</option>
								<option value="other">{$t('lodging.other')}</option>
							</select>
						</div>

						<!-- Rating Field -->
						<div class="flex flex-col">
							<label class="field-label" for="rating">{$t('adventures.rating')}</label>
							<div
								class="flex items-center gap-4 p-3 bg-base-100/80 border border-base-300 rounded-lg"
							>
								<div class="rating">
									<input
										type="radio"
										name="rating"
										id="rating"
										class="rating-hidden"
										checked={Number.isNaN(lodging.rating)}
									/>
									{#each [1, 2, 3, 4, 5] as star}
										<input
											type="radio"
											name="rating"
											class="mask mask-star-2 bg-warning"
											onclick={() => (lodging.rating = star)}
											checked={lodging.rating === star}
										/>
									{/each}
								</div>
								{#if !Number.isNaN(lodging.rating)}
									<button
										type="button"
										class="btn btn-sm btn-error btn-outline gap-2"
										onclick={() => (lodging.rating = NaN)}
									>
										<ClearIcon class="w-4 h-4" />
										{$t('adventures.remove')}
									</button>
								{/if}
							</div>
						</div>

						<!-- Reservation Number -->
						<div class="flex flex-col">
							<label class="field-label" for="reservation">{$t('lodging.reservation_number')}</label>
							<input
								type="text"
								id="reservation"
								bind:value={lodging.reservation_number}
								class="input bg-base-100/80 focus:bg-base-100"
								placeholder={$t('lodging.enter_reservation_number')}
							/>
						</div>
					</div>

					<!-- Right Column -->
					<div class="space-y-4">
						<!-- Link Field -->
						<div class="flex flex-col">
							<label class="field-label" for="link">{$t('adventures.link')}</label>
							<input
								type="url"
								id="link"
								bind:value={lodging.link}
								class="input bg-base-100/80 focus:bg-base-100"
								placeholder={$t('transportation.enter_link')}
							/>
						</div>

						<MoneyInput
							label={$t('adventures.price')}
							value={moneyValue}
							defaultCurrency={preferredCurrency}
							on:change={(event) => {
								lodging.price = event.detail.amount;
								lodging.price_currency = event.detail.currency || preferredCurrency;
							}}
						/>

						<!-- Description Field -->
						<div class="flex flex-col">
							<label class="field-label" for="description">{$t('adventures.description')}</label>
							<MarkdownEditor
								id="description"
								bind:text={lodging.description}
								editor_height="h-32"
								enableFetch
								fetchName={lodging.name}
								fetchLang={$locale || 'en'}
								fetchDisabled={!lodging.name || !lodging.type}
							/>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Check-in/Check-out Dates & Timezone Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-info/10 rounded-lg">
						<svg class="w-5 h-5 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
							/>
						</svg>
					</div>
					<h2 class="text-xl font-bold">{$t('adventures.dates')}</h2>
				</div>

				<div class="space-y-4">
					<!-- All Day and Constrain Dates Toggles -->
					<div class="flex flex-wrap gap-4">
						<label class="flex items-center gap-2 cursor-pointer">
							<input
								type="checkbox"
								class="toggle toggle-primary"
								checked={allDay}
								onchange={handleAllDayToggle}
							/>
							<span class="font-semibold text-sm text-base-content">{$t('adventures.all_day')}</span>
						</label>

						{#if collection}
							<label class="flex items-center gap-2 cursor-pointer">
								<input
									type="checkbox"
									class="toggle toggle-secondary"
									bind:checked={constrainDates}
								/>
								<span class="font-semibold text-sm text-base-content">{$t('adventures.date_constrain')}</span>
							</label>
						{/if}
					</div>

					{#if dateError}
						<div class="alert alert-error bg-error/10 border border-error/30 text-error">
							<InfoIcon class="w-4 h-4" />
							<span class="text-sm">{dateError}</span>
						</div>
					{/if}

					<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
						<!-- Check-in Date -->
						<div class="flex flex-col">
							<label class="field-label" for="check-in">{$t('adventures.check_in')}</label>
							{#if allDay}
								<input
									id="check-in"
									type="date"
									class="input bg-base-100/80 focus:bg-base-100"
									bind:value={localStartDate}
									onchange={handleLocalDateChange}
									min={constrainDates ? constraintStartDate : undefined}
									max={constrainDates ? constraintEndDate : undefined}
								/>
							{:else}
								<input
									id="check-in"
									type="datetime-local"
									class="input bg-base-100/80 focus:bg-base-100"
									bind:value={localStartDate}
									onchange={handleLocalDateChange}
									min={constrainDates ? constraintStartDate : undefined}
									max={constrainDates ? constraintEndDate : undefined}
								/>
							{/if}
						</div>

						<!-- Check-out Date -->
						<div class="flex flex-col">
							<label class="field-label" for="check-out">{$t('adventures.check_out')}</label>
							{#if allDay}
								<input
									id="check-out"
									type="date"
									class="input bg-base-100/80 focus:bg-base-100"
									bind:value={localEndDate}
									onchange={handleLocalDateChange}
									min={constrainDates ? constraintStartDate : undefined}
									max={constrainDates ? constraintEndDate : undefined}
								/>
							{:else}
								<input
									id="check-out"
									type="datetime-local"
									class="input bg-base-100/80 focus:bg-base-100"
									bind:value={localEndDate}
									onchange={handleLocalDateChange}
									min={constrainDates ? constraintStartDate : undefined}
									max={constrainDates ? constraintEndDate : undefined}
								/>
							{/if}
						</div>

						<!-- Timezone Selector (only for timed stays) -->
						{#if !allDay}
							<TimezoneSelector bind:selectedTimezone />
						{/if}
					</div>
				</div>
			</div>
		</div>

	</div>
	</div>

		<!-- Action Buttons -->
		<div
			class="shrink-0 border-t border-base-300 bg-base-100/90 backdrop-blur-lg px-4 md:px-6 py-3 md:py-4 flex gap-3 justify-end"
		>
			<button
				class="btn btn-primary gap-2"
				disabled={!lodging.name || !lodging.type || isReverseGeocoding || isSaving}
				onclick={handleSave}
			>
				{#if isSaving}
					<span class="loading loading-spinner loading-sm"></span>
					{$t('adventures.saving') || 'Saving...'}
				{:else if isReverseGeocoding}
					<span class="loading loading-spinner loading-sm"></span>
					{$t('adventures.processing')}...
				{:else}
					<SaveIcon class="w-5 h-5" />
					{$t('adventures.continue')}
				{/if}
			</button>
		</div>
</div>

<style>
	select option {
		background-color: var(--color-base-100);
		color: var(--color-base-content);
	}
</style>
