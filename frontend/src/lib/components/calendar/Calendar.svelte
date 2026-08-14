<script lang="ts">
	// @ts-ignore
	import Calendar from '@event-calendar/core';
	// @ts-ignore
	import TimeGrid from '@event-calendar/time-grid';
	// @ts-ignore
	import DayGrid from '@event-calendar/day-grid';
	// @ts-ignore
	import Interaction from '@event-calendar/interaction';
	import { t } from 'svelte-i18n';
	import { createEventDispatcher, onMount } from 'svelte';
	import type { CalendarDisplayEvent } from '$lib/calendar/types';

	interface Props {
		events?: CalendarDisplayEvent[];
		height?: string;
		view?: string;
		dayMaxEvents?: number;
		initialDate?: string | Date | null;
		bare?: boolean;
	}

	let {
		events = [],
		height = 'auto',
		view = 'dayGridMonth',
		dayMaxEvents = 4,
		initialDate = null,
		bare = false
	}: Props = $props();

	const dispatch = createEventDispatcher<{
		eventClick: CalendarDisplayEvent;
		datesSet: { start: Date; end: Date; view: string };
	}>();

	let plugins = [TimeGrid, DayGrid, Interaction];
	let styleInjected = false;

	let options = $derived({
		view,
		events,
		date: initialDate || undefined,
		headerToolbar: {
			start: 'prev,next today',
			center: 'title',
			end: 'dayGridMonth,timeGridWeek,timeGridDay'
		},
		buttonText: {
			today: $t('calendar.today'),
			dayGridMonth: $t('calendar.month'),
			timeGridWeek: $t('calendar.week'),
			timeGridDay: $t('calendar.day')
		},
		height,
		eventDisplay: 'block',
		dayMaxEvents,
		moreLinkText: (num: number) => $t('calendar.more_events', { values: { count: num } }),
		eventClick: (info: { event: CalendarDisplayEvent }) => {
			dispatch('eventClick', info.event);
		},
		datesSet: (info: { start: Date; end: Date; view: { type: string } }) => {
			dispatch('datesSet', {
				start: info.start,
				end: info.end,
				view: info.view.type
			});
		},
		eventMouseEnter: (info: { el: HTMLElement }) => {
			info.el.style.cursor = 'pointer';
		},
		themeSystem: 'standard'
	});

	onMount(() => {
		if (styleInjected || document.getElementById('adventurelog-calendar-styles')) return;
		const style = document.createElement('style');
		style.id = 'adventurelog-calendar-styles';
		style.textContent = `
			.ec-toolbar {
				background: hsl(var(--b2)) !important;
				border-radius: 0.75rem !important;
				padding: 1rem !important;
				margin-bottom: 1rem !important;
				border: 1px solid hsl(var(--b3)) !important;
			}
			.ec-button {
				background: hsl(var(--b3)) !important;
				border: 1px solid hsl(var(--b3)) !important;
				color: hsl(var(--bc)) !important;
				border-radius: 0.5rem !important;
				padding: 0.45rem 0.85rem !important;
				font-weight: 500 !important;
			}
			.ec-button:hover {
				background: hsl(var(--b1)) !important;
			}
			.ec-button.ec-button-active {
				background: hsl(var(--p)) !important;
				color: hsl(var(--pc)) !important;
			}
			.ec-day {
				background: hsl(var(--b1)) !important;
				border: 1px solid hsl(var(--b3)) !important;
			}
			.ec-day-today {
				background: hsl(var(--b2)) !important;
			}
			.ec-event {
				border-radius: 0.375rem !important;
				padding: 0.2rem 0.45rem !important;
				font-size: 0.72rem !important;
				font-weight: 600 !important;
				border-width: 0 !important;
			}
			.ec-view {
				background: hsl(var(--b1)) !important;
				border-radius: 0.75rem !important;
				overflow: hidden !important;
			}
		`;
		document.head.appendChild(style);
		styleInjected = true;
	});
</script>

{#if bare}
	<Calendar {plugins} {options} />
{:else}
	<div class="rounded-2xl border border-base-300/60 bg-base-100 overflow-hidden">
		<Calendar {plugins} {options} />
	</div>
{/if}
