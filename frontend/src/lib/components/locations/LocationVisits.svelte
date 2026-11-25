<script lang="ts">
	import { run } from 'svelte/legacy';

	import type {
		Collection,
		Trail,
		Activity,
		Visit,
		TransportationVisit,
		TravelerSummary
	} from '#lib/types.js';
	import { travelerName } from '#lib/travelers.js';
	import TravelerPicker from './TravelerPicker.svelte';
	import VisitTravelers from './VisitTravelers.svelte';
	import TimezoneSelector from '../TimezoneSelector.svelte';
	import { defaultTimezone } from '#lib/dateUtils.js';
	import { t } from 'svelte-i18n';
	import {
		updateLocalDate,
		updateUTCDate,
		validateDateRange,
		toDateOnlyLocal,
		toTimedLocalDefault,
		formatDateInTimezone,
		formatAllDayDate
	} from '#lib/dateUtils.js';
	import { dateFormatFromUser } from '#lib/dateFormat.js';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { isVisitAllDay, allDayDatePart } from '#lib';
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
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import RunFastIcon from '~icons/mdi/run-fast';
	import InfoIcon from '~icons/mdi/information';
	import UploadIcon from '~icons/mdi/upload';
	import CloseIcon from '~icons/mdi/close';
	import ActivityComposer from '../activities/ActivityComposer.svelte';
	import ActivityCard from '../cards/ActivityCard.svelte';
	import DateInput from '../shared/DateInput.svelte';
	import { addToast } from '#lib/toasts.js';
	import CalendarTodayIcon from '~icons/mdi/calendar-today';

	interface Props {
		// Props
		collection?: Collection | null;
		selectedStartTimezone?: string;
		utcStartDate?: string | null;
		utcEndDate?: string | null;
		note?: string | null;
		visits?: Visit[] | null;
		objectId: string;
		trails?: Trail[];
		measurementSystem?: 'metric' | 'imperial';
		initialVisitDate?: string | null; // Used to pre-fill visit date when adding from itinerary planner
		/** The uuid of the location's owner; only they may delete a visit for everyone. */
		ownerUuid?: string | null;
	}

	let {
		collection = null,
		selectedStartTimezone = $bindable(defaultTimezone(collection)),
		utcStartDate = $bindable(null),
		utcEndDate = $bindable(null),
		note = $bindable(null),
		visits = $bindable(null),
		objectId,
		trails = $bindable([]),
		measurementSystem = 'metric',
		initialVisitDate = $bindable(null),
		ownerUuid = null
	}: Props = $props();

	const dateFormat = $derived(dateFormatFromUser(page.data?.user));

	const dispatch = createEventDispatcher();

	// Types

	// Who was there. The signed-in user is on a new visit unless the picker says otherwise.
	const currentUserUuid: string | null = page.data?.user?.uuid ?? null;
	let travelerCandidates: TravelerSummary[] = $state([]);
	let selectedTravelers: string[] = $state(currentUserUuid ? [currentUserUuid] : []);
	// With only the current user to pick, there is nothing to choose.
	let showTravelerPicker = $derived(
		travelerCandidates.some((person) => person.uuid !== currentUserUuid)
	);
	// A visit waiting on the delete confirmation because other people were on it.
	let pendingDelete: Visit | null = $state(null);
	let isDeletingVisit = $state(false);

	async function loadTravelerCandidates() {
		try {
			const response = await fetch(`/api/locations/${objectId}/traveler-candidates/`);
			if (response.ok) travelerCandidates = await response.json();
		} catch (error) {
			console.error('Error loading who can be on a visit:', error);
		}
	}

	function resetTravelers() {
		selectedTravelers = currentUserUuid ? [currentUserUuid] : [];
	}

	function othersOn(visit: Visit): TravelerSummary[] {
		return (visit.travelers ?? []).filter((person) => person.uuid !== currentUserUuid);
	}

	// Component state
	let allDay: boolean = $state(true);
	let localStartDate: string = $state('');
	let localEndDate: string = $state('');
	let fullStartDate: string = $state('');
	let fullEndDate: string = $state('');
	let constrainDates: boolean = $state(false);
	let isEditing = $state(false);
	let visitIdEditing: string | null = $state(null);

	// The visit whose activity composer is open, and the saved activity it edits (none when adding).
	let activityComposer: { visitId: string; activity: Activity | null } | null = $state(null);

	function visitCoversDate(visit: Visit, targetDate: string): boolean {
		if (!visit?.start_date) return false;
		const visitStart = visit.start_date.split('T')[0];
		const visitEnd = (visit.end_date || visit.start_date).split('T')[0];
		return targetDate >= visitStart && targetDate <= visitEnd;
	}

	function getTodayDate(): string {
		const now = new Date();
		const y = now.getFullYear();
		const m = String(now.getMonth() + 1).padStart(2, '0');
		const d = String(now.getDate()).padStart(2, '0');
		return `${y}-${m}-${d}`;
	}

	let todayCovered = $derived(
		Boolean(visits?.some((visit) => visitCoversDate(visit, getTodayDate())))
	);

	let isSavingVisit = $state(false);

	// Reactive constraints
	let constraintStartDate = $derived(
		allDay
			? fullStartDate && fullStartDate.includes('T')
				? fullStartDate.split('T')[0]
				: ''
			: fullStartDate || ''
	);
	let constraintEndDate = $derived(
		allDay
			? fullEndDate && fullEndDate.includes('T')
				? fullEndDate.split('T')[0]
				: ''
			: fullEndDate || ''
	);

	// Set the full date range for constraining purposes
	run(() => {
		if (collection && collection.start_date && collection.end_date) {
			fullStartDate = `${collection.start_date}T00:00`;
			fullEndDate = `${collection.end_date}T23:59`;
		}
	});

	// Update local display dates whenever timezone or UTC dates change
	run(() => {
		if (!isEditing) {
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
					timezone: selectedStartTimezone
				}).localDate;

				localStartDate = start;
				localEndDate = end;
			}
		}
	});

	// Helper functions
	function formatDuration(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		const secs = seconds % 60;

		if (hours > 0) {
			return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
		}
		return `${minutes}:${secs.toString().padStart(2, '0')}`;
	}

	function parseDuration(duration: string): number {
		const parts = duration.split(':').map(Number);
		if (parts.length === 3) {
			return parts[0] * 3600 + parts[1] * 60 + parts[2];
		} else if (parts.length === 2) {
			return parts[0] * 60 + parts[1];
		}
		return 0;
	}

	// Event handlers
	// Entering a start date fills the end with the same day (all-day) or same moment (timed),
	// so logging a single-day visit is one entry. Only fills when the end is empty or now earlier.
	function handleStartDateChange() {
		if (!localStartDate) {
			// An end date without a start is invalid, so clearing the start clears both.
			localEndDate = '';
		} else {
			const startDay = localStartDate.split('T')[0];
			const endDay = localEndDate ? localEndDate.split('T')[0] : '';
			if (!localEndDate || endDay < startDay) {
				localEndDate = allDay ? startDay : toTimedLocalDefault(localStartDate, true);
			}
		}
		handleLocalDateChange();
	}

	function handleLocalDateChange() {
		utcStartDate = updateUTCDate({
			localDate: localStartDate,
			timezone: selectedStartTimezone,
			allDay
		}).utcDate;

		utcEndDate = updateUTCDate({
			localDate: localEndDate,
			timezone: selectedStartTimezone,
			allDay
		}).utcDate;
	}

	function handleAllDayToggle(event: Event) {
		const nextAllDay = (event.currentTarget as HTMLInputElement).checked;

		if (nextAllDay) {
			localStartDate = toDateOnlyLocal(localStartDate);
			localEndDate = toDateOnlyLocal(localEndDate);
		} else {
			localStartDate = toTimedLocalDefault(localStartDate);
			localEndDate = toTimedLocalDefault(localEndDate, true);
		}

		allDay = nextAllDay;

		utcStartDate = updateUTCDate({
			localDate: localStartDate,
			timezone: selectedStartTimezone,
			allDay
		}).utcDate;

		utcEndDate = updateUTCDate({
			localDate: localEndDate,
			timezone: selectedStartTimezone,
			allDay
		}).utcDate;

		if (!allDay) {
			localStartDate = updateLocalDate({
				utcDate: utcStartDate,
				timezone: selectedStartTimezone
			}).localDate;

			localEndDate = updateLocalDate({
				utcDate: utcEndDate,
				timezone: selectedStartTimezone
			}).localDate;
		}
	}

	async function addVisit(isAuto: boolean = false): Promise<boolean> {
		isSavingVisit = true;
		try {
			// If editing an existing visit, patch instead of creating new
			if (visitIdEditing) {
				const editingId = visitIdEditing;
				const response = await fetch(`/api/visits/${editingId}/`, {
					method: 'PATCH',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({
						start_date: utcStartDate,
						end_date: utcEndDate,
						notes: note,
						timezone: selectedStartTimezone,
						// Only sent when the picker is shown and the visit already lists people.
						...(showTravelerPicker && selectedTravelers.length
							? { traveler_uuids: selectedTravelers }
							: {})
					})
				});

				if (response.ok) {
					const updatedVisit: Visit = await response.json();
					visits = visits
						? visits.map((v) => (v.id === editingId ? updatedVisit : v))
						: [updatedVisit];
					// If editVisit removed it from the list, ensure it's present
					if (!visits.some((v) => v.id === updatedVisit.id)) {
						visits = [...visits, updatedVisit];
					}
					dispatch('visitAdded', updatedVisit);
					addToast('success', $t('adventures.visit_updated'));
					visitIdEditing = null;
				} else {
					const errorText = await response.text();
					addToast('error', $t('adventures.visit_update_failed') || errorText);
					return false;
				}
			} else {
				// post to /api/visits for new visit
				const response = await fetch('/api/visits/', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({
						object_id: objectId,
						start_date: utcStartDate,
						end_date: utcEndDate,
						notes: note,
						timezone: selectedStartTimezone,
						location: objectId,
						...(showTravelerPicker && selectedTravelers.length
							? { traveler_uuids: selectedTravelers }
							: {})
					})
				});

				if (response.ok) {
					const newVisit: Visit = await response.json();
					visits = visits ? [...visits, newVisit] : [newVisit];
					dispatch('visitAdded', newVisit);
					if (!isAuto) {
						addToast('success', $t('adventures.visit_added'));
					}
				} else {
					const errorText = await response.text();
					addToast('error', $t('adventures.visit_add_failed') || errorText);
					return false;
				}
			}

			// Reset form fields. If this call was an auto-generated visit, allow clearing even if initialVisitDate is set
			if (!initialVisitDate || isAuto) {
				note = '';
				localStartDate = '';
				localEndDate = '';
				utcStartDate = null;
				utcEndDate = null;
			}
			resetTravelers();
			return true;
		} finally {
			isSavingVisit = false;
		}
	}

	async function addTodayVisit() {
		if (todayCovered || isSavingVisit || visitIdEditing) return;

		const today = getTodayDate();
		allDay = true;
		localStartDate = today;
		localEndDate = today;
		note = '';

		utcStartDate = updateUTCDate({
			localDate: localStartDate,
			timezone: selectedStartTimezone,
			allDay: true
		}).utcDate;

		utcEndDate = updateUTCDate({
			localDate: localEndDate,
			timezone: selectedStartTimezone,
			allDay: true
		}).utcDate;

		await addVisit(false);
	}

	/** A saved activity replaces its older version on the visit, or is added to it. */
	function saveActivity(saved: Activity) {
		const visitId = activityComposer?.visitId;
		visits = (visits ?? []).map((visit) => {
			if (visit.id !== visitId) return visit;
			const activities = visit.activities ?? [];
			return {
				...visit,
				activities: activities.some((item) => item.id === saved.id)
					? activities.map((item) => (item.id === saved.id ? saved : item))
					: [...activities, saved]
			};
		});
		activityComposer = null;
	}

	async function deleteActivity(visitId: string, activityId: string) {
		if (!confirm($t('adventures.confirm_delete_activity'))) return;

		try {
			const response = await fetch(`/api/activities/${activityId}/`, {
				method: 'DELETE'
			});

			if (response.ok) {
				// Refetch the location data to get the updated visits with correct IDs

				const locationResponse = await fetch(`/api/locations/${objectId}/`);
				if (locationResponse.ok) {
					const updatedLocation = await locationResponse.json();
					visits = updatedLocation.visits;
				} else {
					console.error('Failed to refetch location data:', await locationResponse.text());
				}
			} else {
				console.error('Failed to delete activity:', await response.text());
			}
		} catch (error) {
			console.error('Error deleting activity:', error);
		}
	}

	function editVisit(visit: Visit) {
		isEditing = true;
		visitIdEditing = visit.id;
		const isAllDayEvent = isVisitAllDay(visit.start_date, visit.end_date);
		allDay = isAllDayEvent;

		if ('start_timezone' in visit && typeof visit.start_timezone === 'string') {
			selectedStartTimezone = visit.start_timezone;
			if ('end_timezone' in visit && typeof visit.end_timezone === 'string') {
				selectedStartTimezone = visit.end_timezone;
			}
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
					'end_timezone' in visit && typeof visit.end_timezone === 'string'
						? visit.end_timezone
						: selectedStartTimezone
			}).localDate;
		}

		selectedTravelers = visit.travelers?.map((person) => person.uuid) ?? [];
		note = visit.notes;
		constrainDates = Boolean(collection?.start_date && collection?.end_date);
		utcStartDate = visit.start_date;
		utcEndDate = visit.end_date;

		setTimeout(() => {
			isEditing = false;
		}, 0);
	}

	function cancelEditVisit() {
		visitIdEditing = null;
		resetTravelers();
		note = '';
		localStartDate = '';
		localEndDate = '';
		utcStartDate = null;
		utcEndDate = null;
	}

	/** Delete asks first when other people were on the visit, since it is theirs too. */
	function requestRemoveVisit(visit: Visit) {
		if (othersOn(visit).length > 0) {
			pendingDelete = visit;
		} else {
			removeVisit(visit.id);
		}
	}

	async function removeVisit(visitId: string, forEveryone = false) {
		const previousVisits = visits ? [...visits] : [];
		if (visits) {
			visits = visits.filter((v) => v.id !== visitId);
		}

		if (activityComposer?.visitId === visitId) activityComposer = null;

		if (visitIdEditing === visitId) {
			cancelEditVisit();
		}

		// Without for_everyone the server only takes the caller off a visit others were on.
		const response = await fetch(`/api/visits/${visitId}/${forEveryone ? '?for_everyone=1' : ''}`, {
			method: 'DELETE'
		});
		if (!response.ok) {
			console.error('Error deleting visit:', response.statusText);
			visits = previousVisits;
			addToast('error', $t('adventures.visit_add_failed'));
			return;
		}
		dispatch('visitRemoved', visitId);
		if (!forEveryone) {
			// The visit may live on for the others, so show what is still there.
			const locationResponse = await fetch(`/api/locations/${objectId}/`);
			if (locationResponse.ok) visits = (await locationResponse.json()).visits;
		}
	}

	async function confirmRemoveVisit(forEveryone: boolean) {
		const visit = pendingDelete;
		if (!visit) return;
		isDeletingVisit = true;
		try {
			await removeVisit(visit.id, forEveryone);
		} finally {
			isDeletingVisit = false;
			pendingDelete = null;
		}
	}

	/** A visit changed by joining or leaving it; null means leaving deleted it. */
	function travelersChanged(visitId: string, updated: Visit | null) {
		visits = updated
			? (visits ?? []).map((v) => (v.id === visitId ? updated : v))
			: (visits ?? []).filter((v) => v.id !== visitId);
		if (!updated) dispatch('visitRemoved', visitId);
		else dispatch('visitAdded', updated);
	}

	function handleBack() {
		dispatch('back');
	}

	function handleClose() {
		dispatch('close');
	}

	// Lifecycle
	onMount(async () => {
		loadTravelerCandidates();
		localStartDate = updateLocalDate({
			utcDate: utcStartDate,
			timezone: selectedStartTimezone
		}).localDate;

		localEndDate = updateLocalDate({
			utcDate: utcEndDate,
			timezone: selectedStartTimezone
		}).localDate;

		if (!selectedStartTimezone) {
			selectedStartTimezone = defaultTimezone(collection);
		}
		if (!selectedStartTimezone) {
			selectedStartTimezone = defaultTimezone(collection);
		}

		// If initialVisitDate is provided and a visit on that date doesn't exist, create and upload a new all day visit on that date
		if (initialVisitDate) {
			const targetDate = initialVisitDate.split('T')[0]; // Ensure we have just YYYY-MM-DD

			// Check if any visit already exists for this date
			const visitExists = visits?.some((visit) => visitCoversDate(visit, targetDate));

			if (!visitExists) {
				// Set up an all-day visit for this date
				allDay = true;
				localStartDate = targetDate;
				localEndDate = targetDate;

				// Convert to UTC dates
				utcStartDate = updateUTCDate({
					localDate: localStartDate,
					timezone: selectedStartTimezone,
					allDay: true
				}).utcDate;

				utcEndDate = updateUTCDate({
					localDate: localEndDate,
					timezone: selectedStartTimezone,
					allDay: true
				}).utcDate;

				// Automatically save the visit
				await addVisit(true);
				// Clear the initialVisitDate after successful creation
				initialVisitDate = null;
			}
		}
	});

	let isDateValid = $derived(validateDateRange(utcStartDate ?? '', utcEndDate ?? '').valid);
</script>

<div
	class="h-full min-h-0 flex flex-col bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5"
>
	<div class="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-4 md:py-5">
		<div class="max-w-full mx-auto space-y-6">
			{#snippet visitEditor()}
				<div class="space-y-4">
					<div class="flex flex-wrap gap-4">
						<label class="flex items-center gap-2 cursor-pointer" for="all-day-toggle">
							<input
								id="all-day-toggle"
								type="checkbox"
								class="toggle toggle-primary"
								checked={allDay}
								onchange={handleAllDayToggle}
							/>
							<span class="font-semibold text-sm text-base-content">{$t('adventures.all_day')}</span
							>
						</label>

						{#if collection?.start_date && collection?.end_date}
							<label class="flex items-center gap-2 cursor-pointer" for="constrain-dates">
								<input
									id="constrain-dates"
									type="checkbox"
									class="toggle toggle-secondary"
									bind:checked={constrainDates}
								/>
								<span class="font-semibold text-sm text-base-content"
									>{$t('adventures.date_constrain')}</span
								>
							</label>
						{/if}
					</div>

					{#if !isDateValid}
						<div class="alert alert-error bg-error/10 border border-error/30 text-error">
							<AlertIcon class="w-4 h-4" />
							<span class="text-sm">{$t('adventures.invalid_date_range')}</span>
						</div>
					{/if}

					<div class="grid grid-cols-1 items-start lg:grid-cols-3 gap-4">
						<div class="flex flex-col">
							<label class="field-label" for="start-date-input">{$t('adventures.start_date')}</label
							>
							<DateInput
								id="start-date-input"
								bind:value={localStartDate}
								onchange={handleStartDateChange}
								showTime={!allDay}
								min={constrainDates ? constraintStartDate : undefined}
								max={constrainDates ? constraintEndDate : undefined}
							/>
						</div>

						{#if localStartDate}
							<div class="flex flex-col">
								<label class="field-label" for="end-date-input">{$t('adventures.end_date')}</label>
								<DateInput
									id="end-date-input"
									bind:value={localEndDate}
									onchange={handleLocalDateChange}
									showTime={!allDay}
									min={constrainDates ? localStartDate : undefined}
									max={constrainDates ? constraintEndDate : undefined}
								/>
							</div>
						{/if}

						{#if !allDay}
							<TimezoneSelector bind:selectedTimezone={selectedStartTimezone} />
						{/if}
					</div>

					{#if showTravelerPicker}
						<TravelerPicker candidates={travelerCandidates} bind:selected={selectedTravelers} />
					{/if}

					<div>
						<label class="field-label" for="visit-notes">{$t('adventures.notes')}</label>
						<textarea
							id="visit-notes"
							class="textarea textarea-bordered w-full mt-1 bg-base-100/80 focus:bg-base-100"
							rows="3"
							placeholder={$t('adventures.notes_placeholder') + '...'}
							bind:value={note}
						></textarea>
					</div>

					<div class="flex flex-wrap justify-end gap-2">
						{#if visitIdEditing}
							<button
								class="btn btn-ghost btn-sm"
								type="button"
								onclick={cancelEditVisit}
								disabled={isSavingVisit}
							>
								{$t('about.close')}
							</button>
						{/if}
						<button
							class="btn btn-primary btn-sm gap-2"
							type="button"
							disabled={!localStartDate || !isDateValid || isSavingVisit}
							onclick={() => addVisit(false)}
						>
							{#if isSavingVisit}
								<span class="loading loading-spinner loading-xs"></span>
							{:else if visitIdEditing}
								<CheckIcon class="w-4 h-4" />
							{:else}
								<PlusIcon class="w-4 h-4" />
							{/if}
							{visitIdEditing ? $t('adventures.update_visit') : $t('adventures.add_visit')}
						</button>
					</div>
				</div>
			{/snippet}

			{#snippet visitActivityActions(visit: Visit)}
				<button
					class="btn btn-outline btn-success btn-xs gap-1"
					title={$t('adventures.add_activity')}
					onclick={() => (activityComposer = { visitId: visit.id, activity: null })}
				>
					<UploadIcon class="w-3 h-3" />
					{$t('adventures.add_activity')}
				</button>
			{/snippet}

			<!-- Add Visit Section -->
			{#if !visitIdEditing}
				<div class="card bg-base-100 border border-base-300 shadow-lg">
					<div class="card-body p-6">
						<div class="flex flex-wrap items-center justify-between gap-3 mb-6">
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-lg">
									<CalendarIcon class="w-5 h-5 text-primary" />
								</div>
								<h2 class="text-xl font-bold">
									{$t('adventures.add_visit')}
								</h2>
							</div>
							<button
								type="button"
								class="btn btn-primary btn-sm gap-2"
								disabled={todayCovered || isSavingVisit}
								title={todayCovered
									? $t('adventures.visited_today')
									: $t('adventures.add_today_visit')}
								onclick={() => addTodayVisit()}
							>
								{#if isSavingVisit && localStartDate === getTodayDate()}
									<span class="loading loading-spinner loading-xs"></span>
								{:else}
									<CalendarTodayIcon class="w-4 h-4" />
								{/if}
								{$t('adventures.add_today_visit')}
							</button>
						</div>

						{@render visitEditor()}
					</div>
				</div>
			{/if}

			<!-- Visits List -->
			<div class="card bg-base-100 border border-base-300 shadow-lg">
				<div class="card-body p-6">
					<div class="flex items-center gap-3 mb-6">
						<div class="p-2 bg-info/10 rounded-lg">
							<MapMarkerIcon class="w-5 h-5 text-info" />
						</div>
						<h2 class="text-xl font-bold">
							{$t('adventures.visits')}
							<span class="text-base font-normal text-base-content/60">({visits?.length || 0})</span
							>
						</h2>
					</div>

					{#if !visits || visits.length === 0}
						<div class="text-center py-10 text-base-content/60">
							<CalendarIcon class="w-10 h-10 mx-auto mb-3 opacity-40" />
							<p class="text-sm font-medium">{$t('adventures.no_visits')}</p>
							<p class="text-xs text-base-content/40 mt-1 mb-4">
								{$t('adventures.no_visits_description')}
							</p>
							<button
								type="button"
								class="btn btn-primary btn-sm gap-2"
								disabled={todayCovered || isSavingVisit}
								onclick={() => addTodayVisit()}
							>
								<CalendarTodayIcon class="w-4 h-4" />
								{$t('adventures.add_today_visit')}
							</button>
						</div>
					{:else}
						<div class="space-y-3">
							{#each visits as visit (visit.id)}
								<div
									class="bg-base-200/50 p-4 rounded-xl border border-base-300 hover:border-primary/30 transition-colors"
									class:ring-2={visitIdEditing === visit.id}
									class:ring-primary={visitIdEditing === visit.id}
								>
									{#if visitIdEditing === visit.id}
										{@render visitEditor()}
										<div class="flex flex-wrap justify-end gap-1 mt-3">
											{@render visitActivityActions(visit)}
										</div>
									{:else}
										<div class="flex items-start justify-between gap-3">
											<div class="flex-1 min-w-0">
												<div class="flex flex-wrap items-center gap-2 mb-1">
													{#if isVisitAllDay(visit.start_date, visit.end_date)}
														<span class="badge badge-outline badge-sm"
															>{$t('adventures.all_day')}</span
														>
													{:else}
														<span class="badge badge-outline badge-sm gap-1">
															<ClockIcon class="w-3 h-3" />
															{$t('adventures.timed')}
														</span>
													{/if}
													{#if visit.timezone && !isVisitAllDay(visit.start_date, visit.end_date)}
														<span class="badge badge-ghost badge-sm">{visit.timezone}</span>
													{/if}
												</div>
												<div class="text-base font-semibold truncate">
													{#if isVisitAllDay(visit.start_date, visit.end_date)}
														{formatAllDayDate(visit.start_date, dateFormat)}
														– {formatAllDayDate(visit.end_date, dateFormat)}
													{:else if visit.timezone}
														{formatDateInTimezone(visit.start_date, visit.timezone, dateFormat)}
														– {formatDateInTimezone(visit.end_date, visit.timezone, dateFormat)}
													{:else}
														{formatDateInTimezone(visit.start_date, null, dateFormat)}
														– {formatDateInTimezone(visit.end_date, null, dateFormat)}
													{/if}
												</div>

												{#if visit.notes}
													<p
														class="text-sm text-base-content/70 bg-base-100/80 p-2 rounded-lg mt-2 border border-base-300"
													>
														{visit.notes}
													</p>
												{/if}

												<VisitTravelers
													{visit}
													{currentUserUuid}
													onchange={(updated) => travelersChanged(visit.id, updated)}
												/>

												{#if visit.activities && visit.activities.length > 0}
													<div class="flex items-center gap-2 mt-2">
														<RunFastIcon class="w-3.5 h-3.5 text-success" />
														<span class="text-xs text-success font-medium">
															{visit.activities.length}
															{$t('adventures.saved_activities')}
														</span>
													</div>
												{/if}
											</div>

											<div class="flex flex-col items-end gap-2 shrink-0">
												<div class="flex gap-1">
													<button
														class="btn btn-ghost btn-sm btn-square"
														title={$t('adventures.edit_visit')}
														onclick={() => editVisit(visit)}
													>
														<EditIcon class="w-4 h-4" />
													</button>
													<button
														class="btn btn-ghost btn-sm btn-square text-error"
														title={$t('adventures.remove_visit')}
														onclick={() => requestRemoveVisit(visit)}
													>
														<TrashIcon class="w-4 h-4" />
													</button>
												</div>
												<div class="flex flex-wrap justify-end gap-1">
													{@render visitActivityActions(visit)}
												</div>
											</div>
										</div>
									{/if}

									{#if activityComposer?.visitId === visit.id}
										<div class="mt-4 border-t border-base-300 pt-4">
											{#key activityComposer.activity?.id}
												<ActivityComposer
													visitId={visit.id}
													activity={activityComposer.activity}
													dateStart={visit.start_date}
													dateEnd={visit.end_date}
													timezone={visit.timezone}
													{trails}
													{measurementSystem}
													importedIds={(visit.activities ?? []).flatMap((item) =>
														item.external_service_id ? [item.external_service_id] : []
													)}
													onSaved={saveActivity}
													onCancel={() => (activityComposer = null)}
												/>
											{/key}
										</div>
									{/if}

									<!-- Saved Activities Section -->
									{#if visit.activities && visit.activities.length > 0}
										<div class="mt-4 pt-4 border-t border-base-300">
											<div class="flex items-center gap-2 mb-3">
												<RunFastIcon class="w-4 h-4 text-success" />
												<h4 class="font-medium text-sm">
													{$t('adventures.saved_activities')} ({visit.activities.length})
												</h4>
											</div>

											<div class="space-y-2">
												{#each visit.activities as activity (activity.id)}
													<ActivityCard
														{activity}
														{trails}
														{measurementSystem}
														onEdit={() => (activityComposer = { visitId: visit.id, activity })}
														onDelete={() => deleteActivity(visit.id, activity.id)}
													/>
												{/each}
											</div>
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>

			{#if (localStartDate || localEndDate) && !visitIdEditing}
				<div class="alert alert-neutral shadow-sm">
					<InfoIcon class="w-5 h-5" />
					<div>
						<div class="font-medium text-sm">{$t('adventures.dates_not_saved')}</div>
						<div class="text-xs opacity-75">{$t('adventures.dates_not_saved_description')}</div>
					</div>
				</div>
			{/if}
		</div>
	</div>

	{#if pendingDelete}
		{@const others = othersOn(pendingDelete)}
		{@const names = others.map(travelerName).join(', ')}
		{@const isOwner = Boolean(currentUserUuid && ownerUuid === currentUserUuid)}
		<dialog class="modal modal-open" aria-labelledby="delete-visit-title">
			<div class="modal-box max-w-md">
				<h3 id="delete-visit-title" class="text-lg font-bold">{$t('visits.delete_visit_title')}</h3>
				<p class="py-3 text-sm text-base-content/70">
					{$t('visits.stays_for_others', { values: { names } })}
				</p>
				<div class="modal-action flex-wrap">
					<button
						type="button"
						class="btn btn-ghost"
						disabled={isDeletingVisit}
						onclick={() => (pendingDelete = null)}
					>
						{$t('adventures.cancel')}
					</button>
					{#if isOwner}
						<div class="flex flex-col items-end gap-1">
							<button
								type="button"
								class="btn btn-error btn-outline"
								disabled={isDeletingVisit}
								onclick={() => confirmRemoveVisit(true)}
							>
								{$t('visits.delete_for_everyone')}
							</button>
							<span class="text-xs text-base-content/60">
								{$t('visits.others_lose_it', { values: { names } })}
							</span>
						</div>
					{/if}
					<button
						type="button"
						class="btn btn-primary"
						disabled={isDeletingVisit}
						onclick={() => confirmRemoveVisit(false)}
					>
						{$t('visits.remove_me_from_visit')}
					</button>
				</div>
			</div>
			<button
				type="button"
				class="modal-backdrop"
				aria-label={$t('adventures.cancel')}
				onclick={() => (pendingDelete = null)}
			></button>
		</dialog>
	{/if}

	<div
		class="shrink-0 border-t border-base-300 bg-base-100/90 backdrop-blur-lg px-4 md:px-6 py-3 md:py-4 flex gap-3 justify-end"
	>
		<button class="btn btn-ghost gap-2" onclick={handleBack}>
			<ArrowLeftIcon class="w-5 h-5" />
			{$t('adventures.back')}
		</button>

		<button class="btn btn-primary gap-2" onclick={handleClose}>
			<CheckIcon class="w-5 h-5" />
			{$t('adventures.done')}
		</button>
	</div>
</div>
