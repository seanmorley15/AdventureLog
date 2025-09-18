<script lang="ts">
	import type {
		Collection,
		StravaActivity,
		Trail,
		Activity,
		Visit,
		TransportationVisit
	} from '$lib/types';
	import TimezoneSelector from '../TimezoneSelector.svelte';
	import { t } from 'svelte-i18n';
	import { updateLocalDate, updateUTCDate, validateDateRange, formatUTCDate } from '$lib/dateUtils';
	import { onMount } from 'svelte';
	import { isAllDay, SPORT_TYPE_CHOICES } from '$lib';
	import { createEventDispatcher } from 'svelte';
	import { deserialize } from '$app/forms';

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
	import RunFastIcon from '~icons/mdi/run-fast';
	import LoadingIcon from '~icons/mdi/loading';
	import InfoIcon from '~icons/mdi/information';
	import UploadIcon from '~icons/mdi/upload';
	import FileIcon from '~icons/mdi/file';
	import CloseIcon from '~icons/mdi/close';
	import StravaActivityCard from '../StravaActivityCard.svelte';
	import ActivityCard from '../ActivityCard.svelte';

	// Props
	export let collection: Collection | null = null;
	export let selectedStartTimezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;
	export let utcStartDate: string | null = null;
	export let utcEndDate: string | null = null;
	export let note: string | null = null;
	export let visits: Visit[] | null = null;
	export let objectId: string;
	export let trails: Trail[] = [];
	export let measurementSystem: 'metric' | 'imperial' = 'metric';

	const dispatch = createEventDispatcher();

	// Types

	// Component state
	let allDay: boolean = false;
	let localStartDate: string = '';
	let localEndDate: string = '';
	let fullStartDate: string = '';
	let fullEndDate: string = '';
	let constrainDates: boolean = false;
	let isEditing = false;
	let visitIdEditing: string | null = null;

	// Activity management state
	let stravaEnabled: boolean = false;
	let visitActivities: { [visitId: string]: StravaActivity[] } = {};
	let loadingActivities: { [visitId: string]: boolean } = {};
	let expandedVisits: { [visitId: string]: boolean } = {};
	let uploadingActivity: { [visitId: string]: boolean } = {};
	let showActivityUpload: { [visitId: string]: boolean } = {};
	let pendingStravaImport: { [visitId: string]: StravaActivity | null } = {};

	// Activity form state
	let activityForm = {
		name: '',
		sport_type: 'Run',
		distance: null as number | null,
		moving_time: '',
		elapsed_time: '',
		elevation_gain: null as number | null,
		elevation_loss: null as number | null,
		start_date: '',
		calories: null as number | null,
		gpx_file: null as File | null,
		trail: null as string | null,
		elev_high: null as number | null,
		elev_low: null as number | null,
		rest_time: null as number | null,
		average_speed: null as number | null,
		max_speed: null as number | null,
		average_cadence: null as number | null,
		start_lat: null as number | null,
		start_lng: null as number | null,
		end_lat: null as number | null,
		end_lng: null as number | null,
		timezone: undefined as string | undefined
	};

	function getTypeConfig() {
		return {
			startLabel: 'Start Date',
			endLabel: 'End Date',
			icon: CalendarIcon,
			color: 'primary'
		};
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
				timezone: selectedStartTimezone
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
			timezone: selectedStartTimezone,
			allDay
		}).utcDate;

		localStartDate = updateLocalDate({
			utcDate: utcStartDate,
			timezone: selectedStartTimezone
		}).localDate;

		localEndDate = updateLocalDate({
			utcDate: utcEndDate,
			timezone: selectedStartTimezone
		}).localDate;
	}

	async function addVisit() {
		// If editing an existing visit, patch instead of creating new
		if (visitIdEditing) {
			const response = await fetch(`/api/visits/${visitIdEditing}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					start_date: utcStartDate,
					end_date: utcEndDate,
					notes: note,
					timezone: selectedStartTimezone
				})
			});

			if (response.ok) {
				const updatedVisit: Visit = await response.json();
				visits = visits ? [...visits, updatedVisit] : [updatedVisit];
				dispatch('visitAdded', updatedVisit);
				visitIdEditing = null;
			} else {
				const errorText = await response.text();
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
					location: objectId
				})
			});

			if (response.ok) {
				const newVisit: Visit = await response.json();
				visits = visits ? [...visits, newVisit] : [newVisit];
				dispatch('visitAdded', newVisit);
			} else {
				const errorText = await response.text();
				alert(`Failed to add visit: ${errorText}`);
			}
		}

		// Reset form fields
		note = '';
		localStartDate = '';
		localEndDate = '';
		utcStartDate = null;
		utcEndDate = null;
	}

	// Activity management functions
	async function loadActivitiesForVisit(visit: Visit | TransportationVisit) {
		if (!stravaEnabled) return;

		loadingActivities[visit.id] = true;
		loadingActivities = { ...loadingActivities };

		try {
			let startDate = new Date(visit.start_date);
			let endDate = new Date(visit.end_date);

			if (isAllDay(visit.start_date) && visit.end_date.includes('T00:00:00')) {
				endDate = new Date(visit.end_date.replace('T00:00:00', 'T23:59:59'));
			}

			startDate.setHours(startDate.getHours() - 12);
			endDate.setHours(endDate.getHours() + 12);

			const bufferedStart = startDate.toISOString();
			const bufferedEnd = endDate.toISOString();

			const response = await fetch(
				`/api/integrations/strava/activities/?start_date=${bufferedStart}&end_date=${bufferedEnd}`,
				{
					method: 'GET',
					headers: {
						'Content-Type': 'application/json'
					}
				}
			);

			if (response.ok) {
				const apiRes = await response.json();
				const filtered = apiRes.activities;
				visitActivities[visit.id] = filtered;
				visitActivities = { ...visitActivities };
			} else {
				console.error('Failed to load activities for visit:', await response.text());
				visitActivities[visit.id] = [];
				visitActivities = { ...visitActivities };
			}
		} catch (error) {
			console.error('Error loading activities for visit:', error);
			visitActivities[visit.id] = [];
			visitActivities = { ...visitActivities };
		} finally {
			loadingActivities[visit.id] = false;
			loadingActivities = { ...loadingActivities };
		}
	}

	function toggleVisitActivities(visit: Visit | TransportationVisit) {
		const isExpanded = expandedVisits[visit.id];

		if (!isExpanded) {
			expandedVisits[visit.id] = true;
			expandedVisits = { ...expandedVisits };

			if (!visitActivities[visit.id]) {
				loadActivitiesForVisit(visit);
			}
		} else {
			expandedVisits[visit.id] = false;
			expandedVisits = { ...expandedVisits };
		}
	}

	function showActivityUploadForm(visitId: string) {
		showActivityUpload[visitId] = true;
		showActivityUpload = { ...showActivityUpload };

		// Reset form
		activityForm = {
			name: '',
			sport_type: 'Run',
			distance: null,
			moving_time: '',
			elapsed_time: '',
			elevation_gain: null,
			elevation_loss: null,
			start_date: '',
			calories: null,
			gpx_file: null,
			trail: null,
			elev_high: null,
			elev_low: null,
			rest_time: null,
			average_speed: null,
			max_speed: null,
			average_cadence: null,
			start_lat: null,
			start_lng: null,
			end_lat: null,
			end_lng: null,
			timezone: undefined
		};
	}

	function hideActivityUploadForm(visitId: string) {
		showActivityUpload[visitId] = false;
		showActivityUpload = { ...showActivityUpload };

		// Clear pending import
		delete pendingStravaImport[visitId];
		pendingStravaImport = { ...pendingStravaImport };
	}

	function handleGpxFileChange(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target.files && target.files[0]) {
			activityForm.gpx_file = target.files[0];
		}
	}

	async function uploadActivity(visitId: string) {
		if (!activityForm.name.trim()) {
			alert($t('adventures.activity_name_required'));
			return;
		}

		// If this is a Strava import, require GPX file
		if (pendingStravaImport[visitId] && !activityForm.gpx_file) {
			alert($t('strava.gpx_required'));
			return;
		}

		uploadingActivity[visitId] = true;
		uploadingActivity = { ...uploadingActivity };

		try {
			const formData = new FormData();

			// Add basic activity data
			formData.append('visit', visitId);
			formData.append('name', activityForm.name);
			if (activityForm.sport_type) formData.append('sport_type', activityForm.sport_type);
			if (activityForm.distance) formData.append('distance', activityForm.distance.toString());
			if (activityForm.moving_time) {
				const seconds = parseDuration(activityForm.moving_time);
				formData.append('moving_time', `PT${seconds}S`);
			}
			if (activityForm.elapsed_time) {
				const seconds = parseDuration(activityForm.elapsed_time);
				formData.append('elapsed_time', `PT${seconds}S`);
			}
			if (activityForm.elevation_gain)
				formData.append('elevation_gain', activityForm.elevation_gain.toString());
			if (activityForm.elevation_loss)
				formData.append('elevation_loss', activityForm.elevation_loss.toString());
			if (activityForm.start_date)
				formData.append('start_date', formatUTCDate(activityForm.start_date));

			if (activityForm.calories) formData.append('calories', activityForm.calories.toString());
			if (activityForm.trail) formData.append('trail', activityForm.trail);
			if (activityForm.elev_high) formData.append('elev_high', activityForm.elev_high.toString());
			if (activityForm.elev_low) formData.append('elev_low', activityForm.elev_low.toString());
			if (activityForm.rest_time) formData.append('rest_time', activityForm.rest_time.toString());
			if (activityForm.average_speed)
				formData.append('average_speed', activityForm.average_speed.toString());
			if (activityForm.max_speed) formData.append('max_speed', activityForm.max_speed.toString());
			if (activityForm.average_cadence)
				formData.append('average_cadence', activityForm.average_cadence.toString());
			if (activityForm.start_lat !== null)
				formData.append('start_lat', activityForm.start_lat.toString());
			if (activityForm.start_lng !== null)
				formData.append('start_lng', activityForm.start_lng.toString());
			if (activityForm.end_lat !== null)
				formData.append('end_lat', activityForm.end_lat.toString());
			if (activityForm.end_lng !== null)
				formData.append('end_lng', activityForm.end_lng.toString());
			if (activityForm.timezone) {
				formData.append('timezone', activityForm.timezone);
			}

			// Add GPX file if provided
			if (activityForm.gpx_file) {
				formData.append('gpx_file', activityForm.gpx_file);
			}

			// Add external service ID if this is a Strava import
			if (pendingStravaImport[visitId]) {
				formData.append('external_service_id', pendingStravaImport[visitId].id.toString());
			}

			const response = await fetch('/locations?/activity', {
				method: 'POST',
				body: formData
			});

			if (response.ok) {
				const newActivityResponse = deserialize(await response.text()) as { data: Activity };
				const newActivity = newActivityResponse.data as Activity;

				// Update the visit's activities array
				if (visits) {
					visits = visits.map((visit) => {
						if (visit.id === visitId) {
							return {
								...visit,
								activities: [...(visit.activities || []), newActivity]
							};
						}
						return visit;
					});
				}

				// Hide the upload form
				hideActivityUploadForm(visitId);
			} else {
				const errorText = await response.text();
				console.error('Failed to upload activity:', errorText);
			}
		} catch (error) {
			console.error('Error uploading activity:', error);
		} finally {
			uploadingActivity[visitId] = false;
			uploadingActivity = { ...uploadingActivity };
		}
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

	async function handleStravaActivityImport(event: CustomEvent<StravaActivity>, visitId: string) {
		const stravaActivity = event.detail;

		try {
			// Store the pending import and show upload form
			pendingStravaImport[visitId] = stravaActivity;
			pendingStravaImport = { ...pendingStravaImport };

			// Pre-fill the activity form with Strava data
			activityForm = {
				name: stravaActivity.name,
				sport_type: stravaActivity.sport_type || stravaActivity.type,
				distance: stravaActivity.distance || null, // Keep in meters
				moving_time: stravaActivity.moving_time ? formatDuration(stravaActivity.moving_time) : '',
				elapsed_time: stravaActivity.elapsed_time
					? formatDuration(stravaActivity.elapsed_time)
					: '',
				elevation_gain: stravaActivity.total_elevation_gain || null,
				elevation_loss: stravaActivity.estimated_elevation_loss || null,
				start_date: stravaActivity.start_date ? stravaActivity.start_date.substring(0, 16) : '',
				calories: stravaActivity.calories || null,
				gpx_file: null,
				trail: null,
				elev_high: stravaActivity.elev_high || null,
				elev_low: stravaActivity.elev_low || null,
				rest_time: stravaActivity.rest_time || null,
				average_speed: stravaActivity.average_speed || null,
				max_speed: stravaActivity.max_speed || null,
				average_cadence: stravaActivity.average_cadence || null,
				start_lat: stravaActivity.start_latlng ? stravaActivity.start_latlng[0] : null,
				start_lng: stravaActivity.start_latlng ? stravaActivity.start_latlng[1] : null,
				end_lat: stravaActivity.end_latlng ? stravaActivity.end_latlng[0] : null,
				end_lng: stravaActivity.end_latlng ? stravaActivity.end_latlng[1] : null,
				timezone: stravaActivity.timezone || undefined
			};

			// Show the upload form
			showActivityUpload[visitId] = true;
			showActivityUpload = { ...showActivityUpload };
		} catch (error) {
			console.error('Error initiating Strava import:', error);
		}
	}

	function editVisit(visit: Visit) {
		isEditing = true;
		visitIdEditing = visit.id;
		const isAllDayEvent = isAllDay(visit.start_date);
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

		// Remove the visit from the array temporarily for editing
		if (visits) {
			visits = visits.filter((v) => v.id !== visit.id);
		}

		// Clean up activities for this visit
		delete visitActivities[visit.id];
		delete expandedVisits[visit.id];
		delete loadingActivities[visit.id];
		delete showActivityUpload[visit.id];

		note = visit.notes;
		constrainDates = true;
		utcStartDate = visit.start_date;
		utcEndDate = visit.end_date;

		setTimeout(() => {
			isEditing = false;
		}, 0);
	}

	function removeVisit(visitId: string) {
		if (visits) {
			visits = visits.filter((v) => v.id !== visitId);
		}

		// Clean up activities for this visit
		delete visitActivities[visitId];
		delete expandedVisits[visitId];
		delete loadingActivities[visitId];
		delete showActivityUpload[visitId];

		// make the DELETE request
		fetch(`/api/visits/${visitId}/`, {
			method: 'DELETE'
		}).then((response) => {
			if (!response.ok) {
				console.error('Error deleting visit:', response.statusText);
			} else {
				// remove the visit from the local state
				visits = visits?.filter((v) => v.id !== visitId) ?? null;
			}
		});
	}

	function handleBack() {
		dispatch('back');
	}

	function handleClose() {
		dispatch('close');
	}

	// Lifecycle
	onMount(async () => {
		localStartDate = updateLocalDate({
			utcDate: utcStartDate,
			timezone: selectedStartTimezone
		}).localDate;

		localEndDate = updateLocalDate({
			utcDate: utcEndDate,
			timezone: selectedStartTimezone
		}).localDate;

		if (!selectedStartTimezone) {
			selectedStartTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
		}
		if (!selectedStartTimezone) {
			selectedStartTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
		}

		// Check if Strava is enabled by making a simple API call
		try {
			const response = await fetch('/api/integrations/strava/activities', {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json'
				}
			});
			stravaEnabled = response.ok;
		} catch {
			stravaEnabled = false;
		}
	});

	$: isDateValid = validateDateRange(utcStartDate ?? '', utcEndDate ?? '').valid;
	$: typeConfig = getTypeConfig();
</script>

<div class="min-h-screen bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5 p-6">
	<div class="max-w-full mx-auto space-y-6">
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
				</div>

				<!-- Settings Section -->
				<div class="bg-base-50 p-4 rounded-lg border border-base-200 mb-6">
					<div class="flex items-center gap-2 mb-4">
						<SettingsIcon class="w-4 h-4 text-base-content/70" />
						<h3 class="font-medium text-base-content/80">{$t('navbar.settings')}</h3>
					</div>

					<div class="space-y-4">
						<!-- Timezone Selection -->

						<div>
							<label class="label-text text-sm font-medium" for="timezone-selector"
								>{$t('adventures.timezone')}</label
							>
							<div class="mt-1">
								<TimezoneSelector bind:selectedTimezone={selectedStartTimezone} />
							</div>
						</div>

						<!-- Toggles -->
						<div class="flex flex-wrap gap-6">
							<div class="flex items-center gap-3">
								<ClockIcon class="w-4 h-4 text-base-content/70" />
								<label class="label-text text-sm font-medium" for="all-day-toggle"
									>{$t('adventures.all_day')}</label
								>
								<input
									id="all-day-toggle"
									type="checkbox"
									class="toggle toggle-{typeConfig.color} toggle-sm"
									bind:checked={allDay}
									on:change={handleAllDayToggle}
								/>
							</div>

							{#if collection?.start_date && collection?.end_date}
								<div class="flex items-center gap-3">
									<CalendarIcon class="w-4 h-4 text-base-content/70" />
									<label class="label-text text-sm font-medium" for="constrain-dates"
										>{$t('adventures.date_constrain')}</label
									>
									<input
										id="constrain-dates"
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
					<h3 class="font-medium text-base-content/80 mb-4">{$t('adventures.date_selection')}</h3>

					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<!-- Start Date -->
						<div>
							<label class="label-text text-sm font-medium" for="start-date-input">
								{typeConfig.startLabel}
							</label>
							{#if allDay}
								<input
									id="start-date-input"
									type="date"
									class="input input-bordered w-full mt-1"
									bind:value={localStartDate}
									on:change={handleLocalDateChange}
									min={constrainDates ? constraintStartDate : ''}
									max={constrainDates ? constraintEndDate : ''}
								/>
							{:else}
								<input
									id="start-date-input"
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
								<label class="label-text text-sm font-medium" for="end-date-input">
									{typeConfig.endLabel}
								</label>
								{#if allDay}
									<input
										id="end-date-input"
										type="date"
										class="input input-bordered w-full mt-1"
										bind:value={localEndDate}
										on:change={handleLocalDateChange}
										min={constrainDates ? localStartDate : ''}
										max={constrainDates ? constraintEndDate : ''}
									/>
								{:else}
									<input
										id="end-date-input"
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

					<div class="mt-4">
						<label class="label-text text-sm font-medium" for="visit-notes"
							>{$t('adventures.notes')}</label
						>
						<textarea
							id="visit-notes"
							class="textarea textarea-bordered w-full mt-1"
							rows="3"
							placeholder={$t('adventures.notes_placeholder') + '...'}
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
							{visitIdEditing ? $t('adventures.update_visit') : $t('adventures.add_visit')}
						</button>
					</div>
				</div>

				<!-- Validation Error -->
				{#if !isDateValid}
					<div class="alert alert-error mb-6">
						<AlertIcon class="w-5 h-5" />
						<span class="text-sm">{$t('adventures.invalid_date_range')}</span>
					</div>
				{/if}

				<!-- Visits List (Location only) -->

				<div class="bg-base-50 p-4 rounded-lg border border-base-200">
					<h3 class="font-medium text-base-content/80 mb-4">
						{$t('adventures.visits')} ({visits?.length || 0})
					</h3>

					{#if !visits || visits.length === 0}
						<div class="text-center py-8 text-base-content/60">
							<CalendarIcon class="w-8 h-8 mx-auto mb-2 opacity-50" />
							<p class="text-sm">{$t('adventures.no_visits')}</p>
							<p class="text-xs text-base-content/40 mt-1">
								{$t('adventures.no_visits_description')}
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
													<span class="badge badge-outline badge-sm"
														>{$t('adventures.all_day')}</span
													>
												{:else}
													<ClockIcon class="w-3 h-3 text-base-content/50" />
												{/if}
												{#if visit.timezone && !isAllDay(visit.start_date)}
													<span class="badge badge-outline badge-sm">{visit.timezone}</span>
												{/if}
												<div class="text-sm font-medium truncate">
													{#if isAllDay(visit.start_date)}
														{visit.start_date && typeof visit.start_date === 'string'
															? visit.start_date.split('T')[0]
															: ''}
														– {visit.end_date && typeof visit.end_date === 'string'
															? visit.end_date.split('T')[0]
															: ''}
													{:else if 'start_timezone' in visit && visit.timezone}
														{formatDateInTimezone(visit.start_date, visit.timezone)}
														– {formatDateInTimezone(visit.end_date, visit.timezone)}
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

											{#if visit.activities && visit.activities.length > 0}
												<div class="flex items-center gap-2 mt-2">
													<RunFastIcon class="w-3 h-3 text-success" />
													<span class="text-xs text-success font-medium">
														{visit.activities.length}
														{$t('adventures.saved_activities')}
													</span>
												</div>
											{/if}
										</div>

										<!-- Visit Actions -->
										<div class="flex gap-1 ml-4">
											<!-- Activities Button (only show if Strava is enabled) -->
											{#if stravaEnabled}
												<button
													class="btn btn-info btn-xs tooltip tooltip-top gap-1"
													data-tip={$t('adventures.view_strava_activities')}
													on:click={() => toggleVisitActivities(visit)}
												>
													<RunFastIcon class="w-3 h-3" />
													{#if visitActivities[visit.id]}
														({visitActivities[visit.id].length})
													{/if}
												</button>
											{/if}

											<!-- Upload Activity Button -->
											<button
												class="btn btn-success btn-xs tooltip tooltip-top gap-1"
												data-tip={$t('adventures.add_activity')}
												on:click={() => showActivityUploadForm(visit.id)}
											>
												<UploadIcon class="w-3 h-3" />
											</button>

											<button
												class="btn btn-warning btn-xs tooltip tooltip-top"
												data-tip={$t('adventures.edit_visit')}
												on:click={() => editVisit(visit)}
											>
												<EditIcon class="w-3 h-3" />
											</button>
											<button
												class="btn btn-error btn-xs tooltip tooltip-top"
												data-tip={$t('adventures.remove_visit')}
												on:click={() => removeVisit(visit.id)}
											>
												<TrashIcon class="w-3 h-3" />
											</button>
										</div>
									</div>

									<!-- Activity Upload Form -->
									{#if showActivityUpload[visit.id]}
										<div class="mt-4 pt-4 border-t border-base-300">
											<div class="flex items-center justify-between mb-3">
												<div class="flex items-center gap-2">
													<UploadIcon class="w-4 h-4 text-success" />
													<h4 class="font-medium text-sm">
														{#if pendingStravaImport[visit.id]}
															{$t('adventures.complete_strava_import')}
														{:else}
															{$t('adventures.add_new_activity')}
														{/if}
													</h4>
												</div>
												<button
													class="btn btn-ghost btn-xs"
													on:click={() => hideActivityUploadForm(visit.id)}
												>
													<CloseIcon class="w-3 h-3" />
												</button>
											</div>

											{#if pendingStravaImport[visit.id]}
												<div class="alert alert-info mb-4">
													<div class="flex items-center gap-2">
														<RunFastIcon class="w-4 h-4" />
														<div class="text-sm">
															<div class="font-medium">
																{$t('adventures.strava_activity_ready')}
															</div>
															<div class="text-xs opacity-75">
																{$t('adventures.gpx_file_downloaded')}
															</div>
														</div>
													</div>
												</div>
											{/if}

											<div class="bg-base-200/50 p-4 rounded-lg">
												{#if pendingStravaImport[visit.id]}
													<!-- Highlight GPX upload for Strava imports -->
													<div class="mb-6 p-4 bg-warning/10 border-2 border-warning/30 rounded-lg">
														<div class="flex items-center gap-2 mb-2">
															<FileIcon class="w-4 h-4 text-warning" />
															<label
																class="label-text font-medium text-warning"
																for="gpx-file-{visit.id}"
																>{$t('adventures.gpx_file_required')} *</label
															>
														</div>
														<div class="flex gap-2">
															<input
																id="gpx-file-{visit.id}"
																type="file"
																accept=".gpx"
																class="file-input file-input-bordered file-input-warning flex-1"
																on:change={handleGpxFileChange}
															/>
															<button
																type="button"
																class="btn btn-warning btn-sm gap-1"
																on:click={() => {
																	const stravaActivity = pendingStravaImport[visit.id];
																	if (stravaActivity && stravaActivity.export_gpx) {
																		window.open(stravaActivity.export_gpx, '_blank');
																	}
																}}
															>
																<UploadIcon class="w-3 h-3" />
																{$t('adventures.download_gpx')}
															</button>
														</div>
														<div class="text-xs text-warning/80 mt-1">
															{$t('adventures.upload_gpx_file')}
														</div>
													</div>
												{/if}

												<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
													<!-- Activity Name -->
													<div class="md:col-span-2">
														<label
															class="label-text text-xs font-medium"
															for="activity-name-{visit.id}"
															>{$t('adventures.activity_name')} *</label
														>
														<input
															id="activity-name-{visit.id}"
															type="text"
															class="input input-bordered input-sm w-full mt-1"
															placeholder={$t('adventures.activity_name_placeholder')}
															bind:value={activityForm.name}
														/>
													</div>

													<!-- Sport Type -->
													<div>
														<label
															class="label-text text-xs font-medium"
															for="sport-type-{visit.id}">{$t('adventures.sport_type')}</label
														>
														<select
															id="sport-type-{visit.id}"
															class="select select-bordered select-sm w-full mt-1"
															bind:value={activityForm.sport_type}
															disabled={!!pendingStravaImport[visit.id]}
														>
															{#each SPORT_TYPE_CHOICES as sportType}
																<option value={sportType.key}
																	>{sportType.icon} {sportType.label}</option
																>
															{/each}
														</select>
													</div>

													<!-- Distance -->
													<div>
														<label class="label-text text-xs font-medium" for="distance-{visit.id}"
															>{$t('adventures.distance')} (km)</label
														>
														<input
															id="distance-{visit.id}"
															type="number"
															step="0.01"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="5.2"
															bind:value={activityForm.distance}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Moving Time -->
													<div>
														<label
															class="label-text text-xs font-medium"
															for="moving-time-{visit.id}"
															>{$t('adventures.moving_time')} (HH:MM:SS)</label
														>
														<input
															id="moving-time-{visit.id}"
															type="text"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="0:25:30"
															bind:value={activityForm.moving_time}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Elapsed Time -->
													<div>
														<label
															class="label-text text-xs font-medium"
															for="elapsed-time-{visit.id}"
															>{$t('adventures.elapsed_time')} (HH:MM:SS)</label
														>
														<input
															id="elapsed-time-{visit.id}"
															type="text"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="0:30:00"
															bind:value={activityForm.elapsed_time}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Start Date -->
													<div>
														<label
															class="label-text text-xs font-medium"
															for="start-date-{visit.id}">{$t('adventures.start_date')}</label
														>
														<input
															id="start-date-{visit.id}"
															type="datetime-local"
															class="input input-bordered input-sm w-full mt-1"
															bind:value={activityForm.start_date}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Elevation Gain -->
													{#if !activityForm.gpx_file}
														<div>
															<label
																class="label-text text-xs font-medium"
																for="elevation-gain-{visit.id}"
																>{$t('adventures.elevation_gain')} (m)</label
															>
															<input
																id="elevation-gain-{visit.id}"
																type="number"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="150"
																bind:value={activityForm.elevation_gain}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>
													{/if}

													<!-- Elevation Loss -->
													{#if !activityForm.gpx_file}
														<div>
															<label
																class="label-text text-xs font-medium"
																for="elevation-loss-{visit.id}"
																>{$t('adventures.elevation_loss')} (m)</label
															>
															<input
																id="elevation-loss-{visit.id}"
																type="number"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="150"
																bind:value={activityForm.elevation_loss}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>
													{/if}

													<!-- Calories -->
													<div>
														<label class="label-text text-xs font-medium" for="calories-{visit.id}"
															>{$t('adventures.calories')}</label
														>
														<input
															id="calories-{visit.id}"
															type="number"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="300"
															bind:value={activityForm.calories}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Elevation High -->
													{#if !activityForm.gpx_file}
														<div>
															<label
																class="label-text text-xs font-medium"
																for="elevation-high-{visit.id}"
																>{$t('adventures.elevation_high')} (m)</label
															>
															<input
																id="elevation-high-{visit.id}"
																type="number"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="2000"
																bind:value={activityForm.elev_high}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>
													{/if}

													<!-- Elevation Low -->
													{#if !activityForm.gpx_file}
														<div>
															<label
																class="label-text text-xs font-medium"
																for="elevation-low-{visit.id}"
																>{$t('adventures.elevation_low')} (m)</label
															>
															<input
																id="elevation-low-{visit.id}"
																type="number"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="1000"
																bind:value={activityForm.elev_low}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>
													{/if}

													<!-- Rest Time -->
													<div>
														<label class="label-text text-xs font-medium" for="rest-time-{visit.id}"
															>{$t('adventures.rest_time')} (s)</label
														>
														<input
															id="rest-time-{visit.id}"
															type="number"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="60"
															bind:value={activityForm.rest_time}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Start Latitude -->
													<div>
														<label class="label-text text-xs font-medium" for="start-lat-{visit.id}"
															>{$t('adventures.start_lat')} (°)</label
														>
														<input
															id="start-lat-{visit.id}"
															type="number"
															step="any"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="37.7749"
															bind:value={activityForm.start_lat}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Start Longitude -->
													<div>
														<label class="label-text text-xs font-medium" for="start-lng-{visit.id}"
															>{$t('adventures.start_lng')} (°)</label
														>
														<input
															id="start-lng-{visit.id}"
															type="number"
															step="any"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="-122.4194"
															bind:value={activityForm.start_lng}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- End Latitude -->
													<div>
														<label class="label-text text-xs font-medium" for="end-lat-{visit.id}"
															>{$t('adventures.end_lat')} (°)</label
														>
														<input
															id="end-lat-{visit.id}"
															type="number"
															step="any"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="37.7749"
															bind:value={activityForm.end_lat}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- End Longitude -->
													<div>
														<label class="label-text text-xs font-medium" for="end-lng-{visit.id}"
															>{$t('adventures.end_lng')} (°)</label
														>
														<input
															id="end-lng-{visit.id}"
															type="number"
															step="any"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="-122.4194"
															bind:value={activityForm.end_lng}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Timezone -->
													<div>
														<label class="label-text text-xs font-medium" for="timezone-{visit.id}"
															>{$t('adventures.timezone')}</label
														>
														<TimezoneSelector bind:selectedTimezone={activityForm.timezone} />
													</div>

													<!-- Average Speed -->
													<div>
														<label
															class="label-text text-xs font-medium"
															for="average-speed-{visit.id}"
															>{$t('adventures.average_speed')} (m/s)</label
														>
														<input
															id="average-speed-{visit.id}"
															type="number"
															step="any"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="3.5"
															bind:value={activityForm.average_speed}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Max Speed -->
													<div>
														<label class="label-text text-xs font-medium" for="max-speed-{visit.id}"
															>{$t('adventures.max_speed')} (m/s)</label
														>
														<input
															id="max-speed-{visit.id}"
															type="number"
															step="any"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="5.0"
															bind:value={activityForm.max_speed}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Average Cadence -->
													<div>
														<label
															class="label-text text-xs font-medium"
															for="average-cadence-{visit.id}"
															>{$t('adventures.average_cadence')} (rpm)</label
														>
														<input
															id="average-cadence-{visit.id}"
															type="number"
															step="any"
															class="input input-bordered input-sm w-full mt-1"
															placeholder="80"
															bind:value={activityForm.average_cadence}
															readonly={!!pendingStravaImport[visit.id]}
														/>
													</div>

													<!-- Trail Selection -->
													{#if trails && trails.length > 0}
														<div class="md:col-span-2">
															<label
																class="label-text text-xs font-medium"
																for="trail-select-{visit.id}">{$t('adventures.trail')}</label
															>
															<select
																id="trail-select-{visit.id}"
																class="select select-bordered select-sm w-full mt-1"
																bind:value={activityForm.trail}
															>
																<option value="">Select a trail</option>
																{#each trails as trail (trail.id)}
																	<option value={trail.id}>{trail.name}</option>
																{/each}
															</select>
														</div>
													{/if}

													<!-- GPX File (for manual uploads) -->
													{#if !pendingStravaImport[visit.id]}
														<div class="md:col-span-2">
															<label
																class="label-text text-xs font-medium"
																for="gpx-file-manual-{visit.id}">{$t('adventures.gpx_file')}</label
															>
															<input
																id="gpx-file-manual-{visit.id}"
																type="file"
																accept=".gpx"
																class="file-input file-input-bordered file-input-sm w-full mt-1"
																on:change={handleGpxFileChange}
															/>
														</div>
													{/if}
												</div>

												<div class="flex justify-end gap-2 mt-4">
													<button
														class="btn btn-ghost btn-sm"
														on:click={() => hideActivityUploadForm(visit.id)}
														disabled={uploadingActivity[visit.id]}
													>
														Cancel
													</button>
													<button
														class="btn btn-success btn-sm gap-2"
														on:click={() => uploadActivity(visit.id)}
														disabled={uploadingActivity[visit.id] ||
															!activityForm.name.trim() ||
															(pendingStravaImport[visit.id] && !activityForm.gpx_file)}
													>
														{#if uploadingActivity[visit.id]}
															<LoadingIcon class="w-3 h-3 animate-spin" />
															{#if pendingStravaImport[visit.id]}
																{$t('adventures.importing')}...
															{:else}
																{$t('adventures.uploading')}...
															{/if}
														{:else if pendingStravaImport[visit.id]}
															<UploadIcon class="w-3 h-3" />
															{$t('adventures.complete_import')}
														{:else}
															<UploadIcon class="w-3 h-3" />
															{$t('adventures.upload_activity')}
														{/if}
													</button>
												</div>
											</div>
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
														{visit}
														{measurementSystem}
														on:delete={(event) =>
															deleteActivity(event.detail.visitId, event.detail.activityId)}
													/>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Strava Activities Section -->
									{#if stravaEnabled && expandedVisits[visit.id]}
										<div class="mt-4 pt-4 border-t border-base-300">
											<div class="flex items-center gap-2 mb-3">
												<RunFastIcon class="w-4 h-4 text-info" />
												<h4 class="font-medium text-sm">
													{$t('adventures.strava_activities_during_visit')}
												</h4>
												{#if loadingActivities[visit.id]}
													<LoadingIcon class="w-4 h-4 animate-spin text-info" />
												{/if}
											</div>

											{#if loadingActivities[visit.id]}
												<div class="text-center py-4">
													<div class="loading loading-spinner loading-sm"></div>
													<p class="text-xs text-base-content/60 mt-2">
														{$t('adventures.loading_activities')}...
													</p>
												</div>
											{:else if visitActivities[visit.id] && visitActivities[visit.id].length > 0}
												<div class="space-y-2">
													{#each visitActivities[visit.id] as activity (activity.id)}
														<div class="pl-4">
															<StravaActivityCard
																{activity}
																on:import={(event) => handleStravaActivityImport(event, visit.id)}
																{measurementSystem}
															/>
														</div>
													{/each}
												</div>
											{:else}
												<div class="text-center py-4 text-base-content/60">
													<div class="text-2xl mb-2">🏃‍♂️</div>
													<p class="text-xs">{$t('adventures.no_strava_activities')}</p>
												</div>
											{/if}
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		</div>

		<!-- if localStartDate and localEndDate are set, show a callout saying its not saved yet -->
		{#if localStartDate || localEndDate}
			<div class="alert alert-neutral">
				<InfoIcon class="w-5 h-5" />
				<div>
					<div class="font-medium text-sm">{$t('adventures.dates_not_saved')}</div>
					<div class="text-xs opacity-75">{$t('adventures.dates_not_saved_description')}</div>
				</div>
			</div>
		{/if}

		<div class="flex gap-3 justify-end pt-4">
			<button class="btn btn-neutral-200 gap-2" on:click={handleBack}>
				<ArrowLeftIcon class="w-5 h-5" />
				{$t('adventures.back')}
			</button>

			<button class="btn btn-primary gap-2" on:click={handleClose}>
				<CheckIcon class="w-5 h-5" />
				{$t('adventures.done')}
			</button>
		</div>
	</div>
</div>
