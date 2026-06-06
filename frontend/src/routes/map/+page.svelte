<script lang="ts">
	import { DefaultMarker, Popup, Marker, GeoJSON, LineLayer } from 'svelte-maplibre';
	import MapNearbyRadiusLayer from '$lib/components/map/MapNearbyRadiusLayer.svelte';
	import { onDestroy, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
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
	import {
		enrichPlace,
		fetchRecommendations,
		placeToLocationPrefill,
		placeToQuickAddPayload,
		quickAddLocation,
		recommendationToLocationPrefill,
		recommendationToQuickAddPayload
	} from '$lib/map/places';

	import MapIcon from '~icons/mdi/map';
	import Filter from '~icons/mdi/filter-variant';
	import Plus from '~icons/mdi/plus';
	import Clear from '~icons/mdi/close';
	import Eye from '~icons/mdi/eye';
	import PinIcon from '~icons/mdi/map-marker';
	import Calendar from '~icons/mdi/calendar';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';
	import LodgingModal from '$lib/components/lodging/LodgingModal.svelte';
	import ActivityIcon from '~icons/mdi/run-fast';
	import FullMap from '$lib/components/map/FullMap.svelte';
	import MapSearchBar from '$lib/components/map/MapSearchBar.svelte';
	import MapDetailPanel from '$lib/components/map/MapDetailPanel.svelte';
	import MapRecommendationsLayer from '$lib/components/map/MapRecommendationsLayer.svelte';
	import MapFloatingControls from '$lib/components/map/MapFloatingControls.svelte';
	import Compass from '~icons/mdi/compass';

	export let data;

	let createModalOpen = false;
	let lodgingModalOpen = false;
	let showRegions = false;
	let showActivities = false;
	let showCities = false;
	let sidebarOpen = false;
	let sidebarMode: 'controls' | 'preview' = 'controls';

	let basemapType: string = normalizeBasemapType(data.user?.map_style);

	let mapZoom: number = 2;
	let mapCenter: [number, number] = [0, 0];
	/** When true, center/zoom props drive FullMap. Disabled after load so pan/zoom is not fought by easeTo. */
	let syncViewportFromProps = true;
	let mapInstance: maplibregl.Map | undefined = undefined;
	let mapViewportEl: HTMLElement | null = null;
	let updateUrlTimeout: NodeJS.Timeout | null = null;
	const MAP_VIEW_STORAGE_KEY = 'adventurelog.map.view';

	export let initialLatLng: { lat: number; lng: number } | null = null;

	let visitedRegions: VisitedRegion[] = data.props.visitedRegions;
	let visitedCities: VisitedCity[] = [];
	let pins: Pin[] = data.props.pins;
	let activities: Activity[] = [];
	let filteredPins = pins;

	let showVisited = true;
	let showPlanned = true;
	let searchMode: MapSearchMode = 'my';
	let searchQuery = '';
	let selected: MapSelection | null = null;
	let selectedPlace: PlaceSearchResult | null = null;
	let recommendations: Recommendation[] = [];
	let recCategory: 'tourism' | 'food' | 'lodging' = 'tourism';
	let recRadius = 5000;
	let recLoading = false;
	let recError: string | null = null;
	let showSearchThisArea = false;
	let lastRecSearchCenter: [number, number] | null = null;
	let viewportCenter: { lng: number; lat: number } = { lng: 0, lat: 0 };
	let unbindViewportCenter: (() => void) | null = null;

	let newMarker: { lngLat: { lng: number; lat: number } } | null = null;
	let newLongitude: number | null = null;
	let newLatitude: number | null = null;

	let locationCache: Map<string, Location> = new Map();
	let locationRequests: Map<string, Promise<Location | null>> = new Map();
	let previewLocation: Location | null = null;
	let previewLoading = false;
	let previewError: string | null = null;
	let previewRequestSeq = 0;

	let isQuickAdding = false;
	let locationBeingUpdated: Location | undefined = undefined;
	let modalLocationPrefill: Location | null = null;
	let modalLodgingPrefill: Lodging | null = null;
	let modalSkipQuickStart = false;

	const PIN_SOURCE_ID = 'map-pins';
	const pinClusterOptions: ClusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 };

	type VisitStatus = 'visited' | 'planned';

	type PinFeatureProperties = {
		id: string;
		name: string;
		visitStatus: VisitStatus;
		categoryIcon?: string;
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
				categoryIcon: pin.category?.icon || '📍'
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

	$: totalAdventures = pins.length;
	$: visitedAdventures = pins.filter((pin) => pin.is_visited).length;
	$: plannedAdventures = pins.filter((pin) => !pin.is_visited).length;
	$: totalRegions = visitedRegions.length;

	$: isMetric = data.user?.measurement_system !== 'imperial';
	$: recRadiusOptions = isMetric
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
			];

	$: {
		const query = searchMode === 'my' ? searchQuery.toLowerCase().trim() : '';
		filteredPins = pins.filter((pin) => {
			const statusMatch =
				(showVisited && pin.is_visited === true) || (showPlanned && pin.is_visited !== true);
			if (!statusMatch) return false;
			if (!query) return true;
			return (
				pin.name?.toLowerCase().includes(query) ||
				pin.category?.display_name?.toLowerCase().includes(query)
			);
		});
		if (query && filteredPins.length > 0 && typeof window !== 'undefined') {
			zoomToFilteredPins();
		}
	}

	$: {
		if (!newMarker) {
			newLongitude = null;
			newLatitude = null;
		}
	}

	$: {
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
	}

	$: {
		if (showActivities && activities.length === 0) fetchAllActivities();
	}
	$: {
		if (showCities && visitedCities.length === 0) fetchVisitedCities();
	}

	$: selectedPinId = selected?.kind === 'pin' ? selected.pinId : null;
	$: selectedRecId = selected?.kind === 'recommendation' ? selected.item.id : null;
	$: selectedPin = selectedPinId ? pins.find((p) => p.id === selectedPinId) : null;

	$: showLodgingAdd = selected?.kind === 'recommendation' && recCategory === 'lodging';

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

	async function loadPreviewForPin(pinId: string) {
		selected = { kind: 'pin', pinId };
		selectedPlace = null;
		sidebarMode = 'preview';
		if (typeof window !== 'undefined' && window.innerWidth < 1024) {
			sidebarOpen = true;
		}

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

	function attachViewportCenterSync() {
		if (!mapInstance) return;
		unbindViewportCenter?.();
		unbindViewportCenter = bindMapViewportCenterSync(mapInstance, (center) => {
			viewportCenter = center;
		});
	}

	function handleMapLoad() {
		syncViewportFromProps = false;
		attachViewportCenterSync();
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

	async function handleSelectPlace(event: CustomEvent<{ place: PlaceSearchResult }>) {
		let place = event.detail.place;
		selectedPlace = place;
		selected = { kind: 'place', place };
		sidebarMode = 'preview';
		if (typeof window !== 'undefined' && window.innerWidth < 1024) {
			sidebarOpen = true;
		}
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
		if (typeof window !== 'undefined' && window.innerWidth < 1024) {
			sidebarOpen = true;
		}
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
		const { lat, lng } = getMapViewportCenter(mapInstance);
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
		const { center, zoom } = e.detail;
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
			images: (rec.photos || []).map((url, i) => ({
				id: `rec-${i}`,
				image: url,
				is_primary: i === 0,
				immich_id: null
			})),
			attachments: []
		} as Lodging;
		lodgingModalOpen = true;
	}

	async function handleQuickAdd() {
		if (!selected || selected.kind === 'pin') return;
		isQuickAdding = true;
		try {
			const payload =
				selected.kind === 'place'
					? placeToQuickAddPayload(selected.place)
					: recommendationToQuickAddPayload(selected.item);
			const created = await quickAddLocation(payload);
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
		const params = $page.url.searchParams;
		const lat = params.get('lat');
		const lng = params.get('lng');
		const zoom = params.get('zoom');

		if (lat && lng && zoom) {
			const parsedLat = parseFloat(lat);
			const parsedLng = parseFloat(lng);
			const parsedZoom = parseFloat(zoom);
			if (Number.isFinite(parsedLat) && Number.isFinite(parsedLng) && Number.isFinite(parsedZoom)) {
				mapCenter = [parsedLng, parsedLat];
				mapZoom = parsedZoom;
				return () => {
					if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
				};
			}
		}

		const storedView = readStoredMapView();
		if (storedView) {
			mapCenter = storedView.center;
			mapZoom = storedView.zoom;
		}

		return () => {
			if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
		};
	});

	onDestroy(() => {
		unbindViewportCenter?.();
	});
</script>

<svelte:head>
	<title>Location Map</title>
	<meta name="description" content="View your travels on a map." />
</svelte:head>

<svelte:window on:keydown={handleKeydown} />

<div class="w-full h-[calc(100dvh-4rem)] min-h-[24rem] bg-base-200 overflow-hidden">
	<div class="drawer lg:drawer-open h-full w-full">
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
					<svelte:fragment
						slot="marker"
						let:markerProps
						let:markerLngLat
						let:isActive
						let:setActive
					>
						{#if markerProps && markerLngLat}
							{@const isSelected = selectedPinId === markerProps.id}
							<Marker
								lngLat={markerLngLat}
								class={isActive || isSelected ? 'map-pin-active' : 'map-pin'}
							>
								<div class="relative z-[1000]">
									<div
										class="map-pin-hit grid place-items-center w-8 h-8 rounded-full border-2 border-white shadow-lg text-base cursor-pointer transition-all duration-200 hover:scale-110 {markerClassResolver(
											markerProps,
											isSelected
										)}"
										class:scale-110={isActive || isSelected}
										role="button"
										tabindex="0"
										aria-label={markerProps.name}
										aria-pressed={isSelected}
										on:click={(e) => {
											e.stopPropagation();
											handlePinClick(markerProps.id, setActive);
										}}
										on:keydown={(e) => {
											if (e.key !== 'Enter') return;
											e.stopPropagation();
											handlePinClick(markerProps.id, setActive);
										}}
									>
										{markerLabelResolver(markerProps)}
									</div>
								</div>
							</Marker>
						{/if}
					</svelte:fragment>

					<svelte:fragment slot="overlays">
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
					</svelte:fragment>
				</FullMap>
			</div>

			{#if searchMode === 'nearby'}
				<div
					class="absolute top-3 left-1/2 -translate-x-1/2 z-20 pointer-events-none flex flex-col items-center gap-2"
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
							on:click={searchThisArea}
						>
							<Compass class="w-4 h-4" />
							{$t('map.search_this_area')}
						</button>
					{/if}
				</div>
			{/if}

			<!-- Floating map toolbar -->
			<div
				class="absolute top-3 left-3 right-3 z-20 flex flex-wrap items-start gap-1.5 sm:gap-2 pointer-events-none min-w-0"
			>
				<button
					type="button"
					class="btn btn-ghost btn-square btn-sm bg-base-100/90 shadow-md pointer-events-auto lg:hidden shrink-0 mt-0"
					on:click={() => (sidebarOpen = !sidebarOpen)}
					aria-label={$t('map.map_controls')}
				>
					<Filter class="w-5 h-5" />
				</button>

				<div
					class="flex-1 min-w-0 max-w-full sm:max-w-xl pointer-events-auto bg-base-100/90 backdrop-blur-lg rounded-xl shadow-md border border-base-300 p-2 sm:p-2.5"
				>
					<MapSearchBar
						mode={searchMode}
						bind:query={searchQuery}
						{filteredPins}
						on:modeChange={(e) => handleSearchModeChange(e.detail)}
						on:queryChange={(e) => (searchQuery = e.detail)}
						on:selectPin={handleSelectPin}
						on:selectPlace={handleSelectPlace}
					/>
				</div>

				{#if newMarker}
					<div class="flex items-center gap-2 pointer-events-auto shrink-0">
						<button type="button" class="btn btn-primary btn-sm gap-1" on:click={newAdventure}>
							<Plus class="w-4 h-4" />
							<span class="hidden sm:inline">{$t('map.add_location_at_marker')}</span>
						</button>
						<button type="button" class="btn btn-ghost btn-sm btn-square" on:click={clearMarker}>
							<Clear class="w-4 h-4" />
						</button>
					</div>
				{/if}

				<div class="shrink-0 ml-auto pointer-events-auto order-last sm:order-none">
					<MapFloatingControls
						embedded
						map={mapInstance}
						bind:basemapType
						fullscreenTarget={mapViewportEl}
					/>
				</div>
			</div>

			<!-- Compact title badge -->
			<div
				class="absolute bottom-3 left-3 z-20 pointer-events-none hidden sm:flex items-center gap-2 bg-base-100/80 backdrop-blur rounded-lg px-3 py-1.5 border border-base-300 shadow-sm"
			>
				<MapIcon class="w-5 h-5 text-primary" />
				<span class="text-sm font-semibold text-primary">{$t('map.location_map')}</span>
				<span class="text-xs text-base-content/60">
					{filteredPins.length}
					{$t('map.locations_shown')}
				</span>
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-40">
			<label
				for="map-drawer"
				class="drawer-overlay lg:hidden"
				class:pointer-events-none={!sidebarOpen}
				aria-hidden={!sidebarOpen}
			></label>
			<div
				class="w-80 h-full max-h-[calc(100dvh-4rem)] bg-base-100 shadow-2xl flex flex-col overflow-hidden"
			>
				<div class="p-6 flex-1 min-h-0 flex flex-col overflow-hidden">
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

						<div class="flex-1 overflow-y-auto min-h-0 space-y-6">
							<div class="card bg-base-200/50 p-4">
								<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
									<MapIcon class="w-5 h-5" />
									{$t('map.adventure_stats')}
								</h3>
								<div class="space-y-3">
									<div class="stat p-0">
										<div class="stat-title text-sm">{$t('dashboard.total_adventures')}</div>
										<div class="stat-value text-2xl">{totalAdventures}</div>
									</div>
									<div class="grid grid-cols-2 gap-3">
										<div class="stat p-0">
											<div class="stat-title text-xs">{$t('adventures.visited')}</div>
											<div class="stat-value text-lg text-success">{visitedAdventures}</div>
										</div>
										<div class="stat p-0">
											<div class="stat-title text-xs">{$t('adventures.planned')}</div>
											<div class="stat-value text-lg text-info">{plannedAdventures}</div>
										</div>
									</div>
									{#if totalAdventures > 0}
										<progress
											class="progress progress-primary w-full"
											value={visitedAdventures}
											max={totalAdventures}
										></progress>
									{/if}
								</div>
							</div>

							{#if searchMode === 'nearby'}
								<div class="card bg-base-200/50 p-4">
									<h3 class="font-semibold mb-3 flex items-center gap-2">
										<Compass class="w-5 h-5" />
										{$t('map.nearby_controls')}
									</h3>
									<div class="space-y-3">
										<div class="form-control">
											<label class="label py-0" for="rec-category">
												<span class="label-text text-xs">{$t('map.recommendation_category')}</span>
											</label>
											<select
												id="rec-category"
												class="select select-bordered select-sm w-full"
												bind:value={recCategory}
											>
												<option value="tourism">🏛️ {$t('recomendations.tourism')}</option>
												<option value="food">🍴 {$t('recomendations.food')}</option>
												<option value="lodging">🏨 {$t('recomendations.lodging')}</option>
											</select>
										</div>
										<div class="form-control">
											<label class="label py-0" for="rec-radius">
												<span class="label-text text-xs">{$t('map.recommendation_radius')}</span>
											</label>
											<select
												id="rec-radius"
												class="select select-bordered select-sm w-full"
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
											on:click={searchThisArea}
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
															on:click={() => selectRecommendation(rec)}
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
									<Eye class="w-5 h-5" />
									{$t('map.display_options')}
								</h3>
								<div class="space-y-3">
									<label class="label cursor-pointer justify-start gap-3 py-1">
										<input
											type="checkbox"
											bind:checked={showVisited}
											class="checkbox checkbox-success checkbox-sm"
										/>
										<span class="label-text">{$t('adventures.visited')} ({visitedAdventures})</span>
									</label>
									<label class="label cursor-pointer justify-start gap-3 py-1">
										<input
											type="checkbox"
											bind:checked={showPlanned}
											class="checkbox checkbox-info checkbox-sm"
										/>
										<span class="label-text">{$t('adventures.planned')} ({plannedAdventures})</span>
									</label>
									<label class="label cursor-pointer justify-start gap-3 py-1">
										<input
											type="checkbox"
											bind:checked={showRegions}
											class="checkbox checkbox-accent checkbox-sm"
										/>
										<span class="label-text">{$t('profile.visited_regions')} ({totalRegions})</span>
									</label>
									<label class="label cursor-pointer justify-start gap-3 py-1">
										<input
											type="checkbox"
											bind:checked={showCities}
											class="checkbox checkbox-warning checkbox-sm"
										/>
										<span class="label-text">{$t('map.show_visited_cities')}</span>
									</label>
									<label class="label cursor-pointer justify-start gap-3 py-1">
										<input
											type="checkbox"
											bind:checked={showActivities}
											class="checkbox checkbox-error checkbox-sm"
										/>
										<span class="label-text">{$t('settings.activities')}</span>
									</label>
								</div>
							</div>

							<div class="card bg-base-200/50 p-4">
								<h3 class="font-semibold text-lg mb-3 flex items-center gap-2">
									<Plus class="w-5 h-5" />
									{$t('adventures.new_location')}
								</h3>
								{#if newMarker}
									<div class="space-y-2">
										<div class="alert alert-info py-2">
											<span class="text-xs">{$t('map.marker_placed_on_map')}</span>
										</div>
										<button
											type="button"
											class="btn btn-primary btn-sm w-full"
											on:click={newAdventure}
										>
											{$t('map.add_location_at_marker')}
										</button>
									</div>
								{:else}
									<p class="text-xs text-base-content/60 mb-2">
										{$t('map.place_marker_desc_location')}
									</p>
									<button
										type="button"
										class="btn btn-primary btn-sm w-full"
										on:click={() => {
											modalLocationPrefill = null;
											modalSkipQuickStart = false;
											createModalOpen = true;
										}}
									>
										{$t('map.add_location')}
									</button>
								{/if}
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
	:global(.maplibregl-marker.map-pin),
	:global(.mapboxgl-marker.map-pin) {
		pointer-events: none;
	}

	:global(.maplibregl-marker.map-pin .map-pin-hit),
	:global(.mapboxgl-marker.map-pin .map-pin-hit) {
		pointer-events: auto;
	}
</style>
