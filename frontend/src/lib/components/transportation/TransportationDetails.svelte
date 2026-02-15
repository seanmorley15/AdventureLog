<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t, locale } from 'svelte-i18n';
	import { updateLocalDate, updateUTCDate, validateDateRange } from '$lib/dateUtils';
	import type { Collection, Lodging, Transportation, MoneyValue } from '$lib/types';
	import LocationSearchMap from '../shared/LocationSearchMap.svelte';

	// Icons
	import MapIcon from '~icons/mdi/map';
	import ClearIcon from '~icons/mdi/close';
	import InfoIcon from '~icons/mdi/information';
	import GenerateIcon from '~icons/mdi/lightning-bolt';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import SaveIcon from '~icons/mdi/content-save';
	import type { Category, User } from '$lib/types';
	import { TRANSPORTATION_TYPES_ICONS } from '$lib';
	import MarkdownEditor from '../MarkdownEditor.svelte';
	import TimezoneSelector from '../TimezoneSelector.svelte';
	import MoneyInput from '../shared/MoneyInput.svelte';
	import { DEFAULT_CURRENCY, normalizeMoneyPayload, toMoneyValue } from '$lib/money';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import { isAllDay } from '$lib';

	const dispatch = createEventDispatcher();

	let isReverseGeocoding = false;
	let airportMode = false;
	let previousTransportationType: string | null = null;

	let initialSelection: {
		name: string;
		lat: number;
		lng: number;
		location: string;
		category?: any;
	} | null = null;

	// Props (would be passed in from parent component)
	export let initialTransportation: any = null;
	export let currentUser: any = null;
	export let editingTransportation: any = null;
	export let collection: Collection | null = null;
	export let initialVisitDate: string | null = null; // Used to pre-fill visit date when adding from itinerary planner

	// Form data properties
	let transportation: any = {
		name: '',
		type: '',
		description: '',
		rating: NaN,
		link: '',
		date: null,
		end_date: null,
		start_timezone: null,
		end_timezone: null,
		flight_number: null,
		from_location: null,
		to_location: null,
		origin_latitude: null,
		origin_longitude: null,
		destination_latitude: null,
		destination_longitude: null,
		start_code: null,
		end_code: null,
		distance: null,
		collection: collection?.id,
		is_public: true,
		price: null,
		price_currency: DEFAULT_CURRENCY
	};
	const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	let selectedStartTimezone: string = browserTimezone;
	let selectedEndTimezone: string = browserTimezone;
	let localStartDate: string = '';
	let localEndDate: string = '';
	let allDay: boolean = true;
	let constrainDates: boolean = true;
	let fullStartDate: string = '';
	let fullEndDate: string = '';
	let startCodeField: string = '';
	let endCodeField: string = '';

	let user: User | null = null;
	let transportationToEdit: Transportation | null = null;
	let wikiError = '';
	let isGeneratingDesc = false;
	let ownerUser: User | null = null;
	let dateError = '';
	let moneyValue: MoneyValue = { amount: null, currency: DEFAULT_CURRENCY };
	let preferredCurrency: string = DEFAULT_CURRENCY;

	$: user = currentUser;
	$: transportationToEdit = editingTransportation;
	// Set the full date range for constraining purposes (from collection)
	$: if (collection && collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
	}
	// Only assign timezones when this is a timed transportation. Keep timezones null for all-day entries.
	$: {
		const departureZone = selectedStartTimezone || browserTimezone;
		const arrivalZone = selectedEndTimezone || departureZone;
		transportation.start_timezone = allDay ? null : departureZone;
		transportation.end_timezone = allDay ? null : arrivalZone;
		preferredCurrency = user?.default_currency || DEFAULT_CURRENCY;
		const isNewTransportation = !(initialTransportation && initialTransportation.id);
		const isEditing = Boolean(editingTransportation && editingTransportation.id);
		if (isNewTransportation && !isEditing && transportation.price_currency === DEFAULT_CURRENCY) {
			transportation.price_currency = preferredCurrency;
		}
		moneyValue =
			transportation.price === null
				? { amount: null, currency: transportation.price_currency || null }
				: toMoneyValue(transportation.price, transportation.price_currency, preferredCurrency);
	}

	function handleStartCodeInput(value: string) {
		startCodeField = value;
		transportation.start_code = normalizeCode(value);
	}

	function handleEndCodeInput(value: string) {
		endCodeField = value;
		transportation.end_code = normalizeCode(value);
	}

	function handleStartCodeEvent(event: Event) {
		const target = event.target as HTMLInputElement;
		handleStartCodeInput(target?.value || '');
	}

	function handleEndCodeEvent(event: Event) {
		const target = event.target as HTMLInputElement;
		handleEndCodeInput(target?.value || '');
	}

	function normalizeCode(code: string | null): string | null {
		if (!code) return null;
		const trimmed = code.trim().toUpperCase();
		if (!trimmed) return null;
		return trimmed.slice(0, 5);
	}

	function clearAirportCodes() {
		startCodeField = '';
		endCodeField = '';
		transportation.start_code = null;
		transportation.end_code = null;
	}

	// Track previous airport mode to detect when user disables it
	let prevAirportMode = airportMode;
	$: if (prevAirportMode !== airportMode) {
		prevAirportMode = airportMode;
		// When airport mode is disabled, clear airport codes
		if (!airportMode) {
			clearAirportCodes();
		}
	}

	// Auto-enable airport mode only when transportation type CHANGES to plane
	// Do not continuously re-enable - respect user's manual toggle
	$: if (
		transportation.type === 'plane' &&
		previousTransportationType !== 'plane' &&
		!airportMode
	) {
		previousTransportationType = transportation.type;
		airportMode = true;
	} else if (transportation.type !== previousTransportationType) {
		previousTransportationType = transportation.type;
	}

	// Reactive constraints
	$: constraintStartDate = allDay
		? fullStartDate && fullStartDate.includes('T')
			? fullStartDate.split('T')[0]
			: ''
		: fullStartDate || '';
	$: constraintEndDate = allDay
		? fullEndDate && fullEndDate.includes('T')
			? fullEndDate.split('T')[0]
			: ''
		: fullEndDate || '';

	function handleTransportationUpdate(
		event: CustomEvent<{
			start: { name: string; lat: number; lng: number; location: string; code?: string | null };
			end: { name: string; lat: number; lng: number; location: string; code?: string | null };
		}>
	) {
		const { start, end } = event.detail;

		// Update from location - use name (e.g., "John F. Kennedy International Airport") not location (full address)
		transportation.from_location = start.name;
		transportation.origin_latitude = start.lat;
		transportation.origin_longitude = start.lng;
		transportation.start_code = normalizeCode(start.code || '');
		startCodeField = startCodeField || transportation.start_code || '';

		// Update to location - use name (e.g., "Zurich Airport") not location (full address)
		transportation.to_location = end.name;
		transportation.destination_latitude = end.lat;
		transportation.destination_longitude = end.lng;
		transportation.end_code = normalizeCode(end.code || '');
		endCodeField = endCodeField || transportation.end_code || '';

		// Update name if empty (use route)
		if (!transportation.name) {
			transportation.name = `${start.name} → ${end.name}`;
		}
	}

	function handleLocationClear() {
		transportation.from_location = null;
		transportation.to_location = null;
		transportation.origin_latitude = null;
		transportation.origin_longitude = null;
		transportation.destination_latitude = null;
		transportation.destination_longitude = null;
		transportation.start_code = null;
		transportation.end_code = null;
	}

	function handleAllDayToggle() {
		if (allDay) {
			localStartDate = localStartDate ? localStartDate.split('T')[0] : '';
			localEndDate = localEndDate ? localEndDate.split('T')[0] : '';
			// Clear timezones for all-day transportation
			transportation.start_timezone = null;
			transportation.end_timezone = null;
		} else {
			localStartDate = localStartDate ? `${localStartDate}T00:00` : '';
			localEndDate = localEndDate ? `${localEndDate}T23:59` : '';
			// Restore selected timezones when switching back to timed
			selectedEndTimezone = selectedEndTimezone || selectedStartTimezone;
			transportation.start_timezone = selectedStartTimezone;
			transportation.end_timezone = selectedEndTimezone;
		}

		syncAndValidateDates(false);
	}

	function handleLocalDateChange() {
		syncAndValidateDates(false);
	}

	function syncAndValidateDates(autoFillEnd: boolean): boolean {
		dateError = '';

		const departureZone = selectedStartTimezone || browserTimezone;
		const arrivalZone = selectedEndTimezone || departureZone;

		if (localEndDate && !localStartDate) {
			dateError = 'Start date is required when end date is provided';
			localEndDate = '';
			transportation.end_date = null;
		}

		transportation.date = localStartDate
			? updateUTCDate({ localDate: localStartDate, timezone: departureZone, allDay }).utcDate
			: null;
		transportation.end_date = localEndDate
			? updateUTCDate({ localDate: localEndDate, timezone: arrivalZone, allDay }).utcDate
			: null;

		if (!localEndDate && localStartDate && autoFillEnd) {
			const start = allDay
				? DateTime.fromISO(localStartDate, { zone: 'UTC' })
				: DateTime.fromISO(localStartDate, { zone: departureZone });
			if (start.isValid) {
				if (allDay) {
					const defaultEnd = start.plus({ days: 1 }).toISODate();
					if (defaultEnd) {
						localEndDate = defaultEnd;
						transportation.end_date = updateUTCDate({
							localDate: defaultEnd,
							timezone: arrivalZone,
							allDay
						}).utcDate;
					}
				} else {
					const defaultEnd = start
						.setZone(arrivalZone)
						.plus({ days: 1 })
						.set({ hour: 9, minute: 0, second: 0, millisecond: 0 });
					const defaultEndLocal = defaultEnd.toISO({
						suppressSeconds: true,
						suppressMilliseconds: true,
						includeOffset: false
					});
					if (defaultEndLocal) {
						localEndDate = defaultEndLocal.slice(0, 16);
						transportation.end_date = updateUTCDate({
							localDate: localEndDate,
							timezone: arrivalZone,
							allDay
						}).utcDate;
					}
				}
			}
		}

		if (transportation.date || transportation.end_date) {
			// validate start/end dates (constraints are handled elsewhere)
			const validation = validateDateRange(
				transportation.date || '',
				transportation.end_date || ''
			);
			if (!validation.valid) {
				dateError = validation.error || 'Invalid date range';
				transportation.end_date = null;
				localEndDate = '';
				return false;
			}
		}

		return true;
	}

	async function generateDesc() {
		if (!transportation.name) return;

		isGeneratingDesc = true;
		wikiError = '';

		try {
			// Mock Wikipedia API call - replace with actual implementation
			const response = await fetch(
				`/api/generate/desc/?name=${encodeURIComponent(transportation.name)}&lang=${$locale || 'en'}`
			);
			if (response.ok) {
				const data = await response.json();
				transportation.description = data.extract || '';
			} else {
				wikiError = `${$t('adventures.wikipedia_error') || 'Error fetching description from Wikipedia'}`;
			}
		} catch (error) {
			wikiError = `${$t('adventures.wikipedia_error') || ''}`;
		} finally {
			isGeneratingDesc = false;
		}
	}

	async function handleSave() {
		if (!transportation.name || !transportation.type) {
			return;
		}

		const departureZone = selectedStartTimezone || browserTimezone;
		const arrivalZone = selectedEndTimezone || departureZone;

		// Ensure timezones are only persisted for timed transportation
		transportation.start_timezone = allDay ? null : departureZone;
		transportation.end_timezone = allDay ? null : arrivalZone;

		// Normalize codes before sending
		transportation.start_code = normalizeCode(startCodeField || transportation.start_code);
		transportation.end_code = normalizeCode(endCodeField || transportation.end_code);

		if (!syncAndValidateDates(true)) {
			return;
		}

		// round origin and destination coordinates to 6 decimal places
		if (
			transportation.origin_latitude !== null &&
			typeof transportation.origin_latitude === 'number'
		) {
			transportation.origin_latitude = parseFloat(transportation.origin_latitude.toFixed(6));
		}
		if (
			transportation.origin_longitude !== null &&
			typeof transportation.origin_longitude === 'number'
		) {
			transportation.origin_longitude = parseFloat(transportation.origin_longitude.toFixed(6));
		}
		if (
			transportation.destination_latitude !== null &&
			typeof transportation.destination_latitude === 'number'
		) {
			transportation.destination_latitude = parseFloat(
				transportation.destination_latitude.toFixed(6)
			);
		}
		if (
			transportation.destination_longitude !== null &&
			typeof transportation.destination_longitude === 'number'
		) {
			transportation.destination_longitude = parseFloat(
				transportation.destination_longitude.toFixed(6)
			);
		}
		if (collection && collection.id) {
			transportation.collection = collection.id;
		}

		// Build payload and avoid sending an empty `collection` array when editing
		let payload: any = { ...transportation };

		// Normalize price and currency
		// Normalize price and currency consistently, but send explicit nulls when cleared
		if (transportation.price === null) {
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

		// If we're editing and the original location had collection, but the form's collection
		// is empty (i.e. user didn't modify collection), omit collection from payload so the
		// server doesn't clear them unintentionally.
		if (transportationToEdit && transportationToEdit.id) {
			if (
				(!payload.collection || payload.collection.length === 0) &&
				transportationToEdit.collection
			) {
				delete payload.collection;
			}

			let res = await fetch(`/api/transportations/${transportationToEdit.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
			let updatedLocation = await res.json();
			transportation = updatedLocation;
		} else {
			let res = await fetch(`/api/transportations`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
			let newTransportation = await res.json();
			transportation = newTransportation;
		}

		dispatch('save', {
			...transportation
		});
	}

	function handleBack() {
		dispatch('back');
	}

	onMount(() => {
		// Prefer transportation-specific timezones if present, otherwise keep current selection
		if (initialTransportation?.start_timezone) {
			selectedStartTimezone = initialTransportation.start_timezone;
		}
		if (initialTransportation?.end_timezone) {
			selectedEndTimezone = initialTransportation.end_timezone;
		} else if (initialTransportation?.start_timezone) {
			selectedEndTimezone = initialTransportation.start_timezone;
		}

		// Determine if existing dates are all-day using shared helper
		if (initialTransportation?.date) {
			allDay = isAllDay(initialTransportation.date);
		}

		const departureZone = selectedStartTimezone || browserTimezone;
		const arrivalZone = selectedEndTimezone || departureZone;

		// Keep transportation timezones null for all-day entries, otherwise use selected values
		transportation.start_timezone = allDay ? null : departureZone;
		transportation.end_timezone = allDay ? null : arrivalZone;

		// Convert UTC dates to local display, respecting all-day formatting
		if (initialTransportation?.date) {
			if (allDay) {
				localStartDate = initialTransportation.date.split('T')[0];
			} else {
				const result = updateLocalDate({
					utcDate: initialTransportation.date,
					timezone: departureZone
				});
				localStartDate = result.localDate;
			}
		}
		if (initialTransportation?.end_date) {
			if (allDay) {
				localEndDate = initialTransportation.end_date.split('T')[0];
			} else {
				const result = updateLocalDate({
					utcDate: initialTransportation.end_date,
					timezone: arrivalZone
				});
				localEndDate = result.localDate;
			}
		}

		if (initialTransportation && typeof initialTransportation === 'object') {
			// Populate all fields from initialTransportation
			transportation.name = initialTransportation.name || '';
			transportation.type = initialTransportation.type || '';
			transportation.link = initialTransportation.link || '';
			transportation.description = initialTransportation.description || '';
			transportation.rating = initialTransportation.rating ?? NaN;
			transportation.is_public = initialTransportation.is_public ?? true;
			transportation.flight_number = initialTransportation.flight_number || null;
			transportation.start_code = initialTransportation.start_code || null;
			transportation.end_code = initialTransportation.end_code || null;
			transportation.distance = initialTransportation.distance || null;
			transportation.price = initialTransportation.price
				? Number(initialTransportation.price)
				: null;
			transportation.price_currency = initialTransportation.price_currency || preferredCurrency;
			moneyValue = toMoneyValue(
				transportation.price,
				transportation.price_currency,
				preferredCurrency
			);

			// Populate origin/destination data
			transportation.from_location = initialTransportation.from_location || null;
			transportation.to_location = initialTransportation.to_location || null;
			transportation.origin_latitude = initialTransportation.origin_latitude || null;
			transportation.origin_longitude = initialTransportation.origin_longitude || null;
			transportation.destination_latitude = initialTransportation.destination_latitude || null;
			transportation.destination_longitude = initialTransportation.destination_longitude || null;
			startCodeField = transportation.start_code || '';
			endCodeField = transportation.end_code || '';

			if (initialTransportation.user) {
				ownerUser = initialTransportation.user;
			}
		}

		// If adding from itinerary, pre-fill all-day stay with next-day checkout
		if (!initialTransportation?.date && initialVisitDate && !localStartDate) {
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

<div class="min-h-screen bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5 p-6">
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
					bind:isReverseGeocoding
					transportationMode={true}
					bind:airportMode
					showDisplayNameInput={false}
					initialStartLocation={initialTransportation?.origin_latitude &&
					initialTransportation?.origin_longitude
						? {
								name: initialTransportation.from_location || '',
								lat: Number(initialTransportation.origin_latitude),
								lng: Number(initialTransportation.origin_longitude),
								location: initialTransportation.from_location || ''
							}
						: null}
					initialEndLocation={initialTransportation?.destination_latitude &&
					initialTransportation?.destination_longitude
						? {
								name: initialTransportation.to_location || '',
								lat: Number(initialTransportation.destination_latitude),
								lng: Number(initialTransportation.destination_longitude),
								location: initialTransportation.to_location || ''
							}
						: null}
					initialStartCode={initialTransportation?.start_code || null}
					initialEndCode={initialTransportation?.end_code || null}
					on:transportationUpdate={handleTransportationUpdate}
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
						<div class="form-control">
							<label class="label" for="name">
								<span class="label-text font-medium">
									{$t('adventures.name')} <span class="text-error">*</span>
								</span>
							</label>
							<input
								type="text"
								id="name"
								bind:value={transportation.name}
								class="input input-bordered bg-base-100/80 focus:bg-base-100"
								placeholder={$t('transportation.enter_transportation_name')}
								required
							/>
						</div>

						<!-- Type Field -->
						<div class="form-control">
							<label class="label" for="type">
								<span class="label-text font-medium"
									>{$t('transportation.type')} <span class="text-error">*</span></span
								>
							</label>
							<select
								class="select select-bordered w-full bg-base-100/80 focus:bg-base-100"
								name="type"
								id="type"
								required
								bind:value={transportation.type}
							>
								<option disabled value="">{$t('transportation.select_type')}</option>
								{#each Object.entries(TRANSPORTATION_TYPES_ICONS) as [key, icon]}
									<option value={key}>{icon} {key.charAt(0).toUpperCase() + key.slice(1)}</option>
								{/each}
							</select>
						</div>

						<!-- Flight Number Field -->
						<div class="form-control">
							<label class="label" for="flight_number">
								<span class="label-text font-medium">{$t('transportation.flight_number')}</span>
							</label>
							<input
								type="text"
								id="flight_number"
								bind:value={transportation.flight_number}
								class="input input-bordered bg-base-100/80 focus:bg-base-100"
								placeholder={$t('transportation.enter_flight_number')}
							/>
						</div>

						<!-- Start/End Codes -->
						{#if transportation.type === 'plane' || airportMode}
							<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
								<div class="form-control">
									<label class="label" for="start_code">
										<span class="label-text font-medium"
											>{$t('transportation.departure_code') || 'Departure code'}</span
										>
									</label>
									<input
										type="text"
										id="start_code"
										value={startCodeField}
										on:input={handleStartCodeEvent}
										class="input input-bordered bg-base-100/80 focus:bg-base-100 uppercase"
										maxlength="5"
										placeholder={airportMode ? 'JFK' : $t('transportation.departure_code')}
									/>
								</div>
								<div class="form-control">
									<label class="label" for="end_code">
										<span class="label-text font-medium"
											>{$t('transportation.arrival_code') || 'Arrival code'}</span
										>
									</label>
									<input
										type="text"
										id="end_code"
										value={endCodeField}
										on:input={handleEndCodeEvent}
										class="input input-bordered bg-base-100/80 focus:bg-base-100 uppercase"
										maxlength="5"
										placeholder={airportMode ? 'LHR' : $t('transportation.arrival_code')}
									/>
								</div>
							</div>
						{/if}

						<!-- Rating Field -->
						<div class="form-control">
							<label class="label" for="rating">
								<span class="label-text font-medium">{$t('adventures.rating')}</span>
							</label>
							<div
								class="flex items-center gap-4 p-3 bg-base-100/80 border border-base-300 rounded-lg"
							>
								<div class="rating">
									<input
										type="radio"
										name="rating"
										id="rating"
										class="rating-hidden"
										checked={Number.isNaN(transportation.rating)}
									/>
									{#each [1, 2, 3, 4, 5] as star}
										<input
											type="radio"
											name="rating"
											class="mask mask-star-2 bg-warning"
											on:click={() => (transportation.rating = star)}
											checked={transportation.rating === star}
										/>
									{/each}
								</div>
								{#if !Number.isNaN(transportation.rating)}
									<button
										type="button"
										class="btn btn-sm btn-error btn-outline gap-2"
										on:click={() => (transportation.rating = NaN)}
									>
										<ClearIcon class="w-4 h-4" />
										{$t('adventures.remove')}
									</button>
								{/if}
							</div>
						</div>
					</div>

					<!-- Right Column -->
					<div class="space-y-4">
						<!-- Link Field -->
						<div class="form-control">
							<label class="label" for="link">
								<span class="label-text font-medium">{$t('adventures.link')}</span>
							</label>
							<input
								type="url"
								id="link"
								bind:value={transportation.link}
								class="input input-bordered bg-base-100/80 focus:bg-base-100"
								placeholder={$t('transportation.enter_link')}
							/>
						</div>

						<MoneyInput
							label={$t('adventures.price')}
							value={moneyValue}
							on:change={(event) => {
								transportation.price = event.detail.amount;
								transportation.price_currency =
									event.detail.amount === null ? null : event.detail.currency || preferredCurrency;
							}}
						/>

						<!-- Description Field -->
						<div class="form-control">
							<label class="label" for="description">
								<span class="label-text font-medium">{$t('adventures.description')}</span>
							</label>
							<MarkdownEditor bind:text={transportation.description} editor_height="h-32" />

							<div class="flex items-center gap-4 mt-3">
								<button
									type="button"
									class="btn btn-neutral btn-sm gap-2"
									on:click={generateDesc}
									disabled={!transportation.name || isGeneratingDesc || !transportation.type}
								>
									{#if isGeneratingDesc}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<GenerateIcon class="w-4 h-4" />
									{/if}
									{$t('adventures.generate_desc')}
								</button>
								{#if wikiError}
									<div class="alert alert-error alert-sm">
										<InfoIcon class="w-4 h-4" />
										<span class="text-sm">{wikiError}</span>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Departure/Arrival Dates & Timezone Section -->
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
								bind:checked={allDay}
								on:change={handleAllDayToggle}
							/>
							<span class="label-text">{$t('adventures.all_day')}</span>
						</label>

						{#if collection}
							<label class="flex items-center gap-2 cursor-pointer">
								<input
									type="checkbox"
									class="toggle toggle-secondary"
									bind:checked={constrainDates}
								/>
								<span class="label-text">{$t('adventures.date_constrain')}</span>
							</label>
						{/if}
					</div>

					{#if dateError}
						<div class="alert alert-error bg-error/10 border border-error/30 text-error">
							<InfoIcon class="w-4 h-4" />
							<span class="text-sm">{dateError}</span>
						</div>
					{/if}

					<div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-4">
						<!-- Departure Date -->
						<div class="form-control">
							<label class="label" for="departure-date">
								<span class="label-text font-medium">{$t('transportation.departure_date')}</span>
							</label>
							{#if allDay}
								<input
									id="departure-date"
									type="date"
									class="input input-bordered bg-base-100/80 focus:bg-base-100"
									bind:value={localStartDate}
									on:change={handleLocalDateChange}
									min={constrainDates ? constraintStartDate : undefined}
									max={constrainDates ? constraintEndDate : undefined}
								/>
							{:else}
								<input
									id="departure-date"
									type="datetime-local"
									class="input input-bordered bg-base-100/80 focus:bg-base-100"
									bind:value={localStartDate}
									on:change={handleLocalDateChange}
									min={constrainDates ? constraintStartDate : undefined}
									max={constrainDates ? constraintEndDate : undefined}
								/>
							{/if}
						</div>

						<!-- Arrival Date -->
						<div class="form-control">
							<label class="label" for="arrival-date">
								<span class="label-text font-medium">{$t('transportation.arrival_date')}</span>
							</label>
							{#if allDay}
								<input
									id="arrival-date"
									type="date"
									class="input input-bordered bg-base-100/80 focus:bg-base-100"
									bind:value={localEndDate}
									on:change={handleLocalDateChange}
									min={constrainDates ? constraintStartDate : undefined}
									max={constrainDates ? constraintEndDate : undefined}
								/>
							{:else}
								<input
									id="arrival-date"
									type="datetime-local"
									class="input input-bordered bg-base-100/80 focus:bg-base-100"
									bind:value={localEndDate}
									on:change={handleLocalDateChange}
									min={constrainDates ? constraintStartDate : undefined}
									max={constrainDates ? constraintEndDate : undefined}
								/>
							{/if}
						</div>

						<!-- Timezone Selector (only for timed transportation) -->
						{#if !allDay}
							<TimezoneSelector
								bind:selectedTimezone={selectedStartTimezone}
								label={$t('transportation.departure_timezone') ?? 'Departure timezone'}
							/>
							<TimezoneSelector
								bind:selectedTimezone={selectedEndTimezone}
								label={$t('transportation.arrival_timezone') ?? 'Arrival timezone'}
							/>
						{/if}
					</div>
				</div>
			</div>
		</div>

		<!-- Action Buttons -->
		<div class="flex gap-3 justify-end pt-4">
			<button
				class="btn btn-primary gap-2"
				disabled={!transportation.name || !transportation.type || isReverseGeocoding}
				on:click={handleSave}
			>
				{#if isReverseGeocoding}
					<span class="loading loading-spinner loading-sm"></span>
					{$t('adventures.processing')}...
				{:else}
					<SaveIcon class="w-5 h-5" />
					{$t('adventures.continue')}
				{/if}
			</button>
		</div>
	</div>
</div>
