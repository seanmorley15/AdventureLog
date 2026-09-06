<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { CalendarEventType, CalendarStats } from '$lib/calendar/types';
	import { CALENDAR_EVENT_COLORS, CALENDAR_EVENT_TYPES } from '$lib/calendar/events';
	import FilterIcon from '~icons/mdi/filter-variant';
	import DownloadIcon from '~icons/mdi/download';
	import ClearIcon from '~icons/mdi/close';
	import CalendarIcon from '~icons/mdi/calendar';
	import ClockOutline from '~icons/mdi/clock-outline';
	import Tag from '~icons/mdi/tag';

	interface Props {
		stats: CalendarStats;
		activeTypes: Set<CalendarEventType>;
		filteredCount: number;
		totalCount: number;
		isDownloadingIcs?: boolean;
		timezoneMode?: 'event' | 'local';
	}

	let {
		stats,
		activeTypes,
		filteredCount,
		totalCount,
		isDownloadingIcs = false,
		timezoneMode = 'event'
	}: Props = $props();

	const dispatch = createEventDispatcher<{
		toggleType: CalendarEventType;
		clearFilters: void;
		downloadIcs: void;
		timezoneChange: 'event' | 'local';
	}>();

	const typeLabels: Record<CalendarEventType, string> = {
		visit: 'calendar.type_visit',
		location: 'calendar.type_visit',
		transportation: 'calendar.type_transportation',
		lodging: 'calendar.type_lodging',
		collection: 'calendar.type_collection',
		note: 'calendar.type_note',
		checklist: 'calendar.type_checklist'
	};

	function toggleType(type: CalendarEventType) {
		dispatch('toggleType', type);
	}
</script>

<div class="flex h-full flex-col">
	<div class="flex items-center gap-3 mb-8">
		<div class="p-2 bg-primary/10 rounded-lg">
			<FilterIcon class="w-6 h-6 text-primary" />
		</div>
		<h2 class="text-xl font-bold">{$t('adventures.filters_and_stats')}</h2>
	</div>

	<div class="card bg-base-200/50 p-4 mb-4">
		<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
			<CalendarIcon class="w-5 h-5" />
			{$t('calendar.calendar_overview')}
		</h3>

		<div class="space-y-4">
			<div class="stat p-0">
				<div class="stat-title text-sm">{$t('calendar.total_events')}</div>
				<div class="stat-value text-2xl text-primary">{stats.total}</div>
			</div>

			<div class="grid grid-cols-2 gap-4">
				<div class="stat p-0">
					<div class="stat-title text-xs">{$t('calendar.upcoming')}</div>
					<div class="stat-value text-lg text-secondary">{stats.upcoming}</div>
				</div>
				<div class="stat p-0">
					<div class="stat-title text-xs">{$t('calendar.this_month')}</div>
					<div class="stat-value text-lg">{stats.thisMonth}</div>
				</div>
			</div>

			{#if filteredCount !== totalCount}
				<div class="space-y-2">
					<div class="flex justify-between text-sm">
						<span>{$t('calendar.filtered_results')}</span>
						<span>{filteredCount} {$t('worldtravel.of')} {totalCount}</span>
					</div>
					<progress
						class="progress progress-primary w-full"
						value={filteredCount}
						max={totalCount || 1}
					></progress>
				</div>
			{/if}
		</div>
	</div>

	<div class="card bg-base-200/50 p-4 mb-4">
		<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
			<ClockOutline class="w-5 h-5" />
			{$t('calendar.timezone_display')}
		</h3>
		<div class="join w-full">
			<button
				type="button"
				class="btn btn-sm join-item flex-1 {timezoneMode === 'event' ? 'btn-active' : ''}"
				onclick={() => dispatch('timezoneChange', 'event')}
			>
				{$t('calendar.event timezone')}
			</button>
			<button
				type="button"
				class="btn btn-sm join-item flex-1 {timezoneMode === 'local' ? 'btn-active' : ''}"
				onclick={() => dispatch('timezoneChange', 'local')}
			>
				{$t('calendar.your timezone')}
			</button>
		</div>
	</div>

	<div class="card bg-base-200/50 p-4 mb-6">
		<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
			<Tag class="w-5 h-5" />
			{$t('calendar.event_types')}
		</h3>
		<div class="flex flex-wrap gap-2">
			{#each CALENDAR_EVENT_TYPES as type}
				<button
					type="button"
					class="badge badge-lg gap-2 cursor-pointer border transition-opacity"
					class:badge-outline={!activeTypes.has(type)}
					class:opacity-50={!activeTypes.has(type)}
					style={activeTypes.has(type)
						? `background-color: ${CALENDAR_EVENT_COLORS[type]}20; border-color: ${CALENDAR_EVENT_COLORS[type]}; color: inherit;`
						: ''}
					onclick={() => toggleType(type)}
				>
					<span
						class="h-2 w-2 rounded-full"
						style={`background-color: ${CALENDAR_EVENT_COLORS[type]}`}
					></span>
					{$t(typeLabels[type])}
					<span class="opacity-70">({stats.byType[type] || 0})</span>
				</button>
			{/each}
		</div>
	</div>

	<div class="mt-auto space-y-3">
		<button
			type="button"
			class="btn btn-primary w-full gap-2"
			onclick={() => dispatch('downloadIcs')}
			disabled={isDownloadingIcs}
		>
			{#if isDownloadingIcs}
				<span class="loading loading-spinner loading-sm"></span>
			{:else}
				<DownloadIcon class="w-4 h-4" />
			{/if}
			{$t('adventures.download_calendar')}
		</button>

		{#if filteredCount !== totalCount}
			<button
				type="button"
				class="btn btn-ghost w-full gap-2"
				onclick={() => dispatch('clearFilters')}
			>
				<ClearIcon class="w-4 h-4" />
				{$t('worldtravel.clear_filters')}
			</button>
		{/if}
	</div>
</div>
