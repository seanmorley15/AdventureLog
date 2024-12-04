<script lang="ts">
	import type { PageData } from './$types';

	// @ts-ignore
	import Calendar from '@event-calendar/core';
	// @ts-ignore
	import TimeGrid from '@event-calendar/time-grid';
	// @ts-ignore
	import DayGrid from '@event-calendar/day-grid';

	export let data: PageData;

	let adventures = data.props.adventures;

	let dates: Array<{
		id: string;
		start: string;
		end: string;
		title: string;
		backgroundColor?: string;
	}> = [];
	adventures.forEach((adventure) => {
		adventure.visits.forEach((visit) => {
			dates.push({
				id: adventure.id,
				start: visit.start_date,
				end: visit.end_date,
				title: adventure.name + ' ' + adventure.category?.icon
			});
		});
	});

	let plugins = [TimeGrid, DayGrid];
	let options = {
		view: 'dayGridMonth',
		events: [...dates]
	};
</script>

<h1 class="text-center text-2xl font-bold">Adventure Calendar</h1>

<Calendar {plugins} {options} />
