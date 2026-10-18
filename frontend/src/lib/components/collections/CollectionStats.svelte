<script lang="ts">
	import type {
		Checklist,
		Collection,
		Lodging,
		Note,
		Transportation,
		Visit,
		Activity,
		User
	} from '$lib/types';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import { t } from 'svelte-i18n';
	import { BarChart, PieChart } from 'layerchart';
	// lodging icons and helpers
	import {
		LODGING_TYPES_ICONS,
		getActivityIcon,
		SPORT_TYPE_CHOICES,
		isAllDay,
		isAllDayEnd,
		allDayDatePart
	} from '$lib';
	import { dateFormatFromUser, formatDisplayDate } from '$lib/dateFormat';
	import ChartBar from '~icons/mdi/chart-bar';
	import MapMarker from '~icons/mdi/map-marker';
	import MapMarkerCheck from '~icons/mdi/map-marker-check';
	import ImageMultiple from '~icons/mdi/image-multiple';
	import Earth from '~icons/mdi/earth';
	import AccountGroup from '~icons/mdi/account-group';
	import CalendarRange from '~icons/mdi/calendar-range';
	import RoadVariant from '~icons/mdi/road-variant';
	import Run from '~icons/mdi/run';
	import NoteText from '~icons/mdi/note-text';
	import Tag from '~icons/mdi/tag';
	import Bed from '~icons/mdi/bed';

	interface Props {
		collection: Collection;
		user?: User | null;
	}

	let { collection, user = null }: Props = $props();

	const dateFormat = $derived(dateFormatFromUser(user));

	function getLodgingIcon(type: string): string {
		return (LODGING_TYPES_ICONS as Record<string, string>)[type] || '🏨';
	}

	function convertDistance(km: number): number {
		if (user?.measurement_system === 'imperial') {
			return km * 0.621371; // Convert km to miles
		}
		return km;
	}

	function convertElevation(meters: number): number {
		if (user?.measurement_system === 'imperial') {
			return meters * 3.28084; // Convert meters to feet
		}
		return meters;
	}

	function getDistanceUnit(): string {
		return user?.measurement_system === 'imperial' ? 'mi' : 'km';
	}

	function getElevationUnit(): string {
		return user?.measurement_system === 'imperial' ? 'ft' : 'm';
	}

	function hasPlacedCoordinates(latitude?: number | null, longitude?: number | null): boolean {
		const lat = Number(latitude);
		const lng = Number(longitude);
		if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
		// 0,0 is the Gulf of Guinea and gets reverse-geocoded as a country such as Ghana.
		return !(lat === 0 && lng === 0);
	}

	const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
	const distanceFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
	const compactFormatter = new Intl.NumberFormat(undefined, {
		notation: 'compact',
		maximumFractionDigits: 1
	});

	let tripStart = $derived(collection.start_date ? DateTime.fromISO(collection.start_date) : null);
	let tripEnd = $derived(collection.end_date ? DateTime.fromISO(collection.end_date) : null);

	// All-day items (visits, transportation, lodging) are stored as date-only values at
	// midnight UTC (e.g. 2025-07-07T00:00:00Z). Parsing those as a local instant shifts
	// them to the previous evening in timezones west of UTC, which pushes them out of
	// the trip window. Read all-day values by their calendar date, like the rest of the app.
	function parseItemDate(value: string): DateTime {
		return isAllDay(value) || isAllDayEnd(value)
			? DateTime.fromISO(allDayDatePart(value))
			: DateTime.fromISO(value);
	}

	function overlapsCollectionRange(
		startStr: string | null | undefined,
		endStr: string | null | undefined
	): boolean {
		if (!tripStart || !tripEnd) return true; // If no collection window, include everything
		if (!startStr) return false;

		const start = parseItemDate(startStr);
		if (!start.isValid) return false;

		const end = endStr ? parseItemDate(endStr) : start;
		if (!end.isValid) return false;

		// The trip's last day runs until the end of that day, not its midnight.
		return end >= tripStart.startOf('day') && start <= tripEnd.endOf('day');
	}

	function addRangeDays(
		startStr: string | null | undefined,
		endStr: string | null | undefined,
		target: Set<string>
	) {
		if (!startStr) return;
		const start = parseItemDate(startStr);
		const end = endStr ? parseItemDate(endStr) : start;
		if (!start.isValid || !end.isValid) return;

		let cursor = start.startOf('day');
		const finalDay = end.startOf('day');
		while (cursor <= finalDay) {
			target.add(cursor.toISODate());
			cursor = cursor.plus({ days: 1 });
		}
	}

	let tripDurationDays = $derived(
		tripStart && tripEnd ? Math.max(1, Math.floor(tripEnd.diff(tripStart, 'days').days) + 1) : null
	);

	let visitedLocations = $derived(
		(collection.locations || []).filter((loc) =>
			loc.visits?.some((visit) => overlapsCollectionRange(visit.start_date, visit.end_date))
		)
	);

	let visitsInRange = $derived(
		visitedLocations.flatMap((loc) =>
			(loc.visits || []).filter((visit) =>
				overlapsCollectionRange(visit.start_date, visit.end_date)
			)
		)
	);

	let countriesVisited = $derived(
		(() => {
			const map = new Map<string, { name: string; code: string; flag?: string }>();
			visitedLocations.forEach((loc) => {
				if (!hasPlacedCoordinates(loc.latitude, loc.longitude)) return;
				const country = loc.country;
				if (!country) return;
				const key = country.country_code || String(country.id) || country.name;
				if (!key) return;
				if (!map.has(key))
					map.set(key, {
						name: country.name,
						code: country.country_code || '',
						flag: country.flag_url || ''
					});
			});
			return Array.from(map.values());
		})()
	);

	let transportSegments = $derived(
		(collection.transportations || []).filter((segment) =>
			overlapsCollectionRange(segment.date, segment.end_date)
		)
	);

	let totalDistance = $derived(
		convertDistance(transportSegments.reduce((sum, segment) => sum + (segment.distance || 0), 0))
	);

	let lodgingStays = $derived(
		(collection.lodging || []).filter((stay) =>
			overlapsCollectionRange(stay.check_in, stay.check_out)
		)
	);

	let lodgingNights = $derived(
		lodgingStays.reduce((sum, stay) => {
			if (!stay.check_in || !stay.check_out) return sum;
			const start = parseItemDate(stay.check_in);
			const end = parseItemDate(stay.check_out);
			if (!start.isValid || !end.isValid) return sum;

			const startDay = start.startOf('day');
			const endDay = end.startOf('day');
			let diff = endDay.diff(startDay, 'days').days;

			if (!Number.isFinite(diff)) return sum;
			if (diff <= 0) diff = 1;

			return sum + diff;
		}, 0)
	);

	let notesInRange = $derived(
		(collection.notes || []).filter((note: Note) => overlapsCollectionRange(note.date, note.date))
	);

	let checklistsInRange = $derived(
		(collection.checklists || []).filter((list: Checklist) =>
			overlapsCollectionRange(list.date, list.date)
		)
	);

	let imagesInRange = $derived(
		(() => {
			let total = 0;
			visitedLocations.forEach((loc) => (total += loc.images?.length || 0));
			transportSegments.forEach((segment) => (total += segment.images?.length || 0));
			lodgingStays.forEach((stay) => (total += stay.images?.length || 0));
			return total;
		})()
	);

	let regionsVisited = $derived(
		(() => {
			const map = new Map<string, { name: string; country: string }>();
			visitedLocations.forEach((loc) => {
				if (!hasPlacedCoordinates(loc.latitude, loc.longitude)) return;
				const region = loc.region;
				if (!region) return;
				const key = String(region.id || region.name);
				if (!key) return;
				if (!map.has(key)) map.set(key, { name: region.name, country: region.country_name || '' });
			});
			return Array.from(map.values());
		})()
	);

	let citiesVisited = $derived(
		(() => {
			const map = new Map<string, { name: string; region: string }>();
			visitedLocations.forEach((loc) => {
				if (!hasPlacedCoordinates(loc.latitude, loc.longitude)) return;
				const city = loc.city;
				if (!city) return;
				const key = String(city.id || city.name);
				if (!key) return;
				if (!map.has(key)) map.set(key, { name: city.name, region: city.region_name || '' });
			});
			return Array.from(map.values());
		})()
	);

	let categoriesWithIcons = $derived(
		(() => {
			const map = new Map<string, { name: string; icon: string; count: number }>();
			visitedLocations.forEach((loc) => {
				if (!loc.category) return;
				const name = loc.category.display_name || loc.category.name;
				const icon = loc.category.icon || '📍';
				if (!name) return;
				if (!map.has(name)) {
					map.set(name, { name, icon, count: 0 });
				}
				const existing = map.get(name)!;
				existing.count++;
			});
			return Array.from(map.values()).sort((a, b) => b.count - a.count);
		})()
	);

	let activitiesInRange = $derived(
		(() => {
			const activities: Activity[] = [];
			visitsInRange.forEach((visit: Visit) => {
				if (visit.activities && visit.activities.length > 0) {
					activities.push(...visit.activities);
				}
			});
			return activities;
		})()
	);

	let totalActivityDistance = $derived(
		convertDistance(activitiesInRange.reduce((sum, act) => sum + (act.distance || 0), 0) / 1000)
	);
	let totalActivityElevation = $derived(
		convertElevation(activitiesInRange.reduce((sum, act) => sum + (act.elevation_gain || 0), 0))
	);
	let totalActivityCalories = $derived(
		activitiesInRange.reduce((sum, act) => sum + (act.calories || 0), 0)
	);

	let sportTypes = $derived(
		(() => {
			const types = new Map<string, number>();
			activitiesInRange.forEach((act) => {
				const sport = act.sport_type || 'Other';
				types.set(sport, (types.get(sport) || 0) + 1);
			});
			return Array.from(types.entries()).sort((a, b) => b[1] - a[1]);
		})()
	);

	let activeDayCount = $derived(
		(() => {
			const days = new Set<string>();
			visitsInRange.forEach((visit: Visit) => addRangeDays(visit.start_date, visit.end_date, days));
			transportSegments.forEach((segment: Transportation) =>
				addRangeDays(segment.date, segment.end_date, days)
			);
			lodgingStays.forEach((stay: Lodging) => addRangeDays(stay.check_in, stay.check_out, days));
			return days.size;
		})()
	);

	let scopeLabel = $derived.by(() => {
		const dayCount = tripDurationDays || 0;
		const dayUnit = dayCount === 1 ? $t('adventures.day') : $t('adventures.days');

		const countryCount = countriesVisited.length || 0;
		const countryUnit =
			countryCount === 1 ? $t('adventures.country') : $t('adventures.countries') || 'countries';

		const dayPart = dayCount ? `${dayCount} ${dayUnit}` : '';
		const countryPart = countryCount ? `${countryCount} ${countryUnit}` : '';

		const connector = $t('adventures.in') || 'in';
		return [dayPart, countryPart].filter(Boolean).join(` ${connector} `);
	});

	let windowLabel = $derived(
		tripStart && tripEnd
			? `${formatDisplayDate(tripStart.toISODate(), dateFormat)} - ${formatDisplayDate(tripEnd.toISODate(), dateFormat)}`
			: null
	);

	function normalizeTransportType(type?: string | null): string {
		return (type || 'other').trim().toLowerCase();
	}

	function getTransportMeta(type?: string | null) {
		const normalized = normalizeTransportType(type);

		if (
			normalized.includes('flight') ||
			normalized.includes('plane') ||
			normalized.includes('air')
		) {
			return { key: 'flight', icon: '✈️', label: 'Flights' };
		}
		if (normalized.includes('train') || normalized.includes('rail')) {
			return { key: 'train', icon: '🚆', label: 'Trains' };
		}
		if (normalized.includes('bus')) {
			return { key: 'bus', icon: '🚌', label: 'Bus' };
		}
		if (
			normalized.includes('boat') ||
			normalized.includes('ferry') ||
			normalized.includes('ship')
		) {
			return { key: 'boat', icon: '🚢', label: 'Boat' };
		}
		if (normalized.includes('walk')) {
			return { key: 'walk', icon: '🚶', label: 'Walking' };
		}
		if (normalized.includes('bike') || normalized.includes('cycle')) {
			return { key: 'bike', icon: '🚴', label: 'Cycling' };
		}
		if (normalized.includes('drive') || normalized.includes('car')) {
			return { key: 'car', icon: '🚗', label: 'Car' };
		}

		return {
			key: normalized || 'other',
			icon: '🧭',
			label: capitalize(type) || 'Other'
		};
	}

	function capitalize(text?: string | null) {
		if (!text) return '';
		const s = String(text);
		return s.charAt(0).toUpperCase() + s.slice(1);
	}

	function getSportLabel(key: string): string {
		const found = (SPORT_TYPE_CHOICES as Array<any>).find((a) => a.key === key);
		if (found) return found.label;
		return String(key).replace(/([a-z])([A-Z])/g, '$1 $2');
	}

	let distanceByTransportType = $derived(
		(() => {
			const types = new Map<
				string,
				{
					icon: string;
					label: string;
					distance: number;
				}
			>();

			transportSegments.forEach((segment) => {
				const meta = getTransportMeta(segment.type);
				const distance = convertDistance(segment.distance || 0);
				const existing = types.get(meta.key);
				if (existing) {
					existing.distance += distance;
				} else {
					types.set(meta.key, {
						icon: meta.icon,
						label: meta.label,
						distance
					});
				}
			});

			return Array.from(types.values()).sort((a, b) => b.distance - a.distance);
		})()
	);

	let averageLocationRating = $derived(
		(() => {
			const rated = visitedLocations.filter(
				(loc) => loc.rating !== null && loc.rating !== undefined
			);
			if (rated.length === 0) return 0;
			return rated.reduce((sum, loc) => sum + (loc.rating || 0), 0) / rated.length;
		})()
	);

	let checklistStats = $derived(
		(() => {
			let totalItems = 0;
			let checkedItems = 0;
			checklistsInRange.forEach((list) => {
				if (list.items) {
					totalItems += list.items.length;
					checkedItems += list.items.filter((item) => item.is_checked).length;
				}
			});
			return {
				total: totalItems,
				checked: checkedItems,
				percentage: totalItems > 0 ? Math.round((checkedItems / totalItems) * 100) : 0
			};
		})()
	);

	let lodgingTypeBreakdown = $derived(
		(() => {
			const types = new Map<string, number>();
			lodgingStays.forEach((stay) => {
				const type = stay.type || 'Other';
				types.set(type, (types.get(type) || 0) + 1);
			});
			return Array.from(types.entries()).sort((a, b) => b[1] - a[1]);
		})()
	);

	function coversDay(day: DateTime, startStr?: string | null, endStr?: string | null) {
		if (!startStr) return false;
		const start = parseItemDate(startStr).startOf('day');
		const end = (endStr ? parseItemDate(endStr) : parseItemDate(startStr)).startOf('day');
		if (!start.isValid || !end.isValid) return false;
		return day >= start && day <= end;
	}

	let plannedLocations = $derived(
		(collection.locations || []).filter(
			(loc) => !visitedLocations.some((visited) => visited.id === loc.id)
		)
	);

	let dayActivity = $derived.by(() => {
		if (!tripStart || !tripEnd) return [] as { label: string; visits: number; stays: number }[];
		const start = tripStart.startOf('day');
		const end = tripEnd.startOf('day');
		const span = Math.floor(end.diff(start, 'days').days) + 1;
		if (span < 1 || span > 60) return [];
		const rows: { label: string; visits: number; stays: number }[] = [];
		for (let i = 0; i < span; i++) {
			const day = start.plus({ days: i });
			rows.push({
				label: String(i + 1),
				visits: visitsInRange.filter((visit) => coversDay(day, visit.start_date, visit.end_date))
					.length,
				stays: lodgingStays.filter((stay) => coversDay(day, stay.check_in, stay.check_out)).length
			});
		}
		return rows;
	});

	let dayActivityHasValues = $derived(dayActivity.some((row) => row.visits > 0 || row.stays > 0));

	let itemMix = $derived(
		[
			{
				key: 'locations',
				label: $t('locations.locations'),
				value: collection.locations?.length ?? 0
			},
			{ key: 'lodging', label: $t('adventures.lodging'), value: collection.lodging?.length ?? 0 },
			{
				key: 'transport',
				label: $t('adventures.transportation'),
				value: collection.transportations?.length ?? 0
			},
			{ key: 'notes', label: $t('adventures.notes'), value: collection.notes?.length ?? 0 },
			{
				key: 'checklists',
				label: $t('adventures.checklists'),
				value: collection.checklists?.length ?? 0
			}
		].filter((row) => row.value > 0)
	);

	const chartColors = [
		'var(--color-primary)',
		'var(--color-secondary)',
		'var(--color-accent)',
		'var(--color-info)',
		'var(--color-success)',
		'var(--color-warning)'
	];

	let totalAttachments = $derived(
		(() => {
			let total = 0;
			visitedLocations.forEach((loc) => (total += loc.attachments?.length || 0));
			transportSegments.forEach((segment) => (total += segment.attachments?.length || 0));
			lodgingStays.forEach((stay) => (total += stay.attachments?.length || 0));
			return total;
		})()
	);
</script>

<div class="flex w-full flex-col gap-3 pb-6">
	<section class="card bg-base-200 shadow-xl">
		<div class="card-body gap-4 p-4 sm:p-5">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div class="flex min-w-0 items-center gap-3">
					<ChartBar class="h-5 w-5 shrink-0 text-primary" />
					<div class="min-w-0">
						<h2 class="text-lg font-bold">{$t('collections.statistics')}</h2>
						<p class="truncate text-sm text-base-content/70">
							{windowLabel || $t('adventures.folder_view')}
						</p>
					</div>
				</div>
				<div class="flex flex-wrap items-center gap-2">
					{#each countriesVisited.slice(0, 4) as country (country.code || country.name)}
						{#if country.flag}
							<img src={country.flag} alt={country.name} class="h-4 w-6 rounded-sm" />
						{/if}
					{/each}
					{#if scopeLabel}
						<span class="badge badge-outline badge-sm">{scopeLabel}</span>
					{/if}
				</div>
			</div>

			<div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
				<div class="rounded-xl bg-base-100 p-3">
					<div class="flex items-center gap-2 text-xs font-medium text-base-content/60">
						<MapMarker class="h-4 w-4 text-primary" />
						{$t('locations.locations')}
					</div>
					<p class="mt-2 text-2xl font-bold tabular-nums">{visitedLocations.length}</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('adventures.locations_visited')}</p>
				</div>
				<div class="rounded-xl bg-base-100 p-3">
					<div class="flex items-center gap-2 text-xs font-medium text-base-content/60">
						<MapMarkerCheck class="h-4 w-4 text-primary" />
						{$t('adventures.planned')}
					</div>
					<p class="mt-2 text-2xl font-bold tabular-nums">{plannedLocations.length}</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('locations.locations')}</p>
				</div>
				<div class="rounded-xl bg-base-100 p-3">
					<div class="flex items-center gap-2 text-xs font-medium text-base-content/60">
						<ImageMultiple class="h-4 w-4 text-primary" />
						{$t('adventures.photos')}
					</div>
					<p class="mt-2 text-2xl font-bold tabular-nums">
						{compactFormatter.format(imagesInRange)}
					</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('adventures.images_captured')}</p>
				</div>
				<div class="rounded-xl bg-base-100 p-3">
					<div class="flex items-center gap-2 text-xs font-medium text-base-content/60">
						<Earth class="h-4 w-4 text-primary" />
						{$t('adventures.countries')}
					</div>
					<p class="mt-2 text-2xl font-bold tabular-nums">{countriesVisited.length}</p>
					<p class="mt-1 text-xs text-base-content/60">
						{regionsVisited.length}
						{$t('adventures.regions')}
					</p>
				</div>
				<div class="rounded-xl bg-base-100 p-3">
					<div class="flex items-center gap-2 text-xs font-medium text-base-content/60">
						<Bed class="h-4 w-4 text-primary" />
						{$t('adventures.nights')}
					</div>
					<p class="mt-2 text-2xl font-bold tabular-nums">{lodgingNights}</p>
					<p class="mt-1 text-xs text-base-content/60">
						{lodgingStays.length}
						{$t('adventures.stays')}
					</p>
				</div>
				<div class="rounded-xl bg-base-100 p-3">
					<div class="flex items-center gap-2 text-xs font-medium text-base-content/60">
						<AccountGroup class="h-4 w-4 text-primary" />
						{$t('adventures.travelers')}
					</div>
					<p class="mt-2 text-2xl font-bold tabular-nums">
						{collection.collaborators?.length || 0}
					</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('adventures.on_this_trip')}</p>
				</div>
			</div>
		</div>
	</section>

	{#if dayActivityHasValues || itemMix.length > 1}
		<div class="grid grid-cols-1 gap-3 lg:grid-cols-3">
			{#if dayActivityHasValues}
				<section class="card bg-base-200 shadow-xl lg:col-span-2">
					<div class="card-body gap-3 p-4 sm:p-5">
						<div class="flex items-center gap-3">
							<CalendarRange class="h-5 w-5 shrink-0 text-primary" />
							<h3 class="text-lg font-bold">{$t('adventures.trip_timeline')}</h3>
						</div>
						<div class="h-56">
							<BarChart
								data={dayActivity}
								x="label"
								seriesLayout="stack"
								series={[
									{
										key: 'visits',
										value: 'visits',
										label: $t('adventures.visits'),
										color: 'var(--color-primary)'
									},
									{
										key: 'stays',
										value: 'stays',
										label: $t('adventures.stays'),
										color: 'var(--color-secondary)'
									}
								]}
								bandPadding={0.28}
								legend
								class="h-full"
								padding={{ top: 8, right: 8, bottom: 24, left: 28 }}
							/>
						</div>
					</div>
				</section>
			{/if}
			{#if itemMix.length > 1}
				<section class="card bg-base-200 shadow-xl">
					<div class="card-body gap-3 p-4 sm:p-5">
						<div class="flex items-center gap-3">
							<ChartBar class="h-5 w-5 shrink-0 text-primary" />
							<h3 class="text-lg font-bold">{$t('collections.all_items')}</h3>
						</div>
						<div class="h-56">
							<PieChart
								data={itemMix}
								innerRadius={0.62}
								padAngle={0.02}
								cRange={chartColors}
								legend
								class="h-full"
							/>
						</div>
					</div>
				</section>
			{/if}
		</div>
	{/if}

	<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
		{#if countriesVisited.length || regionsVisited.length || citiesVisited.length}
			<section class="card bg-base-200 shadow-xl">
				<div class="card-body gap-4 p-4 sm:p-5">
					<div class="flex items-center gap-3">
						<Earth class="h-5 w-5 shrink-0 text-primary" />
						<h3 class="text-lg font-bold">{$t('adventures.geographic_breakdown')}</h3>
					</div>

					{#if countriesVisited.length}
						<div>
							<p class="mb-2 text-xs font-medium text-base-content/60">
								{$t('adventures.countries')} ({countriesVisited.length})
							</p>
							<div class="flex flex-wrap gap-2">
								{#each countriesVisited as country (country.code || country.name)}
									<span class="badge badge-outline gap-2">
										{#if country.flag}
											<img src={country.flag} alt="" class="h-3 w-5 rounded-sm" />
										{/if}
										{country.name}
									</span>
								{/each}
							</div>
						</div>
					{/if}

					{#if regionsVisited.length}
						<div>
							<p class="mb-2 text-xs font-medium text-base-content/60">
								{$t('adventures.regions')} ({regionsVisited.length})
							</p>
							<div class="flex flex-wrap gap-2">
								{#each regionsVisited.slice(0, 15) as region (`${region.name}-${region.country}`)}
									<span
										class="inline-flex items-center rounded-full bg-base-300 px-3 py-1 text-sm font-medium"
									>
										{region.name}{#if region.country}, {region.country}{/if}
									</span>
								{/each}
								{#if regionsVisited.length > 15}
									<span
										class="inline-flex items-center rounded-full bg-base-300 px-3 py-1 text-sm font-medium"
									>
										+{regionsVisited.length - 15}
									</span>
								{/if}
							</div>
						</div>
					{/if}

					{#if citiesVisited.length}
						<div>
							<p class="mb-2 text-xs font-medium text-base-content/60">
								{$t('adventures.cities')} ({citiesVisited.length})
							</p>
							<div class="flex flex-wrap gap-2">
								{#each citiesVisited.slice(0, 20) as city (`${city.name}-${city.region}`)}
									<span
										class="inline-flex items-center rounded-full bg-base-300 px-3 py-1 text-sm font-medium"
									>
										{city.name}
									</span>
								{/each}
								{#if citiesVisited.length > 20}
									<span
										class="inline-flex items-center rounded-full bg-base-300 px-3 py-1 text-sm font-medium"
									>
										+{citiesVisited.length - 20}
									</span>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</section>
		{/if}

		<section
			class="card bg-base-200 shadow-xl {countriesVisited.length ||
			regionsVisited.length ||
			citiesVisited.length
				? ''
				: 'lg:col-span-2'}"
		>
			<div class="card-body gap-4 p-4 sm:p-5">
				<div class="flex items-center gap-3">
					<CalendarRange class="h-5 w-5 shrink-0 text-primary" />
					<h3 class="text-lg font-bold">{$t('adventures.trip_timeline')}</h3>
				</div>
				<div class="grid grid-cols-2 gap-3">
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.total_days')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">{tripDurationDays ?? '—'}</p>
						<p class="mt-1 text-xs text-base-content/60">{$t('adventures.trip_window')}</p>
					</div>
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.active_days')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">{activeDayCount}</p>
						<p class="mt-1 text-xs text-base-content/60">{$t('adventures.with_activities')}</p>
					</div>
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.visits')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">{visitsInRange.length}</p>
						<p class="mt-1 text-xs text-base-content/60">{$t('adventures.total_visits')}</p>
					</div>
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.nights')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">{lodgingNights}</p>
						<p class="mt-1 text-xs text-base-content/60">
							{lodgingStays.length}
							{$t('adventures.stays')}
						</p>
					</div>
				</div>
			</div>
		</section>
	</div>

	{#if totalDistance > 0}
		<section class="card bg-base-200 shadow-xl">
			<div class="card-body gap-4 p-4 sm:p-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex items-center gap-3">
						<RoadVariant class="h-5 w-5 shrink-0 text-primary" />
						<h3 class="text-lg font-bold">{$t('adventures.distance_traveled')}</h3>
					</div>
					<p class="text-2xl font-bold tabular-nums">
						{numberFormatter.format(totalDistance)}
						<span class="text-sm font-medium text-base-content/60">{getDistanceUnit()}</span>
					</p>
				</div>

				{#if distanceByTransportType.length > 0}
					<div style:height="{Math.max(120, distanceByTransportType.length * 44)}px">
						<BarChart
							data={distanceByTransportType}
							x="distance"
							y="label"
							orientation="horizontal"
							series={[{ key: 'distance', value: 'distance', color: 'var(--color-primary)' }]}
							bandPadding={0.35}
							legend={false}
							padding={{ top: 4, right: 16, bottom: 20, left: 88 }}
						/>
					</div>
				{/if}
			</div>
		</section>
	{/if}

	{#if activitiesInRange.length > 0}
		<section class="card bg-base-200 shadow-xl">
			<div class="card-body gap-4 p-4 sm:p-5">
				<div class="flex items-center gap-3">
					<Run class="h-5 w-5 shrink-0 text-primary" />
					<h3 class="text-lg font-bold">{$t('adventures.physical_activities')}</h3>
				</div>

				<div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60 capitalize">
							{$t('adventures.activities_text')}
						</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">{activitiesInRange.length}</p>
						<p class="mt-1 text-xs text-base-content/60">{$t('adventures.total_recorded')}</p>
					</div>
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.distance')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">
							{distanceFormatter.format(totalActivityDistance)}
						</p>
						<p class="mt-1 text-xs text-base-content/60">{getDistanceUnit()}</p>
					</div>
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.elevation')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">
							{numberFormatter.format(totalActivityElevation)}
						</p>
						<p class="mt-1 text-xs text-base-content/60">{getElevationUnit()}</p>
					</div>
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.calories')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">
							{compactFormatter.format(totalActivityCalories)}
						</p>
						<p class="mt-1 text-xs text-base-content/60">{$t('adventures.burned')}</p>
					</div>
				</div>

				{#if sportTypes.length > 0}
					<div class="flex flex-wrap gap-2">
						{#each sportTypes as [sport, count] (sport)}
							<span class="badge badge-outline gap-2">
								{getActivityIcon(sport)}
								{getSportLabel(sport)}
								<span class="badge badge-ghost badge-xs">{count}</span>
							</span>
						{/each}
					</div>
				{/if}
			</div>
		</section>
	{/if}

	<section class="card bg-base-200 shadow-xl">
		<div class="card-body gap-4 p-4 sm:p-5">
			<div class="flex items-center gap-3">
				<NoteText class="h-5 w-5 shrink-0 text-primary" />
				<h3 class="text-lg font-bold">{$t('adventures.content_media')}</h3>
			</div>

			<div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
				<div class="rounded-xl bg-base-100 p-4">
					<p class="text-xs font-medium text-base-content/60">{$t('adventures.photos')}</p>
					<p class="mt-1 text-2xl font-bold tabular-nums">
						{numberFormatter.format(imagesInRange)}
					</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('adventures.images')}</p>
				</div>
				<div class="rounded-xl bg-base-100 p-4">
					<p class="text-xs font-medium text-base-content/60">{$t('adventures.notes')}</p>
					<p class="mt-1 text-2xl font-bold tabular-nums">{notesInRange.length}</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('adventures.written')}</p>
				</div>
				<div class="rounded-xl bg-base-100 p-4">
					<p class="text-xs font-medium text-base-content/60">{$t('adventures.checklists')}</p>
					<p class="mt-1 text-2xl font-bold tabular-nums">{checklistsInRange.length}</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('adventures.lists')}</p>
				</div>
				<div class="rounded-xl bg-base-100 p-4">
					<p class="text-xs font-medium text-base-content/60">{$t('adventures.transportation')}</p>
					<p class="mt-1 text-2xl font-bold tabular-nums">{transportSegments.length}</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('adventures.segments')}</p>
				</div>
				<div class="rounded-xl bg-base-100 p-4">
					<p class="text-xs font-medium text-base-content/60">{$t('adventures.lodging')}</p>
					<p class="mt-1 text-2xl font-bold tabular-nums">{lodgingStays.length}</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('adventures.places')}</p>
				</div>
				<div class="rounded-xl bg-base-100 p-4">
					<p class="text-xs font-medium text-base-content/60">{$t('locations.locations')}</p>
					<p class="mt-1 text-2xl font-bold tabular-nums">{visitedLocations.length}</p>
					<p class="mt-1 text-xs text-base-content/60">{$t('adventures.visited')}</p>
				</div>
				{#if totalAttachments > 0}
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.attachments')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">{totalAttachments}</p>
						<p class="mt-1 text-xs text-base-content/60">{$t('adventures.files')}</p>
					</div>
				{/if}
				{#if averageLocationRating > 0}
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.avg_rating')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">{averageLocationRating.toFixed(1)}</p>
						<p class="mt-1 text-xs text-base-content/60">{$t('adventures.of_locations')}</p>
					</div>
				{/if}
				{#if checklistStats.total > 0}
					<div class="rounded-xl bg-base-100 p-4">
						<p class="text-xs font-medium text-base-content/60">{$t('adventures.tasks_done')}</p>
						<p class="mt-1 text-2xl font-bold tabular-nums">{checklistStats.percentage}%</p>
						<p class="mt-1 text-xs text-base-content/60">
							{checklistStats.checked}/{checklistStats.total}
							{$t('adventures.items')}
						</p>
					</div>
				{/if}
			</div>
		</div>
	</section>

	{#if categoriesWithIcons.length > 0 || lodgingTypeBreakdown.length > 1}
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			{#if categoriesWithIcons.length > 0}
				<section class="card bg-base-200 shadow-xl">
					<div class="card-body gap-4 p-4 sm:p-5">
						<div class="flex items-center gap-3">
							<Tag class="h-5 w-5 shrink-0 text-primary" />
							<h3 class="text-lg font-bold">{$t('adventures.categories')}</h3>
						</div>
						<div style:height="{Math.max(140, categoriesWithIcons.length * 36)}px">
							<BarChart
								data={categoriesWithIcons}
								x="count"
								y="name"
								orientation="horizontal"
								series={[{ key: 'count', value: 'count', color: 'var(--color-primary)' }]}
								bandPadding={0.35}
								legend={false}
								padding={{ top: 4, right: 16, bottom: 20, left: 108 }}
							/>
						</div>
					</div>
				</section>
			{/if}

			{#if lodgingTypeBreakdown.length > 1}
				<section class="card bg-base-200 shadow-xl">
					<div class="card-body gap-4 p-4 sm:p-5">
						<div class="flex items-center gap-3">
							<Bed class="h-5 w-5 shrink-0 text-primary" />
							<h3 class="text-lg font-bold">{$t('adventures.lodging_types')}</h3>
						</div>
						<div class="flex flex-wrap gap-2">
							{#each lodgingTypeBreakdown as [type, count] (type)}
								<span class="badge badge-outline gap-2">
									{getLodgingIcon(type)}
									{capitalize(type)}
									<span class="badge badge-ghost badge-xs">{count}</span>
								</span>
							{/each}
						</div>
					</div>
				</section>
			{/if}
		</div>
	{/if}
</div>
