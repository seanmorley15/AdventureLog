<script lang="ts">
	import type { Activity, Trail, TransportationVisit, Visit } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import RunFastIcon from '~icons/mdi/run-fast';
	import FileIcon from '~icons/mdi/file';
	import TrashIcon from '~icons/mdi/trash-can';
	import { formatDateInTimezone } from '$lib/dateUtils';

	export let activity: Activity;
	export let trails: Trail[];
	export let visit: Visit | TransportationVisit;

	export let readOnly: boolean = false;

	$: trail = activity.trail ? trails.find((t) => t.id === activity.trail) : null;

	console.log(activity.trail, trails, trail);

	function deleteActivity(visitId: string, activityId: string) {
		// Dispatch an event to the parent component to handle deletion
		dispatch('delete', { visitId, activityId });
	}
</script>

<div class="bg-base-200/50 p-3 rounded-lg">
	<div class="flex items-start justify-between">
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 mb-1">
				<RunFastIcon class="w-3 h-3 text-success flex-shrink-0" />
				<h5 class="font-medium text-sm truncate">{activity.name}</h5>
				<span class="badge badge-outline badge-xs">{activity.type}</span>
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

				{#if trail}
					<div>
						Trail: {trail.name}
					</div>
				{/if}

				{#if activity.start_date}
					<div>
						Started: {formatDateInTimezone(
							activity.start_date,
							activity.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
						)} ({activity.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone})
					</div>
				{/if}

				{#if activity.gpx_file}
					<div class="flex items-center gap-1">
						<FileIcon class="w-3 h-3" />
						<a href={activity.gpx_file} target="_blank" class="link link-primary"> View GPX </a>
					</div>
				{/if}
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
</div>
