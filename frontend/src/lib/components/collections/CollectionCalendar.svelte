<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import { DateTime } from 'luxon';
	import { t } from 'svelte-i18n';
	import type { Collection } from '$lib/types';
	import type { DateFormatPreference } from '$lib/dateFormat';
	import CalendarComponent from '$lib/components/calendar/Calendar.svelte';
	import EventDetailsModal from '$lib/components/calendar/EventDetailsModal.svelte';
	import { buildCollectionCalendarEvents } from '$lib/calendar/events';
	import type { CalendarDisplayEvent, CalendarTimezoneMode } from '$lib/calendar/types';
	import CalendarIcon from '~icons/mdi/calendar';

	interface Props {
		collection: Collection;
		dateFormat?: DateFormatPreference;
	}

	let { collection, dateFormat }: Props = $props();

	const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	let timezoneMode = $state<CalendarTimezoneMode>('event');
	let selectedEvent = $state<CalendarDisplayEvent | null>(null);
	let showEvent = $state(false);
	let frameHeight = $state(0);

	const measureFrame: Attachment = (node) => {
		const measure = () => {
			frameHeight = node.clientHeight;
		};
		measure();
		const observer = new ResizeObserver(measure);
		observer.observe(node);
		return () => observer.disconnect();
	};

	const labels = $derived({
		eventTimezone: $t('collections.event_timezone'),
		localTimezone: $t('collections.local_timezone')
	});
	const events = $derived(
		buildCollectionCalendarEvents(
			collection,
			timezoneMode,
			userTimezone,
			labels,
			(key) => $t(key),
			dateFormat
		)
	);
	const initialDate = $derived.by(() => {
		if (!events.length) return null;

		const rangeStart = collection.start_date ? DateTime.fromISO(collection.start_date) : null;
		const rangeEnd = collection.end_date ? DateTime.fromISO(collection.end_date) : null;
		const valid = events
			.map((event) => ({ date: DateTime.fromISO(event.start), event }))
			.filter(({ date }) => date.isValid)
			.sort((a, b) => a.date.toMillis() - b.date.toMillis());
		const inRange = valid.filter(({ date }) => {
			if (rangeStart?.isValid && date < rangeStart.startOf('day')) return false;
			if (rangeEnd?.isValid && date > rangeEnd.endOf('day')) return false;
			return true;
		});

		return (inRange[0] || valid[0])?.date.toISODate() || null;
	});

	function openEvent(event: CalendarDisplayEvent) {
		selectedEvent = event;
		showEvent = true;
	}

	function closeEvent() {
		showEvent = false;
		selectedEvent = null;
	}
</script>

<div class="flex h-full min-h-0 flex-col">
	<section class="card flex h-full min-h-0 flex-col bg-base-200 shadow-xl">
		<div class="card-body flex min-h-0 flex-1 flex-col gap-3 p-3 sm:p-4">
			<div class="flex flex-wrap items-center justify-between gap-2">
				<div class="flex min-w-0 items-center gap-2">
					<CalendarIcon class="h-5 w-5 shrink-0 text-primary" />
					<h3 class="text-lg font-bold">{$t('navbar.calendar')}</h3>
					<span class="badge badge-ghost badge-sm">
						{events.length}
						{$t('collections.events')}
					</span>
				</div>
				<div class="join">
					<button
						type="button"
						class="btn join-item btn-xs sm:btn-sm"
						class:btn-active={timezoneMode === 'event'}
						onclick={() => (timezoneMode = 'event')}
					>
						{$t('collections.event_timezone')}
					</button>
					<button
						type="button"
						class="btn join-item btn-xs sm:btn-sm"
						class:btn-active={timezoneMode === 'local'}
						onclick={() => (timezoneMode = 'local')}
					>
						{$t('collections.local_timezone')}
					</button>
				</div>
			</div>

			{#if events.length === 0}
				<p class="text-sm text-base-content/60">{$t('collections.no_calendar_events')}</p>
			{/if}

			<div
				class="collection-calendar min-h-0 flex-1 overflow-hidden rounded-xl bg-base-100"
				{@attach measureFrame}
			>
				{#if frameHeight > 0}
					<CalendarComponent
						{events}
						{initialDate}
						height="{frameHeight}px"
						dayMaxEvents={2}
						bare={true}
						on:eventClick={(e) => openEvent(e.detail)}
					/>
				{/if}
			</div>
		</div>
	</section>
</div>

<EventDetailsModal
	show={showEvent}
	event={selectedEvent}
	{timezoneMode}
	{userTimezone}
	onClose={closeEvent}
/>

<style>
	.collection-calendar :global(.ec-toolbar) {
		margin-bottom: 0.5rem !important;
		padding: 0.5rem 0.75rem !important;
	}

	.collection-calendar :global(.ec-body) {
		overflow: hidden !important;
	}

	.collection-calendar :global(.ec-content) {
		display: flex !important;
		height: 100% !important;
		flex-direction: column;
	}

	.collection-calendar :global(.ec-days) {
		height: auto !important;
		min-height: 0 !important;
		flex: 1 1 0 !important;
		overflow: hidden;
	}
</style>
