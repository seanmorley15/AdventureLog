<script lang="ts">
	import type { Collection, StravaActivity, Trail, Activity } from '$lib/types';
	import TimezoneSelector from '../TimezoneSelector.svelte';
	import { t } from 'svelte-i18n';
	import { updateLocalDate, updateUTCDate, validateDateRange, formatUTCDate } from '$lib/dateUtils';
	import { onMount } from 'svelte';
	import { isAllDay } from '$lib';
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
	import UploadIcon from '~icons/mdi/upload';
	import FileIcon from '~icons/mdi/file';
	import CloseIcon from '~icons/mdi/close';
	import StravaActivityCard from '../StravaActivityCard.svelte';

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
	export let trails: Trail[] = [];

	const dispatch = createEventDispatcher();

	// Types
	type Visit = {
		id: string;
		start_date: string;
		end_date: string;
		notes: string;
		timezone: string | null;
		activities?: Activity[];
	};

	type TransportationVisit = {
		id: string;
		start_date: string;
		end_date: string;
		notes: string;
		start_timezone: string;
		end_timezone: string;
		activities?: Activity[];
	};

	// Component state
	let allDay: boolean = false;
	let localStartDate: string = '';
	let localEndDate: string = '';
	let fullStartDate: string = '';
	let fullEndDate: string = '';
	let constrainDates: boolean = false;
	let isEditing = false;

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
		type: 'Run',
		sport_type: 'Run',
		distance: null as number | null,
		moving_time: '',
		elapsed_time: '',
		elevation_gain: null as number | null,
		elevation_loss: null as number | null,
		start_date: '',
		calories: null as number | null,
		notes: '',
		gpx_file: null as File | null
	};

	// Activity types for dropdown
	const activityTypes = [
		'Run',
		'Ride',
		'Swim',
		'Hike',
		'Walk',
		'Workout',
		'CrossTrain',
		'Rock Climbing',
		'Alpine Ski',
		'Nordic Ski',
		'Kayaking',
		'Canoeing',
		'Rowing',
		'Golf',
		'Tennis',
		'Other'
	];

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
				end_timezone: selectedEndTimezone,
				activities: []
			};
			return transportVisit;
		} else {
			const regularVisit: Visit = {
				id: uniqueId,
				start_date: utcStartDate ?? '',
				end_date: utcEndDate ?? utcStartDate ?? '',
				notes: note ?? '',
				timezone: selectedStartTimezone,
				activities: []
			};
			return regularVisit;
		}
	}

	async function addVisit() {
		const newVisit = createVisitObject();

		// Patch updated visits array to location and get the response with actual IDs
		console.log('Adding new visit:', newVisit);
		console.log(objectId);
		if (type === 'location' && objectId) {
			try {
				const updatedVisits = visits ? [...visits, newVisit] : [newVisit];
				console.log('Patching visits:', updatedVisits);

				const response = await fetch(`/api/locations/${objectId}/`, {
					method: 'PATCH',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({ visits: updatedVisits })
				});

				if (response.ok) {
					const updatedLocation = await response.json();
					// Update visits with the response data that contains actual IDs
					visits = updatedLocation.visits;
				} else {
					console.error('Failed to patch visits:', await response.text());
					return; // Don't update local state if API call failed
				}
			} catch (error) {
				console.error('Error patching visits:', error);
				return; // Don't update local state if API call failed
			}
		} else {
			// Fallback for non-location types - add new visit to the visits array
			if (visits) {
				visits = [...visits, newVisit];
			} else {
				visits = [newVisit];
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
			type: 'Run',
			sport_type: 'Run',
			distance: null,
			moving_time: '',
			elapsed_time: '',
			elevation_gain: null,
			elevation_loss: null,
			start_date: '',
			calories: null,
			notes: '',
			gpx_file: null
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
			alert('Activity name is required');
			return;
		}

		// If this is a Strava import, require GPX file
		if (pendingStravaImport[visitId] && !activityForm.gpx_file) {
			alert('Please upload the GPX file to complete the Strava import');
			return;
		}

		uploadingActivity[visitId] = true;
		uploadingActivity = { ...uploadingActivity };

		try {
			const formData = new FormData();

			// Add basic activity data
			formData.append('visit', visitId);
			formData.append('name', activityForm.name);
			formData.append('type', activityForm.type);
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
				formData.append('start_date', new Date(activityForm.start_date).toISOString());
			if (activityForm.calories) formData.append('calories', activityForm.calories.toString());

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
				console.log('Activity uploaded successfully:', newActivity);

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

				const importMessage = pendingStravaImport[visitId]
					? `Strava activity "${activityForm.name}" imported successfully!`
					: 'Activity uploaded successfully!';
				alert(importMessage);
			} else {
				const errorText = await response.text();
				console.error('Failed to upload activity:', errorText);
				alert('Failed to upload activity. Please try again.');
			}
		} catch (error) {
			console.error('Error uploading activity:', error);
			alert('Error uploading activity. Please try again.');
		} finally {
			uploadingActivity[visitId] = false;
			uploadingActivity = { ...uploadingActivity };
		}
	}

	async function deleteActivity(visitId: string, activityId: string) {
		if (!confirm('Are you sure you want to delete this activity?')) return;

		try {
			const response = await fetch(`/api/activities/${activityId}/`, {
				method: 'DELETE'
			});

			if (response.ok) {
				// Update the visit's activities array
				if (visits) {
					visits = visits.map((visit) => {
						if (visit.id === visitId) {
							return {
								...visit,
								activities: (visit.activities || []).filter((a) => a.id !== activityId)
							};
						}
						return visit;
					});
				}

				// Update the location with new visits data
				if (type === 'location' && objectId) {
					await fetch(`/api/locations/${objectId}/`, {
						method: 'PATCH',
						headers: {
							'Content-Type': 'application/json'
						},
						body: JSON.stringify({ visits })
					});
				}
			} else {
				console.error('Failed to delete activity:', await response.text());
				alert('Failed to delete activity. Please try again.');
			}
		} catch (error) {
			console.error('Error deleting activity:', error);
			alert('Error deleting activity. Please try again.');
		}
	}

	async function handleStravaActivityImport(event: CustomEvent<StravaActivity>, visitId: string) {
		const stravaActivity = event.detail;

		try {
			// Open GPX export in new tab
			window.open(stravaActivity.export_gpx, '_blank');

			// Store the pending import and show upload form
			pendingStravaImport[visitId] = stravaActivity;
			pendingStravaImport = { ...pendingStravaImport };

			// Pre-fill the activity form with Strava data
			activityForm = {
				name: stravaActivity.name,
				type: stravaActivity.type,
				sport_type: stravaActivity.sport_type || stravaActivity.type,
				distance: stravaActivity.distance ? stravaActivity.distance / 1000 : null, // Convert to km
				moving_time: stravaActivity.moving_time ? formatDuration(stravaActivity.moving_time) : '',
				elapsed_time: stravaActivity.elapsed_time
					? formatDuration(stravaActivity.elapsed_time)
					: '',
				elevation_gain: stravaActivity.total_elevation_gain || null,
				elevation_loss: stravaActivity.estimated_elevation_loss || null,
				start_date: stravaActivity.start_date ? stravaActivity.start_date.substring(0, 16) : '',
				calories: stravaActivity.calories || null,
				notes: '',
				gpx_file: null
			};

			// Show the upload form
			showActivityUpload[visitId] = true;
			showActivityUpload = { ...showActivityUpload };
		} catch (error) {
			console.error('Error initiating Strava import:', error);
			alert('Error downloading GPX file. Please try again.');
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

		// Update the visits array in the parent component
		if (type === 'location' && objectId) {
			fetch(`/api/locations/${objectId}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ visits })
			});
		}
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

		// Patch updated visits array to location
		if (type === 'location' && objectId) {
			fetch(`/api/locations/${objectId}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ visits })
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

	$: typeConfig = getTypeConfig();
	$: isDateValid = validateDateRange(utcStartDate ?? '', utcEndDate ?? '').valid;
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
									<label class="label-text text-sm font-medium">Constrain to Collection Dates</label
									>
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

												{#if visit.activities && visit.activities.length > 0}
													<div class="flex items-center gap-2 mt-2">
														<RunFastIcon class="w-3 h-3 text-success" />
														<span class="text-xs text-success font-medium">
															{visit.activities.length} saved activities
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
														data-tip="View Strava Activities"
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
													data-tip="Add Activity"
													on:click={() => showActivityUploadForm(visit.id)}
												>
													<UploadIcon class="w-3 h-3" />
												</button>

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

										<!-- Activity Upload Form -->
										{#if showActivityUpload[visit.id]}
											<div class="mt-4 pt-4 border-t border-base-300">
												<div class="flex items-center justify-between mb-3">
													<div class="flex items-center gap-2">
														<UploadIcon class="w-4 h-4 text-success" />
														<h4 class="font-medium text-sm">
															{#if pendingStravaImport[visit.id]}
																Complete Strava Import
															{:else}
																Add New Activity
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
																<div class="font-medium">Strava Activity Ready</div>
																<div class="text-xs opacity-75">
																	GPX file downloaded. Please upload it below to complete the
																	import.
																</div>
															</div>
														</div>
													</div>
												{/if}

												<div class="bg-base-200/50 p-4 rounded-lg">
													{#if pendingStravaImport[visit.id]}
														<!-- Highlight GPX upload for Strava imports -->
														<div
															class="mb-6 p-4 bg-warning/10 border-2 border-warning/30 rounded-lg"
														>
															<div class="flex items-center gap-2 mb-2">
																<FileIcon class="w-4 h-4 text-warning" />
																<label class="label-text font-medium text-warning"
																	>GPX File Required *</label
																>
															</div>
															<input
																type="file"
																accept=".gpx"
																class="file-input file-input-bordered file-input-warning w-full"
																on:change={handleGpxFileChange}
															/>
															<div class="text-xs text-warning/80 mt-1">
																Upload the GPX file that was just downloaded to complete the Strava
																import
															</div>
														</div>
													{/if}

													<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
														<!-- Activity Name -->
														<div class="md:col-span-2">
															<label class="label-text text-xs font-medium">Activity Name *</label>
															<input
																type="text"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="Morning Run"
																bind:value={activityForm.name}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>

														<!-- Activity Type -->
														<div>
															<label class="label-text text-xs font-medium">Type</label>
															<select
																class="select select-bordered select-sm w-full mt-1"
																bind:value={activityForm.type}
																disabled={!!pendingStravaImport[visit.id]}
															>
																{#each activityTypes as activityType}
																	<option value={activityType}>{activityType}</option>
																{/each}
															</select>
														</div>

														<!-- Sport Type -->
														<div>
															<label class="label-text text-xs font-medium">Sport Type</label>
															<input
																type="text"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="Trail Running"
																bind:value={activityForm.sport_type}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>

														<!-- Distance -->
														<div>
															<label class="label-text text-xs font-medium">Distance (km)</label>
															<input
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
															<label class="label-text text-xs font-medium"
																>Moving Time (HH:MM:SS)</label
															>
															<input
																type="text"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="0:25:30"
																bind:value={activityForm.moving_time}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>

														<!-- Elapsed Time -->
														<div>
															<label class="label-text text-xs font-medium"
																>Elapsed Time (HH:MM:SS)</label
															>
															<input
																type="text"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="0:30:00"
																bind:value={activityForm.elapsed_time}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>

														<!-- Start Date -->
														<div>
															<label class="label-text text-xs font-medium">Start Date</label>
															<input
																type="datetime-local"
																class="input input-bordered input-sm w-full mt-1"
																bind:value={activityForm.start_date}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>

														<!-- Elevation Gain -->
														<div>
															<label class="label-text text-xs font-medium"
																>Elevation Gain (m)</label
															>
															<input
																type="number"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="150"
																bind:value={activityForm.elevation_gain}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>

														<!-- Elevation Loss -->
														<div>
															<label class="label-text text-xs font-medium"
																>Elevation Loss (m)</label
															>
															<input
																type="number"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="150"
																bind:value={activityForm.elevation_loss}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>

														<!-- Calories -->
														<div>
															<label class="label-text text-xs font-medium">Calories</label>
															<input
																type="number"
																class="input input-bordered input-sm w-full mt-1"
																placeholder="300"
																bind:value={activityForm.calories}
																readonly={!!pendingStravaImport[visit.id]}
															/>
														</div>

														<!-- GPX File (for manual uploads) -->
														{#if !pendingStravaImport[visit.id]}
															<div class="md:col-span-2">
																<label class="label-text text-xs font-medium">GPX File</label>
																<input
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
																	Importing...
																{:else}
																	Uploading...
																{/if}
															{:else if pendingStravaImport[visit.id]}
																<UploadIcon class="w-3 h-3" />
																Complete Import
															{:else}
																<UploadIcon class="w-3 h-3" />
																Upload Activity
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
														Saved Activities ({visit.activities.length})
													</h4>
												</div>

												<div class="space-y-2">
													{#each visit.activities as activity (activity.id)}
														<div class="bg-base-200/50 p-3 rounded-lg">
															<div class="flex items-start justify-between">
																<div class="flex-1 min-w-0">
																	<div class="flex items-center gap-2 mb-1">
																		<RunFastIcon class="w-3 h-3 text-success flex-shrink-0" />
																		<h5 class="font-medium text-sm truncate">{activity.name}</h5>
																		<span class="badge badge-outline badge-xs">{activity.type}</span
																		>
																	</div>

																	<div class="text-xs text-base-content/70 space-y-1">
																		{#if activity.distance}
																			<div class="flex items-center gap-4">
																				<span>Distance: {activity.distance} km</span>
																				{#if activity.moving_time}
																					<span>Time: {activity.moving_time}</span>
																				{/if}
																			</div>
																		{/if}

																		{#if activity.elevation_gain || activity.elevation_loss}
																			<div class="flex items-center gap-4">
																				{#if activity.elevation_gain}
																					<span>↗ {activity.elevation_gain}m</span>
																				{/if}
																				{#if activity.elevation_loss}
																					<span>↘ {activity.elevation_loss}m</span>
																				{/if}
																			</div>
																		{/if}

																		{#if activity.start_date}
																			<div>
																				Started: {new Date(activity.start_date).toLocaleString()}
																			</div>
																		{/if}

																		{#if activity.gpx_file}
																			<div class="flex items-center gap-1">
																				<FileIcon class="w-3 h-3" />
																				<a
																					href={activity.gpx_file}
																					target="_blank"
																					class="link link-primary"
																				>
																					View GPX
																				</a>
																			</div>
																		{/if}
																	</div>
																</div>

																<button
																	class="btn btn-error btn-xs tooltip tooltip-top ml-2"
																	data-tip="Delete Activity"
																	on:click={() => deleteActivity(visit.id, activity.id)}
																>
																	<TrashIcon class="w-3 h-3" />
																</button>
															</div>
														</div>
													{/each}
												</div>
											</div>
										{/if}

										<!-- Strava Activities Section -->
										{#if stravaEnabled && expandedVisits[visit.id]}
											<div class="mt-4 pt-4 border-t border-base-300">
												<div class="flex items-center gap-2 mb-3">
													<RunFastIcon class="w-4 h-4 text-info" />
													<h4 class="font-medium text-sm">Strava Activities During Visit</h4>
													{#if loadingActivities[visit.id]}
														<LoadingIcon class="w-4 h-4 animate-spin text-info" />
													{/if}
												</div>

												{#if loadingActivities[visit.id]}
													<div class="text-center py-4">
														<div class="loading loading-spinner loading-sm"></div>
														<p class="text-xs text-base-content/60 mt-2">Loading activities...</p>
													</div>
												{:else if visitActivities[visit.id] && visitActivities[visit.id].length > 0}
													<div class="space-y-2">
														{#each visitActivities[visit.id] as activity (activity.id)}
															<div class="pl-4">
																<StravaActivityCard
																	{activity}
																	on:import={(event) => handleStravaActivityImport(event, visit.id)}
																/>
															</div>
														{/each}
													</div>
												{:else}
													<div class="text-center py-4 text-base-content/60">
														<div class="text-2xl mb-2">🏃‍♂️</div>
														<p class="text-xs">No Strava activities found during this visit</p>
													</div>
												{/if}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>

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
