<script lang="ts">
	import { page } from '$app/state';
	import { t } from 'svelte-i18n';
	import {
		getActivityColor,
		getActivityIcon,
		getDistance,
		getElevation,
		SPORT_TYPE_CHOICES
	} from '#lib';
	import { dateFormatFromUser } from '#lib/dateFormat.js';
	import { formatDateInTimezone } from '#lib/dateUtils.js';
	import type { Activity, Trail } from '#lib/types.js';
	import ElevationProfile from '#lib/components/activities/ElevationProfile.svelte';
	import {
		elevationProfile,
		formatDuration,
		parseDuration
	} from '#lib/components/activities/activityForm.js';
	import CaloriesIcon from '~icons/mdi/fire';
	import ClockIcon from '~icons/mdi/clock';
	import EditIcon from '~icons/mdi/pencil';
	import FileIcon from '~icons/mdi/file';
	import HeartIcon from '~icons/mdi/heart-pulse';
	import LocationIcon from '~icons/mdi/map-marker';
	import SpeedometerIcon from '~icons/mdi/speedometer';
	import TrashIcon from '~icons/mdi/trash-can';
	import TrendingUpIcon from '~icons/mdi/trending-up';

	interface Props {
		activity: Activity;
		trails: Trail[];
		measurementSystem?: 'metric' | 'imperial';
		readOnly?: boolean;
		onEdit?: () => void;
		onDelete?: () => void;
	}

	let {
		activity,
		trails,
		measurementSystem = 'metric',
		readOnly = false,
		onEdit,
		onDelete
	}: Props = $props();

	const dateFormat = $derived(dateFormatFromUser(page.data?.user));
	const imperial = $derived(measurementSystem === 'imperial');
	const elevationUnit = $derived(imperial ? 'ft' : 'm');
	const trail = $derived(activity.trail ? trails.find((item) => item.id === activity.trail) : null);
	const sportLabel = $derived(
		SPORT_TYPE_CHOICES.find((choice) => choice.key === activity.sport_type)?.label ??
			activity.sport_type
	);
	const profile = $derived(elevationProfile(activity.geojson));

	const duration = (value: string | null) => formatDuration(parseDuration(value));
	const speed = (value: number) =>
		`${(value * (imperial ? 2.237 : 3.6)).toFixed(1)} ${imperial ? 'mph' : 'km/h'}`;
	const elevation = (meters: number) =>
		`${getElevation(measurementSystem, meters)}${elevationUnit}`;
</script>

<div class="rounded-lg border border-base-300/50 bg-base-200/50 p-4">
	<div class="mb-3 flex items-start justify-between">
		<div class="min-w-0 flex-1">
			<div class="mb-2 flex items-center gap-2">
				<span class="shrink-0 text-lg" aria-hidden="true"
					>{getActivityIcon(activity.sport_type)}</span
				>
				<h5 class="truncate text-base font-semibold">{activity.name}</h5>
				<span
					class="badge badge-sm shrink-0 border-0 text-white"
					style="background-color: {getActivityColor(activity.sport_type)}">{sportLabel}</span
				>
			</div>
			{#if activity.source_attribution}
				<p class="-mt-1 mb-2 text-xs text-base-content/70">{activity.source_attribution}</p>
			{/if}
		</div>

		{#if !readOnly}
			<div class="ml-2 flex gap-1">
				{#if onEdit}
					<button
						type="button"
						class="btn btn-ghost btn-xs tooltip tooltip-top"
						data-tip={$t('activities.edit_activity')}
						aria-label={$t('activities.edit_activity')}
						onclick={onEdit}
					>
						<EditIcon class="h-3 w-3" />
					</button>
				{/if}
				{#if onDelete}
					<button
						type="button"
						class="btn btn-error btn-xs tooltip tooltip-top"
						data-tip={$t('activities.delete_activity')}
						aria-label={$t('activities.delete_activity')}
						onclick={onDelete}
					>
						<TrashIcon class="h-3 w-3" />
					</button>
				{/if}
			</div>
		{/if}
	</div>

	<div class="mb-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
		{#if activity.distance}
			<div class="rounded-sm bg-base-100/50 p-2 text-center">
				<div class="text-lg font-bold text-primary">
					{getDistance(measurementSystem, activity.distance)}
				</div>
				<div class="text-xs text-base-content/70">{imperial ? 'miles' : 'km'}</div>
			</div>
		{/if}
		{#if activity.moving_time}
			<div class="rounded-sm bg-base-100/50 p-2 text-center">
				<div class="text-lg font-bold text-secondary">{duration(activity.moving_time)}</div>
				<div class="text-xs text-base-content/70">{$t('adventures.moving_time')}</div>
			</div>
		{/if}
		{#if activity.elevation_gain}
			<div class="rounded-sm bg-base-100/50 p-2 text-center">
				<div class="text-lg font-bold text-success">
					{getElevation(measurementSystem, activity.elevation_gain)}
				</div>
				<div class="text-xs text-base-content/70">{elevationUnit} ↗</div>
			</div>
		{/if}
		{#if activity.average_speed}
			<div class="rounded-sm bg-base-100/50 p-2 text-center">
				<div class="text-lg font-bold text-accent">{speed(activity.average_speed)}</div>
				<div class="text-xs text-base-content/70">{$t('adventures.average_speed')}</div>
			</div>
		{/if}
	</div>

	<ElevationProfile {profile} {measurementSystem} class="mb-3" />

	<div class="space-y-2 text-xs text-base-content/80">
		{#if activity.elapsed_time || activity.rest_time}
			<div class="flex items-center gap-1">
				<ClockIcon class="h-3 w-3" />
				<span class="flex gap-4">
					{#if activity.elapsed_time}
						<span>{$t('adventures.total')}: {duration(activity.elapsed_time)}</span>
					{/if}
					{#if activity.rest_time}
						<span>{$t('adventures.rest')}: {duration(activity.rest_time)}</span>
					{/if}
				</span>
			</div>
		{/if}

		{#if activity.elev_high || activity.elev_low || activity.elevation_loss}
			<div class="flex items-center gap-1">
				<TrendingUpIcon class="h-3 w-3" />
				<span class="flex gap-4">
					{#if activity.elev_high}
						<span>{$t('adventures.high')}: {elevation(activity.elev_high)}</span>
					{/if}
					{#if activity.elev_low}
						<span>{$t('adventures.low')}: {elevation(activity.elev_low)}</span>
					{/if}
					{#if activity.elevation_loss}
						<span>↘ {elevation(activity.elevation_loss)}</span>
					{/if}
				</span>
			</div>
		{/if}

		{#if activity.max_speed}
			<div class="flex items-center gap-1">
				<SpeedometerIcon class="h-3 w-3" />
				<span>{$t('adventures.max_speed')}: {speed(activity.max_speed)}</span>
			</div>
		{/if}

		{#if activity.average_heart_rate || activity.max_heart_rate}
			<div class="flex items-center gap-1">
				<HeartIcon class="h-3 w-3" />
				<span class="flex gap-4">
					{#if activity.average_heart_rate}
						<span
							>{$t('activities.average_heart_rate')}: {Math.round(activity.average_heart_rate)} bpm</span
						>
					{/if}
					{#if activity.max_heart_rate}
						<span>{$t('activities.max_heart_rate')}: {Math.round(activity.max_heart_rate)} bpm</span
						>
					{/if}
				</span>
			</div>
		{/if}

		{#if activity.average_cadence || activity.calories}
			<div class="flex items-center gap-4">
				{#if activity.average_cadence}
					<span>{$t('adventures.cadence')}: {activity.average_cadence} rpm</span>
				{/if}
				{#if activity.calories}
					<span class="flex items-center gap-1">
						<CaloriesIcon class="h-3 w-3" />
						{activity.calories}
						{$t('adventures.calories')}
					</span>
				{/if}
			</div>
		{/if}

		{#if trail}
			<div class="flex items-center gap-1">
				<LocationIcon class="h-3 w-3" />
				<span>{$t('adventures.trail')}: <span class="font-medium">{trail.name}</span></span>
			</div>
		{/if}

		{#if activity.start_date}
			<div class="border-t border-base-300/50 pt-2">
				<div>
					{$t('activities.started')}: {formatDateInTimezone(
						activity.start_date,
						activity.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
						dateFormat
					)}
				</div>
				{#if activity.timezone}
					<div class="text-xs text-base-content/60">
						{$t('adventures.timezone')}: {activity.timezone}
					</div>
				{/if}
			</div>
		{/if}

		{#if activity.gpx_file}
			<div class="flex items-center gap-1 border-t border-base-300/50 pt-2">
				<FileIcon class="h-3 w-3" />
				<a href={activity.gpx_file} target="_blank" class="link link-primary text-xs">
					{$t('adventures.view_gpx')}
				</a>
			</div>
		{/if}
	</div>
</div>
