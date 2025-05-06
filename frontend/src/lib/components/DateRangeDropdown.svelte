<script lang="ts">
	import type { Collection } from '$lib/types';
	import TimezoneSelector from './TimezoneSelector.svelte';
	import { t } from 'svelte-i18n';
	export let collection: Collection | null = null;
	import { updateLocalDate, updateUTCDate, validateDateRange, formatUTCDate } from '$lib/dateUtils';
	import { onMount } from 'svelte';

	// Initialize with browser's timezone
	let selectedTimezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;

	// Store the UTC dates as source of truth
	export let utcStartDate: string | null = null;
	export let utcEndDate: string | null = null;

	// Local display values
	let localStartDate: string = '';
	let localEndDate: string = '';

	let fullStartDate: string = '';
	let fullEndDate: string = '';

	let constrainDates: boolean = false;

	onMount(async () => {
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

	if (collection && collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
	}

	// Update local display dates whenever timezone or UTC dates change
	$: {
		localStartDate = updateLocalDate({
			utcDate: utcStartDate,
			timezone: selectedTimezone
		}).localDate;
		localEndDate = updateLocalDate({
			utcDate: utcEndDate,
			timezone: selectedTimezone
		}).localDate;
	}

	// Update UTC dates when local dates change
	function handleLocalDateChange() {
		utcStartDate = updateUTCDate({
			localDate: localStartDate,
			timezone: selectedTimezone
		}).utcDate;
		utcEndDate = updateUTCDate({
			localDate: localEndDate,
			timezone: selectedTimezone
		}).utcDate;
	}
</script>

<div class="collapse collapse-plus bg-base-200 mb-4 rounded-lg">
	<input type="checkbox" checked />
	<div class="collapse-title text-xl font-semibold">
		{$t('adventures.date_information')}
	</div>
	<div class="collapse-content space-y-6">
		<!-- Timezone Selector -->
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
			<TimezoneSelector bind:selectedTimezone />
		</div>

		<!-- Dates Input Section -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<!-- Start Date -->
			<div class="flex flex-col space-y-2">
				<label for="date" class="font-medium">
					{$t('adventures.start_date')}
				</label>

				<input
					type="datetime-local"
					id="date"
					name="date"
					bind:value={localStartDate}
					on:change={handleLocalDateChange}
					min={constrainDates ? fullStartDate : ''}
					max={constrainDates ? fullEndDate : ''}
					class="input input-bordered w-full"
				/>

				{#if collection && collection.start_date && collection.end_date}
					<label class="flex items-center gap-2 mt-2">
						<input
							type="checkbox"
							class="toggle toggle-primary"
							id="constrain_dates"
							name="constrain_dates"
							on:change={() => (constrainDates = !constrainDates)}
						/>
						<span class="label-text">{$t('adventures.date_constrain')}</span>
					</label>
				{/if}
			</div>

			<!-- End Date -->
			{#if localStartDate}
				<div class="flex flex-col space-y-2">
					<label for="end_date" class="font-medium">
						{$t('adventures.end_date')}
					</label>

					<input
						type="datetime-local"
						id="end_date"
						name="end_date"
						bind:value={localEndDate}
						on:change={handleLocalDateChange}
						min={constrainDates ? localStartDate : ''}
						max={constrainDates ? fullEndDate : ''}
						class="input input-bordered w-full"
					/>
				</div>
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

		<!-- 
		<div role="alert" class="alert shadow-lg bg-neutral text-neutral-content mt-6">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				class="stroke-info h-6 w-6 shrink-0"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
				></path>
			</svg>
			<span class="ml-2">
				{$t('lodging.current_timezone')}: {selectedTimezone}
			</span>
		</div> -->
	</div>
</div>
