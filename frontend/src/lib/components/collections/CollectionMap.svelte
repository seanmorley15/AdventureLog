<script lang="ts">
	import { untrack } from 'svelte';
	import { stopPropagation } from 'svelte/legacy';

	import FullMap, { type FullMapFeatureCollection } from '$lib/components/map/FullMap.svelte';
	import { GeoJSON, LineLayer, Marker } from 'svelte-maplibre';
	import { goto } from '$app/navigation';
	import { LODGING_TYPES_ICONS, getActivityColor, normalizeBasemapType } from '$lib';
	import Plus from '~icons/mdi/plus';
	import PinIcon from '~icons/mdi/map-marker';
	import Clear from '~icons/mdi/close';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';
	import MapImagePinLayer from '$lib/components/map/MapImagePinLayer.svelte';
	import { collectCollectionImageGeoJson } from '$lib/map/imagePins';
	import { t } from 'svelte-i18n';
	import type { Collection, Location, User } from '$lib/types';
	import { dayPinColor, dayStopPath, pinCoversDay, type PlanPin } from '$lib/collections/plan';
	import {
		CatalogFilters,
		isWithinDateRange,
		locationMatches,
		lodgingMatches,
		transportationMatches
	} from '$lib/collections/catalog.svelte';
	import CollectionCatalogFilters from './CollectionCatalogFilters.svelte';
	import MapMarkerPath from '~icons/mdi/map-marker-path';
	import Numeric from '~icons/mdi/numeric';

	interface Props {
		collection: Collection;
		user?: User | null;
		canModify?: boolean;
		// Allow disabling/enabling clustering for markers
		clusterEnabled?: boolean;
		clusterOptions?: any;
		/** Day-plan pins. A span is one pin, numbered by its start day. */
		planPins?: PlanPin[];
		selectedDay?: number | null;
		highlightedDay?: number | null;
		onPinSelect?: (type: string, objectId: string, dayIndex: number | null) => void;
		/** Map fills its parent and hides the filter chrome. */
		embedded?: boolean;
		mapClass?: string;
		/** Folder maps hide route and trail controls. */
		showRoutes?: boolean;
		/** Shared catalog filters. When omitted the map keeps its own. */
		filters?: CatalogFilters;
		/** Day-numbered pins. Catalog defaults this off so icons show first. */
		numberedPins?: boolean;
		/** Show a map overlay to switch icon pins vs day numbers. */
		pinStyleToggle?: boolean;
	}

	let {
		collection = $bindable(),
		user = null,
		canModify = false,
		clusterEnabled = false,
		clusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 },
		planPins = [],
		selectedDay = null,
		highlightedDay = null,
		onPinSelect,
		embedded = false,
		mapClass = 'w-full h-[600px]',
		showRoutes = true,
		filters = new CatalogFilters(),
		numberedPins = true,
		pinStyleToggle = false
	}: Props = $props();

	let basemapType = $state('default');

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

	let showDayLinks = $state(false);
	let showLocations = $derived(filters.showLocations);
	let showLodging = $derived(filters.showLodging);
	let showTransportation = $derived(filters.showTransportation);
	let showVisited = $derived(filters.showVisited);
	let showPlanned = $derived(filters.showPlanned);
	let showLines = $derived(filters.showLines);
	let showTrails = $derived(filters.showTrails);
	let showImagePins = $derived(filters.showImagePins);
	let startDateFilter = $derived(filters.startDate);
	let endDateFilter = $derived(filters.endDate);
	let selectedCategories = $derived(filters.categories);
	let searchQuery = $derived(filters.search);
	let showNumberedPins = $derived(pinStyleToggle ? filters.numberedPins : numberedPins);

	// Map state for zoom control
	let mapZoom = $state(8);
	let mapCenterCoords: [number, number] = $state([0, 0]);

	// Creation state
	let createModalOpen = $state(false);
	let initialLatLng: { lat: number; lng: number } | null = $state(null);
	let newMarker: { lngLat: { lng: number; lat: number } } | null = $state(null);
	let newLatitude: number | null = $state(null);
	let newLongitude: number | null = $state(null);

	const defaultClusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 };

	// Helper functions
	function parseNumber(value: unknown): number | null {
		if (value === null || value === undefined) return null;
		const num = typeof value === 'number' ? value : Number(value);
		return Number.isFinite(num) ? num : null;
	}

	function sanitizePosition(value: unknown): [number, number] | null {
		if (!Array.isArray(value) || value.length < 2) return null;
		const lon = parseNumber(value[0]);
		const lat = parseNumber(value[1]);
		if (lon === null || lat === null) return null;
		return [lon, lat];
	}

	function sanitizeGeometry(geometry: any): any | null {
		if (!geometry || typeof geometry !== 'object') return null;
		const type = geometry.type;
		const coordinates = geometry.coordinates;

		if (type === 'Point') {
			const position = sanitizePosition(coordinates);
			return position ? { type, coordinates: position } : null;
		}

		if (type === 'LineString' || type === 'MultiPoint') {
			const positions = Array.isArray(coordinates)
				? coordinates
						.map(sanitizePosition)
						.filter((position): position is [number, number] => position !== null)
				: [];
			if (type === 'LineString' && positions.length < 2) return null;
			if (type === 'MultiPoint' && positions.length === 0) return null;
			return { type, coordinates: positions };
		}

		if (type === 'MultiLineString' || type === 'Polygon') {
			const rings = Array.isArray(coordinates)
				? coordinates
						.map((ring: unknown) =>
							Array.isArray(ring)
								? ring
										.map(sanitizePosition)
										.filter((position): position is [number, number] => position !== null)
								: []
						)
						.filter((ring: [number, number][]) => ring.length >= 2)
				: [];
			if (rings.length === 0) return null;
			return { type, coordinates: rings };
		}

		if (type === 'GeometryCollection' && Array.isArray(geometry.geometries)) {
			const geometries = geometry.geometries
				.map(sanitizeGeometry)
				.filter((value: unknown) => value !== null);
			return geometries.length ? { type, geometries } : null;
		}

		if (coordinates == null) return null;
		return { type, coordinates };
	}

	// Never mutate collection $state inside $derived — Svelte 5 throws state_unsafe_mutation
	// in production, which aborts the map template and hides every pin.
	function cloneFeature(feature: any, extraProps?: Record<string, unknown>): any | null {
		if (!feature || typeof feature !== 'object') return null;
		const geometry = sanitizeGeometry(feature.geometry);
		if (!geometry) return null;
		const cloned: Record<string, unknown> = {
			type: feature.type || 'Feature',
			geometry,
			properties: { ...(feature.properties ?? {}), ...extraProps }
		};
		if (feature.id !== undefined) cloned.id = feature.id;
		return cloned;
	}

	function formatShortDate(value: string | null | undefined): string {
		if (!value) return '';
		const parsed = Date.parse(value);
		if (!Number.isFinite(parsed)) return '';
		return new Date(parsed).toISOString().split('T')[0];
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

	function getLodgingIcon(type?: string | null): string {
		if (!type) return '🏨';
		const key = String(type).toLowerCase().trim();
		if (key in LODGING_TYPES_ICONS) {
			return LODGING_TYPES_ICONS[key as keyof typeof LODGING_TYPES_ICONS];
		}
		return '🏨';
	}

	function getTransportIcon(type?: string | null): string {
		if (!type) return '✈️';
		const normalized = String(type).toLowerCase();
		if (normalized.includes('flight') || normalized.includes('plane') || normalized.includes('air'))
			return '✈️';
		if (normalized.includes('train')) return '🚆';
		if (normalized.includes('bus')) return '🚌';
		if (normalized.includes('car') || normalized.includes('drive') || normalized.includes('taxi'))
			return '🚗';
		if (normalized.includes('boat') || normalized.includes('ferry')) return '⛴️';
		return '🚐';
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
				categoryName: l.type || 'other',
				type: 'lodging',
				date: l.check_in || l.check_out || null
			}
		};
	}

	function transportationToFeatures(t: any): MarkerFeature[] {
		const features: MarkerFeature[] = [];
		const icon = getTransportIcon(t?.type || t?.name);
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

	function transportationToLineFeature(t: any): GeoJSON.Feature<GeoJSON.LineString> | null {
		const originLat = parseNumber(t?.origin_latitude);
		const originLon = parseNumber(t?.origin_longitude);
		const destLat = parseNumber(t?.destination_latitude);
		const destLon = parseNumber(t?.destination_longitude);

		if (originLat === null || originLon === null || destLat === null || destLon === null) {
			return null;
		}
		if (originLat === destLat && originLon === destLon) return null;

		return {
			type: 'Feature',
			geometry: {
				type: 'LineString',
				coordinates: [
					[originLon, originLat],
					[destLon, destLat]
				]
			},
			properties: {
				id: String(t.id),
				name: t?.name || t?.type || 'Transportation',
				type: 'transportation',
				_color: '#f59e0b'
			}
		};
	}

	function collectTransportationLinesGeojson(
		transportations: any[]
	): { type: 'FeatureCollection'; features: GeoJSON.Feature<GeoJSON.LineString>[] } | null {
		const features = transportations
			.map(transportationToLineFeature)
			.filter(Boolean) as GeoJSON.Feature<GeoJSON.LineString>[];

		if (features.length === 0) return null;
		return { type: 'FeatureCollection', features };
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

	type DayTrackScope = {
		locationIds: Set<string>;
		transportIds: Set<string>;
	};

	// Merge attachments/activity geojson into a single feature collection
	function dayActivityMatches(activity: any, dayIndex: number | null, trails: any[]): boolean {
		if (dayIndex == null) return true;
		if (activity?.day_index === dayIndex) return true;
		const trail = trails.find((entry) => entry.id === activity?.trail);
		if (!trail?.day_index || !trail.span_end_index) return false;
		return trail.day_index <= dayIndex && dayIndex <= trail.span_end_index;
	}

	function collectLinesGeojson(
		coll: Collection,
		dateWindow: { startDate: string; endDate: string },
		scope: DayTrackScope | null,
		dayIndex: number | null
	): { type: 'FeatureCollection'; features: any[] } | null {
		if (!coll) return null;
		const features: any[] = [];

		const pushFeature = (feature: any, extraProps?: Record<string, unknown>) => {
			const cloned = cloneFeature(feature, extraProps);
			if (cloned) features.push(cloned);
		};

		const pushGeoJson = (geojson: any, extraProps?: Record<string, unknown>) => {
			if (!geojson) return;
			if (geojson.type === 'FeatureCollection' && Array.isArray(geojson.features)) {
				for (const feature of geojson.features) pushFeature(feature, extraProps);
			} else if (geojson.type === 'Feature') {
				pushFeature(geojson, extraProps);
			}
		};

		// Locations: attachments and visits -> activities
		for (const loc of coll.locations || []) {
			if (!locationMatches(loc, filters)) continue;
			if (scope && !scope.locationIds.has(String(loc.id))) continue;
			if (Array.isArray(loc.attachments)) {
				for (const a of loc.attachments) {
					if (!a || !a.geojson) continue;
					pushGeoJson(a.geojson);
				}
			}

			if (Array.isArray(loc.visits)) {
				for (const visit of loc.visits) {
					if (!visit.activities) continue;
					for (const activity of visit.activities) {
						const activityDate = getActivityDate(activity, visit);
						if (!isWithinDateRange(activityDate, dateWindow.startDate, dateWindow.endDate))
							continue;
						if (activity && activity.geojson) {
							const color = getActivityColor(activity.sport_type || (activity as any).type || '');
							pushGeoJson(activity.geojson, {
								_color: color,
								activity_type: activity.sport_type || (activity as any).type || null
							});
						}
					}
				}
			}
		}

		// Day activities carry the GPX. A trail card is only a link.
		for (const activity of coll.day_activities || []) {
			if (!dayActivityMatches(activity, dayIndex, coll.day_trails || [])) continue;
			if (!activity?.geojson) continue;
			const color = getActivityColor(activity.sport_type || '');
			pushGeoJson(activity.geojson, {
				_color: color,
				activity_type: activity.sport_type || null
			});
		}

		// Transportations: attachments
		for (const t of coll.transportations || []) {
			if (!transportationMatches(t, filters)) continue;
			if (scope && !scope.transportIds.has(String(t.id))) continue;
			if (!t || !Array.isArray(t.attachments)) continue;
			for (const a of t.attachments) {
				if (!a || !a.geojson) continue;
				pushGeoJson(a.geojson, { _color: '#60a5fa' });
			}
		}

		if (features.length === 0) return null;
		return { type: 'FeatureCollection', features };
	}

	function appendTrailGeometry(features: any[], geojson: any) {
		if (!geojson) return;
		if (geojson.type === 'FeatureCollection' && Array.isArray(geojson.features)) {
			for (const feature of geojson.features) {
				const cloned = cloneFeature(feature);
				if (cloned) features.push(cloned);
			}
		} else if (geojson.type === 'Feature') {
			const cloned = cloneFeature(geojson);
			if (cloned) features.push(cloned);
		}
	}

	function dayTrailMatches(trail: any, dayIndex: number | null): boolean {
		if (dayIndex == null) return true;
		if (trail?.day_index === dayIndex) return true;
		if (!trail?.day_index || !trail.span_end_index) return false;
		return trail.day_index <= dayIndex && dayIndex <= trail.span_end_index;
	}

	function collectTrailGeojson(
		coll: Collection,
		scope: DayTrackScope | null,
		dayIndex: number | null
	): { type: 'FeatureCollection'; features: any[] } | null {
		if (!coll) return null;
		const features: any[] = [];

		for (const loc of coll.locations || []) {
			if (!locationMatches(loc, filters)) continue;
			if (scope && !scope.locationIds.has(String(loc.id))) continue;
			if (!Array.isArray(loc.trails)) continue;
			for (const trail of loc.trails) appendTrailGeometry(features, trail?.geojson);
		}

		for (const trail of coll.day_trails || []) {
			if (!dayTrailMatches(trail, dayIndex)) continue;
			appendTrailGeometry(features, trail?.geojson);
		}

		if (features.length === 0) return null;
		return { type: 'FeatureCollection', features };
	}

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

	function getMarkerColorClass(props: MarkerProperties) {
		if (props.type === 'lodging') return 'bg-gradient-to-br from-purple-400 to-purple-600';
		if (props.type === 'transportation') return 'bg-gradient-to-br from-amber-400 to-amber-600';
		if (props.visitStatus === 'visited') return 'bg-gradient-to-br from-emerald-400 to-emerald-600';
		if (props.visitStatus === 'planned') return 'bg-gradient-to-br from-blue-400 to-blue-600';
		return 'bg-gray-200';
	}

	function getTypeLabel(props: MarkerProperties) {
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

	function pinObjectId(props: MarkerProperties): string {
		return props.type === 'transportation' ? props.id.split(':')[0] : props.id;
	}

	function pinsFor(props: MarkerProperties): PlanPin[] {
		const objectId = pinObjectId(props);
		return planPins.filter((pin) => pin.type === props.type && pin.objectId === objectId);
	}

	function displayPin(props: MarkerProperties): PlanPin | null {
		const matches = pinsFor(props);
		if (!matches.length) return null;
		if (selectedDay != null) {
			return matches.find((pin) => pinCoversDay(pin, selectedDay)) ?? null;
		}
		return matches.find((pin) => pin.dayIndex != null) ?? matches[0];
	}

	function pinIsHighlighted(pin: PlanPin | null): boolean {
		if (!pin || highlightedDay == null) return false;
		return pinCoversDay(pin, highlightedDay);
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

	$effect(() => {
		const style = user?.map_style;
		if (!style) return;
		if (untrack(() => basemapType) !== 'default') return;
		basemapType = normalizeBasemapType(style);
	});
	let resolvedClusterOptions = $derived(clusterOptions || defaultClusterOptions);
	// Normalize collection start/end dates to YYYY-MM-DD for cross-browser compatibility (Firefox is strict)
	let locationFeatures = $derived(
		(collection?.locations || []).map(locationToFeature).filter(Boolean) as MarkerFeature[]
	);
	let lodgingFeatures = $derived(
		(collection?.lodging || []).map(lodgingToFeature).filter(Boolean) as MarkerFeature[]
	);
	let transportationFeatures = $derived(
		(collection?.transportations || [])
			.flatMap(transportationToFeatures)
			.filter(Boolean) as MarkerFeature[]
	);
	let allFeatures = $derived([...locationFeatures, ...lodgingFeatures, ...transportationFeatures]);
	let trackScope = $derived.by(() => {
		if (selectedDay == null || planPins.length === 0) return null;
		const dayIndex = selectedDay;
		return {
			locationIds: new Set(
				planPins
					.filter((pin) => pin.type === 'location' && pinCoversDay(pin, dayIndex))
					.map((pin) => pin.objectId)
			),
			transportIds: new Set(
				planPins
					.filter((pin) => pin.type === 'transportation' && pinCoversDay(pin, dayIndex))
					.map((pin) => pin.objectId)
			)
		};
	});
	let linesGeoJson = $derived(
		collectLinesGeojson(
			collection,
			{
				startDate: startDateFilter || collection?.start_date || '',
				endDate: endDateFilter || collection?.end_date || ''
			},
			trackScope,
			selectedDay
		)
	);
	let transportationLinesGeoJson = $derived(
		showTransportation
			? collectTransportationLinesGeojson(
					(collection?.transportations || []).filter((item) => {
						if (trackScope && !trackScope.transportIds.has(String(item.id))) return false;
						return transportationMatches(item, filters);
					})
				)
			: null
	);
	let trailsGeoJson = $derived(collectTrailGeojson(collection, trackScope, selectedDay));
	let dayLinkGeoJson = $derived.by(() => {
		if (selectedDay == null || !showDayLinks) return null;
		const coordinates = dayStopPath(collection, selectedDay);
		if (coordinates.length < 2) return null;
		return {
			type: 'FeatureCollection' as const,
			features: [
				{
					type: 'Feature' as const,
					geometry: { type: 'LineString' as const, coordinates },
					properties: { _color: dayPinColor(selectedDay) }
				}
			]
		};
	});
	let trailCount = $derived(
		(collection?.locations || []).reduce(
			(count, loc) => count + (loc.trails || []).filter((trail) => trail.geojson).length,
			0
		) + (collection?.day_trails || []).filter((trail) => trail.geojson).length
	);
	let matchedLocationIds = $derived(
		new Set(
			(collection?.locations ?? [])
				.filter((loc) => locationMatches(loc, filters))
				.map((loc) => String(loc.id))
		)
	);
	let matchedLodgingIds = $derived(
		new Set(
			(collection?.lodging ?? [])
				.filter((item) => lodgingMatches(item, filters))
				.map((item) => String(item.id))
		)
	);
	let matchedTransportIds = $derived(
		new Set(
			(collection?.transportations ?? [])
				.filter((item) => transportationMatches(item, filters))
				.map((item) => String(item.id))
		)
	);
	let filteredFeatures = $derived(
		allFeatures.filter((feature) => {
			const props = feature.properties;
			const listed =
				props.type === 'location'
					? matchedLocationIds.has(props.id)
					: props.type === 'lodging'
						? matchedLodgingIds.has(props.id)
						: matchedTransportIds.has(pinObjectId(props));
			if (!listed) return false;
			if (selectedDay == null || planPins.length === 0) return true;
			return displayPin(props) != null;
		})
	);
	// Auto-zoom when search results change
	$effect(() => {
		const query = searchQuery.trim();
		const matches = filteredFeatures;
		if (!query || matches.length === 0) return;
		untrack(() => zoomToFilteredFeatures());
	});
	let markerGeoJson = $derived({
		type: 'FeatureCollection',
		features: filteredFeatures
	} as MarkerFeatureCollection);
	// Stats
	let visiblePinCount = $derived(filteredFeatures.length);
	let totalPinCount = $derived(allFeatures.length);
	let imagePinGeoJson = $derived(collectCollectionImageGeoJson(collection));
	let imagePinCount = $derived(imagePinGeoJson.features.length);
	let mapKey = $derived(
		`${visiblePinCount}-${startDateFilter}-${endDateFilter}-${showLocations}-${showLodging}-${showTransportation}-${showVisited}-${showPlanned}-${showLines}-${showTrails}-${showImagePins}-${selectedDay ?? 'all'}-${showDayLinks}-${showNumberedPins}-${Array.from(
			selectedCategories
		)
			.sort()
			.join(
				'|'
			)}-${Array.from(filters.lodgingTypes).sort().join('|')}-${Array.from(filters.transportTypes).sort().join('|')}`
	);
	function firstTrackCoordinate(geojson: { features?: any[] } | null): [number, number] | null {
		const coordinates = geojson?.features?.[0]?.geometry?.coordinates;
		if (!Array.isArray(coordinates) || coordinates.length === 0) return null;
		const first = Array.isArray(coordinates[0]) ? coordinates[0] : coordinates;
		if (typeof first[0] !== 'number' || typeof first[1] !== 'number') return null;
		return [first[0], first[1]];
	}

	let mapCenter = $derived(
		mapCenterCoords[0] !== 0 || mapCenterCoords[1] !== 0
			? mapCenterCoords
			: markerGeoJson.features.length
				? markerGeoJson.features[0].geometry.coordinates
				: (firstTrackCoordinate(linesGeoJson) ??
					firstTrackCoordinate(trailsGeoJson) ??
					([0, 0] as [number, number]))
	);
</script>

<!-- Add to Collection CTA (compact) -->
{#if canModify && !embedded}
	<div class="card bg-base-100 shadow-xs mb-3 border border-base-200">
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
					<button type="button" class="btn btn-primary btn-xs" onclick={openCreateModal}>
						<Plus class="w-4 h-4" />
						{$t('adventures.add')}
					</button>
					{#if newMarker}
						<button type="button" class="btn btn-ghost btn-xs" onclick={clearNewMarker}>
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
							onclick={openCreateModal}
						>
							<Plus class="w-3 h-3 sm:w-4 sm:h-4" />
							{$t('adventures.add_here')}
						</button>
						<button type="button" class="btn btn-ghost btn-xxs sm:btn-xs" onclick={clearNewMarker}>
							<Clear class="w-3 h-3 sm:w-4 sm:h-4" />
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}

{#if !embedded}
	<CollectionCatalogFilters
		{filters}
		{collection}
		class="mb-4"
		showMapToggles={showRoutes}
		matchedCount={visiblePinCount}
		totalCount={totalPinCount}
		{trailCount}
		{imagePinCount}
		startOpen={false}
	/>
{/if}

<!-- Map -->
<div
	class={embedded ? 'relative h-full w-full' : 'relative w-full'}
	style={embedded ? undefined : 'min-height:600px; height:600px;'}
>
	<FullMap
		geoJson={markerGeoJson}
		center={mapCenter}
		zoom={mapZoom}
		{mapClass}
		bind:basemapType
		{clusterEnabled}
		clusterOptions={resolvedClusterOptions}
		mapClickEnabled={canModify}
		on:mapClick={handleMapClick}
	>
		{#snippet marker({ markerProps, markerLngLat, isActive, setActive })}
			{#if markerProps && markerLngLat}
				{@const pin = showNumberedPins ? displayPin(markerProps) : null}
				<Marker lngLat={markerLngLat} class={isActive ? 'map-pin-active' : 'map-pin'}>
					<div class="relative group z-[1000] group-hover:z-[10000] focus-within:z-[10000]">
						<div
							class="map-pin-hit relative grid place-items-center w-8 h-8 rounded-full border-2 shadow-lg text-sm font-bold group-hover:scale-110 transition-all duration-200 {pin
								? 'text-white'
								: getMarkerColorClass(markerProps)}"
							class:border-white={!pin?.optional && !pin?.ideas}
							class:border-dashed={pin?.optional || pin?.ideas}
							class:border-warning={pin?.ideas}
							class:scale-110={isActive}
							class:ring-4={pinIsHighlighted(pin)}
							class:ring-primary={pinIsHighlighted(pin)}
							class:cursor-pointer={canNavigate(markerProps)}
							style={pin?.dayIndex
								? `background:${dayPinColor(pin.dayIndex)}`
								: pin?.ideas
									? 'background:#78716c'
									: undefined}
							role="button"
							tabindex="0"
							onmouseenter={() => setActive(true)}
							onmouseleave={() => setActive(false)}
							onfocus={() => setActive(true)}
							onblur={() => setActive(false)}
							onclick={(e) => {
								e.stopPropagation();
								if (onPinSelect) {
									onPinSelect(markerProps.type, pinObjectId(markerProps), pin?.dayIndex ?? null);
									return;
								}
								if (canNavigate(markerProps)) goto(getNavigationUrl(markerProps));
							}}
							onkeydown={(e) => {
								if (e.key !== 'Enter' && e.key !== ' ') return;
								e.preventDefault();
								e.stopPropagation();
								if (onPinSelect) {
									onPinSelect(markerProps.type, pinObjectId(markerProps), pin?.dayIndex ?? null);
									return;
								}
								if (canNavigate(markerProps)) goto(getNavigationUrl(markerProps));
							}}
						>
							{#if pin?.dayIndex}
								{pin.dayIndex}
							{:else if pin?.ideas}
								?
							{:else}
								{markerProps.categoryIcon || '📍'}
							{/if}
							{#if pin?.visited && pin.visitId}
								<a
									href={`/locations/${pin.objectId}#visit-${pin.visitId}`}
									class="absolute -right-1 -top-1 grid h-4 w-4 place-items-center rounded-full bg-success text-[10px] text-success-content"
									aria-label={$t('itinerary.visited')}
									onclick={(e) => e.stopPropagation()}
								>
									✓
								</a>
							{/if}
						</div>

						<!-- Marker Popup -->
						<div
							class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:pointer-events-auto transition-all duration-200 z-[9999]"
							class:opacity-100={isActive}
							class:pointer-events-auto={isActive}
						>
							<div
								class="card card-sm bg-base-100 shadow-xl border border-base-300 min-w-56 max-w-80"
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
												onclick={stopPropagation(() => goto(getNavigationUrl(markerProps)))}
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
		{/snippet}

		{#snippet overlays()}
			{#if showRoutes && dayLinkGeoJson}
				<GeoJSON id={`collection-day-links-${mapKey}`} data={dayLinkGeoJson} generateId>
					<LineLayer
						id={`collection-day-links-casing-${mapKey}`}
						layout={{ 'line-cap': 'round', 'line-join': 'round' }}
						paint={{
							'line-color': '#ffffff',
							'line-width': 6,
							'line-opacity': 0.85
						}}
					/>
					<LineLayer
						id={`collection-day-links-path-${mapKey}`}
						layout={{ 'line-cap': 'round', 'line-join': 'round' }}
						paint={{
							'line-color': ['coalesce', ['get', '_color'], '#0ea5e9'],
							'line-width': 3,
							'line-opacity': 0.95
						}}
					/>
				</GeoJSON>
			{/if}

			{#if showRoutes && showLines && linesGeoJson}
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

			{#if showRoutes && showTrails && trailsGeoJson}
				<GeoJSON id={`collection-trails-${mapKey}`} data={trailsGeoJson} generateId>
					<LineLayer
						id={`collection-trails-path-${mapKey}`}
						paint={{
							'line-color': '#a855f7',
							'line-width': 3,
							'line-opacity': 0.85
						}}
					/>
				</GeoJSON>
			{/if}

			{#if showRoutes && transportationLinesGeoJson}
				<GeoJSON
					id={`collection-transport-lines-${mapKey}`}
					data={transportationLinesGeoJson}
					generateId
				>
					<LineLayer
						id={`collection-transport-lines-path-${mapKey}`}
						paint={{
							'line-color': ['coalesce', ['get', '_color'], '#f59e0b'],
							'line-width': 2.5,
							'line-opacity': 0.85,
							'line-dasharray': [4, 3]
						}}
					/>
				</GeoJSON>
			{/if}

			{#if canModify && newMarker}
				<Marker lngLat={[newMarker.lngLat.lng, newMarker.lngLat.lat]} class="map-pin">
					<div
						class="map-pin-hit grid place-items-center w-10 h-10 rounded-full bg-primary text-primary-content border-2 border-base-100 shadow-lg"
					>
						<Plus class="w-5 h-5" />
					</div>
				</Marker>
			{/if}

			<MapImagePinLayer geoJson={imagePinGeoJson} visible={showImagePins} />
		{/snippet}
	</FullMap>

	{#if selectedDay != null}
		<div class="pointer-events-none absolute left-3 top-3 z-20">
			<button
				type="button"
				class={[
					'pointer-events-auto btn btn-sm gap-2 border border-base-300 bg-base-100/90 shadow-md backdrop-blur-lg',
					showDayLinks && 'border-primary bg-primary text-primary-content'
				]}
				aria-pressed={showDayLinks}
				title={showDayLinks ? $t('itinerary.hide_day_route') : $t('itinerary.show_day_route')}
				onclick={() => (showDayLinks = !showDayLinks)}
			>
				<MapMarkerPath class="h-4 w-4" />
				{$t('itinerary.connect_stops')}
			</button>
		</div>
	{/if}

	{#if pinStyleToggle && planPins.length > 0}
		<div class="pointer-events-none absolute right-3 top-3 z-20">
			<button
				type="button"
				class={[
					'pointer-events-auto btn btn-sm gap-2 border border-base-300 bg-base-100/90 shadow-md backdrop-blur-lg',
					showNumberedPins && 'border-primary bg-primary text-primary-content'
				]}
				aria-pressed={showNumberedPins}
				title={$t('collections.day_numbers')}
				onclick={() => (filters.numberedPins = !showNumberedPins)}
			>
				<Numeric class="h-4 w-4" />
				{$t('collections.day_numbers')}
			</button>
		</div>
	{/if}
</div>

{#if canModify && createModalOpen}
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
