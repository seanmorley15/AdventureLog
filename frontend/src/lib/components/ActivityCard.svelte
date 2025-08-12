<script lang="ts">
	import type { Activity, Trail, TransportationVisit, Visit } from '$lib/types';
	import { t } from 'svelte-i18n';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import RunFastIcon from '~icons/mdi/run-fast';
	import FileIcon from '~icons/mdi/file';
	import TrashIcon from '~icons/mdi/trash-can';
	import SpeedometerIcon from '~icons/mdi/speedometer';
	import TrendingUpIcon from '~icons/mdi/trending-up';
	import ClockIcon from '~icons/mdi/clock';
	import CaloriesIcon from '~icons/mdi/fire';
	import LocationIcon from '~icons/mdi/map-marker';
	import { formatDateInTimezone } from '$lib/dateUtils';
	import { getDistance, getElevation } from '$lib';

	export let activity: Activity;
	export let trails: Trail[];
	export let visit: Visit | TransportationVisit;
	export let measurementSystem: 'metric' | 'imperial' = 'metric';
	export let readOnly: boolean = false;

	$: trail = activity.trail ? trails.find((t) => t.id === activity.trail) : null;

	function deleteActivity(visitId: string, activityId: string) {
		dispatch('delete', { visitId, activityId });
	}

	function formatDuration(isoString: string | null): string {
		if (!isoString) return '';
		// Simple ISO 8601 duration parsing for display
		const match = isoString.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
		if (!match) return isoString;

		const hours = parseInt(match[1] || '0');
		const minutes = parseInt(match[2] || '0');
		const seconds = parseInt(match[3] || '0');

		if (hours > 0) {
			return `${hours}h ${minutes}m`;
		} else if (minutes > 0) {
			return `${minutes}m ${seconds}s`;
		} else {
			return `${seconds}s`;
		}
	}

	function formatSpeed(speed: number | null): string {
		if (!speed) return '';
		const convertedSpeed = measurementSystem === 'imperial' ? speed * 2.237 : speed * 3.6;
		return `${convertedSpeed.toFixed(1)} ${measurementSystem === 'imperial' ? 'mph' : 'km/h'}`;
	}
</script>

<div class="bg-base-200/50 p-4 rounded-lg border border-base-300/50">
	<div class="flex items-start justify-between mb-3">
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 mb-2">
				<RunFastIcon class="w-4 h-4 text-success flex-shrink-0" />
				<h5 class="font-semibold text-base truncate">{activity.name}</h5>
				<div class="flex gap-1">
					{#if activity.sport_type}
						<span class="badge badge-outline badge-sm">{activity.sport_type}</span>
					{/if}
				</div>
			</div>
		</div>

		{#if !readOnly}
			<button
				class="btn btn-error btn-xs tooltip tooltip-top ml-2"
				data-tip="Delete Activity"
				on:click={() => deleteActivity(visit.id, activity.id)}
			>
				<TrashIcon class="w-3 h-3" />
			</button>
		{/if}
	</div>

	<!-- Main Stats Grid -->
	<div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
		{#if activity.distance}
			<div class="bg-base-100/50 p-2 rounded text-center">
				<div class="text-lg font-bold text-primary">
					{getDistance(measurementSystem, activity.distance)}
				</div>
				<div class="text-xs text-base-content/70">
					{measurementSystem === 'imperial' ? 'miles' : 'km'}
				</div>
			</div>
		{/if}

		{#if activity.moving_time}
			<div class="bg-base-100/50 p-2 rounded text-center">
				<div class="text-lg font-bold text-secondary">
					{formatDuration(activity.moving_time)}
				</div>
				<div class="text-xs text-base-content/70">{$t('adventures.moving_time')}</div>
			</div>
		{/if}

		{#if activity.elevation_gain}
			<div class="bg-base-100/50 p-2 rounded text-center">
				<div class="text-lg font-bold text-success">
					{getElevation(measurementSystem, activity.elevation_gain)}
				</div>
				<div class="text-xs text-base-content/70">
					{measurementSystem === 'imperial' ? 'ft' : 'm'} ↗
				</div>
			</div>
		{/if}

		{#if activity.average_speed}
			<div class="bg-base-100/50 p-2 rounded text-center">
				<div class="text-lg font-bold text-accent">
					{formatSpeed(activity.average_speed)}
				</div>
				<div class="text-xs text-base-content/70">{$t('adventures.average_speed')}</div>
			</div>
		{/if}
	</div>

	<!-- Additional Details -->
	<div class="space-y-2 text-xs text-base-content/80">
		<!-- Time Details -->
		{#if activity.elapsed_time || activity.rest_time}
			<div class="flex items-center gap-1">
				<ClockIcon class="w-3 h-3" />
				<span class="flex gap-4">
					{#if activity.elapsed_time}
						<span>{$t('adventures.total')}: {formatDuration(activity.elapsed_time)}</span>
					{/if}
					{#if activity.rest_time}
						<span>{$t('adventures.rest')}: {formatDuration(activity.rest_time)}</span>
					{/if}
				</span>
			</div>
		{/if}

		<!-- Elevation Details -->
		{#if activity.elev_high || activity.elev_low || activity.elevation_loss}
			<div class="flex items-center gap-1">
				<TrendingUpIcon class="w-3 h-3" />
				<span class="flex gap-4">
					{#if activity.elev_high}
						<span
							>{$t('adventures.high')}: {getElevation(
								measurementSystem,
								activity.elev_high
							)}{measurementSystem === 'imperial' ? 'ft' : 'm'}</span
						>
					{/if}
					{#if activity.elev_low}
						<span
							>{$t('adventures.low')}: {getElevation(
								measurementSystem,
								activity.elev_low
							)}{measurementSystem === 'imperial' ? 'ft' : 'm'}</span
						>
					{/if}
					{#if activity.elevation_loss}
						<span
							>↘ {getElevation(measurementSystem, activity.elevation_loss)}{measurementSystem ===
							'imperial'
								? 'ft'
								: 'm'}</span
						>
					{/if}
				</span>
			</div>
		{/if}

		<!-- Speed Details -->
		{#if activity.max_speed}
			<div class="flex items-center gap-1">
				<SpeedometerIcon class="w-3 h-3" />
				<span>{$t('adventures.max_speed')}: {formatSpeed(activity.max_speed)}</span>
			</div>
		{/if}

		<!-- Performance Metrics -->
		{#if activity.average_cadence || activity.calories}
			<div class="flex items-center gap-4">
				{#if activity.average_cadence}
					<span>{$t('adventures.cadence')}: {activity.average_cadence} rpm</span>
				{/if}
				{#if activity.calories}
					<span class="flex items-center gap-1">
						<CaloriesIcon class="w-3 h-3" />
						{activity.calories}
						{$t('adventures.calories')}
					</span>
				{/if}
			</div>
		{/if}

		<!-- Trail Information -->
		{#if trail}
			<div class="flex items-center gap-1">
				<LocationIcon class="w-3 h-3" />
				<span>{$t('adventures.trail')}: <span class="font-medium">{trail.name}</span></span>
			</div>
		{/if}

		<!-- Date Information -->
		{#if activity.start_date}
			<div class="border-t border-base-300/50 pt-2">
				<div>
					Started: {formatDateInTimezone(
						activity.start_date,
						activity.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
					)}
				</div>
				{#if activity.timezone}
					<div class="text-xs text-base-content/60">
						{$t('adventures.timezone')}: {activity.timezone}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Location Information -->
		{#if activity.start_lat && activity.start_lng}
			<div class="flex items-center gap-1">
				<LocationIcon class="w-3 h-3" />
				<span
					>{$t('adventures.start')}: {activity.start_lat.toFixed(4)}, {activity.start_lng.toFixed(
						4
					)}</span
				>
				{#if activity.end_lat && activity.end_lng && (activity.end_lat !== activity.start_lat || activity.end_lng !== activity.start_lng)}
					<span class="ml-2"
						>{$t('adventures.end')}: {activity.end_lat.toFixed(4)}, {activity.end_lng.toFixed(
							4
						)}</span
					>
				{/if}
			</div>
		{/if}

		<!-- GPX File -->
		{#if activity.gpx_file}
			<div class="flex items-center gap-1 pt-2 border-t border-base-300/50">
				<FileIcon class="w-3 h-3" />
				<a href={activity.gpx_file} target="_blank" class="link link-primary text-xs">
					{$t('adventures.view_gpx')}
				</a>
			</div>
		{/if}
	</div>
</div>
