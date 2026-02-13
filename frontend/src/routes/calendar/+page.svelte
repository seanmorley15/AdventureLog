<script lang="ts">
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import CalendarIcon from '~icons/mdi/calendar';
	import DownloadIcon from '~icons/mdi/download';
	import FilterIcon from '~icons/mdi/filter-variant';
	import SearchIcon from '~icons/mdi/magnify';
	import ClearIcon from '~icons/mdi/close';
	import CalendarComponent from '$lib/components/calendar/Calendar.svelte';
	import EventDetailsModal from '$lib/components/calendar/EventDetailsModal.svelte';

	export let data: PageData;

	let locations = data.props.adventures;
	let allDates = data.props.dates;
	let filteredDates = [...allDates];

	let eventDetails: Record<string, { description?: string | null; location?: string | null }> = {};
	let loadingDetailIds = new Set<string>();
	let isLoadingDetails = false;
	let detailsError = '';
	let isDownloadingIcs = false;

	$: selectedAdventureDetails =
		selectedEvent?.extendedProps?.adventureId &&
		eventDetails[selectedEvent.extendedProps.adventureId]
			? eventDetails[selectedEvent.extendedProps.adventureId]
			: null;

	$: currentLocation = selectedEvent?.extendedProps
		? (selectedAdventureDetails?.location ?? selectedEvent.extendedProps.location)
		: '';

	$: descriptionToShow = selectedEvent?.extendedProps
		? (selectedAdventureDetails?.description ?? selectedEvent.extendedProps.description)
		: '';

	// Modal state
	let selectedEvent: any = null;
	let showEventModal = false;

	// Filter state
	let searchFilter = '';
	let sidebarOpen = false;

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

	function handleEventClick(event: any) {
		selectedEvent = event;
		showEventModal = true;
		detailsError = '';

		const adventureId = event?.extendedProps?.adventureId;
		if (adventureId) {
			fetchEventDetails(adventureId);
		}
	}

	function clearFilters() {
		searchFilter = '';
	}

	function closeModal() {
		showEventModal = false;
		selectedEvent = null;
		detailsError = '';
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	async function fetchEventDetails(adventureId: string) {
		if (eventDetails[adventureId] || loadingDetailIds.has(adventureId)) return;

		loadingDetailIds.add(adventureId);
		isLoadingDetails = true;
		detailsError = '';

		try {
			const response = await fetch(`/api/locations/${adventureId}/`);
			if (!response.ok) {
				throw new Error('Failed to load event details');
			}

			const detail = await response.json();
			eventDetails = {
				...eventDetails,
				[adventureId]: {
					description: detail.description,
					location: detail.location ?? ''
				}
			};
		} catch (error) {
			detailsError = 'Unable to load event details right now.';
		} finally {
			loadingDetailIds.delete(adventureId);
			isLoadingDetails = loadingDetailIds.size > 0;
		}
	}

	async function downloadIcs() {
		if (isDownloadingIcs) return;

		isDownloadingIcs = true;

		try {
			const response = await fetch('/api/ics-calendar/generate/');
			if (!response.ok) {
				throw new Error('Unable to generate calendar');
			}

			const blob = await response.blob();
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = 'locations.ics';
			link.click();
			URL.revokeObjectURL(url);
		} catch (error) {
			console.error(error);
		} finally {
			isDownloadingIcs = false;
		}
	}
</script>

<svelte:head>
	<title>{$t('adventures.visit_calendar')} - AdventureLog</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="calendar-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<!-- Header Section -->
			<div class="sticky top-0 z-40 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
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
										{$t('adventures.visit_calendar')}
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
									<div class="stat-title text-xs">{$t('locations.locations')}</div>
									<div class="stat-value text-lg text-secondary">{locations.length}</div>
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
								placeholder={$t('adventures.search_for_location')}
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
				<div class="card bg-base-100 shadow-2xl border border-base-300/50">
					<div class="card-body p-0">
						<CalendarComponent events={filteredDates} onEventClick={handleEventClick} />
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
									<div class="stat-title text-xs">{$t('locations.locations')}</div>
									<div class="stat-value text-lg text-primary">{locations.length}</div>
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
						<button
							type="button"
							class="btn btn-primary w-full gap-2"
							on:click={downloadIcs}
							disabled={isDownloadingIcs}
						>
							{#if isDownloadingIcs}
								<span class="loading loading-spinner loading-sm"></span>
							{:else}
								<DownloadIcon class="w-4 h-4" />
							{/if}
							{$t('adventures.download_calendar')}
						</button>

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
<EventDetailsModal
	show={showEventModal}
	event={selectedEvent}
	{isLoadingDetails}
	{detailsError}
	location={currentLocation}
	description={descriptionToShow}
	onClose={closeModal}
/>
