<script lang="ts">
	import { formatDateInTimezone } from '$lib/dateUtils';
	import type { StravaActivity } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';

	const dispatch = createEventDispatcher();

	export let activity: StravaActivity;
	export let measurementSystem: 'metric' | 'imperial' = 'metric';

	interface SportConfig {
		color: string;
		icon: string;
		name: string;
	}

	const sportTypeConfig: Record<string, SportConfig> = {
		StandUpPaddling: { color: 'info', icon: '🏄', name: 'Stand Up Paddling' },
		Run: { color: 'success', icon: '🏃', name: 'Running' },
		Ride: { color: 'warning', icon: '🚴', name: 'Cycling' },
		Swim: { color: 'primary', icon: '🏊', name: 'Swimming' },
		Hike: { color: 'accent', icon: '🥾', name: 'Hiking' },
		Walk: { color: 'neutral', icon: '🚶', name: 'Walking' },
		default: { color: 'secondary', icon: '⚡', name: 'Activity' }
	};

	function getTypeConfig(type: string): SportConfig {
		return sportTypeConfig[type] || sportTypeConfig.default;
	}

	function formatTime(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		const secs = Math.floor(seconds % 60);

		if (hours > 0) {
			return `${hours}h ${minutes}m ${secs}s`;
		}
		return `${minutes}m ${secs}s`;
	}

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatPace(seconds: number, system: 'metric' | 'imperial'): string {
		const minutes = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		const unit = system === 'metric' ? 'km' : 'mi';
		return `${minutes}:${secs.toString().padStart(2, '0')}/${unit}`;
	}

	function convertElevation(
		meters: number,
		system: 'metric' | 'imperial'
	): { value: number; unit: string } {
		if (system === 'imperial') {
			return { value: meters * 3.28084, unit: 'ft' };
		}
		return { value: meters, unit: 'm' };
	}

	function handleImportActivity() {
		dispatch('import', activity);
	}

	$: typeConfig = getTypeConfig(activity.sport_type);
	$: distance =
		measurementSystem === 'metric'
			? { value: activity.distance_km, unit: 'km' }
			: { value: activity.distance_miles, unit: 'mi' };
	$: speed =
		measurementSystem === 'metric'
			? { value: activity.average_speed_kmh, unit: 'km/h' }
			: { value: activity.average_speed_mph, unit: 'mph' };
	$: maxSpeed =
		measurementSystem === 'metric'
			? { value: activity.max_speed_kmh, unit: 'km/h' }
			: { value: activity.max_speed_mph, unit: 'mph' };
	$: elevation = convertElevation(activity.total_elevation_gain, measurementSystem);
	$: paceSeconds =
		measurementSystem === 'metric' ? activity.pace_per_km_seconds : activity.pace_per_mile_seconds;
</script>

<div class="card bg-base-50 border border-base-200 hover:shadow-md transition-shadow">
	<div class="card-body p-4">
		<!-- Activity Header -->
		<div class="flex items-start justify-between mb-3">
			<div class="flex items-center gap-3">
				<div class="text-2xl" aria-label="Sport icon">{typeConfig.icon}</div>
				<div>
					<h3 class="font-semibold text-lg">{activity.name}</h3>
					<div class="flex items-center gap-2 text-sm text-base-content/70">
						<span class="badge badge-{typeConfig.color} badge-sm">{typeConfig.name}</span>
						<span>•</span>
						<span
							>{formatDateInTimezone(
								activity.start_date,
								activity.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
							)} ({activity.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone})</span
						>
					</div>
				</div>
			</div>

			<div class="flex items-center gap-2">
				<button
					type="button"
					on:click={handleImportActivity}
					class="btn btn-success btn-sm btn-circle"
					aria-label={$t('adventures.import_activity')}
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
						/>
					</svg>
				</button>
				<div class="dropdown dropdown-end">
					<div
						tabindex="0"
						role="button"
						class="btn btn-ghost btn-sm btn-circle"
						aria-label={$t('adventures.activity_options')}
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zM12 13a1 1 0 110-2 1 1 0 010 2zM12 20a1 1 0 110-2 1 1 0 010 2z"
							/>
						</svg>
					</div>
					<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
					<ul
						tabindex="0"
						class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow"
					>
						<li>
							<a href={activity.export_gpx} target="_blank" rel="noopener noreferrer">
								{$t('adventures.export_gpx')}
							</a>
						</li>
						<li>
							<a href={activity.export_original} target="_blank" rel="noopener noreferrer">
								{$t('adventures.export_original')}
							</a>
						</li>
						<li>
							<a
								href="https://www.strava.com/activities/{activity.id}"
								target="_blank"
								rel="noopener noreferrer"
							>
								{$t('adventures.view_on') + ' Strava'}
							</a>
						</li>
					</ul>
				</div>
			</div>
		</div>

		<!-- Main Stats -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
			<div class="stat bg-base-100 rounded-lg p-3">
				<div class="stat-title text-xs">{$t('adventures.distance')}</div>
				<div class="stat-value text-lg">{distance.value.toFixed(2)}</div>
				<div class="stat-desc">{distance.unit}</div>
			</div>
			<div class="stat bg-base-100 rounded-lg p-3">
				<div class="stat-title text-xs">{$t('adventures.time')}</div>
				<div class="stat-value text-lg">{formatTime(activity.moving_time)}</div>
				<div class="stat-desc">{$t('adventures.moving_time')}</div>
			</div>
			<div class="stat bg-base-100 rounded-lg p-3">
				<div class="stat-title text-xs">{$t('adventures.avg_speed')}</div>
				<div class="stat-value text-lg">{speed.value.toFixed(1)}</div>
				<div class="stat-desc">{speed.unit}</div>
			</div>
			<div class="stat bg-base-100 rounded-lg p-3">
				<div class="stat-title text-xs">{$t('adventures.elevation')}</div>
				<div class="stat-value text-lg">{elevation.value.toFixed(0)}</div>
				<div class="stat-desc">{elevation.unit} {$t('adventures.gain')}</div>
			</div>
		</div>

		<!-- Additional Stats -->
		<div class="flex flex-wrap gap-2 text-sm">
			{#if activity.average_cadence}
				<div class="badge badge-ghost">
					<span class="font-medium">{$t('adventures.cadence')}:</span
					>&nbsp;{activity.average_cadence.toFixed(1)}
				</div>
			{/if}
			{#if activity.calories}
				<div class="badge badge-ghost">
					<span class="font-medium">{$t('adventures.calories')}:</span>&nbsp;{activity.calories}
				</div>
			{/if}
			{#if activity.kudos_count > 0}
				<div class="badge badge-ghost">
					<span class="font-medium">Kudos:</span>&nbsp;{activity.kudos_count}
				</div>
			{/if}
			{#if activity.achievement_count > 0}
				<div class="badge badge-success badge-outline">
					<span class="font-medium">{$t('adventures.achievements')}:</span
					>&nbsp;{activity.achievement_count}
				</div>
			{/if}
			{#if activity.pr_count > 0}
				<div class="badge badge-warning badge-outline">
					<span class="font-medium">PRs:</span>&nbsp;{activity.pr_count}
				</div>
			{/if}
		</div>

		<!-- Footer with pace and max speed -->
		{#if paceSeconds}
			<div class="flex justify-between items-center mt-3 pt-3 border-t border-base-300">
				<div class="text-sm">
					<span class="font-medium">{$t('adventures.pace')}:</span>
					{formatPace(paceSeconds, measurementSystem)}
				</div>
				<div class="text-sm">
					<span class="font-medium">{$t('adventures.max_speed')}:</span>
					{maxSpeed.value.toFixed(1)}
					{maxSpeed.unit}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.stat {
		min-height: auto;
	}

	.stat-value {
		font-size: 1.25rem;
		line-height: 1.75rem;
	}
</style>
