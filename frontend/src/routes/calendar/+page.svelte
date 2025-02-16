<script lang="ts">
	import type { PageData } from './$types';

	// @ts-ignore
	import Calendar from '@event-calendar/core';
	// @ts-ignore
	import TimeGrid from '@event-calendar/time-grid';
	// @ts-ignore
	import DayGrid from '@event-calendar/day-grid';
	import { t } from 'svelte-i18n';

	export let data: PageData;

	let adventures = data.props.adventures;
	let dates = data.props.dates;

	let icsCalendar = data.props.ics_calendar;
	// turn the ics calendar into a data URL
	let icsCalendarDataUrl = URL.createObjectURL(new Blob([icsCalendar], { type: 'text/calendar' }));

	let plugins = [TimeGrid, DayGrid];
	let options = {
		view: 'dayGridMonth',
		events: [...dates]
	};
	console.log(dates);
</script>

<h1 class="text-center text-2xl font-bold">{$t('adventures.adventure_calendar')}</h1>

<Calendar {plugins} {options} />

<!-- download calendar -->
<div class="flex items-center justify-center mt-4">
	<a href={icsCalendarDataUrl} download="adventures.ics" class="btn btn-primary"
		>{$t('adventures.download_calendar')}</a
	>
</div>
