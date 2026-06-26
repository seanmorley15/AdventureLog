<script lang="ts">
	import LocationCard from '$lib/components/cards/LocationCard.svelte';
	import CollectionCard from '$lib/components/cards/CollectionCard.svelte';
	import UserAvatar from '$lib/components/UserAvatar.svelte';
	import CalendarAgenda from '$lib/components/calendar/CalendarAgenda.svelte';
	import type { PageData } from './$types';
	import type { ActivityRecord, SlimCollection, UserStats } from '$lib/types';
	import type { CalendarApiEvent } from '$lib/calendar/types';
	import { apiEventsToDisplayEvents } from '$lib/calendar/events';
	import { getDistance, getElevation } from '$lib/index';
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';

	import Plus from '~icons/mdi/plus';
	import FlagCheckeredVariantIcon from '~icons/mdi/flag-checkered-variant';
	import Airplane from '~icons/mdi/airplane';
	import CityVariantOutline from '~icons/mdi/city-variant-outline';
	import MapMarkerStarOutline from '~icons/mdi/map-marker-star-outline';
	import CalendarClock from '~icons/mdi/calendar-clock';
	import FolderMultiple from '~icons/mdi/folder-multiple';
	import MapMarkerMultiple from '~icons/mdi/map-marker-multiple';
	import Run from '~icons/mdi/run';
	import TimerOutline from '~icons/mdi/timer-outline';
	import Mountain from '~icons/mdi/mountain';
	import Fire from '~icons/mdi/fire';
	import Map from '~icons/mdi/map';
	import Calendar from '~icons/mdi/calendar';
	import Magnify from '~icons/mdi/magnify';
	import Account from '~icons/mdi/account';
	import AlertCircle from '~icons/mdi/alert-circle';
	import EmailAlert from '~icons/mdi/email-alert';
	import Earth from '~icons/mdi/earth';
	import ChevronRight from '~icons/mdi/chevron-right';
	import CompassRose from '~icons/mdi/compass-rose';

	export let data: PageData;

	const user = data.user;
	let stats: UserStats | null = data.props.stats;
	let recentLocations = data.props.recentLocations;
	let upcomingTrips: SlimCollection[] = data.props.upcomingTrips;
	let activeTrip: SlimCollection | null = data.props.activeTrip;
	let upcomingEvents: CalendarApiEvent[] = data.props.upcomingEvents;
	let inviteCount = data.props.inviteCount;
	let loadError = data.props.loadError;

	let heroVisible = false;

	onMount(() => {
		requestAnimationFrame(() => {
			heroVisible = true;
		});
	});

	$: stats = data.props.stats;
	$: recentLocations = data.props.recentLocations;
	$: upcomingTrips = data.props.upcomingTrips;
	$: activeTrip = data.props.activeTrip;
	$: upcomingEvents = data.props.upcomingEvents;
	$: inviteCount = data.props.inviteCount;
	$: loadError = data.props.loadError;

	const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	$: measurementSystem = user?.measurement_system || 'metric';
	$: greetingName = user?.first_name || user?.username || '';

	$: timezoneLabels = {
		eventTimezone: $t('calendar.event timezone'),
		localTimezone: $t('calendar.your timezone')
	};

	$: displayEvents = apiEventsToDisplayEvents(
		upcomingEvents,
		'event',
		userTimezone,
		timezoneLabels
	);

	$: agendaEvents = displayEvents
		.filter((event) => event.start.split('T')[0] >= new Date().toISOString().split('T')[0])
		.slice(0, 5);

	function getPercentage(value: number, total: number): number {
		if (!total || total <= 0) return 0;
		return Math.round((value / total) * 100);
	}

	function formatTime(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		if (hours > 0) return `${hours}h ${minutes}m`;
		return `${minutes}m`;
	}

	function getRecordTitle(record: ActivityRecord | null): string {
		if (!record) return '';
		return record.activity_name || record.sport_type || 'Activity';
	}

	$: worldExplorationPercentage = stats
		? getPercentage(stats.visited_country_count, stats.total_countries)
		: 0;
	$: regionExplorationPercentage = stats
		? getPercentage(stats.visited_region_count, stats.total_regions)
		: 0;
	$: cityExplorationPercentage = stats
		? getPercentage(stats.visited_city_count, stats.total_cities)
		: 0;
	$: locationVisitedPercentage = stats
		? getPercentage(stats.visited_location_count, stats.location_count)
		: 0;

	$: isNewUser =
		stats &&
		stats.location_count === 0 &&
		stats.trips_count === 0 &&
		upcomingTrips.length === 0 &&
		!activeTrip;

	$: profileHref = user ? `/profile/${user.username}` : '/settings';

	$: heroTrip = activeTrip ?? upcomingTrips[0] ?? null;
	$: heroTripIsActive = Boolean(activeTrip);

	$: timeGreetingKey = (() => {
		const hour = new Date().getHours();
		if (hour < 12) return 'dashboard.greeting_morning';
		if (hour < 17) return 'dashboard.greeting_afternoon';
		if (hour < 22) return 'dashboard.greeting_evening';
		return 'dashboard.greeting_night';
	})();

	$: welcomeSubtitle = loadError
		? $t('dashboard.stats_error')
		: stats && stats.visited_country_count > 0
			? $t('dashboard.hero_countries', { values: { count: stats.visited_country_count } })
			: stats && stats.location_count > 0
				? stats.location_count === 1
					? $t('dashboard.hero_location_logged')
					: $t('dashboard.hero_locations_logged', {
							values: { count: stats.location_count }
						})
				: $t('dashboard.hero_start_journey');

	function formatTripDate(date: string | null): string {
		if (!date) return '';
		return new Date(date).toLocaleDateString(undefined, {
			timeZone: 'UTC',
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		});
	}

	function getTripBannerImage(trip: SlimCollection): string | null {
		if (trip.primary_image?.image) return trip.primary_image.image;
		const locationImage = trip.location_images?.find((image) => image?.image);
		return locationImage?.image ?? null;
	}

	$: heroTripBannerImage = heroTrip ? getTripBannerImage(heroTrip) : null;

	$: quickLinks = [
		{ href: '/map', labelKey: 'navbar.map', icon: Map },
		{
			href: '/worldtravel',
			labelKey: 'home.explore_world',
			icon: FlagCheckeredVariantIcon
		},
		{ href: '/calendar', labelKey: 'navbar.calendar', icon: Calendar },
		{
			href: '/collections',
			labelKey: 'dashboard.my_collections',
			icon: FolderMultiple
		},
		{ href: '/search', labelKey: 'navbar.search', icon: Magnify },
		{ href: profileHref, labelKey: 'navbar.profile', icon: Account }
	];
</script>

<svelte:head>
	<title>{$t('dashboard.page_title')} | AdventureLog</title>
	<meta name="description" content={$t('dashboard.page_description')} />
</svelte:head>

<div
	class="min-h-screen bg-gradient-to-b from-base-200 via-base-100 to-base-200 relative overflow-hidden"
>
	<!-- Subtle ambient background -->
	<div class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
		<div
			class="absolute -top-40 right-0 h-[28rem] w-[28rem] rounded-full bg-primary/8 blur-3xl"
		></div>
		<div class="absolute bottom-1/4 -left-24 h-64 w-64 rounded-full bg-secondary/6 blur-3xl"></div>
	</div>

	<!-- Hero -->
	<section class="relative overflow-hidden border-b border-base-300/20">
		<!-- Layered background shapes -->
		<div class="pointer-events-none absolute inset-0" aria-hidden="true">
			<div class="absolute -left-20 top-0 h-64 w-64 rounded-full bg-primary/12 blur-3xl"></div>
			<div class="absolute right-0 top-1/3 h-80 w-80 rounded-full bg-secondary/10 blur-3xl"></div>
			<div class="absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-accent/8 blur-2xl"></div>
			<div
				class="dashboard-shape absolute right-[12%] top-8 h-24 w-24 rotate-12 rounded-3xl border border-primary/15 bg-primary/5"
			></div>
			<div
				class="dashboard-shape dashboard-shape-delayed absolute left-[8%] bottom-6 h-16 w-16 -rotate-6 rounded-2xl border border-secondary/15 bg-secondary/5"
			></div>
			<div
				class="dashboard-shape absolute right-[35%] bottom-10 h-10 w-10 rotate-45 rounded-lg bg-accent/10"
			></div>
		</div>

		<div class="container relative z-10 mx-auto px-6 py-10 lg:py-14">
			<div
				class="dashboard-hero relative overflow-hidden rounded-3xl border border-base-300/40 bg-base-100/55 p-6 shadow-lg backdrop-blur-md sm:p-8 lg:p-10"
				class:dashboard-hero-visible={heroVisible}
			>
				<div
					class="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/[0.04] via-transparent to-secondary/[0.05]"
					aria-hidden="true"
				></div>

				<div class="relative grid items-stretch gap-8 lg:grid-cols-[1fr_min(100%,20rem)] lg:gap-10">
					<div
						class="flex min-w-0 flex-col justify-center gap-6 sm:flex-row sm:items-center sm:gap-8"
					>
						<div class="avatar shrink-0">
							<div
								class="h-16 w-16 overflow-hidden rounded-2xl shadow-lg ring-2 ring-primary/25 ring-offset-2 ring-offset-base-100/80 sm:h-[4.5rem] sm:w-[4.5rem]"
							>
								<UserAvatar
									user={user ?? undefined}
									alt={greetingName}
									className="w-full h-full rounded-2xl"
									textClass="text-xl sm:text-2xl"
								/>
							</div>
						</div>

						<div class="min-w-0 flex-1 space-y-5">
							<div>
								<h1
									class="text-3xl font-black leading-tight tracking-tight sm:text-4xl lg:text-[2.75rem]"
								>
									<span class="text-base-content/85">{$t(timeGreetingKey)}</span>{#if greetingName},
										<span
											class="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent"
										>
											{greetingName}
										</span>
									{/if}
								</h1>
								<p class="mt-3 max-w-xl text-base leading-relaxed text-base-content/65 sm:text-lg">
									{welcomeSubtitle}
								</p>
							</div>

							<div class="flex flex-col gap-3 sm:flex-row">
								<a
									href="/locations"
									class="btn btn-primary gap-2 shadow-md transition-shadow hover:shadow-lg"
								>
									<Plus class="h-4 w-4" />
									{$t('map.add_location')}
								</a>
								<a
									href="/collections"
									class="btn btn-outline gap-2 border-base-300/60 bg-base-100/70"
								>
									<FolderMultiple class="h-4 w-4" />
									{$t('dashboard.my_collections')}
								</a>
							</div>
						</div>
					</div>

					<!-- Trip card -->
					<div class="relative w-full lg:justify-self-end">
						<div
							class="pointer-events-none absolute -right-4 -top-4 h-20 w-20 rounded-2xl bg-gradient-to-br from-primary/20 to-secondary/10 blur-sm"
							aria-hidden="true"
						></div>

						{#if heroTrip}
							<a
								href="/collections/{heroTrip.id}"
								class="dashboard-trip-card group relative block h-full overflow-hidden rounded-2xl border border-base-300/50 bg-base-100/90 shadow-md transition-all hover:-translate-y-1 hover:shadow-xl"
							>
								{#if heroTripBannerImage}
									<div class="relative h-36 overflow-hidden bg-base-200 sm:h-40">
										<img
											src={heroTripBannerImage}
											alt={heroTrip.name}
											class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
										/>
										<div
											class="absolute inset-0 bg-gradient-to-t from-base-100 via-base-100/30 to-transparent"
										></div>
									</div>
								{:else}
									<div
										class="relative h-28 overflow-hidden bg-gradient-to-br from-primary/15 via-secondary/10 to-accent/10 sm:h-32"
									>
										<div
											class="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.2),transparent_55%)]"
										></div>
									</div>
								{/if}

								<div class="relative p-5">
									<div class="mb-3 flex items-center justify-between gap-2">
										<span
											class="badge badge-sm gap-1 {heroTripIsActive
												? 'badge-secondary'
												: 'badge-primary'}"
										>
											{#if heroTripIsActive}
												<Airplane class="h-3 w-3" />
												{$t('dashboard.hero_trip_on_the_road')}
											{:else}
												<CalendarClock class="h-3 w-3" />
												{$t('dashboard.hero_trip_coming_up')}
											{/if}
										</span>
										{#if !heroTripIsActive && heroTrip.days_until_start !== null}
											<span class="text-xs font-semibold text-primary/70">
												{$t('dashboard.next_trip_in', {
													values: { days: heroTrip.days_until_start }
												})}
											</span>
										{/if}
									</div>

									<h2
										class="line-clamp-2 text-lg font-bold leading-snug text-base-content transition-colors group-hover:text-primary"
									>
										{heroTrip.name}
									</h2>

									<div
										class="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-base-content/55"
									>
										<span class="inline-flex items-center gap-1">
											<MapMarkerMultiple class="h-4 w-4 shrink-0 text-primary/70" />
											{heroTrip.location_count}
											{$t('locations.locations').toLowerCase()}
										</span>
										{#if heroTrip.start_date}
											<span class="inline-flex items-center gap-1">
												<Calendar class="h-4 w-4 shrink-0 text-secondary/70" />
												{formatTripDate(heroTrip.start_date)}
											</span>
										{/if}
									</div>

									<span
										class="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-primary"
									>
										{$t('dashboard.hero_view_trip')}
										<ChevronRight class="h-4 w-4 transition-transform group-hover:translate-x-1" />
									</span>
								</div>
							</a>
						{:else}
							<div
								class="relative flex h-full min-h-[14rem] flex-col items-center justify-center overflow-hidden rounded-2xl border border-dashed border-base-300/60 bg-gradient-to-br from-base-100/90 to-base-200/40 p-6 text-center"
							>
								<div
									class="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-primary/8"
									aria-hidden="true"
								></div>
								<div class="relative mb-4 rounded-2xl bg-base-200/80 p-4">
									<CompassRose class="h-10 w-10 text-primary/40" />
								</div>
								<h2 class="relative font-bold text-base-content/75">
									{$t('dashboard.hero_trip_empty_title')}
								</h2>
								<p
									class="relative mt-1.5 max-w-[15rem] text-sm leading-relaxed text-base-content/50"
								>
									{$t('dashboard.hero_trip_empty_desc')}
								</p>
								<a href="/collections" class="btn btn-primary btn-sm relative mt-5 gap-2">
									<Plus class="h-4 w-4" />
									{$t('dashboard.my_collections')}
								</a>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</section>

	<div class="container relative z-10 mx-auto px-6 py-8 lg:py-10">
		{#if loadError}
			<div class="alert alert-warning mb-8 shadow-lg">
				<AlertCircle class="h-6 w-6 shrink-0" />
				<span>{$t('dashboard.stats_error')}</span>
			</div>
		{/if}

		{#if isNewUser}
			<div
				class="mb-10 overflow-hidden rounded-2xl border border-base-300/50 bg-base-100/80 shadow-sm"
			>
				<div class="card-body items-center p-8 text-center sm:p-12">
					<div class="mb-5 rounded-2xl bg-primary/10 p-6">
						<CompassRose class="h-14 w-14 text-primary" />
					</div>
					<h2 class="mb-3 text-2xl font-bold text-primary">
						{$t('dashboard.no_recent_adventures')}
					</h2>
					<p class="mb-8 max-w-md text-lg leading-relaxed text-base-content/60">
						{$t('dashboard.document_some_adventures')}
					</p>
					<div class="flex flex-col justify-center gap-4 sm:flex-row">
						<a href="/locations" class="btn btn-primary btn-lg gap-2 shadow-lg">
							<Plus class="h-5 w-5" />
							{$t('map.add_location')}
						</a>
						<a href="/worldtravel" class="btn btn-outline btn-lg gap-2">
							<FlagCheckeredVariantIcon class="h-5 w-5" />
							{$t('home.explore_world')}
						</a>
					</div>
				</div>
			</div>
		{/if}

		{#if stats}
			<!-- Bento stats -->
			<section class="mb-10">
				<div class="mb-5">
					<h2 class="text-xl font-bold text-primary sm:text-2xl">
						{$t('profile.travel_statistics')}
					</h2>
					<p class="text-sm text-base-content/55">{$t('profile.your_journey_at_a_glance')}</p>
				</div>

				<div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
					<a
						href="/worldtravel"
						class="dashboard-stat-card group relative col-span-1 overflow-hidden rounded-2xl border border-success/20 bg-base-100/80 p-5 shadow-sm md:col-span-2 xl:row-span-2"
					>
						<div class="relative flex h-full flex-col justify-between gap-6">
							<div class="flex items-start justify-between gap-4">
								<div>
									<div class="text-xs font-semibold uppercase tracking-widest text-success/70">
										{$t('profile.visited_countries')}
									</div>
									<div class="mt-2 text-5xl font-black text-success">
										{stats.visited_country_count}
									</div>
									<div class="mt-1 text-sm text-success/70">
										{stats.visited_country_count}/{stats.total_countries}
										{$t('home.of_world').toLowerCase()}
									</div>
								</div>
								<div class="rounded-2xl bg-success/15 p-4">
									<Earth class="h-10 w-10 text-success" />
								</div>
							</div>
							<div>
								<div class="mb-2 flex items-end justify-between">
									<span class="text-3xl font-bold text-success">{worldExplorationPercentage}%</span>
									<span class="text-xs text-base-content/50">{$t('home.of_world')}</span>
								</div>
								<progress
									class="progress progress-success h-3 w-full"
									value={stats.visited_country_count}
									max={Math.max(stats.total_countries, 1)}
								></progress>
							</div>
						</div>
					</a>

					<a
						href="/locations"
						class="dashboard-stat-card group rounded-2xl border border-primary/15 bg-base-100/80 p-4 shadow-sm"
					>
						<div class="flex items-center justify-between gap-3">
							<div class="min-w-0">
								<div class="text-xs font-semibold uppercase tracking-wide text-primary/70">
									{$t('dashboard.locations_visited')}
								</div>
								<div class="mt-1 text-3xl font-bold text-primary">
									{stats.visited_location_count}<span class="text-lg text-primary/50"
										>/{stats.location_count}</span
									>
								</div>
							</div>
							<div class="rounded-xl bg-primary/15 p-3">
								<MapMarkerMultiple class="h-7 w-7 text-primary" />
							</div>
						</div>
						{#if stats.location_count > 0}
							<progress
								class="progress progress-primary mt-4 h-2 w-full"
								value={stats.visited_location_count}
								max={Math.max(stats.location_count, 1)}
							></progress>
							<div class="mt-1 text-xs text-primary/60">{locationVisitedPercentage}%</div>
						{/if}
					</a>

					<a
						href="/collections"
						class="dashboard-stat-card group rounded-2xl border border-secondary/15 bg-base-100/80 p-4 shadow-sm"
					>
						<div class="flex items-center justify-between gap-3">
							<div>
								<div class="text-xs font-semibold uppercase tracking-wide text-secondary/70">
									{$t('navbar.collections')}
								</div>
								<div class="mt-1 text-3xl font-bold text-secondary">{stats.trips_count}</div>
								<div class="mt-1 text-xs text-secondary/60">{$t('profile.planned_trips')}</div>
							</div>
							<div class="rounded-xl bg-secondary/15 p-3">
								<FolderMultiple class="h-7 w-7 text-secondary" />
							</div>
						</div>
					</a>

					<a
						href="/worldtravel"
						class="dashboard-stat-card group rounded-2xl border border-info/15 bg-base-100/80 p-4 shadow-sm"
					>
						<div class="flex items-center justify-between gap-3">
							<div class="min-w-0 flex-1">
								<div class="text-xs font-semibold uppercase tracking-wide text-info/70">
									{$t('profile.visited_regions')}
								</div>
								<div class="mt-1 text-3xl font-bold text-info">{stats.visited_region_count}</div>
								<progress
									class="progress progress-info mt-3 h-1.5 w-full"
									value={stats.visited_region_count}
									max={Math.max(stats.total_regions, 1)}
								></progress>
								<div class="mt-1 text-xs text-info/60">{regionExplorationPercentage}%</div>
							</div>
							<div class="rounded-xl bg-info/15 p-3">
								<MapMarkerStarOutline class="h-7 w-7 text-info" />
							</div>
						</div>
					</a>

					<a
						href="/worldtravel"
						class="dashboard-stat-card group rounded-2xl border border-warning/15 bg-base-100/80 p-4 shadow-sm"
					>
						<div class="flex items-center justify-between gap-3">
							<div class="min-w-0 flex-1">
								<div class="text-xs font-semibold uppercase tracking-wide text-warning/70">
									{$t('profile.visited_cities')}
								</div>
								<div class="mt-1 text-3xl font-bold text-warning">{stats.visited_city_count}</div>
								<progress
									class="progress progress-warning mt-3 h-1.5 w-full"
									value={stats.visited_city_count}
									max={Math.max(stats.total_cities, 1)}
								></progress>
								<div class="mt-1 text-xs text-warning/60">{cityExplorationPercentage}%</div>
							</div>
							<div class="rounded-xl bg-warning/15 p-3">
								<CityVariantOutline class="h-7 w-7 text-warning" />
							</div>
						</div>
					</a>

					{#if stats.activities_overall.total_count > 0}
						<div
							class="dashboard-stat-card rounded-2xl border border-accent/15 bg-base-100/80 p-4 shadow-sm md:col-span-2"
						>
							<div class="flex items-center justify-between gap-3">
								<div>
									<div class="text-xs font-semibold uppercase tracking-wide text-accent/70">
										{$t('adventures.activity_statistics')}
									</div>
									<div class="mt-1 text-3xl font-bold text-accent">
										{stats.activities_overall.total_count}
									</div>
									<div class="mt-1 text-sm text-accent/70">
										{getDistance(measurementSystem, stats.activities_overall.total_distance)}
										{measurementSystem === 'imperial' ? 'mi' : 'km'} · {formatTime(
											stats.activities_overall.total_moving_time
										)}
									</div>
								</div>
								<div class="rounded-xl bg-accent/15 p-3">
									<Run class="h-7 w-7 text-accent" />
								</div>
							</div>
						</div>
					{/if}
				</div>
			</section>

			<div class="mb-10 grid grid-cols-1 gap-5 xl:grid-cols-2">
				<section class="rounded-2xl border border-base-300/50 bg-base-100/70 p-5 shadow-sm sm:p-6">
					<div class="mb-5">
						<h2 class="text-lg font-bold text-base-content">{$t('dashboard.whats_next')}</h2>
						<p class="text-sm text-base-content/55">{$t('dashboard.upcoming_trips')}</p>
					</div>

					{#if activeTrip}
						<a
							href="/collections/{activeTrip.id}"
							class="group mb-5 flex items-center gap-4 rounded-xl border border-secondary/25 bg-secondary/5 p-4 transition-colors hover:bg-secondary/10"
						>
							<div class="rounded-xl bg-secondary/20 p-3">
								<Airplane class="h-8 w-8 text-secondary" />
							</div>
							<div class="min-w-0 flex-1">
								<div class="badge badge-secondary badge-sm mb-1">{$t('dashboard.active_trip')}</div>
								<h3 class="truncate text-lg font-bold">{activeTrip.name}</h3>
								<p class="text-sm text-base-content/60">
									{activeTrip.location_count}
									{$t('locations.locations').toLowerCase()}
								</p>
							</div>
							<ChevronRight
								class="h-5 w-5 shrink-0 text-base-content/30 transition-transform group-hover:translate-x-1 group-hover:text-secondary"
							/>
						</a>
					{/if}

					{#if inviteCount > 0}
						<a
							href="/collections"
							class="alert alert-info mb-5 rounded-2xl transition-shadow hover:shadow-md"
						>
							<EmailAlert class="h-5 w-5 shrink-0" />
							<span>{$t('dashboard.pending_invites')}: {inviteCount}</span>
						</a>
					{/if}

					{#if upcomingTrips.length > 0}
						<div class="mb-6 grid grid-cols-1 gap-4">
							{#each upcomingTrips as trip (trip.id)}
								<CollectionCard type="" collection={trip} {user} readOnly />
							{/each}
						</div>
					{:else if !activeTrip}
						<div
							class="mb-6 flex flex-col items-center justify-center rounded-2xl border border-dashed border-base-300/70 bg-base-200/30 py-10"
						>
							<FolderMultiple class="mb-3 h-12 w-12 text-base-content/25" />
							<p class="px-4 text-center text-base-content/60">
								{$t('dashboard.no_upcoming_trips')}
							</p>
							<a href="/collections" class="btn btn-outline btn-sm mt-4">
								{$t('dashboard.my_collections')}
							</a>
						</div>
					{/if}

					<div class="rounded-xl border border-base-300/40 bg-base-200/20 p-4">
						<div class="mb-4 flex items-center justify-between">
							<h3 class="font-bold">{$t('calendar.upcoming_agenda')}</h3>
							<a href="/calendar" class="btn btn-ghost btn-xs gap-1">
								{$t('dashboard.view_all')}
								<ChevronRight class="h-3 w-3" />
							</a>
						</div>
						<CalendarAgenda
							events={agendaEvents}
							emptyMessage={$t('calendar.no_upcoming_events')}
						/>
					</div>
				</section>

				<section class="flex flex-col gap-5">
					{#if stats.activities_overall.total_count > 0}
						<div class="rounded-2xl border border-base-300/50 bg-base-100/70 p-5 shadow-sm sm:p-6">
							<h2 class="mb-4 text-lg font-bold">{$t('dashboard.activity_highlights')}</h2>

							<div class="grid grid-cols-2 gap-3">
								<div class="rounded-2xl border border-base-300/40 bg-base-200/40 p-4">
									<div
										class="text-[10px] font-semibold uppercase tracking-wide text-base-content/50"
									>
										{$t('adventures.total_distance')}
									</div>
									<div class="mt-1 text-2xl font-bold text-primary">
										{getDistance(measurementSystem, stats.activities_overall.total_distance)}
										<span class="text-sm font-normal"
											>{measurementSystem === 'imperial' ? 'mi' : 'km'}</span
										>
									</div>
								</div>
								<div class="rounded-2xl border border-base-300/40 bg-base-200/40 p-4">
									<div
										class="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-base-content/50"
									>
										<TimerOutline class="h-3 w-3" />
										{$t('adventures.moving_time')}
									</div>
									<div class="mt-1 text-2xl font-bold text-secondary">
										{formatTime(stats.activities_overall.total_moving_time)}
									</div>
								</div>
								<div class="rounded-2xl border border-base-300/40 bg-base-200/40 p-4">
									<div
										class="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-base-content/50"
									>
										<Mountain class="h-3 w-3" />
										{$t('adventures.elevation_gain')}
									</div>
									<div class="mt-1 text-2xl font-bold text-success">
										{getElevation(measurementSystem, stats.activities_overall.total_elevation_gain)}
										<span class="text-sm font-normal"
											>{measurementSystem === 'imperial' ? 'ft' : 'm'}</span
										>
									</div>
								</div>
								{#if stats.activities_overall.total_calories > 0}
									<div class="rounded-2xl border border-base-300/40 bg-base-200/40 p-4">
										<div
											class="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-base-content/50"
										>
											<Fire class="h-3 w-3" />
											{$t('adventures.calories')}
										</div>
										<div class="mt-1 text-2xl font-bold text-warning">
											{Math.round(stats.activities_overall.total_calories)}
										</div>
									</div>
								{/if}
							</div>

							{#if stats.activities_overall.record_holders?.max_distance}
								<div class="mt-4 rounded-2xl border border-accent/20 bg-accent/5 p-4">
									<div class="mb-1 text-xs font-semibold uppercase tracking-wide text-accent/80">
										{$t('dashboard.personal_record')}
									</div>
									<p class="text-sm leading-relaxed">
										<span class="font-bold"
											>{getRecordTitle(stats.activities_overall.record_holders.max_distance)}</span
										>
										— {getDistance(
											measurementSystem,
											stats.activities_overall.record_holders.max_distance.metric_value
										)}
										{measurementSystem === 'imperial' ? 'mi' : 'km'}
									</p>
									{#if stats.activities_overall.record_holders.max_distance.location_id}
										<a
											href="/locations/{stats.activities_overall.record_holders.max_distance
												.location_id}"
											class="mt-1 inline-block text-sm text-primary hover:underline"
										>
											{stats.activities_overall.record_holders.max_distance.location_name}
										</a>
									{/if}
								</div>
							{/if}
						</div>
					{/if}

					<div
						class="flex-1 rounded-2xl border border-base-300/50 bg-base-100/70 p-5 shadow-sm sm:p-6"
					>
						<h2 class="mb-4 text-lg font-bold">{$t('dashboard.quick_links')}</h2>

						<div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
							{#each quickLinks as link}
								<a
									href={link.href}
									class="btn btn-ghost h-auto min-h-0 flex-col gap-1.5 py-3 px-2 normal-case font-normal border border-base-300/40 bg-base-200/30"
								>
									<svelte:component this={link.icon} class="h-5 w-5 text-primary" />
									<span class="text-xs leading-tight text-center">{$t(link.labelKey)}</span>
								</a>
							{/each}
						</div>
					</div>
				</section>
			</div>
		{/if}

		<section class="rounded-2xl border border-base-300/50 bg-base-100/70 p-5 shadow-sm sm:p-6">
			<div class="mb-5 flex flex-wrap items-center justify-between gap-4">
				<div>
					<h2 class="text-lg font-bold text-primary sm:text-xl">
						{$t('dashboard.recently_updated')}
					</h2>
					<p class="text-sm text-base-content/55">{$t('home.latest_travel_experiences')}</p>
				</div>
				{#if stats && stats.location_count > 0}
					<a href="/locations" class="btn btn-ghost btn-sm gap-2">
						{$t('dashboard.view_all')}
						<span class="badge badge-primary">{stats.location_count}</span>
					</a>
				{/if}
			</div>

			{#if recentLocations.length > 0}
				<div class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
					{#each recentLocations as adventure (adventure.id)}
						<LocationCard {adventure} readOnly {user} />
					{/each}
				</div>
			{:else}
				<div class="flex flex-col items-center justify-center py-14">
					<div class="mb-6 rounded-3xl bg-base-200/60 p-6">
						<MapMarkerMultiple class="h-16 w-16 text-base-content/25" />
					</div>
					<h3 class="mb-2 text-xl font-semibold text-base-content/70">
						{$t('dashboard.no_recent_locations')}
					</h3>
					<p class="mb-6 max-w-md text-center text-base-content/50">
						{$t('dashboard.document_some_adventures')}
					</p>
					<a href="/locations" class="btn btn-primary gap-2 shadow-lg">
						<Plus class="h-5 w-5" />
						{$t('map.add_location')}
					</a>
				</div>
			{/if}
		</section>
	</div>
</div>

<style>
	.dashboard-hero {
		opacity: 0;
		transform: translateY(8px);
		transition:
			opacity 0.45s ease,
			transform 0.45s ease;
	}

	.dashboard-hero-visible {
		opacity: 1;
		transform: translateY(0);
	}

	.dashboard-shape {
		animation: dashboard-float 8s ease-in-out infinite;
	}

	.dashboard-shape-delayed {
		animation-delay: -3s;
	}

	@keyframes dashboard-float {
		0%,
		100% {
			translate: 0 0;
		}
		50% {
			translate: 0 -8px;
		}
	}

	.dashboard-trip-card {
		background: linear-gradient(135deg, hsl(var(--b1) / 0.95) 0%, hsl(var(--b2) / 0.85) 100%);
	}

	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.dashboard-stat-card {
		transition:
			transform 0.2s ease,
			box-shadow 0.2s ease;
	}

	.dashboard-stat-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 16px -4px rgba(0, 0, 0, 0.1);
	}
</style>
