<script lang="ts">
	import { page } from '$app/state';
	import { t } from 'svelte-i18n';
	import { getActivityColor, getActivityIcon, SPORT_TYPE_CHOICES } from '#lib';
	import { formatDateInTimezone } from '#lib/dateUtils.js';
	import { dateFormatFromUser } from '#lib/dateFormat.js';
	import type { StravaActivity } from '#lib/types.js';
	import { formatDuration } from '#lib/components/activities/activityForm.js';
	import DownloadIcon from '~icons/mdi/download';
	import CheckIcon from '~icons/mdi/check-bold';
	import OpenInNewIcon from '~icons/mdi/open-in-new';

	interface Props {
		activity: StravaActivity;
		measurementSystem?: 'metric' | 'imperial';
		/** Show a download link in place of the import button. */
		downloadOnly?: boolean;
		importing?: boolean;
		/** Already saved as an activity here. */
		imported?: boolean;
		provider?: 'strava' | 'endurain';
		onImport?: (activity: StravaActivity) => void;
	}

	let {
		activity,
		measurementSystem = 'metric',
		downloadOnly = false,
		importing = false,
		imported = false,
		provider = 'strava',
		onImport
	}: Props = $props();

	const dateFormat = $derived(dateFormatFromUser(page.data?.user));
	const imperial = $derived(measurementSystem === 'imperial');
	const zone = $derived(activity.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone);
	const sportLabel = $derived(
		SPORT_TYPE_CHOICES.find((choice) => choice.key === activity.sport_type)?.label ??
			activity.sport_type
	);
	const providerUrl = $derived(
		provider === 'endurain'
			? activity.export_original
			: `https://www.strava.com/activities/${activity.id}`
	);

	const stat = (value: number | null | undefined, digits: number) =>
		value == null || Number.isNaN(value) ? '—' : value.toFixed(digits);
</script>

<div
	class="card border border-base-200 bg-base-100 transition-shadow hover:shadow-md {imported
		? 'opacity-70'
		: ''}"
>
	<div class="card-body gap-3 p-4">
		<div class="flex items-start justify-between gap-3">
			<div class="flex min-w-0 items-center gap-3">
				<div class="text-2xl" aria-hidden="true">{getActivityIcon(activity.sport_type)}</div>
				<div class="min-w-0">
					<h3 class="truncate text-lg font-semibold">{activity.name}</h3>
					{#if activity.garmin_attribution}
						<p class="text-xs text-base-content/70">{activity.garmin_attribution}</p>
					{/if}
					<div class="flex flex-wrap items-center gap-2 text-sm text-base-content/70">
						<span
							class="badge badge-sm border-0 text-white"
							style="background-color: {getActivityColor(activity.sport_type)}">{sportLabel}</span
						>
						<span>
							{formatDateInTimezone(activity.start_date, zone, dateFormat)} ({zone})
						</span>
					</div>
				</div>
			</div>

			<div class="flex shrink-0 items-center gap-2">
				<a
					href={providerUrl}
					target="_blank"
					rel="noopener noreferrer"
					class="btn btn-ghost btn-sm btn-circle"
					aria-label={`${$t('adventures.view_on')} ${provider === 'endurain' ? 'Endurain' : 'Strava'}`}
				>
					<OpenInNewIcon class="h-4 w-4" />
				</a>
				{#if downloadOnly}
					<a
						href={activity.export_gpx}
						target="_blank"
						rel="noopener noreferrer"
						class="btn btn-success btn-sm gap-1"
					>
						<DownloadIcon class="h-4 w-4" />
						{$t('adventures.download_gpx')}
					</a>
				{:else if imported}
					<span class="badge badge-success badge-outline gap-1">
						<CheckIcon class="h-3 w-3" />
						{$t('activities.already_imported')}
					</span>
				{:else}
					<button
						type="button"
						class="btn btn-success btn-sm gap-1"
						disabled={importing}
						onclick={() => onImport?.(activity)}
					>
						{#if importing}
							<span class="loading loading-spinner loading-xs"></span>
						{:else}
							<DownloadIcon class="h-4 w-4" />
						{/if}
						{$t('adventures.import_activity')}
					</button>
				{/if}
			</div>
		</div>

		<div class="grid grid-cols-2 gap-2 md:grid-cols-4">
			<div class="rounded-lg bg-base-200/60 p-3 text-center">
				<div class="text-lg font-bold">
					{stat(imperial ? activity.distance_miles : activity.distance_km, 2)}
				</div>
				<div class="text-xs text-base-content/70">
					{$t('adventures.distance')} ({imperial ? 'mi' : 'km'})
				</div>
			</div>
			<div class="rounded-lg bg-base-200/60 p-3 text-center">
				<div class="text-lg font-bold">{formatDuration(activity.moving_time) || '—'}</div>
				<div class="text-xs text-base-content/70">{$t('adventures.moving_time')}</div>
			</div>
			<div class="rounded-lg bg-base-200/60 p-3 text-center">
				<div class="text-lg font-bold">
					{stat(imperial ? activity.average_speed_mph : activity.average_speed_kmh, 1)}
				</div>
				<div class="text-xs text-base-content/70">
					{$t('adventures.avg_speed')} ({imperial ? 'mph' : 'km/h'})
				</div>
			</div>
			<div class="rounded-lg bg-base-200/60 p-3 text-center">
				<div class="text-lg font-bold">
					{stat(
						imperial ? activity.total_elevation_gain * 3.28084 : activity.total_elevation_gain,
						0
					)}
				</div>
				<div class="text-xs text-base-content/70">
					{$t('adventures.gain')} ({imperial ? 'ft' : 'm'})
				</div>
			</div>
		</div>
	</div>
</div>
