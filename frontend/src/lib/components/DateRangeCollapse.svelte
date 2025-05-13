<script lang="ts">
	import type { Collection } from '$lib/types';
	import TimezoneSelector from './TimezoneSelector.svelte';
	import { t } from 'svelte-i18n';
	export let collection: Collection | null = null;
	import { updateLocalDate, updateUTCDate, validateDateRange, formatUTCDate } from '$lib/dateUtils';
	import { onMount } from 'svelte';
	import { isAllDay } from '$lib';

	export let type: 'adventure' | 'transportation' | 'lodging' = 'adventure';

	// Initialize with browser's timezone
	export let selectedStartTimezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;
	export let selectedEndTimezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;

	let allDay: boolean = false;

	// Store the UTC dates as source of truth
	export let utcStartDate: string | null = null;
	export let utcEndDate: string | null = null;

	export let note: string | null = null;
	type Visit = {
		id: string;
		start_date: string;
		end_date: string;
		notes: string;
		timezone: string | null;
	};

	type TransportationVisit = {
		id: string;
		start_date: string;
		end_date: string;
		notes: string;
		start_timezone: string;
		end_timezone: string;
	};

	export let visits: (Visit | TransportationVisit)[] | null = null;

	// Local display values
	let localStartDate: string = '';
	let localEndDate: string = '';

	let fullStartDate: string = '';
	let fullEndDate: string = '';

	let constrainDates: boolean = false;

	let isEditing = false; // Disable reactivity when editing

	onMount(async () => {
		// Initialize UTC dates
		localStartDate = updateLocalDate({
			utcDate: utcStartDate,
			timezone: selectedStartTimezone
		}).localDate;

		localEndDate = updateLocalDate({
			utcDate: utcEndDate,
			timezone: type === 'transportation' ? selectedEndTimezone : selectedStartTimezone
		}).localDate;

		if (!selectedStartTimezone) {
			selectedStartTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
		}
		if (!selectedEndTimezone) {
			selectedEndTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
		}
	});

	// Set the full date range for constraining purposes
	$: if (collection && collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
	}

	function formatDateInTimezone(utcDate: string, timezone: string): string {
		try {
			return new Intl.DateTimeFormat(undefined, {
				timeZone: timezone,
				year: 'numeric',
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit',
				hour12: true
			}).format(new Date(utcDate));
		} catch {
			return new Date(utcDate).toLocaleString(); // fallback
		}
	}

	// Get constraint dates in the right format based on allDay setting
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

	// Update local display dates whenever timezone or UTC dates change
	$: if (!isEditing) {
		if (allDay) {
			localStartDate = utcStartDate?.substring(0, 10) ?? '';
			localEndDate = utcEndDate?.substring(0, 10) ?? '';
		} else {
			const start = updateLocalDate({
				utcDate: utcStartDate,
				timezone: selectedStartTimezone
			}).localDate;

			const end = updateLocalDate({
				utcDate: utcEndDate,
				timezone: type === 'transportation' ? selectedEndTimezone : selectedStartTimezone
			}).localDate;

			localStartDate = start;
			localEndDate = end;
		}
	}

	// Update UTC dates when local dates change
	function handleLocalDateChange() {
		utcStartDate = updateUTCDate({
			localDate: localStartDate,
			timezone: selectedStartTimezone,
			allDay
		}).utcDate;

		utcEndDate = updateUTCDate({
			localDate: localEndDate,
			timezone: type === 'transportation' ? selectedEndTimezone : selectedStartTimezone,
			allDay
		}).utcDate;
	}

	function createVisitObject(): Visit | TransportationVisit {
		// Generate a unique ID using built-in methods
		const uniqueId = Date.now().toString(36) + Math.random().toString(36).substring(2);

		if (type === 'transportation') {
			const transportVisit: TransportationVisit = {
				id: uniqueId,
				start_date: utcStartDate ?? '',
				end_date: utcEndDate ?? utcStartDate ?? '',
				notes: note ?? '',
				start_timezone: selectedStartTimezone,
				end_timezone: selectedEndTimezone
			};
			return transportVisit;
		} else {
			const regularVisit: Visit = {
				id: uniqueId,
				start_date: utcStartDate ?? '',
				end_date: utcEndDate ?? utcStartDate ?? '',
				notes: note ?? '',
				timezone: selectedStartTimezone
			};
			return regularVisit;
		}
	}
</script>

<div class="collapse collapse-plus bg-base-200 mb-4 rounded-lg">
	<input type="checkbox" />
	<div class="collapse-title text-xl font-semibold">
		{$t('adventures.date_information')}
	</div>
	<div class="collapse-content">
		<!-- Timezone Selector Section -->
		<div class="rounded-xl border border-base-300 bg-base-100 p-4 space-y-4 shadow-sm mb-4">
			<!-- Group Header -->
			<h3 class="text-md font-semibold">{$t('navbar.settings')}</h3>

			{#if type === 'transportation'}
				<!-- Dual timezone selectors for transportation -->
				<div class="space-y-4">
					<div>
						<label class="text-sm font-medium block mb-1">
							{$t('adventures.departure_timezone')}
						</label>
						<TimezoneSelector bind:selectedTimezone={selectedStartTimezone} />
					</div>

					<div>
						<label class="text-sm font-medium block mb-1">
							{$t('adventures.arrival_timezone')}
						</label>
						<TimezoneSelector bind:selectedTimezone={selectedEndTimezone} />
					</div>
				</div>
			{:else}
				<!-- Single timezone selector for other types -->
				<TimezoneSelector bind:selectedTimezone={selectedStartTimezone} />
			{/if}

			<!-- All Day Toggle -->
			<div class="flex justify-between items-center">
				<span class="text-sm">{$t('adventures.all_day')}</span>
				<input
					type="checkbox"
					class="toggle toggle-primary"
					id="all_day"
					name="all_day"
					bind:checked={allDay}
					on:change={() => {
						if (allDay) {
							localStartDate = localStartDate ? localStartDate.split('T')[0] : '';
							localEndDate = localEndDate ? localEndDate.split('T')[0] : '';
						} else {
							localStartDate = localStartDate + 'T00:00';
							localEndDate = localEndDate + 'T23:59';
						}
						utcStartDate = updateUTCDate({
							localDate: localStartDate,
							timezone: selectedStartTimezone,
							allDay
						}).utcDate;
						utcEndDate = updateUTCDate({
							localDate: localEndDate,
							timezone: type === 'transportation' ? selectedEndTimezone : selectedStartTimezone,
							allDay
						}).utcDate;
						localStartDate = updateLocalDate({
							utcDate: utcStartDate,
							timezone: selectedStartTimezone
						}).localDate;
						localEndDate = updateLocalDate({
							utcDate: utcEndDate,
							timezone: type === 'transportation' ? selectedEndTimezone : selectedStartTimezone
						}).localDate;
					}}
				/>
			</div>

			<!-- Constrain Dates Toggle -->
			{#if collection?.start_date && collection?.end_date}
				<div class="flex justify-between items-center">
					<span class="text-sm">{$t('adventures.date_constrain')}</span>
					<input
						type="checkbox"
						id="constrain_dates"
						name="constrain_dates"
						class="toggle toggle-primary"
						on:change={() => (constrainDates = !constrainDates)}
					/>
				</div>
			{/if}
		</div>

		<!-- Dates Input Section -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<!-- Start Date -->
			<div class="space-y-2">
				<label for="date" class="text-sm font-medium">
					{type === 'transportation'
						? $t('adventures.departure_date')
						: $t('adventures.start_date')}
				</label>

				{#if allDay}
					<input
						type="date"
						id="date"
						name="date"
						bind:value={localStartDate}
						on:change={handleLocalDateChange}
						min={constrainDates ? constraintStartDate : ''}
						max={constrainDates ? constraintEndDate : ''}
						class="input input-bordered w-full"
					/>
				{:else}
					<input
						type="datetime-local"
						id="date"
						name="date"
						bind:value={localStartDate}
						on:change={handleLocalDateChange}
						min={constrainDates ? constraintStartDate : ''}
						max={constrainDates ? constraintEndDate : ''}
						class="input input-bordered w-full"
					/>
				{/if}
			</div>

			<!-- End Date -->
			{#if localStartDate}
				<div class="space-y-2">
					<label for="end_date" class="text-sm font-medium">
						{type === 'transportation' ? $t('adventures.arrival_date') : $t('adventures.end_date')}
					</label>

					{#if allDay}
						<input
							type="date"
							id="end_date"
							name="end_date"
							bind:value={localEndDate}
							on:change={handleLocalDateChange}
							min={constrainDates ? localStartDate : ''}
							max={constrainDates ? constraintEndDate : ''}
							class="input input-bordered w-full"
						/>
					{:else}
						<input
							type="datetime-local"
							id="end_date"
							name="end_date"
							bind:value={localEndDate}
							on:change={handleLocalDateChange}
							min={constrainDates ? localStartDate : ''}
							max={constrainDates ? constraintEndDate : ''}
							class="input input-bordered w-full"
						/>
					{/if}
				</div>
			{/if}

			<!-- Notes (for adventures only) -->
			{#if type === 'adventure'}
				<div class="md:col-span-2">
					<label for="note" class="text-sm font-medium block mb-1">
						{$t('adventures.add_notes')}
					</label>
					<textarea
						id="note"
						name="note"
						class="textarea textarea-bordered w-full"
						placeholder={$t('adventures.add_notes')}
						bind:value={note}
						rows="4"
					></textarea>
				</div>
			{/if}
			{#if type === 'adventure'}
				<button
					class="btn btn-primary mb-2"
					type="button"
					on:click={() => {
						const newVisit = createVisitObject();

						// Ensure reactivity by assigning a *new* array
						if (visits) {
							visits = [...visits, newVisit];
						} else {
							visits = [newVisit];
						}

						// Optionally clear the form
						note = '';
						localStartDate = '';
						localEndDate = '';
						utcStartDate = null;
						utcEndDate = null;
					}}
				>
					{$t('adventures.add')}
				</button>
			{/if}
		</div>

		<!-- Validation Message -->
		{#if !validateDateRange(utcStartDate ?? '', utcEndDate ?? '').valid}
			<div role="alert" class="alert alert-error mt-2">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-6 w-6 shrink-0 stroke-current"
					fill="none"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<span>{$t('adventures.invalid_date_range')}</span>
			</div>
		{/if}

		{#if type === 'adventure'}
			<div class="border-t border-neutral pt-4 mb-2">
				<h3 class="text-xl font-semibold">
					{$t('adventures.visits')}
				</h3>

				<!-- Visits List -->
				{#if visits && visits.length === 0}
					<p class="text-sm text-base-content opacity-70">
						{$t('adventures.no_visits')}
					</p>
				{/if}
			</div>

			{#if visits && visits.length > 0}
				<div class="space-y-4">
					{#each visits as visit}
						<div
							class="p-4 border border-neutral rounded-lg bg-base-100 shadow-sm flex flex-col gap-2"
						>
							<p class="text-sm text-base-content font-medium">
								{#if isAllDay(visit.start_date)}
									<span class="badge badge-outline mr-2">{$t('adventures.all_day')}</span>
									{visit.start_date ? visit.start_date.split('T')[0] : ''} – {visit.end_date
										? visit.end_date.split('T')[0]
										: ''}
								{:else if 'start_timezone' in visit}
									{formatDateInTimezone(visit.start_date, visit.start_timezone)} – {formatDateInTimezone(
										visit.end_date,
										visit.end_timezone
									)}
								{:else if visit.timezone}
									{formatDateInTimezone(visit.start_date, visit.timezone)} – {formatDateInTimezone(
										visit.end_date,
										visit.timezone
									)}
								{:else}
									{new Date(visit.start_date).toLocaleString()} – {new Date(
										visit.end_date
									).toLocaleString()}
									<!-- showe timezones badge -->
								{/if}
								{#if 'timezone' in visit && visit.timezone}
									<span class="badge badge-outline ml-2">{visit.timezone}</span>
								{/if}
							</p>

							<!--  -->

							<!-- Display timezone information for transportation visits -->
							{#if 'start_timezone' in visit && 'end_timezone' in visit && visit.start_timezone !== visit.end_timezone}
								<p class="text-xs text-base-content">
									{visit.start_timezone} → {visit.end_timezone}
								</p>
							{/if}

							{#if visit.notes}
								<p class="text-sm text-base-content opacity-70 italic">
									"{visit.notes}"
								</p>
							{/if}

							<div class="flex gap-2 mt-2">
								<button
									class="btn btn-primary btn-sm"
									type="button"
									on:click={() => {
										isEditing = true;
										const isAllDayEvent = isAllDay(visit.start_date);
										allDay = isAllDayEvent;

										// Set timezone information if available
										if ('start_timezone' in visit) {
											// TransportationVisit
											selectedStartTimezone = visit.start_timezone;
											selectedEndTimezone = visit.end_timezone;
										} else if (visit.timezone) {
											// Visit
											selectedStartTimezone = visit.timezone;
										}

										if (isAllDayEvent) {
											localStartDate = visit.start_date.split('T')[0];
											localEndDate = visit.end_date.split('T')[0];
										} else {
											// Update with timezone awareness
											localStartDate = updateLocalDate({
												utcDate: visit.start_date,
												timezone: selectedStartTimezone
											}).localDate;

											localEndDate = updateLocalDate({
												utcDate: visit.end_date,
												timezone:
													'end_timezone' in visit ? visit.end_timezone : selectedStartTimezone
											}).localDate;
										}

										// remove it from visits
										if (visits) {
											visits = visits.filter((v) => v.id !== visit.id);
										}

										note = visit.notes;
										constrainDates = true;
										utcStartDate = visit.start_date;
										utcEndDate = visit.end_date;

										setTimeout(() => {
											isEditing = false;
										}, 0);
									}}
								>
									{$t('lodging.edit')}
								</button>
								<button
									class="btn btn-error btn-sm"
									type="button"
									on:click={() => {
										if (visits) {
											visits = visits.filter((v) => v.id !== visit.id);
										}
									}}
								>
									{$t('adventures.remove')}
								</button>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
</div>
