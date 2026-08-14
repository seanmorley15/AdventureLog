<script lang="ts">
	import { run } from 'svelte/legacy';

	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	import CalendarIcon from '~icons/mdi/calendar';
	import FilterIcon from '~icons/mdi/filter-variant';
	import SearchIcon from '~icons/mdi/magnify';
	import ClearIcon from '~icons/mdi/close';
	import ViewAgenda from '~icons/mdi/view-agenda';
	import ViewModule from '~icons/mdi/view-module';
	import ViewWeek from '~icons/mdi/view-week';
	import ClockOutline from '~icons/mdi/clock-outline';
	import CalendarClock from '~icons/mdi/calendar-clock';
	import CalendarComponent from '$lib/components/calendar/Calendar.svelte';
	import CalendarAgenda from '$lib/components/calendar/CalendarAgenda.svelte';
	import CalendarSidebar from '$lib/components/calendar/CalendarSidebar.svelte';
	import EventDetailsModal from '$lib/components/calendar/EventDetailsModal.svelte';
	import type {
		CalendarApiEvent,
		CalendarDisplayEvent,
		CalendarEventType,
		CalendarViewMode
	} from '$lib/calendar/types';
	import {
		apiEventsToDisplayEvents,
		CALENDAR_EVENT_TYPES,
		computeCalendarStats,
		filterCalendarEvents,
		formatCalendarRange
	} from '$lib/calendar/events';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

	let apiEvents: CalendarApiEvent[] = $state<CalendarApiEvent[]>([]);
	let displayEvents: CalendarDisplayEvent[] = $state([]);
	let filteredEvents: CalendarDisplayEvent[] = $state([]);
	let loadError = $state<string | null>(null);

	$effect.pre(() => {
		apiEvents = (data.props.initialEvents || []) as CalendarApiEvent[];
		loadError = data.props.loadError;
	});
	let isLoading = $state(false);
	let isDownloadingIcs = $state(false);

	let selectedEvent: CalendarDisplayEvent | null = $state(null);
	let showEventModal = $state(false);
	let sidebarOpen = $state(false);

	let searchFilter = $state('');
	let timezoneMode: 'event' | 'local' = $state('event');
	let activeTypes = $state(new Set<CalendarEventType>(CALENDAR_EVENT_TYPES));
	let viewMode: CalendarViewMode = $state('dayGridMonth');
	let calendarView = $state('dayGridMonth');
	let fetchedRanges = new Set<string>();

	let timezoneLabels = $derived({
		eventTimezone: $t('calendar.event timezone'),
		localTimezone: $t('calendar.your timezone')
	});

	run(() => {
		displayEvents = apiEventsToDisplayEvents(
			apiEvents,
			timezoneMode,
			userTimezone,
			timezoneLabels
		);
	});

	run(() => {
		filteredEvents = filterCalendarEvents(displayEvents, {
			search: searchFilter,
			types: activeTypes
		});
	});

	let stats = $derived(computeCalendarStats(displayEvents));

	let agendaEvents = $derived(filteredEvents.filter((event) => {
		const day = event.start.split('T')[0];
		return day >= new Date().toISOString().split('T')[0];
	}));

	let hasActiveFilters =
		$derived(searchFilter.trim().length > 0 || activeTypes.size !== CALENDAR_EVENT_TYPES.length);

	function handleEventClick(event: CalendarDisplayEvent) {
		selectedEvent = event;
		showEventModal = true;
	}

	function closeModal() {
		showEventModal = false;
		selectedEvent = null;
	}

	function toggleType(type: CalendarEventType) {
		const next = new Set(activeTypes);
		if (next.has(type)) {
			if (next.size > 1) next.delete(type);
		} else {
			next.add(type);
		}
		activeTypes = next;
	}

	function clearFilters() {
		searchFilter = '';
		activeTypes = new Set(CALENDAR_EVENT_TYPES);
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function setViewMode(mode: CalendarViewMode) {
		viewMode = mode;
		if (mode === 'agenda') return;
		calendarView = mode;
	}

	async function fetchEventsForRange(start: Date, end: Date) {
		const range = formatCalendarRange(start, end);
		const key = `${range.start}:${range.end}`;
		if (fetchedRanges.has(key)) return;

		isLoading = true;
		try {
			const response = await fetch(`/api/calendar/events/?start=${range.start}&end=${range.end}`);
			if (!response.ok) throw new Error('Failed to load calendar events');
			const payload = await response.json();
			const incoming = (payload.events || []) as CalendarApiEvent[];
			const merged = new Map(apiEvents.map((event) => [event.id, event]));
			for (const event of incoming) merged.set(event.id, event);
			apiEvents = [...merged.values()].sort((a, b) => a.start.localeCompare(b.start));
			fetchedRanges.add(key);
			loadError = null;
		} catch {
			loadError = 'calendar.load_error';
			addToast('error', $t('calendar.load_error'));
		} finally {
			isLoading = false;
		}
	}

	async function handleDatesSet(detail: { start: Date; end: Date }) {
		await fetchEventsForRange(detail.start, detail.end);
	}

	async function downloadIcs() {
		if (isDownloadingIcs) return;
		isDownloadingIcs = true;
		try {
			const response = await fetch('/api/ics-calendar/generate/');
			if (!response.ok) throw new Error('Unable to generate calendar');
			const blob = await response.blob();
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = 'adventurelog.ics';
			link.click();
			URL.revokeObjectURL(url);
			addToast('success', $t('calendar.export_success'));
		} catch {
			addToast('error', $t('calendar.export_error'));
		} finally {
			isDownloadingIcs = false;
		}
	}

	onMount(() => {
		const now = new Date();
		const start = new Date(now.getFullYear(), now.getMonth() - 2, 1);
		const end = new Date(now.getFullYear(), now.getMonth() + 5, 0);
		fetchEventsForRange(start, end);
	});
</script>

<svelte:head>
	<title>{$t('navbar.calendar')} - AdventureLog</title>
	<meta name="description" content="View your travel calendar and upcoming adventures." />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="calendar-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<!-- Header -->
			<div class="sticky top-0 z-40 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4 min-w-0">
							<button class="btn btn-ghost btn-square lg:hidden shrink-0" onclick={toggleSidebar}>
								<FilterIcon class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3 min-w-0">
								<div class="p-2 bg-primary/10 rounded-xl shrink-0">
									<CalendarIcon class="w-8 h-8 text-primary" />
								</div>
								<div class="min-w-0">
									<h1 class="text-3xl font-bold text-primary bg-clip-text truncate">
										{$t('navbar.calendar')}
									</h1>
									<p class="text-sm text-base-content/60">
										{filteredEvents.length}
										{$t('worldtravel.of')}
										{stats.total}
										{$t('calendar.events_scheduled')} ·
										<span class="text-secondary">{stats.upcoming} {$t('calendar.upcoming')}</span>
										·
										<span>{stats.thisMonth} {$t('calendar.this_month')}</span>
										{#if isLoading}
											<span class="loading loading-spinner loading-xs ml-1 align-middle"></span>
										{/if}
									</p>
								</div>
							</div>
						</div>

						<div class="hidden md:flex items-center gap-2 shrink-0">
							<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
								<div class="stat py-2 px-4">
									<div class="stat-figure text-secondary">
										<ClockOutline class="w-5 h-5" />
									</div>
									<div class="stat-title text-xs">{$t('calendar.upcoming')}</div>
									<div class="stat-value text-lg text-secondary">{stats.upcoming}</div>
								</div>
								<div class="stat py-2 px-4">
									<div class="stat-figure text-primary">
										<CalendarClock class="w-5 h-5" />
									</div>
									<div class="stat-title text-xs">{$t('calendar.this_month')}</div>
									<div class="stat-value text-lg">{stats.thisMonth}</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Search & view controls -->
					<div class="mt-4 flex flex-wrap items-center gap-4">
						<div class="relative flex-1 max-w-md min-w-[12rem]">
							<SearchIcon
								class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-base-content/40"
							/>
							<input
								type="text"
								placeholder={$t('calendar.search_placeholder')}
								class="input input-bordered w-full pl-10 pr-10 bg-base-100/80"
								bind:value={searchFilter}
							/>
							{#if searchFilter.length > 0}
								<button
									type="button"
									class="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content"
									onclick={() => (searchFilter = '')}
								>
									<ClearIcon class="w-4 h-4" />
								</button>
							{/if}
						</div>

						<div class="tabs tabs-boxed bg-base-200">
							<button
								type="button"
								class="tab tab-sm gap-2 {viewMode === 'dayGridMonth' ? 'tab-active' : ''}"
								onclick={() => setViewMode('dayGridMonth')}
							>
								<ViewModule class="w-3.5 h-3.5" />
								{$t('calendar.month')}
							</button>
							<button
								type="button"
								class="tab tab-sm gap-2 {viewMode === 'timeGridWeek' ? 'tab-active' : ''}"
								onclick={() => setViewMode('timeGridWeek')}
							>
								<ViewWeek class="w-3.5 h-3.5" />
								{$t('calendar.week')}
							</button>
							<button
								type="button"
								class="tab tab-sm gap-2 {viewMode === 'agenda' ? 'tab-active' : ''}"
								onclick={() => setViewMode('agenda')}
							>
								<ViewAgenda class="w-3.5 h-3.5" />
								{$t('calendar.agenda')}
							</button>
						</div>
					</div>

					<!-- Filter chips -->
					<div class="mt-4 flex flex-wrap items-center gap-2">
						<span class="text-sm font-medium text-base-content/60"
							>{$t('worldtravel.filter_by')}:</span
						>
						{#if filteredEvents.length !== stats.total}
							<div class="badge badge-ghost gap-1">
								{filteredEvents.length} / {stats.total}
							</div>
						{/if}
						{#if hasActiveFilters}
							<button type="button" class="btn btn-ghost btn-xs gap-1" onclick={clearFilters}>
								<ClearIcon class="w-3 h-3" />
								{$t('worldtravel.clear_all')}
							</button>
						{/if}
					</div>
				</div>
			</div>

			<!-- Main content -->
			<div class="container mx-auto px-6 py-8">
				{#if loadError}
					<div class="alert alert-warning mb-6 shadow-sm">
						<span>{$t(loadError)}</span>
					</div>
				{/if}

				<div class="card bg-base-100 shadow-2xl border border-base-300/50">
					<div class="card-body p-0 sm:p-2">
						{#if viewMode === 'agenda'}
							<div class="p-4 sm:p-6">
								<h2 class="text-lg font-semibold mb-4 flex items-center gap-2">
									<ViewAgenda class="w-5 h-5 text-primary" />
									{$t('calendar.upcoming_agenda')}
								</h2>
								<CalendarAgenda
									events={agendaEvents.slice(0, 50)}
									emptyMessage={$t('calendar.no_upcoming_events')}
									on:select={(e) => handleEventClick(e.detail)}
								/>
							</div>
						{:else}
							<CalendarComponent
								events={filteredEvents}
								view={calendarView}
								height="calc(100dvh - 18rem)"
								bare={true}
								on:eventClick={(e) => handleEventClick(e.detail)}
								on:datesSet={(e) => handleDatesSet(e.detail)}
							/>
						{/if}
					</div>
				</div>
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label for="calendar-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<CalendarSidebar
						{stats}
						{activeTypes}
						filteredCount={filteredEvents.length}
						totalCount={displayEvents.length}
						{isDownloadingIcs}
						{timezoneMode}
						on:toggleType={(e) => toggleType(e.detail)}
						on:clearFilters={clearFilters}
						on:downloadIcs={downloadIcs}
						on:timezoneChange={(e) => (timezoneMode = e.detail)}
					/>
				</div>
			</div>
		</div>
	</div>
</div>

<EventDetailsModal
	show={showEventModal}
	event={selectedEvent}
	{timezoneMode}
	{userTimezone}
	onClose={closeModal}
/>
