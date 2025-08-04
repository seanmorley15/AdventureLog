<script lang="ts">
	import { formatDateInTimezone } from '$lib/dateUtils';
	import type { StravaActivity } from '$lib/types';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let activity: StravaActivity;

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

	function formatPace(seconds: number): string {
		const minutes = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${minutes}:${secs.toString().padStart(2, '0')}`;
	}

	function handleImportActivity() {
		dispatch('import', activity);
	}

	$: typeConfig = getTypeConfig(activity.sport_type);
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
					aria-label="Import activity"
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
						aria-label="Activity options"
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
								Export GPX
							</a>
						</li>
						<li>
							<a href={activity.export_original} target="_blank" rel="noopener noreferrer">
								Export Original
							</a>
						</li>
						<li>
							<a
								href="https://www.strava.com/activities/{activity.id}"
								target="_blank"
								rel="noopener noreferrer"
							>
								View on Strava
							</a>
						</li>
					</ul>
				</div>
			</div>
		</div>

		<!-- Main Stats -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
			<div class="stat bg-base-100 rounded-lg p-3">
				<div class="stat-title text-xs">Distance</div>
				<div class="stat-value text-lg">{activity.distance_km.toFixed(2)}</div>
				<div class="stat-desc">km ({activity.distance_miles.toFixed(2)} mi)</div>
			</div>
			<div class="stat bg-base-100 rounded-lg p-3">
				<div class="stat-title text-xs">Time</div>
				<div class="stat-value text-lg">{formatTime(activity.moving_time)}</div>
				<div class="stat-desc">Moving time</div>
			</div>
			<div class="stat bg-base-100 rounded-lg p-3">
				<div class="stat-title text-xs">Avg Speed</div>
				<div class="stat-value text-lg">{activity.average_speed_kmh.toFixed(1)}</div>
				<div class="stat-desc">km/h ({activity.average_speed_mph.toFixed(1)} mph)</div>
			</div>
			<div class="stat bg-base-100 rounded-lg p-3">
				<div class="stat-title text-xs">Elevation</div>
				<div class="stat-value text-lg">{activity.total_elevation_gain.toFixed(0)}</div>
				<div class="stat-desc">m gain</div>
			</div>
		</div>

		<!-- Additional Stats -->
		<div class="flex flex-wrap gap-2 text-sm">
			{#if activity.average_cadence}
				<div class="badge badge-ghost">
					<span class="font-medium">Cadence:</span>&nbsp;{activity.average_cadence.toFixed(1)}
				</div>
			{/if}
			{#if activity.calories}
				<div class="badge badge-ghost">
					<span class="font-medium">Calories:</span>&nbsp;{activity.calories}
				</div>
			{/if}
			{#if activity.kudos_count > 0}
				<div class="badge badge-ghost">
					<span class="font-medium">Kudos:</span>&nbsp;{activity.kudos_count}
				</div>
			{/if}
			{#if activity.achievement_count > 0}
				<div class="badge badge-success badge-outline">
					<span class="font-medium">Achievements:</span>&nbsp;{activity.achievement_count}
				</div>
			{/if}
			{#if activity.pr_count > 0}
				<div class="badge badge-warning badge-outline">
					<span class="font-medium">PRs:</span>&nbsp;{activity.pr_count}
				</div>
			{/if}
		</div>

		<!-- Footer with pace and max speed -->
		{#if activity.pace_per_km_seconds}
			<div class="flex justify-between items-center mt-3 pt-3 border-t border-base-300">
				<div class="text-sm">
					<span class="font-medium">Pace:</span>
					{formatPace(activity.pace_per_km_seconds)}/km
				</div>
				<div class="text-sm">
					<span class="font-medium">Max Speed:</span>
					{activity.max_speed_kmh.toFixed(1)} km/h
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
