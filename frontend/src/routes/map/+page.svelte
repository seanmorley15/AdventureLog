<script lang="ts">
	import { run } from 'svelte/legacy';

	import { DefaultMarker, Popup, Marker, GeoJSON, LineLayer } from 'svelte-maplibre';
	import MapNearbyRadiusLayer from '$lib/components/map/MapNearbyRadiusLayer.svelte';
	import { onDestroy, onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { t } from 'svelte-i18n';
	import { googleContentImage } from '$lib/images';
	import type {
		Activity,
		Location,
		VisitedCity,
		VisitedRegion,
		Pin,
		MapSelection,
		MapSearchMode,
		PlaceSearchResult,
		Recommendation,
		Lodging
	} from '$lib/types.js';
	import type { ClusterOptions } from 'svelte-maplibre';
	import { goto } from '$app/navigation';
	import { getActivityColor, normalizeBasemapType } from '$lib';
	import { page } from '$app/stores';
	import { addToast } from '$lib/toasts';
	import { bindMapViewportCenterSync, getMapViewportCenter } from '$lib/map/viewportCenter';
	import { safeMapResize } from '$lib/map/renderGuard';
	import {
		enrichPlace,
		fetchRecommendations,
		placeToLocationPrefill,
		placeToQuickAddPayload,
		quickAddLocation,
		recommendationToLocationPrefill,
		recommendationToQuickAddPayload,
		resolveQuickAddPayload
	} from '$lib/map/places';

	import MapIcon from '~icons/mdi/map';
	import Filter from '~icons/mdi/filter-variant';
	import Plus from '~icons/mdi/plus';
	import Clear from '~icons/mdi/close';
	import Eye from '~icons/mdi/eye';
	import PinIcon from '~icons/mdi/map-marker';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';
	import LodgingModal from '$lib/components/lodging/LodgingModal.svelte';
	import FullMap from '$lib/components/map/FullMap.svelte';
	import MapSearchBar from '$lib/components/map/MapSearchBar.svelte';
	import MapDetailPanel from '$lib/components/map/MapDetailPanel.svelte';
	import MapRecommendationsLayer from '$lib/components/map/MapRecommendationsLayer.svelte';
	import MapImagePinLayer from '$lib/components/map/MapImagePinLayer.svelte';
	import {
		fetchImageMapPins,
		imageMapPinsToGeoJson,
		imagePinPropsToSelection,
		mapImagePinSelectionToProps,
		type ImageMapPin,
		type ImagePinProperties
	} from '$lib/map/imagePins';
	import MapFloatingControls from '$lib/components/map/MapFloatingControls.svelte';
	import CategoryFilterDropdown from '$lib/components/CategoryFilterDropdown.svelte';
	import Compass from '~icons/mdi/compass';
	import Tag from '~icons/mdi/tag';
	import ChevronLeft from '~icons/mdi/chevron-left';
	import ChevronRight from '~icons/mdi/chevron-right';

	interface Props {
		data: any;
		initialLatLng?: { lat: number; lng: number } | null;
	}

	let { data, initialLatLng = $bindable(null) }: Props = $props();

	let createModalOpen = $state(false);
	let lodgingModalOpen = $state(false);
	let showRegions = $state(false);
	let showActivities = $state(false);
	let showImagePins = $state(false);
	let showCities = $state(false);
	let sidebarOpen = $state(false);
	let sidebarCollapsed = $state(false);
	let sidebarMode: 'controls' | 'preview' = $state('controls');

	let basemapType: string = $state(normalizeBasemapType(undefined));
	$effect.pre(() => {
		basemapType = normalizeBasemapType(data.user?.map_style);
	});

	const MAP_VIEW_STORAGE_KEY = 'adventurelog.map.view';

	function viewFromSearchParams(
		params: URLSearchParams
	): { center: [number, number]; zoom: number } | null {
		const lat = params.get('lat');
		const lng = params.get('lng');
		const zoom = params.get('zoom');
		if (!lat || !lng || zoom === null) return null;
		const parsedLat = parseFloat(lat);
		const parsedLng = parseFloat(lng);
		const parsedZoom = parseFloat(zoom);
		if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLng) || !Number.isFinite(parsedZoom)) {
			return null;
		}
		return { center: [parsedLng, parsedLat], zoom: parsedZoom };
	}

	function readStoredMapView(): { center: [number, number]; zoom: number } | null {
		if (typeof window === 'undefined') return null;
		try {
			const storedValue = window.localStorage.getItem(MAP_VIEW_STORAGE_KEY);
			if (!storedValue) return null;
			const parsed = JSON.parse(storedValue) as { center?: [number, number]; zoom?: number };
			if (
				!Array.isArray(parsed.center) ||
				parsed.center.length < 2 ||
				typeof parsed.zoom !== 'number'
			) {
				return null;
			}
			return { center: [parsed.center[0], parsed.center[1]], zoom: parsed.zoom };
		} catch {
			return null;
		}
	}

	function getInitialMapView(): { center: [number, number]; zoom: number } | null {
		if (!browser) return null;
		return viewFromSearchParams($page.url.searchParams) ?? readStoredMapView();
	}

	const initialView = getInitialMapView();
	let mapZoom: number = $state(initialView?.zoom ?? 2);
	let mapCenter: [number, number] = $state(initialView?.center ?? [0, 0]);
	/** When true, center/zoom props drive FullMap. Disabled after load so pan/zoom is not fought by easeTo. */
	let syncViewportFromProps = $state(true);
	let mapInstance: maplibregl.Map | undefined = $state(undefined);
	let mapViewportEl: HTMLElement | null = $state(null);
	let mapPageEl: HTMLElement | null = $state(null);
	let updateUrlTimeout: NodeJS.Timeout | null = null;

	let visitedRegions: VisitedRegion[] = $derived(data.props.visitedRegions);
	let visitedCities: VisitedCity[] = $state([]);
	let pins: Pin[] = $state<Pin[]>([]);
	$effect.pre(() => {
		pins = data.props.pins;
	});
	let activities: Activity[] = $state([]);
	let imageMapPins: ImageMapPin[] = $state([]);
	let imagePinsLoaded = $state(false);
	let imagePinsLoading = false;
	let filteredPins = $state<Pin[]>([]);

	let showVisited = $state(true);
	let showPlanned = $state(true);
	let typeString = $state('');
	let searchMode: MapSearchMode = $state('my');
	let searchQuery = $state('');
	let selected = $state<MapSelection | null>(null);
	let selectedPlace: PlaceSearchResult | null = $state(null);
	let recommendations: Recommendation[] = $state([]);
	let recCategory = $state<'tourism' | 'food' | 'lodging'>('tourism');
	let recRadius = $state(5000);
	let recLoading = $state(false);
	let recError: string | null = $state(null);
	let showSearchThisArea = $state(false);
	let lastRecSearchCenter: [number, number] | null = null;
	let viewportCenter: { lng: number; lat: number } = $state({ lng: 0, lat: 0 });
	let unbindViewportCenter: (() => void) | null = null;

	let newMarker: { lngLat: { lng: number; lat: number } } | null = $state(null);
	let newLongitude: number | null = $state(null);
	let newLatitude: number | null = $state(null);

	let locationCache: Map<string, Location> = new Map();
	let locationRequests: Map<string, Promise<Location | null>> = new Map();
	let previewLocation: Location | null = $state(null);
	let previewLoading = $state(false);
	let previewError: string | null = $state(null);
	let previewRequestSeq = 0;

	let isQuickAdding = $state(false);
	let locationBeingUpdated: Location | undefined = $state(undefined);
	let modalLocationPrefill: Location | null = $state(null);
	let modalLodgingPrefill: Lodging | null = $state(null);
	let modalSkipQuickStart = $state(false);

	const PIN_SOURCE_ID = 'map-pins';
	const pinClusterOptions: ClusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 };

	type VisitStatus = 'visited' | 'planned';

	type PinFeatureProperties = {
		id: string;
		name: string;
		visitStatus: VisitStatus;
		categoryIcon?: string;
		categoryName?: string;
	};

	function parseCoordinate(value: number | string | null | undefined): number | null {
		if (value === null || value === undefined) return null;
		const numeric = typeof value === 'number' ? value : Number(value);
		return Number.isFinite(numeric) ? numeric : null;
	}

	function pinToFeature(pin: Pin) {
		const lat = parseCoordinate(pin.latitude);
		const lon = parseCoordinate(pin.longitude);
		if (lat === null || lon === null) return null;
		return {
			type: 'Feature' as const,
			geometry: { type: 'Point' as const, coordinates: [lon, lat] as [number, number] },
			properties: {
				id: pin.id,
				name: pin.name,
				visitStatus: pin.is_visited ? ('visited' as VisitStatus) : ('planned' as VisitStatus),
				categoryIcon: pin.category?.icon || '📍',
				categoryName: pin.category?.display_name || pin.category?.name || ''
			}
		};
	}

	function pinToFeatureUnknown(item: unknown) {
		return pinToFeature(item as Pin);
	}

	function getMarkerProps(feature: unknown) {
		const f = feature as { properties?: PinFeatureProperties } | null;
		return f?.properties ?? null;
	}

	function getVisitStatusClass(status: VisitStatus): string {
		switch (status) {
			case 'visited':
				return 'bg-gradient-to-br from-emerald-400 to-emerald-600';
			case 'planned':
				return 'bg-gradient-to-br from-blue-400 to-blue-600';
			default:
				return 'bg-gray-200';
		}
	}

	function markerClassResolver(
		props: { visitStatus?: string; id?: string } | null,
		isSelected: boolean
	): string {
		if (isSelected)
			return (
				'ring-2 ring-primary ring-offset-2 ' +
				getVisitStatusClass((props?.visitStatus as VisitStatus) || 'planned')
			);
		return getVisitStatusClass((props?.visitStatus as VisitStatus) || 'planned');
	}

	function markerLabelResolver(props: { categoryIcon?: string } | null): string {
		return props?.categoryIcon || '📍';
	}

	function getVisitStatusLabel(status: VisitStatus | undefined): string {
		return status === 'visited' ? $t('adventures.visited') : $t('adventures.planned');
	}

	async function ensureImageMapPinsLoaded() {
		if (!browser || imagePinsLoaded || imagePinsLoading) return;
		imagePinsLoading = true;
		try {
			imageMapPins = await fetchImageMapPins();
			imagePinsLoaded = true;
		} catch (error) {
			console.error('Failed to load image map pins:', error);
		} finally {
			imagePinsLoading = false;
		}
	}

	async function fetchAllActivities() {
		const response = await fetch('/api/activities');
		activities = await response.json();
	}

	async function fetchVisitedCities() {
		const response = await fetch('/api/visitedcity');
		visitedCities = await response.json();
	}

	async function fetchLocationDetails(locationId: string): Promise<Location | null> {
		if (locationCache.has(locationId)) {
			return locationCache.get(locationId)!;
		}
		const existing = locationRequests.get(locationId);
		if (existing) return existing;

		const request = (async () => {
			try {
				const response = await fetch(`/api/locations/${locationId}`);
				if (!response.ok) throw new Error(response.statusText);
				const location: Location = await response.json();
				locationCache.set(locationId, location);
				return location;
			} catch (error) {
				console.error('Error fetching location details:', error);
				return null;
			} finally {
				locationRequests.delete(locationId);
			}
		})();

		locationRequests.set(locationId, request);
		return request;
	}

	function revealSidebar() {
		sidebarOpen = true;
		sidebarCollapsed = false;
	}

	async function loadPreviewForPin(pinId: string) {
		selected = { kind: 'pin', pinId };
		selectedPlace = null;
		sidebarMode = 'preview';
		revealSidebar();

		const cached = locationCache.get(pinId) ?? null;
		previewLocation = cached;
		previewError = null;
		if (cached) {
			previewLoading = false;
			return;
		}

		const seq = ++previewRequestSeq;
		previewLoading = true;
		const location = await fetchLocationDetails(pinId);
		if (seq !== previewRequestSeq || selected?.kind !== 'pin' || selected.pinId !== pinId) return;
		previewLoading = false;
		if (!location) {
			previewError = $t('map.search_error');
			return;
		}
		previewLocation = location;
	}

	function clearSelection() {
		selected = null;
		selectedPlace = null;
		previewLocation = null;
		previewError = null;
		previewLoading = false;
		sidebarMode = 'controls';
	}

	function handlePinClick(pinId: string, setActive: (v: boolean) => void) {
		setActive(true);
		loadPreviewForPin(pinId);
	}

	function handleImagePinSelect(event: CustomEvent<{ props: ImagePinProperties }>) {
		const props = event.detail.props;
		if (props.parentType === 'location' && props.parentId) {
			loadPreviewForPin(props.parentId);
			return;
		}

		selected = imagePinPropsToSelection(props);
		selectedPlace = null;
		previewLocation = null;
		previewError = null;
		previewLoading = false;
		sidebarMode = 'preview';
		revealSidebar();
	}

	function handleViewImageParent(event: CustomEvent<{ href: string }>) {
		goto(event.detail.href);
	}

	function attachViewportCenterSync() {
		if (!mapInstance) return;
		unbindViewportCenter?.();
		unbindViewportCenter = bindMapViewportCenterSync(
			mapInstance,
			(center) => {
				viewportCenter = center;
			},
			mapViewportEl
		);
	}

	function refreshMapLayout() {
		safeMapResize(mapInstance);
	}

	function handleMapLoad() {
		const intended = getInitialMapView() ?? { center: mapCenter, zoom: mapZoom };
		mapCenter = intended.center;
		mapZoom = intended.zoom;
		if (mapInstance && syncViewportFromProps) {
			mapInstance.jumpTo({ center: intended.center, zoom: intended.zoom });
		}
		syncViewportFromProps = false;
		attachViewportCenterSync();
		queueMicrotask(refreshMapLayout);
	}

	function flyTo(lat: number, lng: number, zoom = 14) {
		if (mapInstance) {
			mapInstance.easeTo({ center: [lng, lat], zoom, duration: 600 });
			return;
		}
		mapCenter = [lng, lat];
		mapZoom = zoom;
		syncViewportFromProps = true;
	}

	async function handleSelectPin(event: CustomEvent<{ pinId: string }>) {
		const pin = pins.find((p) => p.id === event.detail.pinId);
		if (pin) {
			const lat = parseCoordinate(pin.latitude);
			const lng = parseCoordinate(pin.longitude);
			if (lat !== null && lng !== null) flyTo(lat, lng);
		}
		await loadPreviewForPin(event.detail.pinId);
	}

	async function selectRandomLocation() {
		if (randomEligiblePins.length === 0) {
			addToast('info', $t('map.no_locations_to_explore'));
			return;
		}
		const pin = randomEligiblePins[Math.floor(Math.random() * randomEligiblePins.length)];
		const lat = parseCoordinate(pin.latitude);
		const lng = parseCoordinate(pin.longitude);
		if (lat === null || lng === null) return;
		revealSidebar();
		flyTo(lat, lng);
		await loadPreviewForPin(pin.id);
	}

	async function handleSelectPlace(event: CustomEvent<{ place: PlaceSearchResult }>) {
		let place = event.detail.place;
		selectedPlace = place;
		selected = { kind: 'place', place };
		sidebarMode = 'preview';
		revealSidebar();
		flyTo(place.lat, place.lng);
		if (place.place_id) {
			place = await enrichPlace(place);
			selectedPlace = place;
			selected = { kind: 'place', place };
		}
	}

	function selectRecommendation(item: Recommendation) {
		selected = { kind: 'recommendation', item };
		sidebarMode = 'preview';
		revealSidebar();
		flyTo(item.latitude, item.longitude, 15);
	}

	function handleSelectRecommendation(event: CustomEvent<{ item: Recommendation }>) {
		selectRecommendation(event.detail.item);
	}

	function handleViewFull(event: CustomEvent<{ pinId: string }>) {
		goto(`/locations/${event.detail.pinId}`);
	}

	function backToControls() {
		clearSelection();
	}

	async function searchThisArea() {
		if (!mapInstance) return;
		const { lat, lng } = getMapViewportCenter(mapInstance, mapViewportEl);
		if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

		recLoading = true;
		recError = null;
		showSearchThisArea = false;
		lastRecSearchCenter = [lng, lat];

		try {
			const data = await fetchRecommendations({
				lat,
				lon: lng,
				radius: recRadius,
				category: recCategory
			});
			recommendations = data.results || [];
			if (recommendations.length === 0) {
				recError = $t('map.recommendations_empty');
			}
		} catch (err) {
			recommendations = [];
			recError = err instanceof Error ? err.message : $t('map.recommendations_error');
		} finally {
			recLoading = false;
		}
	}

	function handleMapMove(e: CustomEvent<{ center: { lng: number; lat: number }; zoom: number }>) {
		const { zoom } = e.detail;
		const center = mapInstance ? getMapViewportCenter(mapInstance, mapViewportEl) : e.detail.center;
		viewportCenter = { lng: center.lng, lat: center.lat };
		// Do not update mapCenter/mapZoom here — that re-triggers FullMap easeTo and locks the map.
		persistMapView(center.lat, center.lng, zoom);
		updateUrlParams(center.lat, center.lng, zoom);

		if (searchMode === 'nearby') {
			const prev = lastRecSearchCenter;
			if (!prev) {
				showSearchThisArea = true;
			} else {
				const moved =
					Math.abs(prev[0] - center.lng) > 0.002 || Math.abs(prev[1] - center.lat) > 0.002;
				showSearchThisArea = moved || recommendations.length === 0;
			}
		}
	}

	function addMarker(e: CustomEvent<{ lngLat: { lng: number; lat: number } }>) {
		if (selected?.kind === 'place' || selected?.kind === 'recommendation') return;
		newMarker = { lngLat: e.detail.lngLat };
		newLongitude = e.detail.lngLat.lng;
		newLatitude = e.detail.lngLat.lat;
	}

	function newAdventure() {
		initialLatLng = { lat: newLatitude!, lng: newLongitude! };
		modalLocationPrefill = null;
		modalSkipQuickStart = Boolean(initialLatLng);
		createModalOpen = true;
	}

	async function openModalFromSelection() {
		initialLatLng = null;
		if (selected?.kind === 'place') {
			let place = selectedPlace ?? selected.place;
			if (place.place_id) {
				place = await enrichPlace(place);
				selectedPlace = place;
				selected = { kind: 'place', place };
			}
			modalLocationPrefill = {
				...placeToLocationPrefill(place),
				visits: [],
				collections: [],
				user: data.user ?? null,
				category: null,
				attachments: [],
				trails: [],
				is_public: false,
				is_visited: false
			} as Location;
		} else if (selected?.kind === 'recommendation') {
			modalLocationPrefill = {
				...recommendationToLocationPrefill(selected.item),
				visits: [],
				collections: [],
				user: data.user ?? null,
				category: null,
				attachments: [],
				trails: [],
				is_public: false,
				is_visited: false
			} as Location;
		} else {
			return;
		}
		modalSkipQuickStart = true;
		createModalOpen = true;
	}

	function openLodgingFromRecommendation() {
		if (selected?.kind !== 'recommendation') return;
		const rec = selected.item;
		modalLodgingPrefill = {
			id: '',
			user: data.user?.uuid ?? '',
			name: rec.name,
			type: '',
			description: rec.description,
			rating: rec.rating,
			link: rec.website || rec.google_maps_url || null,
			check_in: null,
			check_out: null,
			timezone: null,
			reservation_number: null,
			price: null,
			price_currency: null,
			latitude: rec.latitude,
			longitude: rec.longitude,
			location: rec.address || rec.description || null,
			is_public: false,
			collection: null,
			created_at: '',
			updated_at: '',
			images: (rec.photos || []).map((url, i) => googleContentImage(`rec-${i}`, url, i === 0)),
			attachments: []
		} as Lodging;
		lodgingModalOpen = true;
	}

	async function handleQuickAdd() {
		if (!selected || selected.kind === 'pin' || selected.kind === 'image') return;
		isQuickAdding = true;
		try {
			const payload =
				selected.kind === 'place'
					? placeToQuickAddPayload(selected.place)
					: recommendationToQuickAddPayload(selected.item);
			const resolved = await resolveQuickAddPayload(payload);
			const created = await quickAddLocation(resolved);
			addToast('success', $t('map.quick_add'));
			const newPin: Pin = {
				id: created.id,
				name: created.name,
				latitude: created.latitude?.toString() || '',
				longitude: created.longitude?.toString() || '',
				is_visited: created.is_visited,
				category: created.category
			};
			pins = [newPin, ...pins];
			locationCache.set(created.id, created);
			selectedPlace = null;
			recommendations = [];
			await loadPreviewForPin(created.id);
		} catch (err) {
			addToast('error', err instanceof Error ? err.message : $t('map.search_error'));
		} finally {
			isQuickAdding = false;
		}
	}

	function createNewAdventure(event: CustomEvent) {
		const location: Location = event.detail;
		const newPin: Pin = {
			id: location.id,
			name: location.name,
			latitude: location.latitude?.toString() || '',
			longitude: location.longitude?.toString() || '',
			is_visited: location.is_visited,
			category: location.category
		};
		pins = [...pins, newPin];
		locationCache.set(location.id, location);
		newMarker = null;
		createModalOpen = false;
		modalLocationPrefill = null;
		loadPreviewForPin(location.id);
	}

	function clearMarker() {
		newMarker = null;
	}

	function zoomToFilteredPins() {
		if (filteredPins.length === 0) return;
		const lngs = filteredPins
			.map((pin) => parseCoordinate(pin.longitude))
			.filter((lng): lng is number => lng !== null);
		const lats = filteredPins
			.map((pin) => parseCoordinate(pin.latitude))
			.filter((lat): lat is number => lat !== null);
		if (lngs.length === 0 || lats.length === 0) return;

		if (filteredPins.length === 1) {
			flyTo(lats[0], lngs[0], 12);
			return;
		}

		const minLng = Math.min(...lngs);
		const maxLng = Math.max(...lngs);
		const minLat = Math.min(...lats);
		const maxLat = Math.max(...lats);

		if (mapInstance) {
			mapInstance.fitBounds(
				[
					[minLng, minLat],
					[maxLng, maxLat]
				],
				{ padding: 48, duration: 600 }
			);
			return;
		}

		mapCenter = [(minLng + maxLng) / 2, (minLat + maxLat) / 2];
		const maxDiff = Math.max(maxLng - minLng, maxLat - minLat);
		if (maxDiff > 50) mapZoom = 3;
		else if (maxDiff > 20) mapZoom = 4;
		else if (maxDiff > 10) mapZoom = 5;
		else if (maxDiff > 5) mapZoom = 6;
		else if (maxDiff > 2) mapZoom = 7;
		else if (maxDiff > 1) mapZoom = 8;
		else mapZoom = 10;
		syncViewportFromProps = true;
	}

	function updateUrlParams(lat: number, lng: number, zoom: number) {
		if (typeof window === 'undefined') return;
		if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
		updateUrlTimeout = setTimeout(() => {
			const url = new URL(window.location.href);
			url.searchParams.set('lat', lat.toFixed(6));
			url.searchParams.set('lng', lng.toFixed(6));
			url.searchParams.set('zoom', zoom.toFixed(2));
			history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
		}, 500);
	}

	function persistMapView(lat: number, lng: number, zoom: number) {
		if (typeof window === 'undefined') return;
		try {
			window.localStorage.setItem(
				MAP_VIEW_STORAGE_KEY,
				JSON.stringify({ center: [lng, lat], zoom })
			);
		} catch {
			/* ignore */
		}
	}

	function handleSearchModeChange(mode: MapSearchMode) {
		searchMode = mode;
		if (mode === 'nearby') {
			showSearchThisArea = true;
			clearSelection();
			queueMicrotask(refreshMapLayout);
		} else {
			recommendations = [];
			recError = null;
			showSearchThisArea = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') clearSelection();
	}

	onMount(() => {
		return () => {
			if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
		};
	});

	onDestroy(() => {
		unbindViewportCenter?.();
	});
	let imagePinGeoJson = $derived(imageMapPinsToGeoJson(imageMapPins));
	let imagePinCount = $derived(imagePinGeoJson.features.length);
	run(() => {
		if (browser && showImagePins) {
			void ensureImageMapPinsLoaded();
		}
	});
	run(() => {
		if (locationBeingUpdated?.id) {
			const index = pins.findIndex((pin) => pin.id === locationBeingUpdated?.id);
			const pinData = {
				id: locationBeingUpdated.id,
				name: locationBeingUpdated.name,
				latitude: locationBeingUpdated.latitude?.toString() || '',
				longitude: locationBeingUpdated.longitude?.toString() || '',
				is_visited: locationBeingUpdated.is_visited,
				category: locationBeingUpdated.category
			};
			if (index !== -1) {
				pins[index] = pinData;
				pins = pins;
			} else {
				pins = [pinData, ...pins];
			}
			locationCache.set(locationBeingUpdated.id, locationBeingUpdated);
		}
	});
	let totalAdventures = $derived(pins.length);
	let visitedAdventures = $derived(pins.filter((pin) => pin.is_visited).length);
	let plannedAdventures = $derived(pins.filter((pin) => !pin.is_visited).length);
	let totalRegions = $derived(visitedRegions.length);
	let categoryFilterNames = $derived(
		typeString ? typeString.split(',').filter((item) => item !== '') : []
	);
	let isMetric = $derived(data.user?.measurement_system !== 'imperial');
	let recRadiusOptions = $derived(
		isMetric
			? [
					{ value: 1000, label: '1 km' },
					{ value: 2000, label: '2 km' },
					{ value: 5000, label: '5 km' },
					{ value: 10000, label: '10 km' },
					{ value: 20000, label: '20 km' },
					{ value: 50000, label: '50 km' }
				]
			: [
					{ value: 1609, label: '1 mi' },
					{ value: 3219, label: '2 mi' },
					{ value: 8047, label: '5 mi' },
					{ value: 16093, label: '10 mi' },
					{ value: 32187, label: '20 mi' },
					{ value: 80467, label: '50 mi' }
				]
	);
	run(() => {
		const query = searchMode === 'my' ? searchQuery.toLowerCase().trim() : '';
		filteredPins = pins.filter((pin) => {
			const statusMatch =
				(showVisited && pin.is_visited === true) || (showPlanned && pin.is_visited !== true);
			if (!statusMatch) return false;
			if (categoryFilterNames.length > 0) {
				const categoryName = pin.category?.name;
				if (!categoryName || !categoryFilterNames.includes(categoryName)) return false;
			}
			if (!query) return true;
			return (
				pin.name?.toLowerCase().includes(query) ||
				pin.category?.display_name?.toLowerCase().includes(query)
			);
		});
		if (query && filteredPins.length > 0 && typeof window !== 'undefined') {
			zoomToFilteredPins();
		}
	});
	run(() => {
		if (!newMarker) {
			newLongitude = null;
			newLatitude = null;
		}
	});
	run(() => {
		if (showActivities && activities.length === 0) fetchAllActivities();
	});
	run(() => {
		if (showCities && visitedCities.length === 0) fetchVisitedCities();
	});
	let selectedPinId = $derived(selected?.kind === 'pin' ? selected.pinId : null);
	let selectedRecId = $derived(selected?.kind === 'recommendation' ? selected.item.id : null);
	let selectedImagePinId = $derived(selected?.kind === 'image' ? selected.imageId : null);
	let previewImagePin = $derived(
		selected?.kind === 'image' ? mapImagePinSelectionToProps(selected) : null
	);
	let selectedPin = $derived(selectedPinId ? pins.find((p) => p.id === selectedPinId) : null);
	let randomEligiblePins = $derived(
		filteredPins.filter((pin) => {
			const lat = parseCoordinate(pin.latitude);
			const lng = parseCoordinate(pin.longitude);
			return lat !== null && lng !== null;
		})
	);
	let showLodgingAdd = $derived(selected?.kind === 'recommendation' && recCategory === 'lodging');
	$effect(() => {
		void sidebarOpen;
		void sidebarCollapsed;
		if (syncViewportFromProps || !mapInstance) return;
		queueMicrotask(refreshMapLayout);
	});
</script>

<svelte:head>
	<title>Location Map</title>
	<meta name="description" content="View your travels on a map." />
</svelte:head>

<svelte:window onkeydown={handleKeydown} />

<div
	bind:this={mapPageEl}
	class={[
		'map-page w-full h-[calc(100dvh-4rem)] min-h-[24rem] bg-base-200 overflow-hidden',
		sidebarCollapsed && 'sidebar-collapsed'
	]}
>
	<div class="drawer map-page-drawer h-full w-full">
		<input id="map-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div
			class="drawer-content relative h-full min-h-0 w-full overflow-hidden"
			bind:this={mapViewportEl}
		>
			<!-- Map (behind UI); pointer-events pass through toolbar gaps -->
			<div class="absolute inset-0 z-0">
				<FullMap
					bind:map={mapInstance}
					bind:basemapType
					sourceId={PIN_SOURCE_ID}
					items={filteredPins}
					toFeature={pinToFeatureUnknown}
					clusterEnabled={true}
					clusterOptions={pinClusterOptions}
					{getMarkerProps}
					mapClass="w-full h-full"
					showMapControls={false}
					zoom={syncViewportFromProps ? mapZoom : undefined}
					center={syncViewportFromProps ? mapCenter : undefined}
					on:load={handleMapLoad}
					on:mapClick={addMarker}
					on:mapMove={handleMapMove}
				>
					{#snippet marker({ markerProps, markerLngLat, isActive, setActive })}
						{#if markerProps && markerLngLat}
							{@const isSelected = selectedPinId === markerProps.id}
							<Marker
								lngLat={markerLngLat}
								class={isActive || isSelected ? 'map-pin-active' : 'map-pin'}
							>
								<div class="relative group z-[1000] group-hover:z-[10000] focus-within:z-[10000]">
									<div
										class="map-pin-hit grid place-items-center w-8 h-8 rounded-full border-2 border-white shadow-lg text-base cursor-pointer transition-all duration-200 group-hover:scale-110 {markerClassResolver(
											markerProps,
											isSelected
										)}"
										class:scale-110={isActive || isSelected}
										role="button"
										tabindex="0"
										aria-label={markerProps.name}
										aria-pressed={isSelected}
										onmouseenter={() => setActive(true)}
										onmouseleave={() => {
											if (!isSelected) setActive(false);
										}}
										onfocus={() => setActive(true)}
										onblur={() => {
											if (!isSelected) setActive(false);
										}}
										onclick={(e) => {
											e.stopPropagation();
											handlePinClick(markerProps.id, setActive);
										}}
										onkeydown={(e) => {
											if (e.key !== 'Enter') return;
											e.stopPropagation();
											handlePinClick(markerProps.id, setActive);
										}}
									>
										{markerLabelResolver(markerProps)}
									</div>

									<div
										class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 pointer-events-none group-hover:opacity-100 group-focus-within:opacity-100 transition-all duration-200 z-[9999]"
										class:opacity-100={isActive || isSelected}
									>
										<div
											class="card card-sm bg-base-100 shadow-xl border border-base-300 min-w-48 max-w-72"
										>
											<div class="card-body gap-2 p-3">
												<h3 class="font-semibold text-sm leading-tight truncate">
													{markerProps.name}
												</h3>
												<div class="flex flex-wrap items-center gap-1.5">
													<span
														class="badge badge-sm {markerProps.visitStatus === 'visited'
															? 'badge-success'
															: 'badge-info'}"
													>
														{getVisitStatusLabel(markerProps.visitStatus)}
													</span>
													{#if markerProps.categoryName}
														<span class="badge badge-ghost badge-sm">
															{markerProps.categoryName}
														</span>
													{/if}
												</div>
												<p class="text-xs text-base-content/60">{$t('map.view_details')}</p>
											</div>
										</div>
									</div>
								</div>
							</Marker>
						{/if}
					{/snippet}

					{#snippet overlays()}
						{#if newMarker}
							<DefaultMarker lngLat={newMarker.lngLat} />
						{/if}

						{#if selectedPlace}
							<DefaultMarker lngLat={[selectedPlace.lng, selectedPlace.lat]} />
						{/if}

						{#if searchMode === 'nearby'}
							<MapNearbyRadiusLayer
								visible={true}
								center={viewportCenter}
								radiusMeters={recRadius}
							/>
						{/if}

						<MapRecommendationsLayer
							{recommendations}
							selectedId={selectedRecId}
							on:select={handleSelectRecommendation}
						/>

						{#each visitedRegions as region}
							{#if showRegions}
								<Marker
									lngLat={[region.longitude, region.latitude]}
									class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-green-300 hover:bg-green-400 text-black shadow-lg cursor-pointer"
								>
									<LocationIcon class="w-5 h-5 text-green-700" />
									<Popup openOn="click" offset={[0, -10]}>
										<div class="space-y-2 text-black">
											<div class="text-lg font-bold">{region.name}</div>
											<div class="badge badge-success badge-sm">{region.region}</div>
										</div>
									</Popup>
								</Marker>
							{/if}
						{/each}

						{#if showCities}
							{#each visitedCities as city}
								<Marker
									lngLat={[city.longitude, city.latitude]}
									class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-blue-300 text-black shadow-lg"
								>
									<LocationIcon class="w-5 h-5 text-blue-700" />
									<Popup openOn="click" offset={[0, -10]}>
										<div class="space-y-2 text-black">
											<div class="text-lg font-bold">{city.name}</div>
										</div>
									</Popup>
								</Marker>
							{/each}
						{/if}

						{#if showActivities}
							{#each activities as activity}
								{#if activity.geojson}
									<GeoJSON data={activity.geojson}>
										<LineLayer
											paint={{
												'line-color': getActivityColor(activity.sport_type),
												'line-width': 3,
												'line-opacity': 0.8
											}}
										/>
									</GeoJSON>
								{/if}
							{/each}
						{/if}

						<MapImagePinLayer
							geoJson={imagePinGeoJson}
							visible={showImagePins}
							navigateOnSelect={false}
							selectedId={selectedImagePinId}
							on:select={handleImagePinSelect}
						/>
					{/snippet}
				</FullMap>
			</div>

			{#if searchMode === 'nearby'}
				<div
					class="map-ui-center absolute top-[8.75rem] sm:top-[7.5rem] lg:top-3 left-1/2 -translate-x-1/2 z-20 pointer-events-none flex flex-col items-center gap-2"
				>
					{#if recLoading}
						<div
							class="bg-base-100/95 backdrop-blur-md rounded-full px-5 py-2.5 shadow-lg border border-base-300/80 flex items-center gap-3"
						>
							<span class="loading loading-spinner loading-sm text-primary"></span>
							<span class="text-sm font-medium text-base-content">{$t('map.searching_nearby')}</span
							>
						</div>
					{:else if showSearchThisArea}
						<button
							type="button"
							class="btn btn-primary btn-sm shadow-lg pointer-events-auto gap-2"
							onclick={searchThisArea}
						>
							<Compass class="w-4 h-4" />
							{$t('map.search_this_area')}
						</button>
					{/if}
				</div>
			{/if}

			<!-- Floating map toolbar -->
			<div
				class="map-ui-left absolute top-3 left-3 right-3 z-20 flex flex-col gap-2 lg:flex-row lg:flex-wrap lg:items-start pointer-events-none min-w-0"
			>
				<div
					class="flex items-start gap-1.5 lg:gap-2 min-w-0 w-full lg:flex-1 lg:max-w-xl pointer-events-none"
				>
					<button
						type="button"
						class="btn btn-ghost btn-square btn-sm bg-base-100/90 shadow-md pointer-events-auto lg:hidden shrink-0 mt-0 relative"
						onclick={() => (sidebarOpen = !sidebarOpen)}
						aria-label={$t('map.map_controls')}
					>
						<Filter class="w-5 h-5" />
						{#if categoryFilterNames.length > 0}
							<span class="absolute top-1 right-1 w-2 h-2 rounded-full bg-primary"></span>
						{/if}
					</button>

					<div
						class="flex-1 min-w-0 pointer-events-auto bg-base-100/90 backdrop-blur-lg rounded-xl shadow-md border border-base-300 p-2 sm:p-2.5"
					>
						<MapSearchBar
							mode={searchMode}
							bind:query={searchQuery}
							{filteredPins}
							randomDisabled={randomEligiblePins.length === 0}
							on:modeChange={(e) => handleSearchModeChange(e.detail)}
							on:queryChange={(e) => (searchQuery = e.detail)}
							on:selectPin={handleSelectPin}
							on:selectPlace={handleSelectPlace}
							on:random={selectRandomLocation}
						/>
					</div>
				</div>

				<div
					class="flex items-center gap-2 justify-end w-full lg:w-auto lg:ml-auto pointer-events-none shrink-0"
				>
					{#if newMarker}
						<div class="flex items-center gap-2 pointer-events-auto shrink-0">
							<button type="button" class="btn btn-primary btn-sm gap-1" onclick={newAdventure}>
								<Plus class="w-4 h-4" />
								<span class="hidden sm:inline">{$t('map.add_location_at_marker')}</span>
							</button>
							<button type="button" class="btn btn-ghost btn-sm btn-square" onclick={clearMarker}>
								<Clear class="w-4 h-4" />
							</button>
						</div>
					{/if}

					<div class="pointer-events-auto shrink-0">
						<MapFloatingControls
							embedded
							map={mapInstance}
							bind:basemapType
							fullscreenTarget={mapPageEl}
						/>
					</div>
				</div>
			</div>
		</div>

		<!-- Sidebar: overlay drawer on mobile, floating panel on desktop -->
		<div class="drawer-side z-40">
			<label
				for="map-drawer"
				class="drawer-overlay lg:hidden"
				class:pointer-events-none={!sidebarOpen}
				aria-hidden={!sidebarOpen}
			></label>
			<div
				class="map-controls-panel w-80 h-full max-h-[calc(100dvh-4rem)] bg-base-100/95 backdrop-blur-xl flex flex-col overflow-hidden lg:overflow-visible border-base-300/80 lg:border"
			>
				<button
					type="button"
					class="map-controls-toggle hidden lg:grid place-items-center h-10 w-8 bg-base-100/95 backdrop-blur-xl border border-base-300/80 border-l-0 rounded-r-xl text-base-content/70 hover:text-base-content hover:bg-base-200/80"
					onclick={() => (sidebarCollapsed = !sidebarCollapsed)}
					aria-expanded={!sidebarCollapsed}
					aria-controls="map-controls-panel-body"
					aria-label={sidebarCollapsed ? $t('map.show_controls') : $t('map.hide_controls')}
				>
					{#if sidebarCollapsed}
						<ChevronRight class="w-5 h-5" />
					{:else}
						<ChevronLeft class="w-5 h-5" />
					{/if}
				</button>
				<div
					id="map-controls-panel-body"
					class="p-6 flex-1 min-h-0 h-full flex flex-col overflow-hidden lg:rounded-[inherit]"
				>
					{#if sidebarMode === 'preview'}
						<div class="flex items-center gap-2 mb-4 shrink-0">
							<div class="p-2 bg-primary/10 rounded-lg">
								<PinIcon class="w-5 h-5 text-primary" />
							</div>
							<h2 class="text-lg font-bold">{$t('map.preview_panel')}</h2>
						</div>
						<div class="flex-1 min-h-0 overflow-hidden flex flex-col min-w-0">
							<MapDetailPanel
								selectionKind={selected?.kind ?? null}
								location={previewLocation}
								place={selected?.kind === 'place' ? selected.place : null}
								recommendation={selected?.kind === 'recommendation' ? selected.item : null}
								imagePin={previewImagePin}
								pinName={selectedPin?.name ?? ''}
								pinVisitStatus={selectedPin?.is_visited ? 'visited' : 'planned'}
								pinCategoryIcon={selectedPin?.category?.icon ?? ''}
								loading={previewLoading}
								error={previewError}
								{isQuickAdding}
								{showLodgingAdd}
								{isMetric}
								on:back={backToControls}
								on:viewFull={handleViewFull}
								on:viewImageParent={handleViewImageParent}
								on:quickAdd={handleQuickAdd}
								on:addDetails={openModalFromSelection}
								on:addLodging={openLodgingFromRecommendation}
							/>
						</div>
					{:else}
						<div class="flex items-center gap-3 mb-6 shrink-0">
							<div class="p-2 bg-primary/10 rounded-lg">
								<Filter class="w-6 h-6 text-primary" />
							</div>
							<h2 class="text-xl font-bold">{$t('map.map_controls')}</h2>
						</div>

						<div class="flex-1 overflow-y-auto min-h-0 space-y-4">
							<div class="card bg-base-200/50 p-3">
								<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
									<MapIcon class="w-5 h-5" />
									{$t('map.stats')}
								</h3>
								<div class="grid grid-cols-3 gap-2">
									<div class="text-center min-w-0">
										<div class="text-[10px] uppercase tracking-wide text-base-content/50 truncate">
											{$t('locations.locations')}
										</div>
										<div class="text-lg font-bold leading-tight">{totalAdventures}</div>
									</div>
									<div class="text-center min-w-0">
										<div class="text-[10px] uppercase tracking-wide text-base-content/50 truncate">
											{$t('adventures.visited')}
										</div>
										<div class="text-lg font-bold leading-tight text-success">
											{visitedAdventures}
										</div>
									</div>
									<div class="text-center min-w-0">
										<div class="text-[10px] uppercase tracking-wide text-base-content/50 truncate">
											{$t('adventures.planned')}
										</div>
										<div class="text-lg font-bold leading-tight text-info">{plannedAdventures}</div>
									</div>
								</div>
								{#if totalAdventures > 0}
									<progress
										class="progress progress-primary progress-xs w-full mt-2"
										value={visitedAdventures}
										max={totalAdventures}
									></progress>
								{/if}
							</div>

							{#if searchMode === 'nearby'}
								<div class="card bg-base-200/50 p-4">
									<h3 class="font-semibold mb-3 flex items-center gap-2">
										<Compass class="w-5 h-5" />
										{$t('map.nearby_controls')}
									</h3>
									<div class="space-y-3">
										<div class="flex flex-col">
											<label class="field-label text-xs" for="rec-category"
												>{$t('map.recommendation_category')}</label
											>
											<select
												id="rec-category"
												class="select select-sm w-full"
												bind:value={recCategory}
											>
												<option value="tourism">🏛️ {$t('recomendations.tourism')}</option>
												<option value="food">🍴 {$t('recomendations.food')}</option>
												<option value="lodging">🏨 {$t('recomendations.lodging')}</option>
											</select>
										</div>
										<div class="flex flex-col">
											<label class="field-label text-xs" for="rec-radius"
												>{$t('map.recommendation_radius')}</label
											>
											<select
												id="rec-radius"
												class="select select-sm w-full"
												bind:value={recRadius}
											>
												{#each recRadiusOptions as opt}
													<option value={opt.value}>{opt.label}</option>
												{/each}
											</select>
										</div>
										<button
											type="button"
											class="btn btn-primary btn-sm w-full"
											disabled={recLoading}
											onclick={searchThisArea}
										>
											{$t('map.search_this_area')}
										</button>
										{#if recError}
											<div class="alert alert-warning alert-soft py-2 text-xs">{recError}</div>
										{:else if recommendations.length > 0}
											<p class="text-xs text-base-content/60">
												{$t('map.recommendations_count', {
													values: { count: recommendations.length }
												})}
											</p>
											<ul class="menu menu-sm bg-base-100 rounded-box max-h-40 overflow-y-auto">
												{#each recommendations.slice(0, 12) as rec (rec.id)}
													<li>
														<button
															type="button"
															class={selectedRecId === rec.id ? 'active' : ''}
															onclick={() => selectRecommendation(rec)}
														>
															<span class="truncate">{rec.name}</span>
														</button>
													</li>
												{/each}
											</ul>
										{/if}
									</div>
								</div>
							{/if}

							<div class="card bg-base-200/50 p-4">
								<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
									<Tag class="w-5 h-5" />
									{$t('adventures.categories')}
								</h3>
								<CategoryFilterDropdown bind:types={typeString} />
							</div>

							<div class="card bg-base-200/50 p-4">
								<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
									<Eye class="w-5 h-5" />
									{$t('map.display_options')}
								</h3>
								<div class="flex flex-col">
									<label class="filter-option">
										<input
											type="checkbox"
											bind:checked={showVisited}
											class="checkbox checkbox-success"
										/>
										<span class="text-sm leading-snug min-w-0"
											>{$t('adventures.visited')} ({visitedAdventures})</span
										>
									</label>
									<label class="filter-option">
										<input
											type="checkbox"
											bind:checked={showPlanned}
											class="checkbox checkbox-info"
										/>
										<span class="text-sm leading-snug min-w-0"
											>{$t('adventures.planned')} ({plannedAdventures})</span
										>
									</label>
									<label class="filter-option">
										<input
											type="checkbox"
											bind:checked={showRegions}
											class="checkbox checkbox-accent"
										/>
										<span class="text-sm leading-snug min-w-0"
											>{$t('profile.visited_regions')} ({totalRegions})</span
										>
									</label>
									<label class="filter-option">
										<input
											type="checkbox"
											bind:checked={showCities}
											class="checkbox checkbox-warning"
										/>
										<span class="text-sm leading-snug min-w-0">{$t('map.show_visited_cities')}</span
										>
									</label>
									<label class="filter-option">
										<input
											type="checkbox"
											bind:checked={showImagePins}
											class="checkbox checkbox-secondary"
										/>
										<span class="text-sm leading-snug min-w-0">
											{$t('map.photos')}{#if imagePinsLoaded}
												{' '}({imagePinCount}){/if}
										</span>
									</label>
									<label class="filter-option">
										<input
											type="checkbox"
											bind:checked={showActivities}
											class="checkbox checkbox-error"
										/>
										<span class="text-sm leading-snug min-w-0">{$t('settings.activities')}</span>
									</label>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>

{#if createModalOpen}
	<NewLocationModal
		on:close={() => {
			createModalOpen = false;
			modalLocationPrefill = null;
		}}
		on:save={createNewAdventure}
		on:create={createNewAdventure}
		{initialLatLng}
		user={data.user}
		locationToEdit={modalLocationPrefill}
		skipQuickStart={modalSkipQuickStart}
		bind:location={locationBeingUpdated}
	/>
{/if}

{#if lodgingModalOpen && modalLodgingPrefill}
	<LodgingModal
		user={data.user}
		lodgingToEdit={modalLodgingPrefill}
		on:close={() => {
			lodgingModalOpen = false;
			modalLodgingPrefill = null;
		}}
		on:save={() => {
			lodgingModalOpen = false;
			modalLodgingPrefill = null;
			addToast('success', $t('map.add_as_lodging'));
		}}
	/>
{/if}

<style>
	.map-page {
		--map-float-inset: 0.75rem;
		--map-float-width: 20rem;
		--map-float-gutter: calc(var(--map-float-inset) + var(--map-float-width) + 0.75rem);
	}

	.map-page:fullscreen,
	.map-page:-webkit-full-screen {
		width: 100%;
		height: 100%;
		max-height: none;
		min-height: 100%;
		background-color: var(--color-base-200);
	}

	.map-page:fullscreen .map-page-drawer,
	.map-page:-webkit-full-screen .map-page-drawer,
	.map-page:fullscreen .drawer-content,
	.map-page:-webkit-full-screen .drawer-content {
		width: 100%;
		height: 100%;
	}

	@media (min-width: 1024px) {
		.map-page-drawer {
			display: block;
			position: relative;
		}

		.drawer-content {
			width: 100%;
			height: 100%;
		}

		.drawer-side {
			pointer-events: none;
			visibility: visible;
			opacity: 1;
			position: absolute;
			inset: 0;
			width: 100%;
			height: 100%;
			overflow: visible;
			background: transparent;
			z-index: 30;
		}

		.drawer-overlay {
			display: none;
		}

		.drawer-side > .map-controls-panel {
			pointer-events: auto;
			translate: 0;
			will-change: transform;
			width: var(--map-float-width);
			height: calc(100% - (var(--map-float-inset) * 2));
			max-height: none;
			margin: var(--map-float-inset);
			border-radius: 1rem;
			overflow: visible;
			transition: translate 0.28s cubic-bezier(0.22, 1, 0.36, 1);
		}

		.map-controls-toggle {
			position: absolute;
			top: 50%;
			right: 0;
			translate: 100% -50%;
			z-index: 2;
		}

		.map-ui-left,
		.map-ui-center {
			transition: left 0.28s cubic-bezier(0.22, 1, 0.36, 1);
		}

		.map-ui-left {
			left: var(--map-float-gutter);
		}

		.map-ui-center {
			left: calc(50% + (var(--map-float-gutter) / 2));
		}

		.sidebar-collapsed {
			--map-float-gutter: var(--map-float-inset);
		}

		.sidebar-collapsed .drawer-side > .map-controls-panel {
			translate: calc(-1 * (var(--map-float-width) + var(--map-float-inset)));
		}

		.sidebar-collapsed .map-controls-toggle {
			border-left-width: 1px;
			border-top-left-radius: 0.75rem;
			border-bottom-left-radius: 0.75rem;
		}
	}

	:global(.maplibregl-marker.map-pin),
	:global(.mapboxgl-marker.map-pin) {
		pointer-events: none;
	}

	:global(.maplibregl-marker.map-pin .map-pin-hit),
	:global(.mapboxgl-marker.map-pin .map-pin-hit) {
		pointer-events: auto;
	}
</style>
