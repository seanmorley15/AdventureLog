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
		// Auto-detect all-day for transportation and lodging types
		if ((type === 'transportation' || type === 'lodging') && utcStartDate) {
			allDay = isAllDay(utcStartDate);
		}

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

<div
	class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
>
	<input type="checkbox" />
	<div class="collapse-title text-xl font-semibold bg-gradient-to-r from-primary/10 to-primary/5">
		<div class="flex items-center gap-3">
			<div class="p-2 bg-primary/10 rounded-lg">
				<svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
					/>
				</svg>
			</div>
			{$t('adventures.date_information')}
		</div>
	</div>
	<div class="collapse-content bg-base-100/50 p-6">
		<!-- Settings -->
		<div class="card bg-base-100 border border-base-300/50 mb-6">
			<div class="card-body p-4">
				<h3 class="text-lg font-bold mb-4">Settings</h3>

				<div class="space-y-3">
					{#if type === 'transportation'}
						<div class="grid grid-cols-2 gap-4">
							<div>
								<label class="label-text text-sm font-medium">Departure Timezone</label>
								<div class="mt-1">
									<TimezoneSelector bind:selectedTimezone={selectedStartTimezone} />
								</div>
							</div>
							<div>
								<label class="label-text text-sm font-medium">Arrival Timezone</label>
								<div class="mt-1">
									<TimezoneSelector bind:selectedTimezone={selectedEndTimezone} />
								</div>
							</div>
						</div>
					{:else}
						<div>
							<label class="label-text text-sm font-medium">Timezone</label>
							<div class="mt-1">
								<TimezoneSelector bind:selectedTimezone={selectedStartTimezone} />
							</div>
						</div>
					{/if}

					<div class="flex items-center justify-between">
						<label class="label-text text-sm font-medium">All Day</label>
						<input
							type="checkbox"
							class="toggle toggle-primary"
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

					{#if collection?.start_date && collection?.end_date}
						<div class="flex items-center justify-between">
							<label class="label-text text-sm font-medium">Constrain to Collection Dates</label>
							<input
								type="checkbox"
								class="toggle toggle-primary"
								on:change={() => (constrainDates = !constrainDates)}
							/>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<!-- Date Selection -->
		<div class="card bg-base-100 border border-base-300/50 mb-6">
			<div class="card-body p-4">
				<h3 class="text-lg font-bold mb-4">Date Selection</h3>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label class="label-text text-sm font-medium">
							{type === 'transportation'
								? 'Departure Date'
								: type === 'lodging'
									? 'Check In'
									: 'Start Date'}
						</label>
						{#if allDay}
							<input
								type="date"
								class="input input-bordered w-full mt-1"
								bind:value={localStartDate}
								on:change={handleLocalDateChange}
								min={constrainDates ? constraintStartDate : ''}
								max={constrainDates ? constraintEndDate : ''}
							/>
						{:else}
							<input
								type="datetime-local"
								class="input input-bordered w-full mt-1"
								bind:value={localStartDate}
								on:change={handleLocalDateChange}
								min={constrainDates ? constraintStartDate : ''}
								max={constrainDates ? constraintEndDate : ''}
							/>
						{/if}
					</div>

					{#if localStartDate}
						<div>
							<label class="label-text text-sm font-medium">
								{type === 'transportation'
									? 'Arrival Date'
									: type === 'lodging'
										? 'Check Out'
										: 'End Date'}
							</label>
							{#if allDay}
								<input
									type="date"
									class="input input-bordered w-full mt-1"
									bind:value={localEndDate}
									on:change={handleLocalDateChange}
									min={constrainDates ? localStartDate : ''}
									max={constrainDates ? constraintEndDate : ''}
								/>
							{:else}
								<input
									type="datetime-local"
									class="input input-bordered w-full mt-1"
									bind:value={localEndDate}
									on:change={handleLocalDateChange}
									min={constrainDates ? localStartDate : ''}
									max={constrainDates ? constraintEndDate : ''}
								/>
							{/if}
						</div>
					{/if}
				</div>

				{#if type === 'adventure'}
					<div class="mt-4">
						<label class="label-text text-sm font-medium">Notes</label>
						<textarea
							class="textarea textarea-bordered w-full mt-1"
							rows="3"
							placeholder="Add notes..."
							bind:value={note}
						></textarea>
					</div>

					<div class="flex justify-end mt-4">
						<button
							class="btn btn-primary btn-sm"
							type="button"
							on:click={() => {
								const newVisit = createVisitObject();
								if (visits) {
									visits = [...visits, newVisit];
								} else {
									visits = [newVisit];
								}
								note = '';
								localStartDate = '';
								localEndDate = '';
								utcStartDate = null;
								utcEndDate = null;
							}}
						>
							Add Visit
						</button>
					</div>
				{/if}
			</div>
		</div>

		<!-- Validation -->
		{#if !validateDateRange(utcStartDate ?? '', utcEndDate ?? '').valid}
			<div class="alert alert-error mb-6">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<span>Invalid date range</span>
			</div>
		{/if}

		<!-- Visits List -->
		{#if type === 'adventure'}
			<div class="card bg-base-100 border border-base-300/50">
				<div class="card-body p-4">
					<h3 class="text-lg font-bold mb-4">Visits</h3>

					{#if visits && visits.length === 0}
						<div class="text-center py-8 text-base-content/60">
							<p class="text-sm">No visits added yet</p>
						</div>
					{/if}

					{#if visits && visits.length > 0}
						<div class="space-y-3">
							{#each visits as visit}
								<div class="p-3 bg-base-200/50 rounded-lg border border-base-300/30">
									<div class="flex items-start justify-between">
										<div class="flex-1">
											<div class="text-sm font-medium mb-1">
												{#if isAllDay(visit.start_date)}
													<span class="badge badge-outline badge-sm mr-2">All Day</span>
													{visit.start_date && typeof visit.start_date === 'string'
														? visit.start_date.split('T')[0]
														: ''}
													– {visit.end_date && typeof visit.end_date === 'string'
														? visit.end_date.split('T')[0]
														: ''}
												{:else if 'start_timezone' in visit}
													{formatDateInTimezone(visit.start_date, visit.start_timezone)}
													– {formatDateInTimezone(visit.end_date, visit.end_timezone)}
												{:else if visit.timezone}
													{formatDateInTimezone(visit.start_date, visit.timezone)}
													– {formatDateInTimezone(visit.end_date, visit.timezone)}
												{:else}
													{new Date(visit.start_date).toLocaleString()}
													– {new Date(visit.end_date).toLocaleString()}
												{/if}
											</div>

											{#if visit.notes}
												<p class="text-xs text-base-content/70 mt-1">"{visit.notes}"</p>
											{/if}
										</div>

										<div class="flex gap-2">
											<button
												class="btn btn-primary btn-xs"
												type="button"
												on:click={() => {
													isEditing = true;
													const isAllDayEvent = isAllDay(visit.start_date);
													allDay = isAllDayEvent;

													if ('start_timezone' in visit) {
														selectedStartTimezone = visit.start_timezone;
														selectedEndTimezone = visit.end_timezone;
													} else if (visit.timezone) {
														selectedStartTimezone = visit.timezone;
													}

													if (isAllDayEvent) {
														localStartDate = visit.start_date.split('T')[0];
														localEndDate = visit.end_date.split('T')[0];
													} else {
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
												Edit
											</button>
											<button
												class="btn btn-error btn-xs"
												type="button"
												on:click={() => {
													if (visits) {
														visits = visits.filter((v) => v.id !== visit.id);
													}
												}}
											>
												Remove
											</button>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>
