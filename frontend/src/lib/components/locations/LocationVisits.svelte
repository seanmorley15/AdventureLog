<script lang="ts">
	import type { Collection } from '$lib/types';
	import TimezoneSelector from '../TimezoneSelector.svelte';
	import { t } from 'svelte-i18n';
	import { updateLocalDate, updateUTCDate, validateDateRange, formatUTCDate } from '$lib/dateUtils';
	import { onMount } from 'svelte';
	import { isAllDay } from '$lib';
	import { createEventDispatcher } from 'svelte';

	// Icons
	import CalendarIcon from '~icons/mdi/calendar';
	import ClockIcon from '~icons/mdi/clock';
	import MapMarkerIcon from '~icons/mdi/map-marker';
	import PlusIcon from '~icons/mdi/plus';
	import EditIcon from '~icons/mdi/pencil';
	import TrashIcon from '~icons/mdi/delete';
	import AlertIcon from '~icons/mdi/alert';
	import CheckIcon from '~icons/mdi/check';
	import SettingsIcon from '~icons/mdi/cog';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';

	// Props
	export let collection: Collection | null = null;
	export let type: 'location' | 'transportation' | 'lodging' = 'location';
	export let selectedStartTimezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;
	export let selectedEndTimezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;
	export let utcStartDate: string | null = null;
	export let utcEndDate: string | null = null;
	export let note: string | null = null;
	export let visits: (Visit | TransportationVisit)[] | null = null;
	export let objectId: string;

	const dispatch = createEventDispatcher();

	// Types
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

	// Component state
	let allDay: boolean = false;
	let localStartDate: string = '';
	let localEndDate: string = '';
	let fullStartDate: string = '';
	let fullEndDate: string = '';
	let constrainDates: boolean = false;
	let isEditing = false;
	let isExpanded = true;

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

	// Set the full date range for constraining purposes
	$: if (collection && collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
	}

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

	// Helper functions
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
			return new Date(utcDate).toLocaleString();
		}
	}

	function getTypeConfig() {
		switch (type) {
			case 'transportation':
				return {
					startLabel: 'Departure Date',
					endLabel: 'Arrival Date',
					icon: MapMarkerIcon,
					color: 'accent'
				};
			case 'lodging':
				return {
					startLabel: 'Check In',
					endLabel: 'Check Out',
					icon: CalendarIcon,
					color: 'secondary'
				};
			default:
				return {
					startLabel: 'Start Date',
					endLabel: 'End Date',
					icon: CalendarIcon,
					color: 'primary'
				};
		}
	}

	// Event handlers
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

	function handleAllDayToggle() {
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
	}

	function createVisitObject(): Visit | TransportationVisit {
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

	async function addVisit() {
		const newVisit = createVisitObject();

		// Add new visit to the visits array
		if (visits) {
			visits = [...visits, newVisit];
		} else {
			visits = [newVisit];
		}

		// Reset form fields
		note = '';
		localStartDate = '';
		localEndDate = '';
		utcStartDate = null;
		utcEndDate = null;

		// Patch updated visits array to location
		if (type === 'location' && objectId) {
			try {
				const response = await fetch(`/api/locations/${objectId}/`, {
					method: 'PATCH',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({ visits }) // Send updated visits array
				});

				if (!response.ok) {
					console.error('Failed to patch visits:', await response.text());
				}
			} catch (error) {
				console.error('Error patching visits:', error);
			}
		}
	}

	function editVisit(visit: Visit | TransportationVisit) {
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
				timezone: 'end_timezone' in visit ? visit.end_timezone : selectedStartTimezone
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

		// Update the visits array in the parent component
		if (type === 'location' && objectId) {
			fetch(`/api/locations/${objectId}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ visits }) // Send updated visits array
			});
		}
	}

	function removeVisit(visitId: string) {
		if (visits) {
			visits = visits.filter((v) => v.id !== visitId);
		}

		// Patch updated visits array to location
		if (type === 'location' && objectId) {
			fetch(`/api/locations/${objectId}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ visits }) // Send updated visits array
			});
		}
	}

	function handleBack() {
		dispatch('back');
	}

	function handleClose() {
		dispatch('close');
	}

	// Lifecycle
	onMount(async () => {
		if ((type === 'transportation' || type === 'lodging') && utcStartDate) {
			allDay = isAllDay(utcStartDate);
		}

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

	$: typeConfig = getTypeConfig();
	$: isDateValid = validateDateRange(utcStartDate ?? '', utcEndDate ?? '').valid;
</script>

<div class="card bg-base-100 border border-base-300 shadow-lg">
	<div class="card-body p-6">
		<!-- Header -->
		<div class="flex items-center justify-between mb-6">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-{typeConfig.color}/10 rounded-lg">
					<svelte:component this={typeConfig.icon} class="w-5 h-5 text-{typeConfig.color}" />
				</div>
				<h2 class="text-xl font-bold">{$t('adventures.date_information')}</h2>
			</div>
			<button class="btn btn-ghost btn-sm" on:click={() => (isExpanded = !isExpanded)}>
				{isExpanded ? 'Collapse' : 'Expand'}
			</button>
		</div>

		{#if isExpanded}
			<!-- Settings Section -->
			<div class="bg-base-50 p-4 rounded-lg border border-base-200 mb-6">
				<div class="flex items-center gap-2 mb-4">
					<SettingsIcon class="w-4 h-4 text-base-content/70" />
					<h3 class="font-medium text-base-content/80">Settings</h3>
				</div>

				<div class="space-y-4">
					<!-- Timezone Selection -->
					{#if type === 'transportation'}
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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

					<!-- Toggles -->
					<div class="flex flex-wrap gap-6">
						<div class="flex items-center gap-3">
							<ClockIcon class="w-4 h-4 text-base-content/70" />
							<label class="label-text text-sm font-medium">All Day</label>
							<input
								type="checkbox"
								class="toggle toggle-{typeConfig.color} toggle-sm"
								bind:checked={allDay}
								on:change={handleAllDayToggle}
							/>
						</div>

						{#if collection?.start_date && collection?.end_date}
							<div class="flex items-center gap-3">
								<CalendarIcon class="w-4 h-4 text-base-content/70" />
								<label class="label-text text-sm font-medium">Constrain to Collection Dates</label>
								<input
									type="checkbox"
									class="toggle toggle-{typeConfig.color} toggle-sm"
									bind:checked={constrainDates}
								/>
							</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Date Selection Section -->
			<div class="bg-base-50 p-4 rounded-lg border border-base-200 mb-6">
				<h3 class="font-medium text-base-content/80 mb-4">Date Selection</h3>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<!-- Start Date -->
					<div>
						<label class="label-text text-sm font-medium">
							{typeConfig.startLabel}
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

					<!-- End Date -->
					{#if localStartDate}
						<div>
							<label class="label-text text-sm font-medium">
								{typeConfig.endLabel}
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

				<!-- Notes (Location only) -->
				{#if type === 'location'}
					<div class="mt-4">
						<label class="label-text text-sm font-medium">Notes</label>
						<textarea
							class="textarea textarea-bordered w-full mt-1"
							rows="3"
							placeholder="Add notes about this visit..."
							bind:value={note}
						></textarea>
					</div>

					<!-- Add Visit Button -->
					<div class="flex justify-end mt-4">
						<button
							class="btn btn-{typeConfig.color} btn-sm gap-2"
							type="button"
							disabled={!localStartDate || !isDateValid}
							on:click={addVisit}
						>
							<PlusIcon class="w-4 h-4" />
							Add Visit
						</button>
					</div>
				{/if}
			</div>

			<!-- Validation Error -->
			{#if !isDateValid}
				<div class="alert alert-error mb-6">
					<AlertIcon class="w-5 h-5" />
					<span class="text-sm">Invalid date range - end date must be after start date</span>
				</div>
			{/if}

			<!-- Visits List (Location only) -->
			{#if type === 'location'}
				<div class="bg-base-50 p-4 rounded-lg border border-base-200">
					<h3 class="font-medium text-base-content/80 mb-4">
						Visits ({visits?.length || 0})
					</h3>

					{#if !visits || visits.length === 0}
						<div class="text-center py-8 text-base-content/60">
							<CalendarIcon class="w-8 h-8 mx-auto mb-2 opacity-50" />
							<p class="text-sm">No visits added yet</p>
							<p class="text-xs text-base-content/40 mt-1">
								Create your first visit by selecting dates above
							</p>
						</div>
					{:else}
						<div class="space-y-3">
							{#each visits as visit (visit.id)}
								<div
									class="bg-base-100 p-4 rounded-lg border border-base-300 hover:border-base-400 transition-colors"
								>
									<div class="flex items-start justify-between">
										<div class="flex-1 min-w-0">
											<div class="flex items-center gap-2 mb-2">
												{#if isAllDay(visit.start_date)}
													<span class="badge badge-outline badge-sm">All Day</span>
												{:else}
													<ClockIcon class="w-3 h-3 text-base-content/50" />
												{/if}
												<div class="text-sm font-medium truncate">
													{#if isAllDay(visit.start_date)}
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
											</div>

											{#if visit.notes}
												<p class="text-xs text-base-content/70 bg-base-200/50 p-2 rounded">
													"{visit.notes}"
												</p>
											{/if}
										</div>

										<!-- Visit Actions -->
										<div class="flex gap-1 ml-4">
											<button
												class="btn btn-warning btn-xs tooltip tooltip-top"
												data-tip="Edit Visit"
												on:click={() => editVisit(visit)}
											>
												<EditIcon class="w-3 h-3" />
											</button>
											<button
												class="btn btn-error btn-xs tooltip tooltip-top"
												data-tip="Remove Visit"
												on:click={() => removeVisit(visit.id)}
											>
												<TrashIcon class="w-3 h-3" />
											</button>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		{/if}
		<div class="flex gap-3 justify-end pt-4">
			<button class="btn btn-neutral-200 gap-2" on:click={handleBack}>
				<ArrowLeftIcon class="w-5 h-5" />
				Back
			</button>

			<button class="btn btn-primary gap-2" on:click={handleClose}>
				<CheckIcon class="w-5 h-5" />
				Done
			</button>
		</div>
	</div>
</div>
