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
	let selectedTimezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;

	let allDay: boolean = false;

	// Store the UTC dates as source of truth
	export let utcStartDate: string | null = null;
	export let utcEndDate: string | null = null;

	console.log('UTC Start Date:', utcStartDate);
	console.log('UTC End Date:', utcEndDate);

	export let note: string | null = null;
	type Visit = {
		id: string;
		start_date: string;
		end_date: string;
		notes: string;
	};
	export let visits: Visit[] | null = null;

	// Local display values
	let localStartDate: string = '';
	let localEndDate: string = '';

	let fullStartDate: string = '';
	let fullEndDate: string = '';

	let constrainDates: boolean = false;

	let isEditing = false; // Disable reactivity when editing

	onMount(async () => {
		console.log('Selected timezone:', selectedTimezone);
		console.log('UTC Start Date:', utcStartDate);
		console.log('UTC End Date:', utcEndDate);
		// Initialize UTC dates from transportationToEdit if available
		localStartDate = updateLocalDate({
			utcDate: utcStartDate,
			timezone: selectedTimezone
		}).localDate;
		localEndDate = updateLocalDate({
			utcDate: utcEndDate,
			timezone: selectedTimezone
		}).localDate;
	});

	// Set the full date range for constraining purposes
	$: if (collection && collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
	}

	// Get constraint dates in the right format based on allDay setting
	$: constraintStartDate = allDay
		? fullStartDate
			? fullStartDate.split('T')[0]
			: ''
		: fullStartDate;
	$: constraintEndDate = allDay ? (fullEndDate ? fullEndDate.split('T')[0] : '') : fullEndDate;

	// Update local display dates whenever timezone or UTC dates change
	$: if (!isEditing) {
		if (allDay) {
			localStartDate = utcStartDate?.substring(0, 10) ?? '';
			localEndDate = utcEndDate?.substring(0, 10) ?? '';
		} else {
			const start = updateLocalDate({
				utcDate: utcStartDate,
				timezone: selectedTimezone
			}).localDate;

			const end = updateLocalDate({
				utcDate: utcEndDate,
				timezone: selectedTimezone
			}).localDate;

			localStartDate = start;
			localEndDate = end;
		}
	}

	// Update UTC dates when local dates change
	function handleLocalDateChange() {
		utcStartDate = updateUTCDate({
			localDate: localStartDate,
			timezone: selectedTimezone,
			allDay
		}).utcDate;

		utcEndDate = updateUTCDate({
			localDate: localEndDate,
			timezone: selectedTimezone,
			allDay
		}).utcDate;
	}
</script>

<div class="collapse collapse-plus bg-base-200 mb-4 rounded-lg">
	<input type="checkbox" />
	<div class="collapse-title text-xl font-semibold">
		{$t('adventures.date_information')}
	</div>
	<div class="collapse-content space-y-6">
		<!-- Timezone Selector -->
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
			<TimezoneSelector bind:selectedTimezone />
		</div>

		<div class="rounded-xl border border-base-300 bg-base-100 p-4 space-y-4 shadow-sm">
			<!-- Group Header -->
			<h3 class="text-md font-semibold">{$t('navbar.settings')}</h3>

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
							localStartDate = localStartDate.split('T')[0];
							localEndDate = localEndDate.split('T')[0];
						} else {
							localStartDate = localStartDate + 'T00:00';
							localEndDate = localEndDate + 'T23:59';
						}
						utcStartDate = updateUTCDate({
							localDate: localStartDate,
							timezone: selectedTimezone,
							allDay
						}).utcDate;
						utcEndDate = updateUTCDate({
							localDate: localEndDate,
							timezone: selectedTimezone,
							allDay
						}).utcDate;
						localStartDate = updateLocalDate({
							utcDate: utcStartDate,
							timezone: selectedTimezone
						}).localDate;
						localEndDate = updateLocalDate({
							utcDate: utcEndDate,
							timezone: selectedTimezone
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
					{$t('adventures.start_date')}
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
						{$t('adventures.end_date')}
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
					class="btn btn-primary"
					type="button"
					on:click={() => {
						const newVisit = {
							id: crypto.randomUUID(),
							start_date: utcStartDate ?? '',
							end_date: utcEndDate ?? utcStartDate ?? '',
							notes: note ?? ''
						};

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
		{#if !validateDateRange(localStartDate, localEndDate).valid}
			<div role="alert" class="alert alert-error">
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
			<div class="border-t border-neutral pt-4">
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
									{visit.start_date.split('T')[0]} – {visit.end_date.split('T')[0]}
								{:else}
									{new Date(visit.start_date).toLocaleString()} – {new Date(
										visit.end_date
									).toLocaleString()}
								{/if}
							</p>

							<!-- If the selected timezone is not the current one show the timezone + the time converted there -->

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

										if (isAllDayEvent) {
											localStartDate = visit.start_date.split('T')[0];
											localEndDate = visit.end_date.split('T')[0];
										} else {
											const startDate = new Date(visit.start_date);
											const endDate = new Date(visit.end_date);

											localStartDate = `${startDate.getFullYear()}-${String(
												startDate.getMonth() + 1
											).padStart(2, '0')}-${String(startDate.getDate()).padStart(2, '0')}T${String(
												startDate.getHours()
											).padStart(2, '0')}:${String(startDate.getMinutes()).padStart(2, '0')}`;

											localEndDate = `${endDate.getFullYear()}-${String(
												endDate.getMonth() + 1
											).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}T${String(
												endDate.getHours()
											).padStart(2, '0')}:${String(endDate.getMinutes()).padStart(2, '0')}`;
										}

										// remove it from visits
										if (visits) {
											visits = visits.filter((v) => v.id !== visit.id);
										}

										note = visit.notes;
										constrainDates = true;
										utcStartDate = visit.start_date;
										utcEndDate = visit.end_date;
										type = 'adventure';

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
