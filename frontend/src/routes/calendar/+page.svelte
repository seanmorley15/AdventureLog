<script lang="ts">
	import type { PageData } from './$types';
	// @ts-ignore
	import Calendar from '@event-calendar/core';
	// @ts-ignore
	import TimeGrid from '@event-calendar/time-grid';
	// @ts-ignore
	import DayGrid from '@event-calendar/day-grid';
	// @ts-ignore
	import Interaction from '@event-calendar/interaction';
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import CalendarIcon from '~icons/mdi/calendar';
	import DownloadIcon from '~icons/mdi/download';
	import FilterIcon from '~icons/mdi/filter-variant';
	import CloseIcon from '~icons/mdi/close';
	import MapMarkerIcon from '~icons/mdi/map-marker';
	import ClockIcon from '~icons/mdi/clock';
	import SearchIcon from '~icons/mdi/magnify';
	import ClearIcon from '~icons/mdi/close';
	import { marked } from 'marked'; // Import the markdown parser

	export let data: PageData;

	const renderMarkdown = (markdown: string) => {
		return marked(markdown);
	};

	let adventures = data.props.adventures;
	let allDates = data.props.dates;
	let filteredDates = [...allDates];

	let icsCalendar = data.props.ics_calendar;
	let icsCalendarDataUrl = URL.createObjectURL(new Blob([icsCalendar], { type: 'text/calendar' }));

	// Modal state
	let selectedEvent: any = null;
	let showEventModal = false;

	// Filter state
	let showFilters = false;
	let searchFilter = '';
	let sidebarOpen = false;

	// Get unique categories for filter

	// Apply filters
	$: {
		filteredDates = allDates.filter((event) => {
			const matchesSearch =
				!searchFilter ||
				event.extendedProps?.adventureName.toLowerCase().includes(searchFilter.toLowerCase()) ||
				event.extendedProps?.location?.toLowerCase().includes(searchFilter.toLowerCase());

			return matchesSearch;
		});
	}

	let plugins = [TimeGrid, DayGrid, Interaction];
	$: options = {
		view: 'dayGridMonth',
		events: filteredDates,
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
		height: 'auto',
		eventDisplay: 'block',
		dayMaxEvents: 3,
		moreLinkText: (num: number) => `+${num} more`,
		eventClick: (info: any) => {
			selectedEvent = info.event;
			showEventModal = true;
		},
		eventMouseEnter: (info: any) => {
			info.el.style.cursor = 'pointer';
		},
		themeSystem: 'standard'
	};

	function clearFilters() {
		searchFilter = '';
	}

	function closeModal() {
		showEventModal = false;
		selectedEvent = null;
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	onMount(() => {
		// Add custom CSS for calendar styling
		const style = document.createElement('style');
		style.textContent = `
			.ec-toolbar {
				background: hsl(var(--b2)) !important;
				border-radius: 0.75rem !important;
				padding: 1.25rem !important;
				margin-bottom: 1.5rem !important;
				border: 1px solid hsl(var(--b3)) !important;
				box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important;
			}
			.ec-button {
				background: hsl(var(--b3)) !important;
				border: 1px solid hsl(var(--b3)) !important;
				color: hsl(var(--bc)) !important;
				border-radius: 0.5rem !important;
				padding: 0.5rem 1rem !important;
				font-weight: 500 !important;
				transition: all 0.2s ease !important;
			}
			.ec-button:hover {
				background: hsl(var(--b1)) !important;
				transform: translateY(-1px) !important;
				box-shadow: 0 4px 12px rgb(0 0 0 / 0.15) !important;
			}
			.ec-button.ec-button-active {
				background: hsl(var(--p)) !important;
				color: hsl(var(--pc)) !important;
				box-shadow: 0 4px 12px hsl(var(--p) / 0.3) !important;
			}
			.ec-day {
				background: hsl(var(--b1)) !important;
				border: 1px solid hsl(var(--b3)) !important;
				transition: background-color 0.2s ease !important;
			}
			.ec-day:hover {
				background: hsl(var(--b2)) !important;
			}
			.ec-day-today {
				background: hsl(var(--b2)) !important;
				position: relative !important;
			}
			.ec-day-today::before {
				content: '' !important;
				position: absolute !important;
				top: 0 !important;
				left: 0 !important;
				right: 0 !important;
				height: 3px !important;
				background: hsl(var(--p)) !important;
				border-radius: 0.25rem !important;
			}
			.ec-event {
				border-radius: 0.375rem !important;
				padding: 0.25rem 0.5rem !important;
				font-size: 0.75rem !important;
				font-weight: 600 !important;
				transition: all 0.2s ease !important;
				box-shadow: 0 1px 3px rgb(0 0 0 / 0.1) !important;
			}
			.ec-event:hover {
				transform: translateY(-1px) !important;
				box-shadow: 0 4px 12px rgb(0 0 0 / 0.15) !important;
			}
			.ec-view {
				background: hsl(var(--b1)) !important;
				border-radius: 0.75rem !important;
				overflow: hidden !important;
			}
		`;
		document.head.appendChild(style);
	});
</script>

<svelte:head>
	<title>{$t('adventures.adventure_calendar')} - AdventureLog</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open p-[12px]">
		<input id="calendar-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content bg-white rounded-[24px] overflow-hidden">
			<!-- Header Section -->
			<div class="sticky top-0 z-30">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4">
							<button class="btn btn-ghost btn-square lg:hidden" on:click={toggleSidebar}>
								<FilterIcon class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-xl">
									<CalendarIcon class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold text-primary bg-clip-text">
										{$t('adventures.adventure_calendar')}
									</h1>
									<p class="text-sm text-base-content/60">
										{filteredDates.length}
										{$t('calendar.events_scheduled')}
									</p>
								</div>
							</div>
						</div>

						<!-- Quick Stats -->
						<div class="hidden md:flex items-center gap-2">
							<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('calendar.total_events')}</div>
									<div class="stat-value text-lg text-primary">{allDates.length}</div>
								</div>
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('navbar.adventures')}</div>
									<div class="stat-value text-lg text-secondary">{adventures.length}</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Search Bar -->
					<div class="mt-4 flex items-center gap-4">
						<div class="relative flex-1 max-w-md">
							<SearchIcon
								class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-base-content/40"
							/>
							<input
								type="text"
								placeholder="Search adventures or locations..."
								class="input input-bordered w-full pl-10 pr-10 bg-base-100/80"
								bind:value={searchFilter}
							/>
							{#if searchFilter.length > 0}
								<button
									class="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content"
									on:click={() => (searchFilter = '')}
								>
									<ClearIcon class="w-4 h-4" />
								</button>
							{/if}
						</div>
					</div>

					<!-- Filter Chips -->
					<div class="mt-4 flex flex-wrap items-center gap-2">
						<span class="text-sm font-medium text-base-content/60"
							>{$t('worldtravel.filter_by')}:</span
						>
						{#if searchFilter}
							<button class="btn btn-ghost btn-xs gap-1" on:click={clearFilters}>
								<ClearIcon class="w-3 h-3" />
								{$t('worldtravel.clear_all')}
							</button>
						{/if}
					</div>
				</div>
			</div>

			<!-- Main Content -->
			<div class="container mx-auto px-6 py-8">
				<!-- Calendar -->
				<div class="card bg-base-100 border border-base-300/50">
					<div class="card-body p-0">
						<Calendar {plugins} {options} />
					</div>
				</div>
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label for="calendar-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<!-- Sidebar Header -->
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<FilterIcon class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('adventures.filters_and_stats')}</h2>
					</div>

					<!-- Calendar Statistics -->
					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<CalendarIcon class="w-5 h-5" />
							{$t('calendar.calendar_overview')}
						</h3>

						<div class="space-y-4">
							<div class="stat p-0">
								<div class="stat-title text-sm">{$t('calendar.total_events')}</div>
								<div class="stat-value text-2xl">{allDates.length}</div>
							</div>

							<div class="grid grid-cols-2 gap-4">
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('navbar.adventures')}</div>
									<div class="stat-value text-lg text-primary">{adventures.length}</div>
								</div>
							</div>

							{#if filteredDates.length !== allDates.length}
								<div class="space-y-2">
									<div class="flex justify-between text-sm">
										<span>{$t('calendar.filtered_results')}</span>
										<span>{filteredDates.length} {$t('worldtravel.of')} {allDates.length}</span>
									</div>
									<progress
										class="progress progress-primary w-full"
										value={filteredDates.length}
										max={allDates.length}
									></progress>
								</div>
							{/if}
						</div>
					</div>

					<!-- Quick Actions -->
					<div class="space-y-3">
						<a
							href={icsCalendarDataUrl}
							download="adventures.ics"
							class="btn btn-primary w-full gap-2"
						>
							<DownloadIcon class="w-4 h-4" />
							{$t('adventures.download_calendar')}
						</a>

						<button class="btn btn-ghost w-full gap-2" on:click={clearFilters}>
							<ClearIcon class="w-4 h-4" />
							{$t('worldtravel.clear_filters')}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<!-- Event Details Modal -->
{#if showEventModal && selectedEvent}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<div class="modal modal-open">
		<div class="modal-box max-w-2xl bg-base-100 border border-base-300/50 shadow-2xl">
			<div class="flex items-start justify-between mb-6">
				<div class="flex items-center gap-4">
					<div class="p-3 bg-primary/10 rounded-xl">
						<span class="text-2xl">{selectedEvent.extendedProps.icon}</span>
					</div>
					<div>
						<h3 class="text-2xl font-bold">{selectedEvent.extendedProps.adventureName}</h3>
						<div class="badge badge-primary badge-lg mt-2">
							{selectedEvent.extendedProps.category}
						</div>
					</div>
				</div>
				<button class="btn btn-ghost btn-sm btn-circle" on:click={closeModal}>
					<CloseIcon class="w-5 h-5" />
				</button>
			</div>

			<div class="space-y-4">
				<!-- Date & Time -->
				<div class="card bg-base-200/50 border border-base-300/30">
					<div class="card-body p-4">
						<div class="flex items-center gap-3">
							<ClockIcon class="w-6 h-6 text-primary flex-shrink-0" />
							<div>
								<div class="font-semibold text-lg">
									{#if selectedEvent.extendedProps.isAllDay}
										{$t('calendar.all_day_event')}
									{:else}
										{selectedEvent.extendedProps.formattedStart}
										{#if selectedEvent.extendedProps.formattedEnd !== selectedEvent.extendedProps.formattedStart}
											→ {selectedEvent.extendedProps.formattedEnd}
										{/if}
									{/if}
								</div>
								{#if !selectedEvent.extendedProps.isAllDay && selectedEvent.extendedProps.timezone}
									<div class="text-sm text-base-content/70 mt-1">
										{selectedEvent.extendedProps.timezone}
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>

				<!-- Location -->
				{#if selectedEvent.extendedProps.location}
					<div class="card bg-base-200/50 border border-base-300/30">
						<div class="card-body p-4">
							<div class="flex items-center gap-3">
								<MapMarkerIcon class="w-6 h-6 text-primary flex-shrink-0" />
								<div class="font-semibold text-lg">{selectedEvent.extendedProps.location}</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Description -->
				{#if selectedEvent.extendedProps.description}
					<div class="card bg-base-200/50 border border-base-300/30">
						<div class="card-body p-4">
							<div class="font-semibold text-lg mb-3">{$t('adventures.description')}</div>
							<article
								class="prose overflow-auto h-full max-w-full p-4 border border-base-300 rounded-lg mb-4 mt-4"
							>
								{@html renderMarkdown(selectedEvent.extendedProps.description || '')}
							</article>
						</div>
					</div>
				{/if}

				{#if selectedEvent.extendedProps.adventureId}
					<a
						href={`/adventures/${selectedEvent.extendedProps.adventureId}`}
						class="btn btn-neutral btn-block mt-4"
					>
						{$t('map.view_details')}
					</a>
				{/if}
			</div>

			<div class="modal-action mt-8">
				<button class="btn btn-primary btn-lg" on:click={closeModal}> {$t('about.close')} </button>
			</div>
		</div>
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="modal-backdrop" on:click={closeModal}></div>
	</div>
{/if}
