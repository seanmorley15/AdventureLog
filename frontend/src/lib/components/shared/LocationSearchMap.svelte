<script context="module" lang="ts">
	// Search mode type for transportation - exported for use in other components
	export type SearchMode = 'location' | 'airport' | 'train' | 'bus' | 'cab' | 'vtc';

	// Type for unified search results with source grouping
	export type UnifiedSearchResult = {
		id?: string;
		name: string;
		display_name: string;
		lat: number;
		lon: number;
		type?: string;
		category?: string;
		code?: string | null;
		source: 'address' | 'location' | 'lodging' | 'departure' | 'arrival';
	};
</script>

<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { MapLibre, Marker, MapEvents } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { getBasemapUrl } from '$lib';

	import SearchIcon from '~icons/mdi/magnify';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import MapIcon from '~icons/mdi/map';
	import CheckIcon from '~icons/mdi/check';
	import ClearIcon from '~icons/mdi/close';
	import PinIcon from '~icons/mdi/map-marker';
	import AirplaneIcon from '~icons/mdi/airplane';
	import TrainIcon from '~icons/mdi/train';
	import BusIcon from '~icons/mdi/bus';
	import TaxiIcon from '~icons/mdi/taxi';
	import LimoIcon from '~icons/mdi/car-estate';
	import SwapIcon from '~icons/mdi/swap-horizontal';
	import BedIcon from '~icons/mdi/bed';
	import DepartureIcon from '~icons/mdi/arrow-top-right';
	import ArrivalIcon from '~icons/mdi/arrow-bottom-left';

	// Search mode configuration
	const SEARCH_MODE_CONFIG: Record<SearchMode, {
		suffix: string;
		departureLabel: string;
		arrivalLabel: string;
		placeholder: string;
		icon: any;
	}> = {
		location: {
			suffix: '',
			departureLabel: 'adventures.start_location',
			arrivalLabel: 'adventures.end_location',
			placeholder: 'transportation.enter_from_location',
			icon: PinIcon
		},
		airport: {
			suffix: ' Airport',
			departureLabel: 'adventures.departure_airport',
			arrivalLabel: 'adventures.arrival_airport',
			placeholder: 'adventures.airport_code_examples',
			icon: AirplaneIcon
		},
		train: {
			suffix: ' Station',
			departureLabel: 'adventures.departure_station',
			arrivalLabel: 'adventures.arrival_station',
			placeholder: 'adventures.station_name_examples',
			icon: TrainIcon
		},
		bus: {
			suffix: ' Bus Station',
			departureLabel: 'adventures.departure_stop',
			arrivalLabel: 'adventures.arrival_stop',
			placeholder: 'adventures.bus_stop_examples',
			icon: BusIcon
		},
		cab: {
			suffix: '',
			departureLabel: 'adventures.pickup_location',
			arrivalLabel: 'adventures.dropoff_location',
			placeholder: 'adventures.address_examples',
			icon: TaxiIcon
		},
		vtc: {
			suffix: '',
			departureLabel: 'adventures.pickup_location',
			arrivalLabel: 'adventures.dropoff_location',
			placeholder: 'adventures.address_examples',
			icon: LimoIcon
		}
	};

	type GeoSelection = {
		name: string;
		lat: number;
		lng: number;
		location: string;
		type?: string;
		category?: string;
	};

	type LocationMeta = {
		city?: { name: string; id: string; visited: boolean };
		region?: { name: string; id: string; visited: boolean };
		country?: { name: string; country_code: string; visited: boolean };
		display_name?: string;
		location_name?: string;
	};

	const dispatch = createEventDispatcher();

	export let initialSelection: GeoSelection | null = null;
	export let searchQuery = '';
	export let displayName = '';
	export let showDisplayNameInput = true;
	export let displayNamePosition: 'before' | 'after' = 'before';
	export let displayNameLabel = '';
	export let displayNamePlaceholder = '';
	export let isReverseGeocoding = false;
	export let transportationMode = false; // New prop for transportation mode
	export let searchMode: SearchMode = 'location'; // Search mode for transportation
	// Props for initial transportation locations when editing
	export let initialStartLocation: {
		name: string;
		lat: number;
		lng: number;
		location: string;
	} | null = null;
	export let initialEndLocation: {
		name: string;
		lat: number;
		lng: number;
		location: string;
	} | null = null;
	export let initialStartCode: string | null = null;
	export let initialEndCode: string | null = null;
	// Enable unified search to include user's locations and lodgings
	export let unifiedSearch = false;

	let isSearching = false;
	let searchResults: GeoSelection[] = [];
	// Grouped results for unified search mode
	let unifiedResults: {
		addresses: UnifiedSearchResult[];
		locations: UnifiedSearchResult[];
		lodging: UnifiedSearchResult[];
		departures: UnifiedSearchResult[];
		arrivals: UnifiedSearchResult[];
	} = { addresses: [], locations: [], lodging: [], departures: [], arrivals: [] };
	let selectedLocation: GeoSelection | null = null;
	let selectedMarker: { lng: number; lat: number } | null = null;
	let locationData: LocationMeta | null = null;
	let mapCenter: [number, number] = [-74.5, 40];
	let mapZoom: number | undefined = 2;
	let mapBounds: [[number, number], [number, number]] | null = null;
	let mapComponent: any;
	let searchTimeout: ReturnType<typeof setTimeout>;
	let initialApplied = false;
	let initialTransportationApplied = false;
	let isInitializing = false;

	// Track any provided codes (airport / station / etc)
	let startCode: string | null = null;
	let endCode: string | null = null;

	// track previous search mode to detect toggles
	let prevSearchMode = searchMode;
	let searchModeInitialized = false;

	// Clear inputs/selections when searchMode is changed (but not during initial setup)
	$: if (prevSearchMode !== searchMode) {
		prevSearchMode = searchMode;

		// Only clear if this is not the first time searchMode is being set
		// This prevents wiping out initial location data when editing existing transportations
		if (searchModeInitialized) {
			// clear single-location search state
			searchQuery = '';
			searchResults = [];
			selectedLocation = null;
			selectedMarker = null;
			locationData = null;

			// clear transportation-mode search state
			startSearchQuery = '';
			endSearchQuery = '';
			startSearchResults = [];
			endSearchResults = [];
			selectedStartLocation = null;
			selectedEndLocation = null;
			startMarker = null;
			endMarker = null;
			mapBounds = null;
			startLocationData = null;
			startCode = null;
			endCode = null;
			endLocationData = null;
		}

		searchModeInitialized = true;
	}

	// Helper to check if we're in a station/airport mode (not plain location)
	// Modes that show codes/badges: airport, train, bus (not cab/vtc which behave like address)
	$: isStationMode = searchMode === 'airport' || searchMode === 'train' || searchMode === 'bus';
	$: isAirportMode = searchMode === 'airport';

	// Transportation mode variables
	let startSearchQuery = '';
	let endSearchQuery = '';
	let startSearchResults: (GeoSelection & { source?: string })[] = [];
	let endSearchResults: (GeoSelection & { source?: string })[] = [];
	// Grouped results for unified search in transportation mode
	let startUnifiedResults: {
		addresses: UnifiedSearchResult[];
		locations: UnifiedSearchResult[];
		lodging: UnifiedSearchResult[];
		departures: UnifiedSearchResult[];
		arrivals: UnifiedSearchResult[];
	} = { addresses: [], locations: [], lodging: [], departures: [], arrivals: [] };
	let endUnifiedResults: {
		addresses: UnifiedSearchResult[];
		locations: UnifiedSearchResult[];
		lodging: UnifiedSearchResult[];
		departures: UnifiedSearchResult[];
		arrivals: UnifiedSearchResult[];
	} = { addresses: [], locations: [], lodging: [], departures: [], arrivals: [] };
	let selectedStartLocation: GeoSelection | null = null;
	let selectedEndLocation: GeoSelection | null = null;
	let startMarker: { lng: number; lat: number } | null = null;
	let endMarker: { lng: number; lat: number } | null = null;
	let startLocationData: LocationMeta | null = null;
	let endLocationData: LocationMeta | null = null;
	let isSearchingStart = false;
	let isSearchingEnd = false;
	let startSearchTimeout: ReturnType<typeof setTimeout>;
	let endSearchTimeout: ReturnType<typeof setTimeout>;

	async function applyInitialSelection(selection: GeoSelection) {
		selectedLocation = selection;
		selectedMarker = { lng: selection.lng, lat: selection.lat };
		mapCenter = [selection.lng, selection.lat];
		mapZoom = 14;
		searchQuery = selection.location || selection.name || '';
		displayName = selection.location || selection.name;
		await performDetailedReverseGeocode(selection.lat, selection.lng);
	}

	async function applyInitialTransportationLocations() {
		isInitializing = true;

		if (initialStartLocation) {
			selectedStartLocation = {
				name: initialStartLocation.name,
				lat: initialStartLocation.lat,
				lng: initialStartLocation.lng,
				location: initialStartLocation.location
			};
			startMarker = { lng: initialStartLocation.lng, lat: initialStartLocation.lat };
			if (isStationMode) {
				startCode =
					initialStartCode || deriveCode(initialStartLocation.name, initialStartLocation.name);
				startSearchQuery = startCode || initialStartLocation.location || initialStartLocation.name;
			} else {
				startCode = null;
				startSearchQuery = initialStartLocation.location || initialStartLocation.name;
			}
			// Never perform reverse geocoding when we have initial location data
			// to avoid overwriting airport names with generic locations
		}

		if (initialEndLocation) {
			selectedEndLocation = {
				name: initialEndLocation.name,
				lat: initialEndLocation.lat,
				lng: initialEndLocation.lng,
				location: initialEndLocation.location
			};
			endMarker = { lng: initialEndLocation.lng, lat: initialEndLocation.lat };
			if (isStationMode) {
				endCode = initialEndCode || deriveCode(initialEndLocation.name, initialEndLocation.name);
				endSearchQuery = endCode || initialEndLocation.location || initialEndLocation.name;
			} else {
				endCode = null;
				endSearchQuery = initialEndLocation.location || initialEndLocation.name;
			}
			// Never perform reverse geocoding when we have initial location data
			// to avoid overwriting airport names with generic locations
		}

		updateMapBounds();
		emitTransportationUpdate();

		// Small delay to ensure all reactive updates complete before allowing searches
		setTimeout(() => {
			isInitializing = false;
		}, 100);
	}

	// Helper to extract a meaningful name from geocoding result
	function extractName(result: any): string {
		// If name exists and is not just a number, use it
		if (result.name && !/^\d+$/.test(result.name.trim())) {
			return result.name;
		}
		// Fallback: use first part of display_name (before first comma)
		if (result.display_name) {
			const firstPart = result.display_name.split(',')[0].trim();
			if (firstPart) return firstPart;
		}
		// Last resort: return the name or empty string
		return result.name || '';
	}

	// Helper to convert unified search result to GeoSelection
	function unifiedToGeoSelection(result: UnifiedSearchResult): GeoSelection & { source?: string; code?: string | null } {
		return {
			name: result.name,
			lat: typeof result.lat === 'string' ? parseFloat(result.lat) : result.lat,
			lng: typeof result.lon === 'string' ? parseFloat(result.lon) : result.lon,
			location: result.display_name,
			type: result.type,
			category: result.category,
			source: result.source,
			code: result.code
		};
	}

	// Build unified search URL - station modes (airport/train/bus) skip internal entity search
	function buildUnifiedSearchUrl(query: string): string {
		const params = new URLSearchParams({
			query,
			search_mode: searchMode
		});
		if (isStationMode) {
			params.set('include_locations', 'false');
			params.set('include_lodging', 'false');
			params.set('include_transportation', 'false');
		}
		return `/api/reverse-geocode/unified_search/?${params.toString()}`;
	}

	async function searchLocations(query: string) {
		if (!query.trim() || query.length < 3) {
			searchResults = [];
			unifiedResults = { addresses: [], locations: [], lodging: [], departures: [], arrivals: [] };
			return;
		}

		isSearching = true;
		try {
			if (unifiedSearch) {
				// Use unified search endpoint - pass raw query + search_mode (suffix applied server-side to geocoding only)
				const response = await fetch(buildUnifiedSearchUrl(query));
				const data = await response.json();
				unifiedResults = {
					addresses: data.addresses || [],
					locations: data.locations || [],
					lodging: data.lodging || [],
					departures: data.departures || [],
					arrivals: data.arrivals || []
				};
				// Combine all results for backward compatibility
				searchResults = [
					...unifiedResults.locations.map(unifiedToGeoSelection),
					...unifiedResults.lodging.map(unifiedToGeoSelection),
					...unifiedResults.departures.map(unifiedToGeoSelection),
					...unifiedResults.arrivals.map(unifiedToGeoSelection),
					...unifiedResults.addresses.map(unifiedToGeoSelection)
				];
			} else {
				// Original geocode-only search (suffix still useful for pure geocoding)
				const searchTerm = `${query}${SEARCH_MODE_CONFIG[searchMode].suffix}`;
				const response = await fetch(
					`/api/reverse-geocode/search/?query=${encodeURIComponent(searchTerm)}`
				);
				const results = await response.json();

				searchResults = results.map((result: any) => ({
					id: result.name + result.lat + result.lon,
					name: extractName(result),
					lat: parseFloat(result.lat),
					lng: parseFloat(result.lon),
					type: result.type,
					category: result.category,
					location: result.display_name,
					importance: result.importance,
					powered_by: result.powered_by
				}));
			}
		} catch (error) {
			console.error('Search error:', error);
			searchResults = [];
			unifiedResults = { addresses: [], locations: [], lodging: [], departures: [], arrivals: [] };
		} finally {
			isSearching = false;
		}
	}

	async function searchStartLocation(query: string) {
		if (!query.trim() || query.length < 3) {
			startSearchResults = [];
			startUnifiedResults = { addresses: [], locations: [], lodging: [], departures: [], arrivals: [] };
			return;
		}

		isSearchingStart = true;
		try {
			if (unifiedSearch) {
				// Use unified search endpoint - pass raw query + search_mode (suffix applied server-side to geocoding only)
				const response = await fetch(buildUnifiedSearchUrl(query));
				const data = await response.json();
				startUnifiedResults = {
					addresses: data.addresses || [],
					locations: data.locations || [],
					lodging: data.lodging || [],
					departures: data.departures || [],
					arrivals: data.arrivals || []
				};
				// Combine all results for the dropdown
				startSearchResults = [
					...startUnifiedResults.locations.map(unifiedToGeoSelection),
					...startUnifiedResults.lodging.map(unifiedToGeoSelection),
					...startUnifiedResults.departures.map(unifiedToGeoSelection),
					...startUnifiedResults.arrivals.map(unifiedToGeoSelection),
					...startUnifiedResults.addresses.map(unifiedToGeoSelection)
				];
			} else {
				const searchTerm = `${query}${SEARCH_MODE_CONFIG[searchMode].suffix}`;
				const response = await fetch(
					`/api/reverse-geocode/search/?query=${encodeURIComponent(searchTerm)}`
				);
				const results = await response.json();

				startSearchResults = results.map((result: any) => ({
					id: result.name + result.lat + result.lon,
					name: extractName(result),
					lat: parseFloat(result.lat),
					lng: parseFloat(result.lon),
					type: result.type,
					category: result.category,
					location: result.display_name,
					importance: result.importance,
					powered_by: result.powered_by
				}));
			}
		} catch (error) {
			console.error('Search error:', error);
			startSearchResults = [];
			startUnifiedResults = { addresses: [], locations: [], lodging: [], departures: [], arrivals: [] };
		} finally {
			isSearchingStart = false;
		}
	}

	async function searchEndLocation(query: string) {
		if (!query.trim() || query.length < 3) {
			endSearchResults = [];
			endUnifiedResults = { addresses: [], locations: [], lodging: [], departures: [], arrivals: [] };
			return;
		}

		isSearchingEnd = true;
		try {
			if (unifiedSearch) {
				// Use unified search endpoint - pass raw query + search_mode (suffix applied server-side to geocoding only)
				const response = await fetch(buildUnifiedSearchUrl(query));
				const data = await response.json();
				endUnifiedResults = {
					addresses: data.addresses || [],
					locations: data.locations || [],
					lodging: data.lodging || [],
					departures: data.departures || [],
					arrivals: data.arrivals || []
				};
				// Combine all results for the dropdown
				endSearchResults = [
					...endUnifiedResults.locations.map(unifiedToGeoSelection),
					...endUnifiedResults.lodging.map(unifiedToGeoSelection),
					...endUnifiedResults.departures.map(unifiedToGeoSelection),
					...endUnifiedResults.arrivals.map(unifiedToGeoSelection),
					...endUnifiedResults.addresses.map(unifiedToGeoSelection)
				];
			} else {
				const searchTerm = `${query}${SEARCH_MODE_CONFIG[searchMode].suffix}`;
				const response = await fetch(
					`/api/reverse-geocode/search/?query=${encodeURIComponent(searchTerm)}`
				);
				const results = await response.json();

				endSearchResults = results.map((result: any) => ({
					id: result.name + result.lat + result.lon,
					name: extractName(result),
					lat: parseFloat(result.lat),
					lng: parseFloat(result.lon),
					type: result.type,
					category: result.category,
					location: result.display_name,
					importance: result.importance,
					powered_by: result.powered_by
				}));
			}
		} catch (error) {
			console.error('Search error:', error);
			endSearchResults = [];
			endUnifiedResults = { addresses: [], locations: [], lodging: [], departures: [], arrivals: [] };
		} finally {
			isSearchingEnd = false;
		}
	}

	function handleSearchInput() {
		if (isInitializing) return;
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			searchLocations(searchQuery);
		}, 300);
	}

	function handleStartSearchInput() {
		if (isInitializing) return;
		clearTimeout(startSearchTimeout);
		startSearchTimeout = setTimeout(() => {
			searchStartLocation(startSearchQuery);
		}, 300);
	}

	function handleEndSearchInput() {
		if (isInitializing) return;
		clearTimeout(endSearchTimeout);
		endSearchTimeout = setTimeout(() => {
			searchEndLocation(endSearchQuery);
		}, 300);
	}

	function deriveCode(value: string | undefined, fallback?: string): string | null {
		if (!value && !fallback) return null;
		const match = value?.match(/\b([A-Z0-9]{3,5})\b/) || value?.match(/\(([A-Z0-9]{3,5})\)/);
		if (match && match[1]) return match[1].toUpperCase();
		const candidate = (fallback || '').trim();
		if (candidate.length && candidate.length <= 5) return candidate.toUpperCase();
		return null;
	}

	function resolveCode(selection: GeoSelection | null, typedQuery: string): string | null {
		// Prefer explicit user-typed code when in airport mode
		const fromTyped = deriveCode(typedQuery, typedQuery);
		if (fromTyped) return fromTyped;
		if (selection) {
			const fromName = deriveCode(selection.name, typedQuery);
			if (fromName) return fromName;
			const fromLocation = deriveCode(selection.location, typedQuery);
			if (fromLocation) return fromLocation;
		}
		return null;
	}

	function emitUpdate(selection: GeoSelection) {
		dispatch('update', {
			name: selection.name,
			lat: selection.lat,
			lng: selection.lng,
			location: selection.location
		});
	}

	function emitTransportationUpdate() {
		// Emit if we have at least one location selected
		if (selectedStartLocation || selectedEndLocation) {
			dispatch('transportationUpdate', {
				start: selectedStartLocation ? {
					name: selectedStartLocation.name,
					lat: selectedStartLocation.lat,
					lng: selectedStartLocation.lng,
					location: selectedStartLocation.location,
					city: startLocationData?.city?.name || null,
					code: startCode
				} : null,
				end: selectedEndLocation ? {
					name: selectedEndLocation.name,
					lat: selectedEndLocation.lat,
					lng: selectedEndLocation.lng,
					location: selectedEndLocation.location,
					city: endLocationData?.city?.name || null,
					code: endCode
				} : null
			});
		}
	}

	async function selectSearchResult(searchResult: GeoSelection) {
		selectedLocation = searchResult;
		selectedMarker = { lng: searchResult.lng, lat: searchResult.lat };
		mapCenter = [searchResult.lng, searchResult.lat];
		mapZoom = 14;
		searchResults = [];
		searchQuery = searchResult.location || searchResult.name;

		displayName = searchResult.location || searchResult.name;

		emitUpdate(searchResult);
		await performDetailedReverseGeocode(searchResult.lat, searchResult.lng);
	}

	async function selectStartSearchResult(searchResult: GeoSelection & { code?: string | null }) {
		selectedStartLocation = searchResult;
		startMarker = { lng: searchResult.lng, lat: searchResult.lat };
		startSearchResults = [];

		const typedQuery = startSearchQuery;
		// Prefer backend-provided code (from departure/arrival entities)
		const backendCode = searchResult.code || null;

		// Handle codes based on mode
		if (isAirportMode) {
			// Airport mode: derive IATA codes
			const airportCodeMatch = searchResult.name.match(/\(([A-Z]{3})\)/);
			startSearchQuery = airportCodeMatch ? airportCodeMatch[1] : searchResult.name;
			startCode = backendCode || resolveCode(searchResult, typedQuery);
			if (!startCode) {
				startCode =
					deriveCode(searchResult.name, startSearchQuery) || deriveCode(searchResult.location);
			}
			if (startCode) {
				startSearchQuery = startCode;
			}
		} else if (isStationMode) {
			// Train/bus mode: prefer backend code, then city name after reverse geocode
			startSearchQuery = searchResult.location || searchResult.name;
			startCode = backendCode; // Will be set after reverse geocode if still null
		} else {
			// Address/cab/vtc mode: no codes
			startSearchQuery = searchResult.location || searchResult.name;
			startCode = null;
		}

		await performDetailedReverseGeocode(searchResult.lat, searchResult.lng, 'start');

		// For train/bus, set code to city name after reverse geocode (only if not already set)
		if (isStationMode && !isAirportMode && !startCode && startLocationData?.city?.name) {
			startCode = startLocationData.city.name;
		}
		updateMapBounds();
		emitTransportationUpdate();
	}

	async function selectEndSearchResult(searchResult: GeoSelection & { code?: string | null }) {
		selectedEndLocation = searchResult;
		endMarker = { lng: searchResult.lng, lat: searchResult.lat };
		endSearchResults = [];

		const typedQuery = endSearchQuery;
		// Prefer backend-provided code (from departure/arrival entities)
		const backendCode = searchResult.code || null;

		// Handle codes based on mode
		if (isAirportMode) {
			// Airport mode: derive IATA codes
			const airportCodeMatch = searchResult.name.match(/\(([A-Z]{3})\)/);
			endSearchQuery = airportCodeMatch ? airportCodeMatch[1] : searchResult.name;
			endCode = backendCode || resolveCode(searchResult, typedQuery);
			if (!endCode) {
				endCode =
					deriveCode(searchResult.name, endSearchQuery) || deriveCode(searchResult.location);
			}
			if (endCode) {
				endSearchQuery = endCode;
			}
		} else if (isStationMode) {
			// Train/bus mode: prefer backend code, then city name after reverse geocode
			endSearchQuery = searchResult.location || searchResult.name;
			endCode = backendCode; // Will be set after reverse geocode if still null
		} else {
			// Address/cab/vtc mode: no codes
			endSearchQuery = searchResult.location || searchResult.name;
			endCode = null;
		}

		await performDetailedReverseGeocode(searchResult.lat, searchResult.lng, 'end');

		// For train/bus, set code to city name after reverse geocode (only if not already set)
		if (isStationMode && !isAirportMode && !endCode && endLocationData?.city?.name) {
			endCode = endLocationData.city.name;
		}
		updateMapBounds();
		emitTransportationUpdate();
	}

	function updateMapBounds() {
		if (startMarker && endMarker) {
			const minLng = Math.min(startMarker.lng, endMarker.lng);
			const maxLng = Math.max(startMarker.lng, endMarker.lng);
			const minLat = Math.min(startMarker.lat, endMarker.lat);
			const maxLat = Math.max(startMarker.lat, endMarker.lat);

			// Add a small padding so pins are not flush against the edge when fitting
			const lonPadding = Math.max((maxLng - minLng) * 0.1, 0.5);
			const latPadding = Math.max((maxLat - minLat) * 0.1, 0.5);

			mapBounds = [
				[minLng - lonPadding, minLat - latPadding],
				[maxLng + lonPadding, maxLat + latPadding]
			];
			mapCenter = [(minLng + maxLng) / 2, (minLat + maxLat) / 2];
			mapZoom = undefined;
		} else if (startMarker) {
			mapCenter = [startMarker.lng, startMarker.lat];
			mapZoom = 8;
			mapBounds = null;
		} else if (endMarker) {
			mapCenter = [endMarker.lng, endMarker.lat];
			mapZoom = 8;
			mapBounds = null;
		} else {
			mapBounds = null;
		}
	}

	async function handleMapClick(e: { detail: { lngLat: { lng: number; lat: number } } }) {
		selectedMarker = {
			lng: e.detail.lngLat.lng,
			lat: e.detail.lngLat.lat
		};

		await reverseGeocode(e.detail.lngLat.lng, e.detail.lngLat.lat);
	}

	async function reverseGeocode(lng: number, lat: number) {
		isReverseGeocoding = true;

		try {
			const response = await fetch(`/api/reverse-geocode/search/?query=${lat},${lng}`);
			const results = await response.json();

			if (results && results.length > 0) {
				const result = results[0];
				selectedLocation = {
					name: result.name,
					lat: lat,
					lng: lng,
					location: result.display_name,
					type: result.type,
					category: result.category
				};
				searchQuery = result.display_name || result.name;
				displayName = result.display_name || result.name;
			} else {
				selectedLocation = {
					name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
					lat: lat,
					lng: lng,
					location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
				};
				searchQuery = selectedLocation.name;
				displayName = selectedLocation.location;
			}

			if (selectedLocation) {
				emitUpdate(selectedLocation);
			}

			await performDetailedReverseGeocode(lat, lng);
		} catch (error) {
			console.error('Reverse geocoding error:', error);
			selectedLocation = {
				name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
				lat: lat,
				lng: lng,
				location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
			};
			searchQuery = selectedLocation.name;
			if (!displayName) displayName = selectedLocation.location;
			locationData = null;
			if (selectedLocation) emitUpdate(selectedLocation);
		} finally {
			isReverseGeocoding = false;
		}
	}

	async function performDetailedReverseGeocode(
		lat: number,
		lng: number,
		target: 'single' | 'start' | 'end' = 'single'
	) {
		try {
			const response = await fetch(
				`/api/reverse-geocode/reverse_geocode/?lat=${lat}&lon=${lng}&format=json`
			);

			if (response.ok) {
				const data = await response.json();
				const metaData = {
					city: data.city
						? {
								name: data.city,
								id: data.city_id,
								visited: data.city_visited || false
							}
						: undefined,
					region: data.region
						? {
								name: data.region,
								id: data.region_id,
								visited: data.region_visited || false
							}
						: undefined,
					country: data.country
						? {
								name: data.country,
								country_code: data.country_id,
								visited: false
							}
						: undefined,
					display_name: data.display_name,
					location_name: data.location_name
				};

				if (target === 'start') {
					startLocationData = metaData;
				} else if (target === 'end') {
					endLocationData = metaData;
				} else {
					locationData = metaData;
					displayName = data.display_name;
				}
			} else {
				if (target === 'start') {
					startLocationData = null;
				} else if (target === 'end') {
					endLocationData = null;
				} else {
					locationData = null;
				}
			}
		} catch (error) {
			console.error('Detailed reverse geocoding error:', error);
			if (target === 'start') {
				startLocationData = null;
			} else if (target === 'end') {
				endLocationData = null;
			} else {
				locationData = null;
			}
		}
	}

	function useCurrentLocation() {
		if ('geolocation' in navigator) {
			navigator.geolocation.getCurrentPosition(
				async (position) => {
					const lat = position.coords.latitude;
					const lng = position.coords.longitude;
					selectedMarker = { lng, lat };
					mapCenter = [lng, lat];
					mapZoom = 14;
					await reverseGeocode(lng, lat);
				},
				(error) => {
					console.error('Geolocation error:', error);
				}
			);
		}
	}

	function clearLocationSelection() {
		if (transportationMode) {
			selectedStartLocation = null;
			selectedEndLocation = null;
			startMarker = null;
			endMarker = null;
			startLocationData = null;
			endLocationData = null;
			startCode = null;
			endCode = null;
			startSearchQuery = '';
			endSearchQuery = '';
			startSearchResults = [];
			endSearchResults = [];
		} else {
			selectedLocation = null;
			selectedMarker = null;
			locationData = null;
			searchQuery = '';
			searchResults = [];
			displayName = '';
		}
		mapCenter = [-74.5, 40];
		mapZoom = 2;
		mapBounds = null;
		dispatch('clear');
	}

	$: if (!initialApplied && initialSelection) {
		initialApplied = true;
		applyInitialSelection(initialSelection);
	}

	$: if (
		!initialTransportationApplied &&
		transportationMode &&
		(initialStartLocation || initialEndLocation)
	) {
		initialTransportationApplied = true;
		applyInitialTransportationLocations();
	}
</script>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
	<div class="space-y-4">
		<!-- Transportation Mode Selector -->
		{#if transportationMode}
			<div class="flex gap-1 justify-center flex-wrap">
				<button
					type="button"
					class="btn btn-xs gap-0.5 px-2"
					class:btn-primary={searchMode === 'location'}
					class:btn-ghost={searchMode !== 'location'}
					on:click={() => (searchMode = 'location')}
				>
					<PinIcon class="w-3.5 h-3.5" />
					<span class="text-xs">{$t('adventures.address')}</span>
				</button>
				<button
					type="button"
					class="btn btn-xs gap-0.5 px-2"
					class:btn-primary={searchMode === 'airport'}
					class:btn-ghost={searchMode !== 'airport'}
					on:click={() => (searchMode = 'airport')}
				>
					<AirplaneIcon class="w-3.5 h-3.5" />
					<span class="text-xs">{$t('adventures.airport')}</span>
				</button>
				<button
					type="button"
					class="btn btn-xs gap-0.5 px-2"
					class:btn-primary={searchMode === 'train'}
					class:btn-ghost={searchMode !== 'train'}
					on:click={() => (searchMode = 'train')}
				>
					<TrainIcon class="w-3.5 h-3.5" />
					<span class="text-xs">{$t('adventures.train')}</span>
				</button>
				<button
					type="button"
					class="btn btn-xs gap-0.5 px-2"
					class:btn-primary={searchMode === 'bus'}
					class:btn-ghost={searchMode !== 'bus'}
					on:click={() => (searchMode = 'bus')}
				>
					<BusIcon class="w-3.5 h-3.5" />
					<span class="text-xs">{$t('adventures.bus')}</span>
				</button>
				<button
					type="button"
					class="btn btn-xs gap-0.5 px-2"
					class:btn-primary={searchMode === 'cab'}
					class:btn-ghost={searchMode !== 'cab'}
					on:click={() => (searchMode = 'cab')}
				>
					<TaxiIcon class="w-3.5 h-3.5" />
					<span class="text-xs">{$t('adventures.cab')}</span>
				</button>
				<button
					type="button"
					class="btn btn-xs gap-0.5 px-2"
					class:btn-primary={searchMode === 'vtc'}
					class:btn-ghost={searchMode !== 'vtc'}
					on:click={() => (searchMode = 'vtc')}
				>
					<LimoIcon class="w-3.5 h-3.5" />
					<span class="text-xs">{$t('adventures.vtc')}</span>
				</button>
			</div>
		{/if}

		{#if showDisplayNameInput && displayNamePosition === 'before' && !transportationMode}
			<div class="form-control">
				<label class="label" for="location-display">
					<span class="label-text font-medium">
						{displayNameLabel || $t('adventures.location_display_name')}
					</span>
				</label>
				<input
					type="text"
					id="location-display"
					bind:value={displayName}
					class="input input-bordered bg-base-100/80 focus:bg-base-100"
					placeholder={displayNamePlaceholder || $t('adventures.enter_location_display_name')}
				/>
			</div>
		{/if}

		{#if transportationMode}
			<!-- Start Location Search -->
			<div class="form-control">
				<label class="label" for="search-start-location">
					<span class="label-text font-medium flex items-center gap-2">
						<svelte:component this={SEARCH_MODE_CONFIG[searchMode].icon} class="w-4 h-4 text-success" />
						{$t(SEARCH_MODE_CONFIG[searchMode].departureLabel)}
					</span>
				</label>
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<SearchIcon class="w-4 h-4 text-base-content/40" />
					</div>
					<input
						type="text"
						id="search-start-location"
						bind:value={startSearchQuery}
						on:input={handleStartSearchInput}
						placeholder={$t(SEARCH_MODE_CONFIG[searchMode].placeholder)}
						class="input input-bordered w-full pl-10 pr-4 bg-base-100/80 focus:bg-base-100"
						class:input-success={selectedStartLocation}
					/>
					{#if startSearchQuery && !selectedStartLocation}
						<button
							class="absolute inset-y-0 right-0 pr-3 flex items-center"
							on:click={() => {
								startSearchQuery = '';
								startSearchResults = [];
							}}
						>
							<ClearIcon class="w-4 h-4 text-base-content/40 hover:text-base-content" />
						</button>
					{/if}
				</div>
			</div>

			{#if isSearchingStart}
				<div class="flex items-center justify-center py-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="ml-2 text-sm text-base-content/60">{$t('adventures.searching')}...</span>
				</div>
			{:else if startSearchQuery.length >= 3 && startSearchResults.length === 0 && !selectedStartLocation}
				<div class="text-center py-3 text-sm text-base-content/50">
					{$t('adventures.no_results')}
				</div>
			{:else if startSearchResults.length > 0}
				<div class="space-y-2">
					<div class="max-h-48 overflow-y-auto space-y-1">
						{#if unifiedSearch && (startUnifiedResults.locations.length > 0 || startUnifiedResults.lodging.length > 0 || startUnifiedResults.departures.length > 0 || startUnifiedResults.arrivals.length > 0 || startUnifiedResults.addresses.length > 0)}
							<!-- Grouped results for unified search -->
							{#if startUnifiedResults.locations.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<PinIcon class="w-3 h-3" />
									{$t('navbar.locations')}
								</div>
								{#each startUnifiedResults.locations as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-primary/50 transition-colors"
										on:click={() => selectStartSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<PinIcon class="w-4 h-4 text-primary mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.category}
													<div class="text-xs text-primary/70 capitalize">{result.category}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
							{#if startUnifiedResults.lodging.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<BedIcon class="w-3 h-3" />
									{$t('navbar.lodging')}
								</div>
								{#each startUnifiedResults.lodging as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-pink-500/50 transition-colors"
										on:click={() => selectStartSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<BedIcon class="w-4 h-4 text-pink-500 mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.type}
													<div class="text-xs text-pink-500/70 capitalize">{result.type}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
							{#if startUnifiedResults.departures.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<DepartureIcon class="w-3 h-3" />
									{$t('adventures.departures')}
								</div>
								{#each startUnifiedResults.departures as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-amber-500/50 transition-colors"
										on:click={() => selectStartSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<DepartureIcon class="w-4 h-4 text-amber-500 mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.type}
													<div class="text-xs text-amber-500/70 capitalize">{result.type}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
							{#if startUnifiedResults.arrivals.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<ArrivalIcon class="w-3 h-3" />
									{$t('adventures.arrivals')}
								</div>
								{#each startUnifiedResults.arrivals as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-amber-500/50 transition-colors"
										on:click={() => selectStartSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<ArrivalIcon class="w-4 h-4 text-amber-500 mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.type}
													<div class="text-xs text-amber-500/70 capitalize">{result.type}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
							{#if startUnifiedResults.addresses.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<MapIcon class="w-3 h-3" />
									{$t('adventures.addresses')}
								</div>
								{#each startUnifiedResults.addresses as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-success/50 transition-colors"
										on:click={() => selectStartSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<MapIcon class="w-4 h-4 text-success mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.category}
													<div class="text-xs text-success/70 capitalize">{result.category}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
						{:else}
							<!-- Non-grouped results (original behavior) -->
							{#each startSearchResults as result}
								<button
									class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-success/50 transition-colors"
									on:click={() => selectStartSearchResult(result)}
								>
									<div class="flex items-start gap-3">
										<PinIcon class="w-4 h-4 text-success mt-1 flex-shrink-0" />
										<div class="min-w-0 flex-1">
											<div class="font-medium text-sm truncate">{result.name}</div>
											<div class="text-xs text-base-content/60 truncate">{result.location}</div>
											{#if result.category}
												<div class="text-xs text-success/70 capitalize">{result.category}</div>
											{/if}
										</div>
									</div>
								</button>
							{/each}
						{/if}
					</div>
				</div>
			{/if}

			<!-- End Location Search -->
			<div class="form-control">
				<label class="label" for="search-end-location">
					<span class="label-text font-medium flex items-center gap-2">
						<svelte:component this={SEARCH_MODE_CONFIG[searchMode].icon} class="w-4 h-4 text-error" />
						{$t(SEARCH_MODE_CONFIG[searchMode].arrivalLabel)}
					</span>
				</label>
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<SearchIcon class="w-4 h-4 text-base-content/40" />
					</div>
					<input
						type="text"
						id="search-end-location"
						bind:value={endSearchQuery}
						on:input={handleEndSearchInput}
						placeholder={$t(SEARCH_MODE_CONFIG[searchMode].placeholder)}
						class="input input-bordered w-full pl-10 pr-4 bg-base-100/80 focus:bg-base-100"
						class:input-error={selectedEndLocation}
					/>
					{#if endSearchQuery && !selectedEndLocation}
						<button
							class="absolute inset-y-0 right-0 pr-3 flex items-center"
							on:click={() => {
								endSearchQuery = '';
								endSearchResults = [];
							}}
						>
							<ClearIcon class="w-4 h-4 text-base-content/40 hover:text-base-content" />
						</button>
					{/if}
				</div>
			</div>

			{#if isSearchingEnd}
				<div class="flex items-center justify-center py-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="ml-2 text-sm text-base-content/60">{$t('adventures.searching')}...</span>
				</div>
			{:else if endSearchQuery.length >= 3 && endSearchResults.length === 0 && !selectedEndLocation}
				<div class="text-center py-3 text-sm text-base-content/50">
					{$t('adventures.no_results')}
				</div>
			{:else if endSearchResults.length > 0}
				<div class="space-y-2">
					<div class="max-h-48 overflow-y-auto space-y-1">
						{#if unifiedSearch && (endUnifiedResults.locations.length > 0 || endUnifiedResults.lodging.length > 0 || endUnifiedResults.departures.length > 0 || endUnifiedResults.arrivals.length > 0 || endUnifiedResults.addresses.length > 0)}
							<!-- Grouped results for unified search -->
							{#if endUnifiedResults.locations.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<PinIcon class="w-3 h-3" />
									{$t('navbar.locations')}
								</div>
								{#each endUnifiedResults.locations as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-primary/50 transition-colors"
										on:click={() => selectEndSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<PinIcon class="w-4 h-4 text-primary mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.category}
													<div class="text-xs text-primary/70 capitalize">{result.category}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
							{#if endUnifiedResults.lodging.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<BedIcon class="w-3 h-3" />
									{$t('navbar.lodging')}
								</div>
								{#each endUnifiedResults.lodging as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-pink-500/50 transition-colors"
										on:click={() => selectEndSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<BedIcon class="w-4 h-4 text-pink-500 mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.type}
													<div class="text-xs text-pink-500/70 capitalize">{result.type}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
							{#if endUnifiedResults.departures.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<DepartureIcon class="w-3 h-3" />
									{$t('adventures.departures')}
								</div>
								{#each endUnifiedResults.departures as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-amber-500/50 transition-colors"
										on:click={() => selectEndSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<DepartureIcon class="w-4 h-4 text-amber-500 mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.type}
													<div class="text-xs text-amber-500/70 capitalize">{result.type}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
							{#if endUnifiedResults.arrivals.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<ArrivalIcon class="w-3 h-3" />
									{$t('adventures.arrivals')}
								</div>
								{#each endUnifiedResults.arrivals as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-amber-500/50 transition-colors"
										on:click={() => selectEndSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<ArrivalIcon class="w-4 h-4 text-amber-500 mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.type}
													<div class="text-xs text-amber-500/70 capitalize">{result.type}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
							{#if endUnifiedResults.addresses.length > 0}
								<div class="text-xs font-semibold text-base-content/50 px-2 pt-1 flex items-center gap-1">
									<MapIcon class="w-3 h-3" />
									{$t('adventures.addresses')}
								</div>
								{#each endUnifiedResults.addresses as result}
									<button
										class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-error/50 transition-colors"
										on:click={() => selectEndSearchResult(unifiedToGeoSelection(result))}
									>
										<div class="flex items-start gap-3">
											<MapIcon class="w-4 h-4 text-error mt-1 flex-shrink-0" />
											<div class="min-w-0 flex-1">
												<div class="font-medium text-sm truncate">{result.name}</div>
												<div class="text-xs text-base-content/60 truncate">{result.display_name}</div>
												{#if result.category}
													<div class="text-xs text-error/70 capitalize">{result.category}</div>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							{/if}
						{:else}
							<!-- Non-grouped results (original behavior) -->
							{#each endSearchResults as result}
								<button
									class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-error/50 transition-colors"
									on:click={() => selectEndSearchResult(result)}
								>
									<div class="flex items-start gap-3">
										<PinIcon class="w-4 h-4 text-error mt-1 flex-shrink-0" />
										<div class="min-w-0 flex-1">
											<div class="font-medium text-sm truncate">{result.name}</div>
											<div class="text-xs text-base-content/60 truncate">{result.location}</div>
											{#if result.category}
												<div class="text-xs text-error/70 capitalize">{result.category}</div>
											{/if}
										</div>
									</div>
								</button>
							{/each}
						{/if}
					</div>
				</div>
			{/if}

			<!-- Selected Locations Summary for Transportation Mode -->
			{#if selectedStartLocation && selectedEndLocation}
				<div class="card bg-success/10 border border-success/30">
					<div class="card-body p-4">
						<div class="flex items-start gap-3">
							<div class="p-2 bg-success/20 rounded-lg">
								<SwapIcon class="w-4 h-4 text-success" />
							</div>
							<div class="flex-1 min-w-0 space-y-2">
								<h4 class="font-semibold text-success mb-1">{$t('adventures.route_selected')}</h4>

								<!-- Start Location -->
								<div class="flex items-start gap-2">
									<PinIcon class="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
									<div class="min-w-0 flex-1">
										<p class="text-sm font-medium text-base-content/80 truncate">
											{selectedStartLocation.name}
											{#if startCode}
												<span class="badge badge-success badge-sm ml-2">{startCode}</span>
											{/if}
										</p>
										<p class="text-xs text-base-content/60">
											{startMarker?.lat.toFixed(6)}, {startMarker?.lng.toFixed(6)}
										</p>
									</div>
								</div>

								<div class="divider my-1"></div>

								<!-- End Location -->
								<div class="flex items-start gap-2">
									<PinIcon class="w-4 h-4 text-error mt-0.5 flex-shrink-0" />
									<div class="min-w-0 flex-1">
										<p class="text-sm font-medium text-base-content/80 truncate">
											{selectedEndLocation.name}
											{#if endCode}
												<span class="badge badge-error badge-sm ml-2">{endCode}</span>
											{/if}
										</p>
										<p class="text-xs text-base-content/60">
											{endMarker?.lat.toFixed(6)}, {endMarker?.lng.toFixed(6)}
										</p>
									</div>
								</div>
							</div>
							<button class="btn btn-ghost btn-sm" on:click={clearLocationSelection}>
								<ClearIcon class="w-4 h-4" />
							</button>
						</div>
					</div>
				</div>
			{/if}
		{:else}
			<!-- Single Location Mode (Original) -->
			<div class="form-control">
				<label class="label" for="search-location">
					<span class="label-text font-medium">{$t('adventures.search_location')}</span>
				</label>
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<SearchIcon class="w-4 h-4 text-base-content/40" />
					</div>
					<input
						type="text"
						id="search-location"
						bind:value={searchQuery}
						on:input={handleSearchInput}
						placeholder={$t('adventures.search_placeholder')}
						class="input input-bordered w-full pl-10 pr-4 bg-base-100/80 focus:bg-base-100"
						class:input-primary={selectedLocation}
					/>
					{#if searchQuery && !selectedLocation}
						<button
							class="absolute inset-y-0 right-0 pr-3 flex items-center"
							on:click={clearLocationSelection}
						>
							<ClearIcon class="w-4 h-4 text-base-content/40 hover:text-base-content" />
						</button>
					{/if}
				</div>
			</div>

			{#if isSearching}
				<div class="flex items-center justify-center py-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="ml-2 text-sm text-base-content/60">{$t('adventures.searching')}...</span>
				</div>
			{:else if searchResults.length > 0}
				<div class="space-y-2">
					<div class="label">
						<span class="label-text text-sm font-medium">{$t('adventures.search_results')}</span>
					</div>
					<div class="max-h-48 overflow-y-auto space-y-1">
						{#each searchResults as result}
							<button
								class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-primary/50 transition-colors"
								on:click={() => selectSearchResult(result)}
							>
								<div class="flex items-start gap-3">
									<PinIcon class="w-4 h-4 text-primary mt-1 flex-shrink-0" />
									<div class="min-w-0 flex-1">
										<div class="font-medium text-sm truncate">{result.name}</div>
										<div class="text-xs text-base-content/60 truncate">{result.location}</div>
										{#if result.category}
											<div class="text-xs text-primary/70 capitalize">{result.category}</div>
										{/if}
									</div>
								</div>
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<div class="flex items-center gap-2">
				<div class="divider divider-horizontal text-xs">{$t('adventures.or')}</div>
			</div>

			<button class="btn btn-outline gap-2 w-full" on:click={useCurrentLocation}>
				<LocationIcon class="w-4 h-4" />
				{$t('adventures.use_current_location')}
			</button>

			{#if showDisplayNameInput && displayNamePosition === 'after'}
				<div class="form-control">
					<label class="label" for="location-display-after">
						<span class="label-text font-medium">
							{displayNameLabel || $t('adventures.location_display_name')}
						</span>
					</label>
					<input
						type="text"
						id="location-display-after"
						bind:value={displayName}
						class="input input-bordered bg-base-100/80 focus:bg-base-100"
						placeholder={displayNamePlaceholder || $t('adventures.enter_location_display_name')}
					/>
				</div>
			{/if}

			{#if selectedLocation && selectedMarker}
				<div class="card bg-success/10 border border-success/30">
					<div class="card-body p-4">
						<div class="flex items-start gap-3">
							<div class="p-2 bg-success/20 rounded-lg">
								<CheckIcon class="w-4 h-4 text-success" />
							</div>
							<div class="flex-1 min-w-0">
								<h4 class="font-semibold text-success mb-1">
									{$t('adventures.location_selected')}
								</h4>
								<p class="text-sm text-base-content/80 truncate">{selectedLocation.name}</p>
								<p class="text-xs text-base-content/60 mt-1">
									{selectedMarker.lat.toFixed(6)}, {selectedMarker.lng.toFixed(6)}
								</p>

								{#if locationData?.city || locationData?.region || locationData?.country}
									<div class="flex flex-wrap gap-2 mt-3">
										{#if locationData.city}
											<div class="badge badge-info badge-sm gap-1">
												🏙️ {locationData.city.name}
											</div>
										{/if}
										{#if locationData.region}
											<div class="badge badge-warning badge-sm gap-1">
												🗺️ {locationData.region.name}
											</div>
										{/if}
										{#if locationData.country}
											<div class="badge badge-success badge-sm gap-1">
												🌎 {locationData.country.name}
											</div>
										{/if}
									</div>
								{/if}
							</div>
							<button class="btn btn-ghost btn-sm" on:click={clearLocationSelection}>
								<ClearIcon class="w-4 h-4" />
							</button>
						</div>
					</div>
				</div>
			{/if}
		{/if}
	</div>

	<div class="space-y-4">
		<div class="flex items-center justify-between">
			<div class="label">
				<span class="label-text font-medium">{$t('worldtravel.interactive_map')}</span>
			</div>
			{#if isReverseGeocoding}
				<div class="flex items-center gap-2">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="text-sm text-base-content/60"
						>{$t('worldtravel.getting_location_details')}...</span
					>
				</div>
			{/if}
		</div>

		<div class="relative">
			<MapLibre
				bind:this={mapComponent}
				style={getBasemapUrl()}
				class="w-full h-80 rounded-lg border border-base-300"
				center={mapCenter}
				zoom={mapZoom}
				bounds={mapBounds ?? undefined}
				standardControls
			>
				<MapEvents on:click={handleMapClick} />

				{#if transportationMode}
					{#if startMarker}
						<Marker
							lngLat={[startMarker.lng, startMarker.lat]}
							class="grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-success shadow-lg cursor-pointer"
						>
							<PinIcon class="w-5 h-5 text-success-content" />
						</Marker>
					{/if}
					{#if endMarker}
						<Marker
							lngLat={[endMarker.lng, endMarker.lat]}
							class="grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-error shadow-lg cursor-pointer"
						>
							<PinIcon class="w-5 h-5 text-error-content" />
						</Marker>
					{/if}
				{:else if selectedMarker}
					<Marker
						lngLat={[selectedMarker.lng, selectedMarker.lat]}
						class="grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-primary shadow-lg cursor-pointer"
					>
						<PinIcon class="w-5 h-5 text-primary-content" />
					</Marker>
				{/if}
			</MapLibre>
		</div>

		{#if transportationMode}
			{#if !startMarker && !endMarker}
				<p class="text-sm text-base-content/60 text-center">
					{$t('adventures.search_start_end_locations')}
				</p>
			{:else if !startMarker}
				<p class="text-sm text-base-content/60 text-center">
					{$t('adventures.search_start_location')}
				</p>
			{:else if !endMarker}
				<p class="text-sm text-base-content/60 text-center">
					{$t('adventures.search_end_location')}
				</p>
			{/if}
		{:else if !selectedMarker}
			<p class="text-sm text-base-content/60 text-center">{$t('adventures.click_on_map')}</p>
		{/if}
	</div>
</div>
