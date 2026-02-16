<script lang="ts">
	import FullMap, { type FullMapFeatureCollection } from '$lib/components/map/FullMap.svelte';
	import { GeoJSON, LineLayer, Marker } from 'svelte-maplibre';
	import { goto } from '$app/navigation';
	import { getActivityColor } from '$lib';
	import { getTransportationIcon, getLodgingIcon } from '$lib/stores/entityTypes';
	import SearchIcon from '~icons/mdi/magnify';
	import FilterIcon from '~icons/mdi/filter-variant';
	import ChevronDown from '~icons/mdi/chevron-down';
	import Plus from '~icons/mdi/plus';
	import PinIcon from '~icons/mdi/map-marker';
	import Clear from '~icons/mdi/close';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';
	import { t } from 'svelte-i18n';
	import { get as getStore } from 'svelte/store';
	import type { Collection, Location, User } from '$lib/types';

	export let collection: Collection;
	export let user: User | null = null;
	// Allow disabling/enabling clustering for markers
	export let clusterEnabled: boolean = false;
	export let clusterOptions: any = { radius: 300, maxZoom: 8, minPoints: 2 };

	type MarkerType = 'location' | 'lodging' | 'transportation';
	type VisitStatus = 'visited' | 'planned';

	type MarkerProperties = {
		id: string;
		name: string;
		visitStatus?: VisitStatus;
		categoryIcon?: string;
		categoryName?: string | null;
		type: MarkerType;
		date?: string | null;
		transportRole?: 'origin' | 'destination';
	};

	type MarkerFeature = {
		type: 'Feature';
		geometry: { type: 'Point'; coordinates: [number, number] };
		properties: MarkerProperties;
	};

	type MarkerFeatureCollection = {
		type: 'FeatureCollection';
		features: MarkerFeature[];
	};

	// Filter state
	let showFilters = false;
	let showLocations = true;
	let showLodging = true;
	let showTransportation = true;
	let showVisited = true;
	let showPlanned = true;
	let showLines = true;
	let startDateFilter = '';
	let endDateFilter = '';
	let selectedCategories: Set<string> = new Set();
	let searchQuery = '';

	// Map state for zoom control
	let mapZoom = 8;
	let mapCenterCoords: [number, number] = [0, 0];

	// Creation state
	let createModalOpen = false;
	let initialLatLng: { lat: number; lng: number } | null = null;
	let newMarker: { lngLat: { lng: number; lat: number } } | null = null;
	let newLatitude: number | null = null;
	let newLongitude: number | null = null;

	const defaultClusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 };
	$: resolvedClusterOptions = clusterOptions || defaultClusterOptions;

	// Helper functions
	function parseNumber(value: unknown): number | null {
		if (value === null || value === undefined) return null;
		const num = typeof value === 'number' ? value : Number(value);
		return Number.isFinite(num) ? num : null;
	}

	function parseDate(value: string | null | undefined): number | null {
		if (!value) return null;
		const ts = Date.parse(value);
		return Number.isFinite(ts) ? ts : null;
	}

	function formatShortDate(value: string | null | undefined): string {
		if (!value) return '';
		const parsed = parseDate(value);
		if (!parsed) return '';
		return new Date(parsed).toISOString().split('T')[0];
	}

	// Normalize collection start/end dates to YYYY-MM-DD for cross-browser compatibility (Firefox is strict)
	$: collectionStartDateISO = formatShortDate(collection?.start_date || null) || undefined;
	$: collectionEndDateISO = formatShortDate(collection?.end_date || null) || undefined;

	type FilterConfig = {
		showLocations: boolean;
		showLodging: boolean;
		showTransportation: boolean;
		showVisited: boolean;
		showPlanned: boolean;
		startDate: string;
		endDate: string;
		categories: Set<string>;
	};

	function isWithinDateRange(
		value: string | null | undefined,
		startDate: string,
		endDate: string
	): boolean {
		const hasRange = Boolean(startDate || endDate);
		if (!hasRange) return true;
		const ts = parseDate(value ?? null);
		if (!ts) return false;
		const startTs = startDate ? Date.parse(startDate) : -Infinity;
		const endTs = endDate ? Date.parse(endDate) + 24 * 60 * 60 * 1000 - 1 : Infinity;
		return ts >= startTs && ts <= endTs;
	}

	function getLocationPrimaryDate(loc: any): string | null {
		if (Array.isArray(loc?.visits) && loc.visits.length) {
			const dates = loc.visits
				.map((v: any) => v?.start_date || v?.end_date)
				.filter((d: string | null | undefined) => Boolean(d))
				.sort();
			return dates[0] || null;
		}
		return null;
	}

	function getTransportationDate(t: any): string | null {
		return t?.date || t?.start_date || t?.end_date || null;
	}


	function locationToFeature(loc: any): MarkerFeature | null {
		const lat = parseNumber(loc?.latitude);
		const lon = parseNumber(loc?.longitude);
		if (lat === null || lon === null) return null;
		return {
			type: 'Feature',
			geometry: { type: 'Point', coordinates: [lon, lat] },
			properties: {
				id: String(loc.id),
				name: loc.name,
				visitStatus: loc.is_visited ? 'visited' : 'planned',
				categoryIcon: loc.category?.icon || '📍',
				categoryName: loc.category?.display_name || null,
				type: 'location',
				date: getLocationPrimaryDate(loc)
			}
		};
	}

	function lodgingToFeature(l: any): MarkerFeature | null {
		const lat = parseNumber(l?.latitude);
		const lon = parseNumber(l?.longitude);
		if (lat === null || lon === null) return null;
		return {
			type: 'Feature',
			geometry: { type: 'Point', coordinates: [lon, lat] },
			properties: {
				id: String(l.id),
				name: l.name || 'Lodging',
				categoryIcon: getLodgingIcon(l.type),
				categoryName: l.type || 'Lodging',
				type: 'lodging',
				date: l.check_in || l.check_out || null
			}
		};
	}

	function transportationToFeatures(t: any): MarkerFeature[] {
		const features: MarkerFeature[] = [];
		const icon = getTransportationIcon(t?.type || t?.name);
		const date = getTransportationDate(t);
		const baseName = t?.name || t?.type || 'Transportation';

		const pushPoint = (lat: number | null, lon: number | null, role: 'origin' | 'destination') => {
			if (lat === null || lon === null) return;
			features.push({
				type: 'Feature',
				geometry: { type: 'Point', coordinates: [lon, lat] },
				properties: {
					id: `${t.id}:${role}`,
					name: `${baseName} ${role === 'origin' ? 'Start' : 'End'}`,
					categoryIcon: icon,
					categoryName: t?.type || 'Transportation',
					type: 'transportation',
					date,
					transportRole: role
				}
			});
		};

		pushPoint(parseNumber(t?.origin_latitude), parseNumber(t?.origin_longitude), 'origin');
		pushPoint(
			parseNumber(t?.destination_latitude),
			parseNumber(t?.destination_longitude),
			'destination'
		);

		return features;
	}

	function getActivityDate(activity: any, visit?: any): string | null {
		return (
			activity?.start_date ||
			activity?.start_date_local ||
			visit?.start_date ||
			visit?.end_date ||
			null
		);
	}

	// Merge attachments/activity geojson into a single feature collection
	function collectLinesGeojson(
		coll: Collection,
		filters: { startDate: string; endDate: string }
	): { type: 'FeatureCollection'; features: any[] } | null {
		if (!coll) return null;
		const features: any[] = [];

		// Locations: attachments and visits -> activities
		for (const loc of coll.locations || []) {
			if (Array.isArray(loc.attachments)) {
				for (const a of loc.attachments) {
					if (!a || !a.geojson) continue;
					if (a.geojson.type === 'FeatureCollection' && Array.isArray(a.geojson.features)) {
						features.push(...a.geojson.features);
					} else if (a.geojson.type === 'Feature') {
						features.push(a.geojson);
					}
				}
			}

			if (Array.isArray(loc.visits)) {
				for (const visit of loc.visits) {
					if (!visit.activities) continue;
					for (const activity of visit.activities) {
						const activityDate = getActivityDate(activity, visit);
						if (!isWithinDateRange(activityDate, filters.startDate, filters.endDate)) continue;
						if (activity && activity.geojson) {
							// normalize features and inject activity-type color
							const color = getActivityColor(activity.sport_type || (activity as any).type || '');
							if (
								activity.geojson.type === 'FeatureCollection' &&
								Array.isArray(activity.geojson.features)
							) {
								for (const f of activity.geojson.features) {
									if (f && typeof f === 'object') {
										f.properties = f.properties || {};
										f.properties._color = color;
										f.properties.activity_type =
											activity.sport_type || (activity as any).type || null;
										features.push(f);
									}
								}
							} else if (activity.geojson.type === 'Feature') {
								const f = activity.geojson as any;
								f.properties = f.properties || {};
								f.properties._color = color;
								f.properties.activity_type = activity.sport_type || (activity as any).type || null;
								features.push(f);
							}
						}
					}
				}
			}
		}

		// Transportations: attachments
		for (const t of coll.transportations || []) {
			if (!t || !Array.isArray(t.attachments)) continue;
			for (const a of t.attachments) {
				if (!a || !a.geojson) continue;
				if (a.geojson.type === 'FeatureCollection' && Array.isArray(a.geojson.features)) {
					for (const f of a.geojson.features) {
						if (f && typeof f === 'object') {
							f.properties = f.properties || {};
							// default transport attachments to a neutral blue color
							f.properties._color = f.properties._color || '#60a5fa';
							features.push(f);
						}
					}
				} else if (a.geojson.type === 'Feature') {
					const f = a.geojson as any;
					f.properties = f.properties || {};
					f.properties._color = f.properties._color || '#60a5fa';
					features.push(f);
				}
			}
		}

		if (features.length === 0) return null;
		return { type: 'FeatureCollection', features };
	}

	// Build features and apply filters
	$: categoryOptions = Array.from(
		new Set(
			(collection?.locations || [])
				.map((loc: any) => loc?.category?.display_name)
				.filter((name: string | null | undefined) => Boolean(name))
		)
	).sort();

	$: locationFeatures = (collection?.locations || [])
		.map(locationToFeature)
		.filter(Boolean) as MarkerFeature[];

	$: lodgingFeatures = (collection?.lodging || [])
		.map(lodgingToFeature)
		.filter(Boolean) as MarkerFeature[];

	$: transportationFeatures = (collection?.transportations || [])
		.flatMap(transportationToFeatures)
		.filter(Boolean) as MarkerFeature[];

	$: allFeatures = [...locationFeatures, ...lodgingFeatures, ...transportationFeatures];
	$: linesGeoJson = collectLinesGeojson(collection, {
		startDate: startDateFilter || collection?.start_date || '',
		endDate: endDateFilter || collection?.end_date || ''
	});

	function matchesFilters(
		feature: MarkerFeature,
		filters: FilterConfig & { search: string }
	): boolean {
		const props = feature.properties;

		// Search filter
		if (filters.search) {
			const query = filters.search.toLowerCase();
			const nameMatch = props.name?.toLowerCase().includes(query);
			const categoryMatch = props.categoryName?.toLowerCase().includes(query);
			if (!nameMatch && !categoryMatch) return false;
		}

		if (props.type === 'location') {
			if (!filters.showLocations) return false;
			if (props.visitStatus === 'visited' && !filters.showVisited) return false;
			if (props.visitStatus === 'planned' && !filters.showPlanned) return false;
			if (filters.categories.size) {
				if (!props.categoryName || !filters.categories.has(props.categoryName)) return false;
			}
		} else if (props.type === 'lodging') {
			if (!filters.showLodging) return false;
		} else if (props.type === 'transportation') {
			if (!filters.showTransportation) return false;
		}

		if (!isWithinDateRange(props.date ?? null, filters.startDate, filters.endDate)) return false;
		return true;
	}

	$: filteredFeatures = allFeatures.filter((feature) =>
		matchesFilters(feature, {
			showLocations,
			showLodging,
			showTransportation,
			showVisited,
			showPlanned,
			startDate: startDateFilter,
			endDate: endDateFilter,
			categories: selectedCategories,
			search: searchQuery.trim()
		})
	);

	// Auto-zoom when search results change
	$: if (searchQuery.trim() && filteredFeatures.length > 0) {
		zoomToFilteredFeatures();
	}

	$: markerGeoJson = {
		type: 'FeatureCollection',
		features: filteredFeatures
	} as MarkerFeatureCollection;

	// Stats
	$: visiblePinCount = filteredFeatures.length;
	$: totalPinCount = allFeatures.length;
	$: totalLocations = locationFeatures.length;
	$: visitedCount = locationFeatures.filter((f) => f.properties.visitStatus === 'visited').length;
	$: plannedCount = locationFeatures.filter((f) => f.properties.visitStatus === 'planned').length;
	$: filteredVisitedCount = filteredFeatures.filter(
		(f) => f.properties.type === 'location' && f.properties.visitStatus === 'visited'
	).length;
	$: filteredPlannedCount = filteredFeatures.filter(
		(f) => f.properties.type === 'location' && f.properties.visitStatus === 'planned'
	).length;
	$: hasActiveCategoryFilter = selectedCategories.size > 0;
	$: hasActiveDateFilter = Boolean(startDateFilter || endDateFilter);
	$: hasActiveSearchFilter = Boolean(searchQuery.trim());
	$: filtersPristine =
		showLocations &&
		showLodging &&
		showTransportation &&
		showVisited &&
		showPlanned &&
		showLines &&
		!hasActiveCategoryFilter &&
		!hasActiveDateFilter &&
		!hasActiveSearchFilter;

	function zoomToFilteredFeatures() {
		if (filteredFeatures.length === 0) return;

		const coords = filteredFeatures.map((f) => f.geometry.coordinates);
		const lngs = coords.map((c) => c[0]);
		const lats = coords.map((c) => c[1]);

		const minLng = Math.min(...lngs);
		const maxLng = Math.max(...lngs);
		const minLat = Math.min(...lats);
		const maxLat = Math.max(...lats);

		if (filteredFeatures.length === 1) {
			// Single marker - center on it with a nice zoom level
			mapCenterCoords = [lngs[0], lats[0]];
			mapZoom = 12;
		} else {
			// Multiple markers - fit bounds with padding
			const centerLng = (minLng + maxLng) / 2;
			const centerLat = (minLat + maxLat) / 2;
			mapCenterCoords = [centerLng, centerLat];

			// Calculate appropriate zoom level based on bounds
			const lngDiff = maxLng - minLng;
			const latDiff = maxLat - minLat;
			const maxDiff = Math.max(lngDiff, latDiff);

			if (maxDiff > 50) mapZoom = 3;
			else if (maxDiff > 20) mapZoom = 4;
			else if (maxDiff > 10) mapZoom = 5;
			else if (maxDiff > 5) mapZoom = 6;
			else if (maxDiff > 2) mapZoom = 7;
			else if (maxDiff > 1) mapZoom = 8;
			else if (maxDiff > 0.5) mapZoom = 9;
			else mapZoom = 10;
		}
	}
	$: mapKey = `${visiblePinCount}-${startDateFilter}-${endDateFilter}-${showLocations}-${showLodging}-${showTransportation}-${showVisited}-${showPlanned}-${showLines}-${Array.from(
		selectedCategories
	)
		.sort()
		.join('|')}`;
	$: mapCenter =
		mapCenterCoords[0] !== 0 || mapCenterCoords[1] !== 0
			? mapCenterCoords
			: markerGeoJson.features.length
				? markerGeoJson.features[0].geometry.coordinates
				: ([0, 0] as [number, number]);

	function handleMapClick(e: CustomEvent<{ lngLat: { lng: number; lat: number } }>) {
		newMarker = { lngLat: e.detail.lngLat };
		newLongitude = e.detail.lngLat.lng;
		newLatitude = e.detail.lngLat.lat;
	}

	function openCreateModal() {
		initialLatLng = newMarker ? { lat: newMarker.lngLat.lat, lng: newMarker.lngLat.lng } : null;
		createModalOpen = true;
	}

	function clearNewMarker() {
		newMarker = null;
		newLatitude = null;
		newLongitude = null;
	}

	function upsertLocation(newLocation: Location) {
		const existingLocations = collection?.locations || [];
		const idx = existingLocations.findIndex((loc) => loc.id === newLocation.id);
		const nextLocations =
			idx === -1
				? [...existingLocations, newLocation]
				: existingLocations.map((loc, i) => (i === idx ? { ...loc, ...newLocation } : loc));

		collection = { ...collection, locations: nextLocations };
	}

	function handleLocationCreated(event: CustomEvent<Location>) {
		upsertLocation(event.detail);

		const lat = parseNumber(event.detail.latitude);
		const lon = parseNumber(event.detail.longitude);
		if (lat !== null && lon !== null) {
			mapCenterCoords = [lon, lat];
			mapZoom = 12;
		}

		createModalOpen = false;
		clearNewMarker();
	}

	function handleLocationSaved(event: CustomEvent<Location>) {
		upsertLocation(event.detail);

		const lat = parseNumber(event.detail.latitude);
		const lon = parseNumber(event.detail.longitude);
		if (lat !== null && lon !== null) {
			mapCenterCoords = [lon, lat];
			mapZoom = 12;
		}

		createModalOpen = false;
		clearNewMarker();
	}

	function toggleCategory(name: string) {
		const next = new Set(selectedCategories);
		if (next.has(name)) {
			next.delete(name);
		} else {
			next.add(name);
		}
		selectedCategories = next;
	}

	function resetFilters() {
		showLocations = true;
		showLodging = true;
		showTransportation = true;
		showVisited = true;
		showPlanned = true;
		showLines = true;
		startDateFilter = '';
		endDateFilter = '';
		selectedCategories = new Set();
		searchQuery = '';
	}

	function getMarkerColorClass(props: MarkerProperties) {
		if (props.type === 'lodging') return 'bg-gradient-to-br from-purple-400 to-purple-600';
		if (props.type === 'transportation') return 'bg-gradient-to-br from-amber-400 to-amber-600';
		if (props.visitStatus === 'visited') return 'bg-gradient-to-br from-emerald-400 to-emerald-600';
		if (props.visitStatus === 'planned') return 'bg-gradient-to-br from-blue-400 to-blue-600';
		return 'bg-gray-200';
	}

	function getTypeLabel(props: MarkerProperties) {
		const $t = getStore(t);
		if (props.type === 'lodging') return $t('adventures.lodging');
		if (props.type === 'transportation') {
			return props.transportRole === 'origin'
				? $t('adventures.transport_start')
				: props.transportRole === 'destination'
					? $t('adventures.transport_end')
					: $t('adventures.transportation');
		}
		return props.visitStatus === 'visited' ? $t('adventures.visited') : $t('adventures.planned');
	}

	function canNavigate(props: MarkerProperties) {
		return true;
	}

	function getNavigationUrl(props: MarkerProperties): string {
		if (props.type === 'location') {
			return `/locations/${props.id}`;
		} else if (props.type === 'lodging') {
			return `/lodging/${props.id}`;
		} else if (props.type === 'transportation') {
			// Extract the base ID (remove the :origin or :destination suffix)
			const baseId = props.id.split(':')[0];
			return `/transportations/${baseId}`;
		}
		return '#';
	}
</script>

<!-- Add to Collection CTA (compact) -->
<div class="card bg-base-100 shadow-sm mb-3 border border-base-200">
	<div class="card-body py-3 px-4 gap-2">
		<div class="flex items-center justify-between gap-3">
			<div class="flex items-center gap-2 min-w-0">
				<span
					class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 text-primary"
				>
					<Plus class="w-4 h-4" />
				</span>
				<div class="min-w-0">
					<p class="text-sm font-semibold leading-tight truncate">
						{$t('adventures.add_to_collection')}
					</p>
					<p class="text-xs text-base-content/60 leading-tight truncate">
						{$t('adventures.click_map_add_marker')}
					</p>
				</div>
			</div>
			<div class="flex items-center gap-2">
				<button type="button" class="btn btn-primary btn-xs" on:click={openCreateModal}>
					<Plus class="w-4 h-4" />
					{$t('adventures.add')}
				</button>
				{#if newMarker}
					<button type="button" class="btn btn-ghost btn-xs" on:click={clearNewMarker}>
						<Clear class="w-4 h-4" />
						{$t('adventures.clear')}
					</button>
				{/if}
			</div>
		</div>

		{#if newMarker}
			<div
				class="alert alert-info alert-sm flex flex-col sm:flex-row sm:items-center gap-2 py-2 px-3"
			>
				<div class="flex items-center gap-2 text-xs sm:text-sm">
					<PinIcon class="w-4 h-4" />
					<span class="truncate">
						{newLatitude?.toFixed(4)}, {newLongitude?.toFixed(4)}
					</span>
				</div>
				<div class="flex gap-2 sm:ml-auto">
					<button
						type="button"
						class="btn btn-primary btn-xxs sm:btn-xs"
						on:click={openCreateModal}
					>
						<Plus class="w-3 h-3 sm:w-4 sm:h-4" />
						{$t('adventures.add_here')}
					</button>
					<button type="button" class="btn btn-ghost btn-xxs sm:btn-xs" on:click={clearNewMarker}>
						<Clear class="w-3 h-3 sm:w-4 sm:h-4" />
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- Filter Header -->
<div class="card bg-base-100 shadow-lg mb-4">
	<div class="card-body p-4">
		<!-- Toggle filter visibility -->
		<div class="flex items-center justify-between gap-4">
			<div class="flex items-center gap-2 min-w-0 flex-1">
				<span
					class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 text-primary shrink-0"
				>
					<FilterIcon class="w-4 h-4" />
				</span>
				<button
					type="button"
					class="btn btn-sm btn-ghost justify-between items-center gap-3 flex-1 min-w-0"
					on:click={() => (showFilters = !showFilters)}
				>
					<span class="font-medium leading-tight"
						>{showFilters ? $t('adventures.hide_filters') : $t('adventures.show_filters')}</span
					>
					<ChevronDown
						class="w-4 h-4 shrink-0 transition-transform {showFilters ? 'rotate-180' : ''}"
					/>
				</button>
			</div>

			<div class="flex items-center gap-2">
				<div class="badge badge-ghost badge-sm">
					{visiblePinCount}/{totalPinCount}
					{$t('adventures.pins')}
				</div>
				{#if !filtersPristine}
					<button type="button" class="btn btn-xs btn-ghost" on:click={resetFilters}>
						{$t('adventures.reset_filters')}
					</button>
				{/if}
			</div>
		</div>

		<!-- Expanded Filter UI -->
		{#if showFilters}
			<div class="divider my-2"></div>
			<div class="space-y-4">
				<!-- Search Bar -->
				<label class="input input-bordered input-sm flex items-center gap-2">
					<SearchIcon class="h-4 w-4 opacity-70" />
					<input
						type="text"
						class="grow"
						placeholder={$t('map.search_locations')}
						bind:value={searchQuery}
					/>
					{#if searchQuery}
						<button
							type="button"
							class="btn btn-ghost btn-xs btn-circle"
							on:click={() => (searchQuery = '')}
							aria-label={$t('adventures.clear_search')}
						>
							✕
						</button>
					{/if}
				</label>

				<!-- Visit Status -->
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
					<div class="flex items-center gap-3 rounded-box border border-base-300 p-3">
						<div
							class="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 grid place-items-center text-base-100"
						>
							✓
						</div>
						<div class="flex flex-col">
							<span class="text-xs uppercase text-base-content/60">{$t('adventures.visited')}</span>
							<span class="font-semibold text-sm">{filteredVisitedCount}</span>
						</div>
						<label class="label cursor-pointer gap-2 p-0 ml-auto">
							<input type="checkbox" bind:checked={showVisited} class="toggle toggle-sm" />
						</label>
					</div>

					<div class="flex items-center gap-3 rounded-box border border-base-300 p-3">
						<div
							class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 grid place-items-center text-base-100"
						>
							○
						</div>
						<div class="flex flex-col">
							<span class="text-xs uppercase text-base-content/60">{$t('adventures.planned')}</span>
							<span class="font-semibold text-sm">{filteredPlannedCount}</span>
						</div>
						<label class="label cursor-pointer gap-2 p-0 ml-auto">
							<input type="checkbox" bind:checked={showPlanned} class="toggle toggle-sm" />
						</label>
					</div>
				</div>

				<!-- Pin Types -->
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
					<div class="flex items-center gap-3 rounded-box border border-base-300 p-3">
						<div
							class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 grid place-items-center text-base-100"
						>
							📍
						</div>
						<div class="flex flex-col">
							<span class="text-xs uppercase text-base-content/60">{$t('locations.locations')}</span
							>
							<span class="font-semibold text-sm">{locationFeatures.length}</span>
						</div>
						<label class="label cursor-pointer gap-2 p-0 ml-auto">
							<input
								type="checkbox"
								bind:checked={showLocations}
								class="toggle toggle-sm toggle-primary"
							/>
						</label>
					</div>

					{#if lodgingFeatures.length}
						<div class="flex items-center gap-3 rounded-box border border-base-300 p-3">
							<div
								class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-purple-600 grid place-items-center text-base-100"
							>
								🏨
							</div>
							<div class="flex flex-col">
								<span class="text-xs uppercase text-base-content/60"
									>{$t('adventures.lodging')}</span
								>
								<span class="font-semibold text-sm">{lodgingFeatures.length}</span>
							</div>
							<label class="label cursor-pointer gap-2 p-0 ml-auto">
								<input
									type="checkbox"
									bind:checked={showLodging}
									class="toggle toggle-sm toggle-secondary"
								/>
							</label>
						</div>
					{/if}

					{#if transportationFeatures.length}
						<div class="flex items-center gap-3 rounded-box border border-base-300 p-3">
							<div
								class="w-10 h-10 rounded-full bg-gradient-to-br from-amber-400 to-amber-600 grid place-items-center text-base-100"
							>
								✈️
							</div>
							<div class="flex flex-col">
								<span class="text-xs uppercase text-base-content/60"
									>{$t('adventures.transportation')}</span
								>
								<span class="font-semibold text-sm">{transportationFeatures.length / 2}</span>
							</div>
							<label class="label cursor-pointer gap-2 p-0 ml-auto">
								<input
									type="checkbox"
									bind:checked={showTransportation}
									class="toggle toggle-sm toggle-accent"
								/>
							</label>
						</div>
					{/if}
				</div>

				<!-- Category Filter -->
				{#if categoryOptions.length}
					<div class="space-y-2">
						<div class="flex items-center justify-between">
							<span class="text-sm font-medium">{$t('adventures.categories')}</span>
							{#if hasActiveCategoryFilter}
								<button
									type="button"
									class="btn btn-ghost btn-xs"
									on:click={() => (selectedCategories = new Set())}
								>
									{$t('adventures.clear')}
								</button>
							{/if}
						</div>
						<div class="flex flex-wrap gap-2">
							{#each categoryOptions as category}
								<button
									type="button"
									class="badge {selectedCategories.has(category)
										? 'badge-primary'
										: 'badge-ghost'} cursor-pointer hover:scale-105 transition-transform"
									on:click={() => toggleCategory(category)}
								>
									{category}
								</button>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Date Range Filter -->
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
					<label class="form-control">
						<span class="label label-text text-xs">{$t('adventures.start_date')}</span>
						<input
							type="date"
							bind:value={startDateFilter}
							class="input input-sm input-bordered w-full"
							min={collectionStartDateISO}
							max={collectionEndDateISO}
						/>
					</label>
					<label class="form-control">
						<span class="label label-text text-xs">{$t('adventures.end_date')}</span>
						<input
							type="date"
							bind:value={endDateFilter}
							class="input input-sm input-bordered w-full"
							min={collectionStartDateISO}
							max={collectionEndDateISO}
						/>
					</label>
				</div>

				<!-- Routes & Activities Filter -->
				<div class="space-y-2">
					<div class="flex items-center justify-between">
						<span class="text-sm font-medium">{$t('adventures.routes_and_activities')}</span>
					</div>
					<div class="flex items-center gap-3 rounded-box border border-base-300 p-3">
						<div
							class="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 grid place-items-center text-base-100"
						>
							🗺️
						</div>
						<div class="flex flex-col flex-1">
							<span class="text-xs uppercase text-base-content/60"
								>{$t('adventures.gpx_routes')}</span
							>
							<span class="text-xs text-base-content/70"
								>{$t('adventures.transport_activity_paths')}</span
							>
						</div>
						<label class="label cursor-pointer gap-2 p-0 ml-auto">
							<input type="checkbox" bind:checked={showLines} class="toggle toggle-sm" />
						</label>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- Map -->
<div class="w-full" style="min-height:600px; height:600px;">
	<FullMap
		geoJson={markerGeoJson}
		center={mapCenter}
		zoom={mapZoom}
		mapClass="w-full h-[600px]"
		{clusterEnabled}
		clusterOptions={resolvedClusterOptions}
		on:mapClick={handleMapClick}
	>
		<svelte:fragment slot="marker" let:markerProps let:markerLngLat let:isActive let:setActive>
			{#if markerProps && markerLngLat}
				<Marker lngLat={markerLngLat} class={isActive ? 'map-pin-active' : 'map-pin'}>
					<div class="relative group z-[1000] group-hover:z-[10000] focus-within:z-[10000]">
						<div
							class="map-pin-hit grid place-items-center w-8 h-8 rounded-full border-2 border-white shadow-lg text-base group-hover:scale-110 transition-all duration-200 {getMarkerColorClass(
								markerProps
							)}"
							class:scale-110={isActive}
							class:cursor-pointer={canNavigate(markerProps)}
							class:cursor-default={!canNavigate(markerProps)}
							role="button"
							tabindex="0"
							on:mouseenter={() => setActive(true)}
							on:mouseleave={() => setActive(false)}
							on:focus={() => setActive(true)}
							on:blur={() => setActive(false)}
							on:click={(e) => {
								e.stopPropagation();
								if (canNavigate(markerProps)) goto(getNavigationUrl(markerProps));
							}}
							on:keydown={(e) => {
								if ((e.key === 'Enter' || e.key === ' ') && canNavigate(markerProps)) {
									e.preventDefault();
									e.stopPropagation();
									goto(getNavigationUrl(markerProps));
								}
							}}
						>
							{markerProps.categoryIcon || '📍'}
						</div>

						<!-- Marker Popup -->
						<div
							class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:pointer-events-auto transition-all duration-200 z-[9999]"
							class:opacity-100={isActive}
							class:pointer-events-auto={isActive}
						>
							<div
								class="card card-compact bg-base-100 shadow-xl border border-base-300 min-w-56 max-w-80"
							>
								<div class="card-body gap-3">
									<div class="space-y-2">
										<div class="min-w-0">
											<h3 class="card-title text-sm leading-tight truncate">{markerProps.name}</h3>
											<div class="mt-1 flex flex-wrap items-center gap-2">
												<div
													class="badge badge-sm {markerProps.type === 'lodging'
														? 'badge-secondary'
														: markerProps.type === 'transportation'
															? 'badge-accent'
															: markerProps.visitStatus === 'visited'
																? 'badge-success'
																: 'badge-info'}"
												>
													{getTypeLabel(markerProps)}
												</div>
												{#if markerProps.categoryName}
													<div class="badge badge-ghost badge-sm">{markerProps.categoryName}</div>
												{/if}
												{#if markerProps.date}
													<div class="badge badge-ghost badge-sm">
														{formatShortDate(markerProps.date)}
													</div>
												{/if}
											</div>
										</div>
									</div>
									{#if canNavigate(markerProps)}
										<div class="card-actions">
											<button
												class="btn btn-xs btn-primary"
												on:click|stopPropagation={() => goto(getNavigationUrl(markerProps))}
											>
												{$t('adventures.open_details')}
											</button>
										</div>
									{/if}
								</div>
							</div>
						</div>
					</div>
				</Marker>
			{/if}
		</svelte:fragment>

		<svelte:fragment slot="overlays">
			{#if showLines && linesGeoJson}
				<GeoJSON id={`collection-lines-${mapKey}`} data={linesGeoJson} generateId>
					<LineLayer
						id={`collection-lines-path-${mapKey}`}
						paint={{
							'line-color': ['coalesce', ['get', '_color'], '#60a5fa'],
							'line-width': 3,
							'line-opacity': 0.9
						}}
					/>
				</GeoJSON>
			{/if}

			{#if newMarker}
				<Marker lngLat={[newMarker.lngLat.lng, newMarker.lngLat.lat]} class="map-pin">
					<div
						class="map-pin-hit grid place-items-center w-10 h-10 rounded-full bg-primary text-primary-content border-2 border-base-100 shadow-lg"
					>
						<Plus class="w-5 h-5" />
					</div>
				</Marker>
			{/if}
		</svelte:fragment>
	</FullMap>
</div>

{#if createModalOpen}
	<NewLocationModal
		on:create={handleLocationCreated}
		on:save={handleLocationSaved}
		on:close={() => (createModalOpen = false)}
		{initialLatLng}
		{collection}
		{user}
	/>
{/if}

<style>
	:global(.min-h-\[600px\]) {
		min-height: 600px;
	}
</style>
