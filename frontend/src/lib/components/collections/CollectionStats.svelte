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
	import { get } from 'svelte/store';
	import { getActivityIcon, SPORT_TYPE_CHOICES } from '$lib';
	import { getLodgingIcon } from '$lib/stores/entityTypes';

	export let collection: Collection;
	export let user: User | null = null;

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

	function getDistanceUnitLong(): string {
		return user?.measurement_system === 'imperial' ? 'miles' : 'kilometers';
	}

	function getElevationUnit(): string {
		return user?.measurement_system === 'imperial' ? 'ft' : 'm';
	}

	function getElevationUnitLong(): string {
		return user?.measurement_system === 'imperial' ? 'feet' : 'meters';
	}

	const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
	const distanceFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
	const compactFormatter = new Intl.NumberFormat(undefined, {
		notation: 'compact',
		maximumFractionDigits: 1
	});

	const tripStart = collection.start_date ? DateTime.fromISO(collection.start_date) : null;
	const tripEnd = collection.end_date ? DateTime.fromISO(collection.end_date) : null;

	function overlapsCollectionRange(
		startStr: string | null | undefined,
		endStr: string | null | undefined
	): boolean {
		if (!tripStart || !tripEnd) return true; // If no collection window, include everything
		if (!startStr) return false;

		const start = DateTime.fromISO(startStr);
		if (!start.isValid) return false;

		const end = endStr ? DateTime.fromISO(endStr) : start;
		if (!end.isValid) return false;

		return end >= tripStart && start <= tripEnd;
	}

	function addRangeDays(
		startStr: string | null | undefined,
		endStr: string | null | undefined,
		target: Set<string>
	) {
		if (!startStr) return;
		const start = DateTime.fromISO(startStr);
		const end = endStr ? DateTime.fromISO(endStr) : start;
		if (!start.isValid || !end.isValid) return;

		let cursor = start.startOf('day');
		const finalDay = end.startOf('day');
		while (cursor <= finalDay) {
			target.add(cursor.toISODate());
			cursor = cursor.plus({ days: 1 });
		}
	}

	$: tripDurationDays =
		tripStart && tripEnd ? Math.max(1, Math.floor(tripEnd.diff(tripStart, 'days').days) + 1) : null;

	$: visitedLocations = (collection.locations || []).filter((loc) =>
		loc.visits?.some((visit) => overlapsCollectionRange(visit.start_date, visit.end_date))
	);

	$: visitsInRange = visitedLocations.flatMap((loc) =>
		(loc.visits || []).filter((visit) => overlapsCollectionRange(visit.start_date, visit.end_date))
	);

	$: countriesVisited = (() => {
		const map = new Map<string, { name: string; code: string; flag?: string }>();
		visitedLocations.forEach((loc) => {
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
	})();

	$: transportSegments = (collection.transportations || []).filter((segment) =>
		overlapsCollectionRange(segment.date, segment.end_date)
	);

	$: totalDistance = convertDistance(
		transportSegments.reduce((sum, segment) => sum + (segment.distance || 0), 0)
	);

	$: lodgingStays = (collection.lodging || []).filter((stay) =>
		overlapsCollectionRange(stay.check_in, stay.check_out)
	);

	$: lodgingNights = lodgingStays.reduce((sum, stay) => {
		if (!stay.check_in || !stay.check_out) return sum;
		const start = DateTime.fromISO(stay.check_in);
		const end = DateTime.fromISO(stay.check_out);
		if (!start.isValid || !end.isValid) return sum;

		const startDay = start.startOf('day');
		const endDay = end.startOf('day');
		let diff = endDay.diff(startDay, 'days').days;

		if (!Number.isFinite(diff)) return sum;
		if (diff <= 0) diff = 1;

		return sum + diff;
	}, 0);

	$: notesInRange = (collection.notes || []).filter((note: Note) =>
		overlapsCollectionRange(note.date, note.date)
	);

	$: checklistsInRange = (collection.checklists || []).filter((list: Checklist) =>
		overlapsCollectionRange(list.date, list.date)
	);

	$: imagesInRange = (() => {
		let total = 0;
		visitedLocations.forEach((loc) => (total += loc.images?.length || 0));
		transportSegments.forEach((segment) => (total += segment.images?.length || 0));
		lodgingStays.forEach((stay) => (total += stay.images?.length || 0));
		return total;
	})();

	$: regionsVisited = (() => {
		const map = new Map<string, { name: string; country: string }>();
		visitedLocations.forEach((loc) => {
			const region = loc.region;
			if (!region) return;
			const key = String(region.id || region.name);
			if (!key) return;
			if (!map.has(key)) map.set(key, { name: region.name, country: region.country_name || '' });
		});
		return Array.from(map.values());
	})();

	$: citiesVisited = (() => {
		const map = new Map<string, { name: string; region: string }>();
		visitedLocations.forEach((loc) => {
			const city = loc.city;
			if (!city) return;
			const key = String(city.id || city.name);
			if (!key) return;
			if (!map.has(key)) map.set(key, { name: city.name, region: city.region_name || '' });
		});
		return Array.from(map.values());
	})();

	$: categoriesWithIcons = (() => {
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
	})();

	$: activitiesInRange = (() => {
		const activities: Activity[] = [];
		visitsInRange.forEach((visit: Visit) => {
			if (visit.activities && visit.activities.length > 0) {
				activities.push(...visit.activities);
			}
		});
		return activities;
	})();

	$: totalActivityDistance = convertDistance(
		activitiesInRange.reduce((sum, act) => sum + (act.distance || 0), 0) / 1000
	);
	$: totalActivityElevation = convertElevation(
		activitiesInRange.reduce((sum, act) => sum + (act.elevation_gain || 0), 0)
	);
	$: totalActivityCalories = activitiesInRange.reduce((sum, act) => sum + (act.calories || 0), 0);

	$: sportTypes = (() => {
		const types = new Map<string, number>();
		activitiesInRange.forEach((act) => {
			const sport = act.sport_type || 'Other';
			types.set(sport, (types.get(sport) || 0) + 1);
		});
		return Array.from(types.entries()).sort((a, b) => b[1] - a[1]);
	})();

	$: activeDayCount = (() => {
		const days = new Set<string>();
		visitsInRange.forEach((visit: Visit) => addRangeDays(visit.start_date, visit.end_date, days));
		transportSegments.forEach((segment: Transportation) =>
			addRangeDays(segment.date, segment.end_date, days)
		);
		lodgingStays.forEach((stay: Lodging) => addRangeDays(stay.check_in, stay.check_out, days));
		return days.size;
	})();

	$: scopeLabel = (() => {
		const $t = get(t);
		const dayCount = tripDurationDays || 0;
		const dayUnit = dayCount === 1 ? $t('adventures.day') : $t('adventures.days');

		const countryCount = countriesVisited.length || 0;
		const countryUnit =
			countryCount === 1 ? $t('adventures.country') : $t('adventures.countries') || 'countries';

		const dayPart = dayCount ? `${dayCount} ${dayUnit}` : '';
		const countryPart = countryCount ? `${countryCount} ${countryUnit}` : '';

		const connector = $t('adventures.in') || 'in';
		return [dayPart, countryPart].filter(Boolean).join(` ${connector} `);
	})();

	$: windowLabel =
		tripStart && tripEnd
			? `${tripStart.toLocaleString(DateTime.DATE_MED)} - ${tripEnd.toLocaleString(DateTime.DATE_MED)}`
			: null;

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

	function getTransportIcon(type?: string | null) {
		return getTransportMeta(type).icon;
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

	$: distanceByTransportType = (() => {
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
	})();

	$: averageLocationRating = (() => {
		const rated = visitedLocations.filter((loc) => loc.rating !== null && loc.rating !== undefined);
		if (rated.length === 0) return 0;
		return rated.reduce((sum, loc) => sum + (loc.rating || 0), 0) / rated.length;
	})();

	$: checklistStats = (() => {
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
	})();

	$: lodgingTypeBreakdown = (() => {
		const types = new Map<string, number>();
		lodgingStays.forEach((stay) => {
			const type = stay.type || 'Other';
			types.set(type, (types.get(type) || 0) + 1);
		});
		return Array.from(types.entries()).sort((a, b) => b[1] - a[1]);
	})();

	$: totalAttachments = (() => {
		let total = 0;
		visitedLocations.forEach((loc) => (total += loc.attachments?.length || 0));
		transportSegments.forEach((segment) => (total += segment.attachments?.length || 0));
		lodgingStays.forEach((stay) => (total += stay.attachments?.length || 0));
		return total;
	})();
</script>

<div class="space-y-6">
	<!-- Hero Overview Card -->
	<div
		class="card bg-gradient-to-br from-primary/10 to-secondary/10 shadow-xl border border-primary/20"
	>
		<div class="card-body space-y-4">
			<div class="flex flex-col gap-3">
				<div class="flex flex-wrap items-center gap-2">
					{#if countriesVisited.length}
						{#each countriesVisited.slice(0, 3) as country}
							{#if country.flag}
								<img src={country.flag} alt={country.name} class="w-8 h-6 rounded shadow-sm" />
							{/if}
						{/each}
					{/if}
					<h2 class="text-3xl font-bold">{collection.name}</h2>
				</div>

				{#if windowLabel}
					<div class="flex flex-wrap items-center gap-2 text-sm">
						<span class="badge badge-lg badge-ghost">📅 {windowLabel}</span>
						{#if scopeLabel}
							<span class="badge badge-lg badge-primary">{scopeLabel}</span>
						{/if}
					</div>
				{:else}
					<p class="text-sm opacity-70">📁 {$t('adventures.folder_view')}</p>
				{/if}
			</div>

			<!-- Key Stats Row -->
			<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
				<div class="stat bg-base-100 rounded-lg shadow p-4 border border-info/20">
					<div class="stat-figure text-info text-3xl">📍</div>
					<div class="stat-title text-xs">{$t('adventures.footprints')}</div>
					<div class="stat-value text-info text-2xl">{visitedLocations.length}</div>
					<div class="stat-desc">{$t('adventures.locations_visited')}</div>
				</div>

				<div class="stat bg-base-100 rounded-lg shadow p-4 border border-success/20">
					<div class="stat-figure text-success text-3xl">📸</div>
					<div class="stat-title text-xs">{$t('adventures.photos')}</div>
					<div class="stat-value text-success text-2xl">
						{compactFormatter.format(imagesInRange)}
					</div>
					<div class="stat-desc">{$t('adventures.images_captured')}</div>
				</div>

				<div class="stat bg-base-100 rounded-lg shadow p-4 border border-warning/20">
					<div class="stat-figure text-warning text-3xl">🗺️</div>
					<div class="stat-title text-xs">{$t('adventures.countries')}</div>
					<div class="stat-value text-warning text-2xl">{countriesVisited.length}</div>
					<div class="stat-desc">
						{regionsVisited.length}
						{$t('adventures.regions')}, {citiesVisited.length}
						{$t('adventures.cities')}
					</div>
				</div>

				<div class="stat bg-base-100 rounded-lg shadow p-4 border border-accent/20">
					<div class="stat-figure text-accent text-3xl">👥</div>
					<div class="stat-title text-xs">{$t('adventures.travelers')}</div>
					<div class="stat-value text-accent text-2xl">
						{collection.collaborators?.length || 0}
					</div>
					<div class="stat-desc">{$t('adventures.on_this_trip')}</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Geographic Breakdown -->
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body space-y-4">
			<h3 class="card-title text-xl flex items-center gap-2">
				<span class="text-2xl">🌎</span>
				{$t('adventures.geographic_breakdown')}
			</h3>

			{#if countriesVisited.length}
				<div>
					<h4 class="font-semibold mb-2 flex items-center gap-2">
						<span>🏳️</span>
						{$t('adventures.countries')} ({countriesVisited.length})
					</h4>
					<div class="flex flex-wrap gap-2">
						{#each countriesVisited as country}
							<div class="flex items-center gap-2 badge badge-lg badge-primary badge-outline p-3">
								{#if country.flag}
									<img src={country.flag} alt={country.name} class="w-6 h-4 rounded" />
								{/if}
								<span class="font-medium">{country.name}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if regionsVisited.length}
				<div>
					<h4 class="font-semibold mb-2 flex items-center gap-2">
						<span>🗺️</span>
						{$t('adventures.regions')} ({regionsVisited.length})
					</h4>
					<div class="flex flex-wrap gap-2">
						{#each regionsVisited.slice(0, 15) as region}
							<span class="badge badge-lg badge-secondary badge-outline">
								{region.name}{#if region.country}, {region.country}{/if}
							</span>
						{/each}
						{#if regionsVisited.length > 15}
							<span class="badge badge-lg badge-ghost">+{regionsVisited.length - 15} more</span>
						{/if}
					</div>
				</div>
			{/if}

			{#if citiesVisited.length}
				<div>
					<h4 class="font-semibold mb-2 flex items-center gap-2">
						<span>🏙️</span>
						{$t('adventures.cities')} ({citiesVisited.length})
					</h4>
					<div class="flex flex-wrap gap-2">
						{#each citiesVisited.slice(0, 20) as city}
							<span class="badge badge-accent badge-outline">
								{city.name}
							</span>
						{/each}
						{#if citiesVisited.length > 20}
							<span class="badge badge-ghost">+{citiesVisited.length - 20} more</span>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!-- Trip Timeline & Duration -->
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body">
			<h3 class="card-title text-xl flex items-center gap-2">
				<span class="text-2xl">📆</span>
				{$t('adventures.trip_timeline')}
			</h3>
			<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
				<div class="stat bg-primary/10 rounded-lg p-4">
					<div class="stat-title text-xs">{$t('adventures.total_days')}</div>
					<div class="stat-value text-primary text-2xl">{tripDurationDays ?? 'N/A'}</div>
					<div class="stat-desc">{$t('adventures.trip_window')}</div>
				</div>
				<div class="stat bg-success/10 rounded-lg p-4">
					<div class="stat-title text-xs">{$t('adventures.active_days')}</div>
					<div class="stat-value text-success text-2xl">{activeDayCount}</div>
					<div class="stat-desc">{$t('adventures.with_activities')}</div>
				</div>
				<div class="stat bg-info/10 rounded-lg p-4">
					<div class="stat-title text-xs">{$t('adventures.visits')}</div>
					<div class="stat-value text-info text-2xl">{visitsInRange.length}</div>
					<div class="stat-desc">{$t('adventures.total_visits')}</div>
				</div>
				<div class="stat bg-warning/10 rounded-lg p-4">
					<div class="stat-title text-xs">{$t('adventures.nights')}</div>
					<div class="stat-value text-warning text-2xl">{lodgingNights}</div>
					<div class="stat-desc">{lodgingStays.length} {$t('adventures.stays')}</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Distance Breakdown -->
	{#if totalDistance > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<h3 class="card-title text-xl flex items-center gap-2 mb-2">
					<span class="text-2xl">🛣️</span>
					{$t('adventures.distance_traveled')}
				</h3>

				<div
					class="flex items-center justify-center p-6 bg-gradient-to-r from-primary/20 to-secondary/20 rounded-lg mb-4"
				>
					<div class="text-center">
						<div class="text-5xl font-bold text-primary">
							{numberFormatter.format(totalDistance)}
						</div>
						<div class="text-sm opacity-70 mt-1">
							{getDistanceUnitLong()}
							{$t('adventures.traveled')}
						</div>
					</div>
				</div>

				{#if distanceByTransportType.length > 0}
					<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
						{#each distanceByTransportType as type}
							<div class="stat bg-base-300 rounded-lg p-3">
								<div class="stat-figure text-3xl">{type.icon}</div>
								<div class="stat-title text-xs">{type.label}</div>
								<div class="stat-value text-lg">
									{distanceFormatter.format(type.distance)}
								</div>
								<div class="stat-desc text-xs">{getDistanceUnitLong()}</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/if}
	<!-- Activities Stats -->
	{#if activitiesInRange.length > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<h3 class="card-title text-xl flex items-center gap-2 mb-2">
					<span class="text-2xl">🏃</span>
					{$t('adventures.physical_activities')}
				</h3>

				<div class="stats stats-vertical sm:stats-horizontal shadow mb-4">
					<div class="stat bg-accent/10">
						<div class="stat-figure text-accent text-3xl">🎯</div>
						<div class="stat-title">{$t('adventures.activities')}</div>
						<div class="stat-value text-accent">{activitiesInRange.length}</div>
						<div class="stat-desc">{$t('adventures.total_recorded')}</div>
					</div>
					<div class="stat bg-info/10">
						<div class="stat-figure text-info text-3xl">📏</div>
						<div class="stat-title">{$t('adventures.distance')}</div>
						<div class="stat-value text-info">
							{distanceFormatter.format(totalActivityDistance)}
						</div>
						<div class="stat-desc">{getDistanceUnitLong()}</div>
					</div>
					<div class="stat bg-success/10">
						<div class="stat-figure text-success text-3xl">⛰️</div>
						<div class="stat-title">{$t('adventures.elevation')}</div>
						<div class="stat-value text-success">
							{numberFormatter.format(totalActivityElevation)}
						</div>
						<div class="stat-desc">{getElevationUnitLong()} {$t('adventures.gained')}</div>
					</div>
					<div class="stat bg-warning/10">
						<div class="stat-figure text-warning text-3xl">🔥</div>
						<div class="stat-title">{$t('adventures.calories')}</div>
						<div class="stat-value text-warning">
							{compactFormatter.format(totalActivityCalories)}
						</div>
						<div class="stat-desc">{$t('adventures.burned')}</div>
					</div>
				</div>

				{#if sportTypes.length > 0}
					<div>
						<h4 class="font-semibold mb-2">Sport Types</h4>
						<div class="flex flex-wrap gap-2">
							{#each sportTypes as [sport, count]}
								<div class="badge badge-lg badge-primary badge-outline p-3 flex items-center gap-2">
									<span class="text-lg">{getActivityIcon(sport)}</span>
									<span class="font-medium">{getSportLabel(sport)}</span>
									<span class="badge badge-xs badge-primary ml-2">{count}</span>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Content & Media -->
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body">
			<h3 class="card-title text-xl flex items-center gap-2 mb-2">
				<span class="text-2xl">📱</span>
				{$t('adventures.content_media')}
			</h3>

			<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
				<div
					class="stat bg-gradient-to-br from-primary/20 to-primary/5 rounded-lg p-4 border border-primary/30"
				>
					<div class="stat-figure text-primary text-3xl">📸</div>
					<div class="stat-title text-xs">{$t('adventures.photos')}</div>
					<div class="stat-value text-primary text-2xl">
						{numberFormatter.format(imagesInRange)}
					</div>
					<div class="stat-desc">{$t('adventures.images')}</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-secondary/20 to-secondary/5 rounded-lg p-4 border border-secondary/30"
				>
					<div class="stat-figure text-secondary text-3xl">📝</div>
					<div class="stat-title text-xs">{$t('adventures.notes')}</div>
					<div class="stat-value text-secondary text-2xl">{notesInRange.length}</div>
					<div class="stat-desc">{$t('adventures.written')}</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-accent/20 to-accent/5 rounded-lg p-4 border border-accent/30"
				>
					<div class="stat-figure text-accent text-3xl">✅</div>
					<div class="stat-title text-xs">{$t('adventures.checklists')}</div>
					<div class="stat-value text-accent text-2xl">{checklistsInRange.length}</div>
					<div class="stat-desc">{$t('adventures.lists')}</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-info/20 to-info/5 rounded-lg p-4 border border-info/30"
				>
					<div class="stat-figure text-info text-3xl">🚆</div>
					<div class="stat-title text-xs">{$t('adventures.transportation')}</div>
					<div class="stat-value text-info text-2xl">{transportSegments.length}</div>
					<div class="stat-desc">{$t('adventures.segments')}</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-success/20 to-success/5 rounded-lg p-4 border border-success/30"
				>
					<div class="stat-figure text-success text-3xl">🏨</div>
					<div class="stat-title text-xs">{$t('adventures.lodging')}</div>
					<div class="stat-value text-success text-2xl">{lodgingStays.length}</div>
					<div class="stat-desc">{$t('adventures.places')}</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-warning/20 to-warning/5 rounded-lg p-4 border border-warning/30"
				>
					<div class="stat-figure text-warning text-3xl">📍</div>
					<div class="stat-title text-xs">{$t('locations.locations')}</div>
					<div class="stat-value text-warning text-2xl">{visitedLocations.length}</div>
					<div class="stat-desc">{$t('adventures.visited')}</div>
				</div>

				{#if totalAttachments > 0}
					<div
						class="stat bg-gradient-to-br from-error/20 to-error/5 rounded-lg p-4 border border-error/30"
					>
						<div class="stat-figure text-error text-3xl">📎</div>
						<div class="stat-title text-xs">{$t('adventures.attachments')}</div>
						<div class="stat-value text-error text-2xl">{totalAttachments}</div>
						<div class="stat-desc">{$t('adventures.files')}</div>
					</div>
				{/if}
			</div>

			<!-- Additional Stats Row -->
			{#if averageLocationRating > 0 || checklistStats.total > 0 || lodgingTypeBreakdown.length > 0}
				<div class="divider">{$t('adventures.more_details')}</div>
				<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
					{#if averageLocationRating > 0}
						<div class="stat bg-base-300 rounded-lg p-4">
							<div class="stat-figure text-2xl">⭐</div>
							<div class="stat-title text-xs">{$t('adventures.avg_rating')}</div>
							<div class="stat-value text-lg">{averageLocationRating.toFixed(1)}</div>
							<div class="stat-desc text-xs">{$t('adventures.of_locations')}</div>
						</div>
					{/if}

					{#if checklistStats.total > 0}
						<div class="stat bg-base-300 rounded-lg p-4">
							<div class="stat-figure text-2xl">✓</div>
							<div class="stat-title text-xs">{$t('adventures.tasks_done')}</div>
							<div class="stat-value text-lg">{checklistStats.percentage}%</div>
							<div class="stat-desc text-xs">
								{checklistStats.checked}/{checklistStats.total}
								{$t('adventures.items')}
							</div>
						</div>
					{/if}

					{#if lodgingTypeBreakdown.length > 0}
						<div class="stat bg-base-300 rounded-lg p-4">
							<div class="stat-figure text-2xl">🛏️</div>
							<div class="stat-title text-xs">{$t('adventures.lodging_types')}</div>
							<div class="stat-value text-lg">{lodgingTypeBreakdown.length}</div>
							<div class="stat-desc text-xs truncate">
								{getLodgingIcon(lodgingTypeBreakdown[0][0])}
								{capitalize(lodgingTypeBreakdown[0][0])}
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>

	<!-- Categories -->
	{#if categoriesWithIcons.length > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<h3 class="card-title text-xl flex items-center gap-2">
					<span class="text-2xl">🏷️</span>
					{$t('adventures.categories')}
				</h3>
				<div class="flex flex-wrap gap-2">
					{#each categoriesWithIcons as category}
						<div class="badge badge-lg badge-primary badge-outline p-3 flex items-center gap-2">
							<span class="text-lg">{category.icon}</span>
							<span class="font-medium">{category.name}</span>
							<span class="badge badge-xs badge-primary">{category.count}</span>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}

	<!-- Lodging Types Breakdown -->
	{#if lodgingTypeBreakdown.length > 1}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<h3 class="card-title text-xl flex items-center gap-2">
					<span class="text-2xl">🏨</span>
					Lodging Types
				</h3>
				<div class="flex flex-wrap gap-2">
					{#each lodgingTypeBreakdown as [type, count]}
						<div class="badge badge-lg badge-success badge-outline p-3 flex items-center gap-2">
							<span class="text-lg">{getLodgingIcon(type)}</span>
							<span class="font-medium">{capitalize(type)}</span>
							<span class="badge badge-xs badge-success ml-2">{count}</span>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>
