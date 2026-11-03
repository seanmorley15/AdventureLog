<script lang="ts">
	import { onMount } from 'svelte';
	import { deserialize } from '$app/forms';
	import { t } from 'svelte-i18n';
	import type { Activity, StravaActivity, Trail } from '#lib/types.js';
	import { SPORT_TYPE_CHOICES, isVisitAllDay, allDayDatePart } from '#lib';
	import { addToast } from '#lib/toasts.js';
	import DateInput from '#lib/components/shared/DateInput.svelte';
	import TimezoneSelector from '#lib/components/TimezoneSelector.svelte';
	import StravaActivityCard from '#lib/components/StravaActivityCard.svelte';
	import RunFastIcon from '~icons/mdi/run-fast';
	import UploadIcon from '~icons/mdi/upload';
	import LoadingIcon from '~icons/mdi/loading';

	interface Props {
		visitId?: string | null;
		dayId?: string | null;
		dateStart?: string | null;
		dateEnd?: string | null;
		timezone?: string | null;
		trails?: Trail[];
		measurementSystem?: 'metric' | 'imperial';
		/** Open on the manual form, or on an integration list. */
		initialPanel?: 'form' | 'strava' | 'endurain';
		onSaved: (activity: Activity) => void;
		onCancel?: () => void;
	}

	let {
		visitId = null,
		dayId = null,
		dateStart = null,
		dateEnd = null,
		timezone = null,
		trails = [],
		measurementSystem = 'metric',
		initialPanel = 'form',
		onSaved,
		onCancel
	}: Props = $props();

	const isImperial = $derived(measurementSystem === 'imperial');
	const distanceUnit = $derived(isImperial ? 'mi' : 'km');
	const elevationUnit = $derived(isImperial ? 'ft' : 'm');
	const speedUnit = $derived(isImperial ? 'mph' : 'km/h');

	let panelChoice = $state<'form' | 'strava' | 'endurain' | null>(null);
	const panel = $derived(panelChoice ?? initialPanel);
	let stravaEnabled = $state(false);
	let endurainEnabled = $state(false);
	let stravaActivities = $state<StravaActivity[]>([]);
	let endurainActivities = $state<StravaActivity[]>([]);
	let loadingStrava = $state(false);
	let loadingEndurain = $state(false);
	let importingEndurain = $state(false);
	let saving = $state(false);
	let showExtras = $state(false);
	let pendingProvider = $state<'strava' | 'endurain' | null>(null);
	let externalId = $state<string | null>(null);

	let name = $state('');
	let sportType = $state('Hike');
	let distance = $state<number | null>(null);
	let movingTime = $state('');
	let elapsedTime = $state('');
	let elevationGain = $state<number | null>(null);
	let elevationLoss = $state<number | null>(null);
	let startDate = $state('');
	let startDateLocal = $state('');
	let calories = $state<number | null>(null);
	let gpxFile = $state<File | null>(null);
	let trailId = $state('');
	let elevHigh = $state<number | null>(null);
	let elevLow = $state<number | null>(null);
	let restTime = $state<number | null>(null);
	let averageSpeed = $state<number | null>(null);
	let maxSpeed = $state<number | null>(null);
	let averageCadence = $state<number | null>(null);
	let startLat = $state<number | null>(null);
	let startLng = $state<number | null>(null);
	let endLat = $state<number | null>(null);
	let endLng = $state<number | null>(null);
	let zoneChoice = $state<string | null>(null);
	let zone = $derived(zoneChoice ?? timezone ?? 'UTC');

	const locked = $derived(pendingProvider === 'strava');

	function roundTo(value: number, digits: number) {
		const factor = 10 ** digits;
		return Math.round(value * factor) / factor;
	}
	function metersToDistance(meters: number | null | undefined) {
		if (meters == null) return null;
		return roundTo(isImperial ? meters / 1609.34 : meters / 1000, 2);
	}
	function distanceToMeters(value: number | null) {
		if (value == null) return null;
		return isImperial ? value * 1609.34 : value * 1000;
	}
	function metersToElevation(meters: number | null | undefined) {
		if (meters == null) return null;
		return roundTo(isImperial ? meters * 3.28084 : meters, 0);
	}
	function elevationToMeters(value: number | null) {
		if (value == null) return null;
		return isImperial ? value / 3.28084 : value;
	}
	function metersPerSecondToSpeed(metersPerSecond: number | null | undefined) {
		if (metersPerSecond == null) return null;
		return roundTo(isImperial ? metersPerSecond * 2.236936 : metersPerSecond * 3.6, 1);
	}
	function speedToMetersPerSecond(value: number | null) {
		if (value == null) return null;
		return isImperial ? value / 2.236936 : value / 3.6;
	}
	function formatDuration(seconds: number) {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		const secs = Math.floor(seconds % 60);
		if (hours > 0)
			return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
		return `${minutes}:${secs.toString().padStart(2, '0')}`;
	}
	function parseDuration(duration: string) {
		const parts = duration.split(':').map(Number);
		if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
		if (parts.length === 2) return parts[0] * 60 + parts[1];
		return parts[0] || 0;
	}

	function fillFromExternal(activity: StravaActivity) {
		name = activity.name;
		sportType = activity.sport_type || activity.type || 'Hike';
		distance = metersToDistance(activity.distance ?? null);
		movingTime = activity.moving_time ? formatDuration(activity.moving_time) : '';
		elapsedTime = activity.elapsed_time ? formatDuration(activity.elapsed_time) : '';
		elevationGain = metersToElevation(activity.total_elevation_gain ?? null);
		elevationLoss = metersToElevation(activity.estimated_elevation_loss ?? null);
		startDate = activity.start_date ? activity.start_date.substring(0, 16) : '';
		startDateLocal = activity.start_date_local ? activity.start_date_local.substring(0, 16) : '';
		calories = activity.calories ?? null;
		elevHigh = metersToElevation(activity.elev_high ?? null);
		elevLow = metersToElevation(activity.elev_low ?? null);
		restTime = activity.rest_time ?? null;
		averageSpeed = metersPerSecondToSpeed(activity.average_speed ?? null);
		maxSpeed = metersPerSecondToSpeed(activity.max_speed ?? null);
		averageCadence = activity.average_cadence ?? null;
		startLat = activity.start_latlng ? activity.start_latlng[0] : null;
		startLng = activity.start_latlng ? activity.start_latlng[1] : null;
		endLat = activity.end_latlng ? activity.end_latlng[0] : null;
		endLng = activity.end_latlng ? activity.end_latlng[1] : null;
		zoneChoice = activity.timezone || timezone || zone;
		externalId = String(activity.id);
		showExtras = true;
	}

	function activityWindow() {
		const startMs = dateStart ? Date.parse(dateStart) : Date.now() - 30 * 86400000;
		let endMs = dateEnd ? Date.parse(dateEnd) : Date.now();
		if (dateStart && dateEnd && isVisitAllDay(dateStart, dateEnd)) {
			endMs = Date.parse(`${allDayDatePart(dateEnd)}T23:59:59Z`);
		}
		return {
			start: new Date(startMs - 12 * 60 * 60 * 1000).toISOString(),
			end: new Date(endMs + 12 * 60 * 60 * 1000).toISOString()
		};
	}

	async function loadStrava() {
		if (!stravaEnabled) return;
		loadingStrava = true;
		panelChoice = 'strava';
		try {
			const { start, end } = activityWindow();
			const response = await fetch(
				`/api/integrations/strava/activities/?start_date=${start}&end_date=${end}`
			);
			const data = response.ok ? await response.json() : { activities: [] };
			stravaActivities = data.activities || [];
		} catch (error) {
			console.error(error);
			stravaActivities = [];
		} finally {
			loadingStrava = false;
		}
	}

	async function loadEndurain() {
		if (!endurainEnabled) return;
		loadingEndurain = true;
		panelChoice = 'endurain';
		try {
			const { start, end } = activityWindow();
			const response = await fetch(
				`/api/integrations/endurain/activities/?start_date=${start}&end_date=${end}`
			);
			const data = response.ok ? await response.json() : { activities: [] };
			endurainActivities = data.activities || [];
		} catch (error) {
			console.error(error);
			endurainActivities = [];
		} finally {
			loadingEndurain = false;
		}
	}

	function importStrava(event: CustomEvent<StravaActivity>) {
		fillFromExternal(event.detail);
		pendingProvider = 'strava';
		gpxFile = null;
		panelChoice = 'form';
	}

	async function importEndurain(event: CustomEvent<StravaActivity>) {
		const activity = event.detail;
		importingEndurain = true;
		pendingProvider = 'endurain';
		fillFromExternal(activity);
		try {
			const gpxResponse = await fetch(activity.export_gpx);
			if (gpxResponse.ok) {
				const blob = await gpxResponse.blob();
				const filename = `${activity.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.gpx`;
				gpxFile = new File([blob], filename, { type: 'application/gpx+xml' });
			}
		} catch (error) {
			console.error(error);
		} finally {
			importingEndurain = false;
		}
		panelChoice = 'form';
	}

	async function save() {
		if (!name.trim()) return;
		if (pendingProvider === 'strava' && !gpxFile) {
			addToast('error', $t('strava.gpx_required'));
			return;
		}
		saving = true;
		try {
			const formData = new FormData();
			if (visitId) formData.append('visit', visitId);
			if (dayId) formData.append('day', dayId);
			formData.append('name', name.trim());
			formData.append('sport_type', sportType);
			const distanceMeters = distanceToMeters(distance);
			if (distanceMeters != null) formData.append('distance', String(distanceMeters));
			if (movingTime) formData.append('moving_time', `PT${parseDuration(movingTime)}S`);
			if (elapsedTime) formData.append('elapsed_time', `PT${parseDuration(elapsedTime)}S`);
			const gain = elevationToMeters(elevationGain);
			if (gain != null) formData.append('elevation_gain', String(gain));
			const loss = elevationToMeters(elevationLoss);
			if (loss != null) formData.append('elevation_loss', String(loss));
			if (startDate) formData.append('start_date', startDate);
			if (startDateLocal) formData.append('start_date_local', startDateLocal);
			if (calories != null) formData.append('calories', String(calories));
			if (trailId) formData.append('trail', trailId);
			const high = elevationToMeters(elevHigh);
			if (high != null) formData.append('elev_high', String(high));
			const low = elevationToMeters(elevLow);
			if (low != null) formData.append('elev_low', String(low));
			if (restTime != null) formData.append('rest_time', `PT${restTime}S`);
			const avg = speedToMetersPerSecond(averageSpeed);
			if (avg != null) formData.append('average_speed', String(avg));
			const max = speedToMetersPerSecond(maxSpeed);
			if (max != null) formData.append('max_speed', String(max));
			if (averageCadence != null) formData.append('average_cadence', String(averageCadence));
			if (startLat != null) formData.append('start_lat', String(startLat));
			if (startLng != null) formData.append('start_lng', String(startLng));
			if (endLat != null) formData.append('end_lat', String(endLat));
			if (endLng != null) formData.append('end_lng', String(endLng));
			if (zone) formData.append('timezone', zone);
			if (gpxFile) formData.append('gpx_file', gpxFile);
			if (externalId) formData.append('external_service_id', externalId);

			const response = await fetch('/locations?/activity', { method: 'POST', body: formData });
			if (!response.ok) {
				addToast('error', $t('adventures.activity_upload_error'));
				return;
			}
			const parsed = deserialize(await response.text()) as { data?: Activity & { error?: string } };
			if (!parsed.data || parsed.data.error || !parsed.data.id) {
				addToast('error', parsed.data?.error || $t('adventures.activity_upload_error'));
				return;
			}
			addToast('success', $t('adventures.activity_upload_success'));
			onSaved(parsed.data);
		} catch (error) {
			console.error(error);
			addToast('error', $t('adventures.activity_upload_error'));
		} finally {
			saving = false;
		}
	}

	onMount(async () => {
		try {
			const response = await fetch('/api/integrations');
			if (response.ok) {
				const integrations = await response.json();
				stravaEnabled = Boolean(integrations.strava?.exists);
				endurainEnabled = Boolean(integrations.endurain?.exists);
			}
		} catch {
			stravaEnabled = false;
			endurainEnabled = false;
		}
		if (initialPanel === 'strava') void loadStrava();
		if (initialPanel === 'endurain') void loadEndurain();
	});
</script>

<div class="space-y-4">
	<div class="flex flex-wrap gap-2">
		<button
			type="button"
			class="btn btn-sm {panel === 'form' ? 'btn-success' : 'btn-outline'}"
			onclick={() => (panelChoice = 'form')}
		>
			<UploadIcon class="h-4 w-4" />
			{$t('adventures.add_activity')}
		</button>
		{#if stravaEnabled}
			<button
				type="button"
				class="btn btn-sm {panel === 'strava' ? 'btn-info' : 'btn-outline btn-info'}"
				onclick={loadStrava}
			>
				<RunFastIcon class="h-4 w-4" />
				Strava
			</button>
		{/if}
		{#if endurainEnabled}
			<button
				type="button"
				class="btn btn-sm {panel === 'endurain' ? 'btn-secondary' : 'btn-outline btn-secondary'}"
				onclick={loadEndurain}
			>
				<RunFastIcon class="h-4 w-4" />
				Endurain
			</button>
		{/if}
	</div>

	{#if panel === 'strava'}
		<div class="rounded-lg border border-base-300 bg-base-200/40 p-4">
			<h4 class="mb-3 font-medium">{$t('adventures.strava_activities_during_visit')}</h4>
			{#if loadingStrava}
				<div class="flex justify-center py-6"><span class="loading loading-spinner"></span></div>
			{:else if stravaActivities.length === 0}
				<p class="text-sm text-base-content/60">{$t('adventures.no_strava_activities')}</p>
			{:else}
				<div class="space-y-2">
					{#each stravaActivities as activity (activity.id)}
						<StravaActivityCard {activity} {measurementSystem} on:import={importStrava} />
					{/each}
				</div>
			{/if}
		</div>
	{:else if panel === 'endurain'}
		<div class="rounded-lg border border-base-300 bg-base-200/40 p-4">
			<h4 class="mb-3 font-medium">{$t('adventures.endurain_activities_during_visit')}</h4>
			{#if loadingEndurain}
				<div class="flex justify-center py-6"><span class="loading loading-spinner"></span></div>
			{:else if endurainActivities.length === 0}
				<p class="text-sm text-base-content/60">{$t('adventures.no_endurain_activities')}</p>
			{:else}
				<div class="space-y-2">
					{#each endurainActivities as activity (activity.id)}
						<StravaActivityCard
							{activity}
							provider="endurain"
							importing={importingEndurain}
							{measurementSystem}
							on:import={importEndurain}
						/>
					{/each}
				</div>
			{/if}
		</div>
	{:else}
		<div class="rounded-lg border border-base-300 bg-base-100 p-4">
			<h4 class="mb-3 font-medium">
				{pendingProvider === 'strava'
					? $t('adventures.complete_strava_import')
					: $t('adventures.add_new_activity')}
			</h4>
			{#if pendingProvider === 'strava'}
				<div class="alert alert-info mb-4">
					<div>
						<div class="font-medium">{$t('adventures.strava_activity_ready')}</div>
						<div class="text-xs">{$t('adventures.upload_gpx_file')}</div>
					</div>
					{#if externalId}
						<button
							type="button"
							class="btn btn-xs btn-outline"
							onclick={() => {
								const match = stravaActivities.find((item) => String(item.id) === externalId);
								if (match?.export_gpx) window.open(match.export_gpx, '_blank');
							}}
						>
							{$t('adventures.download_gpx')}
						</button>
					{/if}
				</div>
			{/if}
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
				<div class="md:col-span-2">
					<label class="field-label" for="activity-name">{$t('adventures.activity_name')}</label>
					<input id="activity-name" class="input mt-1 w-full" bind:value={name} required />
				</div>
				<div>
					<label class="field-label" for="sport-type">{$t('adventures.sport_type')}</label>
					<select
						id="sport-type"
						class="select mt-1 w-full"
						bind:value={sportType}
						disabled={locked}
					>
						{#each SPORT_TYPE_CHOICES as sportTypeChoice (sportTypeChoice.key)}
							<option value={sportTypeChoice.key}
								>{sportTypeChoice.icon} {sportTypeChoice.label}</option
							>
						{/each}
					</select>
				</div>
				<div>
					<label class="field-label" for="activity-start">{$t('adventures.start_date')}</label>
					<DateInput
						id="activity-start"
						bind:value={startDate}
						showTime
						size="sm"
						readonly={locked}
					/>
				</div>
				<div class="md:col-span-2">
					<TimezoneSelector bind:selectedTimezone={zone} size="sm" />
				</div>
				<div>
					<label class="field-label" for="distance"
						>{$t('adventures.distance')} ({distanceUnit})</label
					>
					<input
						id="distance"
						type="number"
						step="0.01"
						min="0"
						class="input mt-1 w-full"
						bind:value={distance}
						readonly={locked}
					/>
				</div>
				<div>
					<label class="field-label" for="moving-time"
						>{$t('adventures.moving_time')} (HH:MM:SS)</label
					>
					<input
						id="moving-time"
						class="input mt-1 w-full"
						placeholder="0:25:30"
						bind:value={movingTime}
						readonly={locked}
					/>
				</div>
				<div>
					<label class="field-label" for="elapsed-time"
						>{$t('adventures.elapsed_time')} (HH:MM:SS)</label
					>
					<input
						id="elapsed-time"
						class="input mt-1 w-full"
						placeholder="0:30:00"
						bind:value={elapsedTime}
						readonly={locked}
					/>
				</div>
				{#if !gpxFile}
					<div>
						<label class="field-label" for="elevation-gain"
							>{$t('adventures.elevation_gain')} ({elevationUnit})</label
						>
						<input
							id="elevation-gain"
							type="number"
							min="0"
							class="input mt-1 w-full"
							bind:value={elevationGain}
							readonly={locked}
						/>
					</div>
					<div>
						<label class="field-label" for="elevation-loss"
							>{$t('adventures.elevation_loss')} ({elevationUnit})</label
						>
						<input
							id="elevation-loss"
							type="number"
							min="0"
							class="input mt-1 w-full"
							bind:value={elevationLoss}
							readonly={locked}
						/>
					</div>
				{/if}
				{#if trails.length > 0}
					<div class="md:col-span-2">
						<label class="field-label" for="activity-trail">{$t('adventures.trail')}</label>
						<select id="activity-trail" class="select mt-1 w-full" bind:value={trailId}>
							<option value="">—</option>
							{#each trails as trail (trail.id)}
								<option value={trail.id}>{trail.name}</option>
							{/each}
						</select>
					</div>
				{/if}
				<div class="md:col-span-2">
					<label class="field-label" for="activity-gpx">
						{$t('adventures.gpx_file')}
						{#if pendingProvider === 'strava'}<span class="text-error">*</span>{/if}
					</label>
					<input
						id="activity-gpx"
						type="file"
						accept=".gpx"
						class="file-input mt-1 w-full"
						onchange={(event) => {
							gpxFile = event.currentTarget.files?.[0] ?? null;
						}}
					/>
					<p class="field-hint">{$t('adventures.activity_gpx_optional_hint')}</p>
				</div>
				<div class="md:col-span-2">
					<button
						type="button"
						class="btn btn-ghost btn-sm px-0"
						onclick={() => (showExtras = !showExtras)}
					>
						{showExtras ? $t('adventures.hide_details') : $t('adventures.more_details')}
					</button>
				</div>
				{#if showExtras}
					<div>
						<label class="field-label" for="calories">{$t('adventures.calories')}</label>
						<input
							id="calories"
							type="number"
							min="0"
							class="input mt-1 w-full"
							bind:value={calories}
							readonly={locked}
						/>
					</div>
					<div>
						<label class="field-label" for="average-speed"
							>{$t('adventures.average_speed')} ({speedUnit})</label
						>
						<input
							id="average-speed"
							type="number"
							step="0.1"
							class="input mt-1 w-full"
							bind:value={averageSpeed}
							readonly={locked}
						/>
					</div>
					<div>
						<label class="field-label" for="max-speed"
							>{$t('adventures.max_speed')} ({speedUnit})</label
						>
						<input
							id="max-speed"
							type="number"
							step="0.1"
							class="input mt-1 w-full"
							bind:value={maxSpeed}
							readonly={locked}
						/>
					</div>
					<div>
						<label class="field-label" for="cadence">{$t('adventures.average_cadence')}</label>
						<input
							id="cadence"
							type="number"
							min="0"
							class="input mt-1 w-full"
							bind:value={averageCadence}
							readonly={locked}
						/>
					</div>
				{/if}
			</div>
			<div class="mt-4 flex justify-end gap-2">
				{#if onCancel}
					<button type="button" class="btn btn-ghost btn-sm" disabled={saving} onclick={onCancel}>
						{$t('adventures.cancel')}
					</button>
				{/if}
				<button
					type="button"
					class="btn btn-success btn-sm gap-2"
					disabled={saving || !name.trim() || (pendingProvider === 'strava' && !gpxFile)}
					onclick={save}
				>
					{#if saving}
						<LoadingIcon class="h-4 w-4 animate-spin" />
					{:else}
						<UploadIcon class="h-4 w-4" />
					{/if}
					{pendingProvider ? $t('adventures.complete_import') : $t('adventures.upload_activity')}
				</button>
			</div>
		</div>
	{/if}
</div>
