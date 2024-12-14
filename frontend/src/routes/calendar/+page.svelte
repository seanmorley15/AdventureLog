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

	let plugins = [TimeGrid, DayGrid];
	let options = {
		view: 'dayGridMonth',
		events: [...dates]
	};
</script>

<h1 class="text-center text-2xl font-bold">{$t('adventures.adventure_calendar')}</h1>

<Calendar {plugins} {options} />
