<script lang="ts">
	import { DefaultMarker, Popup, Marker, GeoJSON, LineLayer } from 'svelte-maplibre';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { Activity, Location, VisitedCity, VisitedRegion, Pin } from '$lib/types.js';
	import type { LodgingPin, TransportationPin } from './+page.server';
	import type { ClusterOptions } from 'svelte-maplibre';
	import { goto } from '$app/navigation';
	import { getActivityColor } from '$lib';
	import { getTransportationIcon, getLodgingIcon } from '$lib/stores/entityTypes';
	import { page } from '$app/stores';

	// Icons
	import MapIcon from '~icons/mdi/map';
	import Filter from '~icons/mdi/filter-variant';
	import Plus from '~icons/mdi/plus';
	import Clear from '~icons/mdi/close';
	import Eye from '~icons/mdi/eye';
	import PinIcon from '~icons/mdi/map-marker';
	import Calendar from '~icons/mdi/calendar';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';
	import ActivityIcon from '~icons/mdi/run-fast';
	import SearchIcon from '~icons/mdi/magnify';
	import HotelIcon from '~icons/mdi/bed';
	import CategoryIcon from '~icons/mdi/tag';
	import TransportIcon from '~icons/mdi/airplane';
	import ChevronDown from '~icons/mdi/chevron-down';
	import ChevronUp from '~icons/mdi/chevron-up';
	import Star from '~icons/mdi/star';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import FullMap from '$lib/components/map/FullMap.svelte';

	export let data;

	let createModalOpen: boolean = false;
	let showRegions: boolean = false;
	let showActivities: boolean = false;
	let showCities: boolean = false;
	let sidebarOpen: boolean = false;

	let basemapType: string = 'default';

	// Map state from URL params
	let mapZoom: number = 2;
	let mapCenter: [number, number] = [0, 0];
	let updateUrlTimeout: NodeJS.Timeout | null = null;

	export let initialLatLng: { lat: number; lng: number } | null = null;

	let visitedRegions: VisitedRegion[] = data.props.visitedRegions;
	let visitedCities: VisitedCity[] = [];
	let pins: Pin[] = data.props.pins; // Lightweight pin objects
	let lodgingPins: LodgingPin[] = data.props.lodgingPins || [];
	let transportationPins: TransportationPin[] = data.props.transportationPins || [];
	let activities: Activity[] = [];

	// Display toggles
	let showLodging: boolean = true;
	let showLocations: boolean = true;
	let showTransportation: boolean = true;

	// Sub-filter expansion toggles
	let expandLocationFilters: boolean = false;
	let expandLodgingFilters: boolean = false;
	let expandTransportationFilters: boolean = false;

	// Category and type filters - Set contains HIDDEN types (empty = show all)
	let hiddenCategories: Set<string> = new Set();
	let hiddenLodgingTypes: Set<string> = new Set();
	let hiddenTransportationTypes: Set<string> = new Set();

	let filteredPins = pins;
	let filteredLodgingPins = lodgingPins;
	let filteredTransportationPins = transportationPins;

	let showVisited: boolean = true;
	let showPlanned: boolean = true;
	let searchQuery: string = '';
	let minRating: number = 0; // 0 means no filter
	let ratingHover: number | null = null;
	let minPriceTier: number = 0; // 0 means no filter (1-4 for 💰 to 💰💰💰💰)
	let priceTierHover: number | null = null;

	// Get unique categories from pins with their icons
	$: availableCategories = [...new Set(pins.map((pin) => pin.category?.display_name).filter(Boolean))] as string[];

	// Map category names to their icons
	$: categoryIconMap = (() => {
		const map: Record<string, string> = {};
		for (const pin of pins) {
			if (pin.category?.display_name && pin.category?.icon) {
				map[pin.category.display_name] = pin.category.icon;
			}
		}
		return map;
	})();

	// Get unique lodging types
	$: availableLodgingTypes = [...new Set(lodgingPins.map((l) => l.type).filter(Boolean))] as string[];

	// Get unique transportation types
	$: availableTransportationTypes = [...new Set(transportationPins.map((t) => t.type).filter(Boolean))] as string[];

	let newMarker: { lngLat: any } | null = null;
	let newLongitude: number | null = null;
	let newLatitude: number | null = null;

	// Cache for full location data
	let locationCache: Map<string, Location> = new Map();
	let loadingLocations: Set<string> = new Set();
	let locationRequests: Map<string, Promise<Location | null>> = new Map();

	// Hover/focus popup state
	let hoveredPinId: string | null = null;
	let hoveredLocation: Location | null = null;
	let hoveredLocationLoading: boolean = false;
	let hoveredLocationError: string | null = null;
	let hoverRequestSeq = 0;

	// Touch/coarse-pointer devices: tap should open preview instead of navigating.
	let isTouchLike: boolean = false;

	let locationBeingUpdated: Location | undefined = undefined;

	// Clustering configuration
	const PIN_SOURCE_ID = 'map-pins';
	const pinClusterOptions: ClusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 };

	type VisitStatus = 'visited' | 'planned';
	type PinType = 'location' | 'lodging' | 'transport-departure' | 'transport-arrival';

	type PinFeatureProperties = {
		id: string;
		name: string;
		visitStatus: VisitStatus;
		categoryIcon?: string;
		pinType: PinType;
		pinColor: string; // 'blue' | 'pink' | 'amber'
		subInfo?: string; // For transport: from/to location
		groupedItems?: GroupedItem[]; // For grouped transport pins
		locationName?: string; // For grouped transport pins (e.g., airport name)
	};

	type PinFeature = {
		type: 'Feature';
		geometry: {
			type: 'Point';
			coordinates: [number, number];
		};
		properties: PinFeatureProperties;
	};

	type PinFeatureCollection = {
		type: 'FeatureCollection';
		features: PinFeature[];
	};

	// Grouped item for pins at same location (any type)
	type GroupedItem = {
		id: string;
		name: string;
		icon: string;
		subInfo?: string;
		itemType: 'location' | 'lodging' | 'transport'; // Type for routing
		direction?: 'departure' | 'arrival'; // For transport items
	};

	// Unified pin type for clustering
	type UnifiedPin = {
		id: string;
		name: string;
		latitude: string | number;
		longitude: string | number;
		is_visited: boolean;
		icon: string;
		pinType: PinType;
		pinColor: string;
		subInfo?: string;
		// For grouped transport pins at same location
		groupedItems?: GroupedItem[];
		locationName?: string; // e.g., airport name
	};

	// Helper to create coordinate key (rounded to ~1m precision to group nearby items)
	function coordKey(lat: string | number, lng: string | number): string {
		const latNum = typeof lat === 'string' ? parseFloat(lat) : lat;
		const lngNum = typeof lng === 'string' ? parseFloat(lng) : lng;
		// Round to 5 decimal places (~1m precision)
		return `${latNum.toFixed(5)},${lngNum.toFixed(5)}`;
	}

	// Combine all filtered pins into a single array, grouping items at same coordinates
	$: allFilteredPins = (() => {
		// Collect all items with their coordinates
		type MapItem = {
			id: string;
			name: string;
			lat: number;
			lng: number;
			is_visited: boolean;
			icon: string;
			pinType: PinType;
			pinColor: string;
			itemType: 'location' | 'lodging' | 'transport';
			subInfo?: string;
			direction?: 'departure' | 'arrival';
		};

		const allItems: Map<string, MapItem[]> = new Map();

		// Helper to add item to coordinate group
		const addItem = (item: MapItem) => {
			const key = coordKey(item.lat, item.lng);
			if (!allItems.has(key)) {
				allItems.set(key, []);
			}
			allItems.get(key)!.push(item);
		};

		// Add location pins
		for (const pin of filteredPins) {
			const lat = parseCoordinate(pin.latitude);
			const lng = parseCoordinate(pin.longitude);
			if (lat !== null && lng !== null) {
				addItem({
					id: pin.id,
					name: pin.name,
					lat,
					lng,
					is_visited: pin.is_visited ?? false,
					icon: pin.category?.icon || '📍',
					pinType: 'location',
					pinColor: 'blue',
					itemType: 'location'
				});
			}
		}

		// Add lodging pins
		for (const lodging of filteredLodgingPins) {
			const lat = parseCoordinate(lodging.latitude);
			const lng = parseCoordinate(lodging.longitude);
			if (lat !== null && lng !== null) {
				addItem({
					id: lodging.id,
					name: lodging.name,
					lat,
					lng,
					is_visited: lodging.is_visited,
					icon: getLodgingIcon(lodging.type),
					pinType: 'lodging',
					pinColor: 'pink',
					itemType: 'lodging'
				});
			}
		}

		// Add transportation pins (both departure and arrival points)
		for (const transport of filteredTransportationPins) {
			// Departure point
			const depLat = parseCoordinate(transport.origin_latitude);
			const depLng = parseCoordinate(transport.origin_longitude);
			if (depLat !== null && depLng !== null) {
				const routeInfo = transport.to_location ? `→ ${transport.to_location}` : '';
				addItem({
					id: transport.id,
					name: transport.name,
					lat: depLat,
					lng: depLng,
					is_visited: transport.is_visited,
					icon: getTransportationIcon(transport.type),
					pinType: 'transport-departure',
					pinColor: 'amber',
					itemType: 'transport',
					subInfo: routeInfo,
					direction: 'departure'
				});
			}
			// Arrival point
			const arrLat = parseCoordinate(transport.destination_latitude);
			const arrLng = parseCoordinate(transport.destination_longitude);
			if (arrLat !== null && arrLng !== null) {
				const routeInfo = transport.from_location ? `${transport.from_location} →` : '';
				addItem({
					id: transport.id,
					name: transport.name,
					lat: arrLat,
					lng: arrLng,
					is_visited: transport.is_visited,
					icon: getTransportationIcon(transport.type),
					pinType: 'transport-arrival',
					pinColor: 'amber',
					itemType: 'transport',
					subInfo: routeInfo,
					direction: 'arrival'
				});
			}
		}

		// Build unified pins, grouping items at same coordinates
		const unified: UnifiedPin[] = [];

		for (const [key, items] of allItems) {
			const [lat, lng] = key.split(',').map(Number);

			if (items.length === 1) {
				// Single item - show as individual pin
				const item = items[0];
				unified.push({
					id: item.itemType === 'transport' ? `${item.id}-${item.direction === 'departure' ? 'dep' : 'arr'}` : item.id,
					name: item.name,
					latitude: lat,
					longitude: lng,
					is_visited: item.is_visited,
					icon: item.icon,
					pinType: item.pinType,
					pinColor: item.pinColor,
					subInfo: item.subInfo
				});
			} else {
				// Multiple items at same location - create grouped pin
				const groupedItems: GroupedItem[] = items.map(item => ({
					id: item.id,
					name: item.name,
					icon: item.icon,
					subInfo: item.subInfo,
					itemType: item.itemType,
					direction: item.direction
				}));

				// Count item types to determine dominant type and color
				const locationCount = items.filter(i => i.itemType === 'location').length;
				const lodgingCount = items.filter(i => i.itemType === 'lodging').length;
				const transportCount = items.filter(i => i.itemType === 'transport').length;
				const hasLocation = locationCount > 0;
				const hasLodging = lodgingCount > 0;
				const hasTransport = transportCount > 0;
				const typeCount = [hasLocation, hasLodging, hasTransport].filter(Boolean).length;

				// Determine color: purple if mixed, otherwise single type color
				let primaryColor: string;
				if (typeCount > 1) {
					primaryColor = 'purple'; // Mixed types
				} else if (hasLocation) {
					primaryColor = 'blue';
				} else if (hasLodging) {
					primaryColor = 'pink';
				} else {
					primaryColor = 'amber';
				}

				// Determine dominant icon: use type with most items, or stack icon if tie
				let groupIcon: string;
				const maxCount = Math.max(locationCount, lodgingCount, transportCount);
				const dominantTypes = [
					locationCount === maxCount ? 'location' : null,
					lodgingCount === maxCount ? 'lodging' : null,
					transportCount === maxCount ? 'transport' : null
				].filter(Boolean);

				if (dominantTypes.length === 1) {
					// One dominant type - use first item of that type's icon
					const dominantType = dominantTypes[0];
					const dominantItem = items.find(i => i.itemType === dominantType);
					groupIcon = dominantItem?.icon || '📚';
				} else {
					// Tie or mixed - use stack icon
					groupIcon = '📚';
				}
				const hasVisited = items.some(i => i.is_visited);

				// Use first location name if available, or first item name
				const locationItem = items.find(i => i.itemType === 'location');
				const displayName = locationItem?.name || items[0].name;

				unified.push({
					id: `group-${key}`,
					name: displayName,
					latitude: lat,
					longitude: lng,
					is_visited: hasVisited,
					icon: groupIcon,
					pinType: 'location', // Use location as default for mixed groups
					pinColor: primaryColor,
					locationName: displayName,
					groupedItems
				});
			}
		}

		return unified;
	})();

	function parseCoordinate(value: number | string | null | undefined): number | null {
		if (value === null || value === undefined) return null;
		const numeric = typeof value === 'number' ? value : Number(value);
		return Number.isFinite(numeric) ? numeric : null;
	}

	function unifiedPinToFeature(pin: UnifiedPin): PinFeature | null {
		const lat = parseCoordinate(pin.latitude);
		const lon = parseCoordinate(pin.longitude);
		if (lat === null || lon === null) return null;

		return {
			type: 'Feature',
			geometry: { type: 'Point', coordinates: [lon, lat] },
			properties: {
				id: pin.id,
				name: pin.name,
				visitStatus: pin.is_visited ? 'visited' : 'planned',
				categoryIcon: pin.icon,
				pinType: pin.pinType,
				pinColor: pin.pinColor,
				subInfo: pin.subInfo,
				groupedItems: pin.groupedItems,
				locationName: pin.locationName
			}
		};
	}

	function pinToFeatureUnknown(item: unknown) {
		return unifiedPinToFeature(item as UnifiedPin);
	}

	function getMarkerProps(feature: any): PinFeatureProperties | null {
		if (!feature || !feature.properties) return null;
		const props = { ...feature.properties };
		// Parse groupedItems if it was serialized as JSON string
		if (props.groupedItems && typeof props.groupedItems === 'string') {
			try {
				props.groupedItems = JSON.parse(props.groupedItems);
			} catch {
				props.groupedItems = undefined;
			}
		}
		return props;
	}

	// Get pin color gradient based on pin type
	function getPinColorClass(pinColor: string): string {
		switch (pinColor) {
			case 'pink':
				return 'bg-gradient-to-br from-pink-400 to-pink-600';
			case 'amber':
				return 'bg-gradient-to-br from-amber-400 to-amber-600';
			case 'purple':
				return 'bg-gradient-to-br from-purple-400 to-purple-600';
			case 'blue':
			default:
				return 'bg-gradient-to-br from-blue-400 to-blue-600';
		}
	}

	// Get visit status border class
	function getVisitStatusBorderClass(status: VisitStatus): string {
		switch (status) {
			case 'visited':
				return 'border-[3px] border-white';
			case 'planned':
				return 'border-[3px] border-dashed border-white/60';
			default:
				return '';
		}
	}

	function markerClassResolver(props: { visitStatus?: string; pinColor?: string } | null): string {
		const colorClass = getPinColorClass(props?.pinColor || 'blue');
		const borderClass = getVisitStatusBorderClass((props?.visitStatus as VisitStatus) || 'planned');
		return `${colorClass} ${borderClass}`;
	}

	function markerLabelResolver(props: { categoryIcon?: string } | null): string {
		if (!props) return '📍';
		return props.categoryIcon || '📍';
	}

	// Get URL for a grouped item based on its type
	function getGroupedItemUrl(item: GroupedItem): string {
		switch (item.itemType) {
			case 'location':
				return `/locations/${item.id}`;
			case 'lodging':
				return `/lodging/${item.id}`;
			case 'transport':
				return `/transportations/${item.id}`;
			default:
				return `/locations/${item.id}`;
		}
	}

	function getDetailUrl(props: PinFeatureProperties): string {
		const id = props.id.replace(/-dep$/, '').replace(/-arr$/, '').replace(/^group-.*$/, '');
		switch (props.pinType) {
			case 'lodging':
				return `/lodging/${id}`;
			case 'transport-departure':
			case 'transport-arrival':
				return `/transportations/${id}`;
			case 'location':
			default:
				return `/locations/${id}`;
		}
	}

	async function handleViewDetails(props: PinFeatureProperties) {
		goto(getDetailUrl(props));
	}

	function getTypeLabel(pinType: PinType): string {
		switch (pinType) {
			case 'lodging':
				return $t('navbar.lodging');
			case 'transport-departure':
				return $t('transportation.departure');
			case 'transport-arrival':
				return $t('transportation.arrival');
			case 'location':
			default:
				return $t('navbar.locations');
		}
	}

	// Statistics
	$: totalAdventures = pins.length;
	$: visitedAdventures = pins.filter((pin) => pin.is_visited).length;
	$: plannedAdventures = pins.filter((pin) => !pin.is_visited).length;
	$: totalLodging = lodgingPins.length;
	$: visitedLodging = lodgingPins.filter((l) => l.is_visited).length;
	$: plannedLodging = lodgingPins.filter((l) => !l.is_visited).length;
	$: totalRegions = visitedRegions.length;

	// Get unique categories for filtering
	$: categories = [...new Set(pins.map((pin) => pin.category?.display_name).filter(Boolean))];

	// Toggle category visibility (click to hide/show)
	function toggleCategory(category: string) {
		if (hiddenCategories.has(category)) {
			hiddenCategories.delete(category);
		} else {
			hiddenCategories.add(category);
		}
		hiddenCategories = new Set(hiddenCategories); // Trigger reactivity
	}

	// Toggle lodging type visibility
	function toggleLodgingType(type: string) {
		if (hiddenLodgingTypes.has(type)) {
			hiddenLodgingTypes.delete(type);
		} else {
			hiddenLodgingTypes.add(type);
		}
		hiddenLodgingTypes = new Set(hiddenLodgingTypes);
	}

	// Toggle transportation type visibility
	function toggleTransportationType(type: string) {
		if (hiddenTransportationTypes.has(type)) {
			hiddenTransportationTypes.delete(type);
		} else {
			hiddenTransportationTypes.add(type);
		}
		hiddenTransportationTypes = new Set(hiddenTransportationTypes);
	}

	// Clear all category filters (reset to show all)
	function clearCategoryFilters() {
		hiddenCategories = new Set();
	}

	// Clear all lodging type filters (reset to show all)
	function clearLodgingTypeFilters() {
		hiddenLodgingTypes = new Set();
	}

	// Clear all transportation type filters (reset to show all)
	function clearTransportationTypeFilters() {
		hiddenTransportationTypes = new Set();
	}

	// Check if a category is visible (for UI - active badge)
	function isCategoryVisible(category: string): boolean {
		return !hiddenCategories.has(category);
	}

	// Check if a lodging type is visible
	function isLodgingTypeVisible(type: string): boolean {
		return !hiddenLodgingTypes.has(type);
	}

	// Check if a transportation type is visible
	function isTransportationTypeVisible(type: string): boolean {
		return !hiddenTransportationTypes.has(type);
	}

	// Updates the filtered pins based on the checkboxes, categories, and search query
	$: {
		const query = searchQuery.toLowerCase().trim();
		filteredPins = pins.filter((pin) => {
			// Filter by show locations toggle
			if (!showLocations) return false;

			// Filter by visited/planned status
			const statusMatch =
				(showVisited && pin.is_visited === true) || (showPlanned && pin.is_visited !== true);
			if (!statusMatch) return false;

			// Filter by hidden categories - if category is hidden, exclude it
			const categoryName = pin.category?.display_name;
			if (categoryName && hiddenCategories.has(categoryName)) return false;

			// Filter by minimum rating
			if (minRating > 0) {
				if (!pin.average_rating || pin.average_rating < minRating) return false;
			}

			// Filter by minimum price tier
			if (minPriceTier > 0) {
				if (!pin.price_tier || pin.price_tier < minPriceTier) return false;
			}

			// Filter by search query
			if (!query) return true;
			return (
				pin.name?.toLowerCase().includes(query) ||
				pin.category?.display_name?.toLowerCase().includes(query)
			);
		});

	}

	// Filter lodging pins
	$: {
		const query = searchQuery.toLowerCase().trim();
		filteredLodgingPins = lodgingPins.filter((lodging) => {
			// Filter by show lodging toggle
			if (!showLodging) return false;

			// Filter by visited/planned status
			const statusMatch =
				(showVisited && lodging.is_visited === true) || (showPlanned && lodging.is_visited !== true);
			if (!statusMatch) return false;

			// Filter by hidden lodging types
			if (lodging.type && hiddenLodgingTypes.has(lodging.type)) return false;

			// Filter by minimum rating
			if (minRating > 0) {
				if (!lodging.average_rating || lodging.average_rating < minRating) return false;
			}

			// Filter by minimum price tier
			if (minPriceTier > 0) {
				if (!lodging.price_tier || lodging.price_tier < minPriceTier) return false;
			}

			// Filter by search query
			if (!query) return true;
			return lodging.name?.toLowerCase().includes(query) || lodging.type?.toLowerCase().includes(query);
		});
	}

	// Filter transportation pins
	$: {
		const query = searchQuery.toLowerCase().trim();
		filteredTransportationPins = transportationPins.filter((transport) => {
			// Filter by show transportation toggle
			if (!showTransportation) return false;

			// Filter by visited/planned status
			const statusMatch =
				(showVisited && transport.is_visited === true) || (showPlanned && transport.is_visited !== true);
			if (!statusMatch) return false;

			// Filter by hidden transportation types
			if (transport.type && hiddenTransportationTypes.has(transport.type)) return false;

			// Filter by minimum rating
			if (minRating > 0) {
				if (!transport.average_rating || transport.average_rating < minRating) return false;
			}

			// Note: Transportation uses average_price instead of price tier, so skip tier filtering

			// Filter by search query
			if (!query) return true;
			return (
				transport.name?.toLowerCase().includes(query) ||
				transport.type?.toLowerCase().includes(query) ||
				transport.from_location?.toLowerCase().includes(query) ||
				transport.to_location?.toLowerCase().includes(query)
			);
		});
	}

	// Auto-zoom to search results when search query changes (for any type)
	$: {
		const query = searchQuery.toLowerCase().trim();
		const hasResults = filteredPins.length > 0 || filteredLodgingPins.length > 0 || filteredTransportationPins.length > 0;
		if (query && hasResults && typeof window !== 'undefined') {
			zoomToFilteredPins();
		}
	}

	// Reset the longitude and latitude when the newMarker is set to null
	$: {
		if (!newMarker) {
			newLongitude = null;
			newLatitude = null;
		}
	}

	// Sync the locationBeingUpdated with the pins array
	$: {
		if (locationBeingUpdated && locationBeingUpdated.id) {
			const index = pins.findIndex((pin) => pin.id === locationBeingUpdated?.id);

			if (index !== -1) {
				// Update existing pin with new data
				pins[index] = {
					id: locationBeingUpdated.id,
					name: locationBeingUpdated.name,
					latitude: locationBeingUpdated.latitude?.toString() || '',
					longitude: locationBeingUpdated.longitude?.toString() || '',
					is_visited: locationBeingUpdated.is_visited,
					category: locationBeingUpdated.category
				};
				pins = pins; // Trigger reactivity
			} else {
				// Add new pin
				const newPin: Pin = {
					id: locationBeingUpdated.id,
					name: locationBeingUpdated.name,
					latitude: locationBeingUpdated.latitude?.toString() || '',
					longitude: locationBeingUpdated.longitude?.toString() || '',
					is_visited: locationBeingUpdated.is_visited,
					category: locationBeingUpdated.category
				};
				pins = [newPin, ...pins];
			}

			// Also update the cache
			locationCache.set(locationBeingUpdated.id, locationBeingUpdated);
		}
	}

	$: {
		// if show activities is true, fetch all activities
		if (showActivities && activities.length === 0) {
			fetchAllActivities();
		}
	}

	async function fetchAllActivities() {
		const response = await fetch('/api/activities');
		activities = await response.json();
	}

	$: {
		if (showCities && visitedCities.length === 0) {
			fetchVisitedCities();
		}
	}

	async function fetchVisitedCities() {
		const response = await fetch('/api/visitedcity');
		visitedCities = await response.json();
	}

	function formatDateForPopup(value: string | null | undefined): string {
		if (!value) return '';
		// Most API date strings here are ISO-ish; for a popup, a short date is enough.
		return value.split('T')[0] ?? value;
	}

	function truncateForPopup(value: string | null | undefined, max = 140): string {
		if (!value) return '';
		const normalized = value.replace(/\s+/g, ' ').trim();
		if (normalized.length <= max) return normalized;
		return `${normalized.slice(0, max).trim()}…`;
	}

	async function fetchLocationDetails(locationId: string): Promise<Location | null> {
		// Check cache first
		if (locationCache.has(locationId)) {
			return locationCache.get(locationId)!;
		}

		// Reuse in-flight requests so hover doesn't trigger duplicate fetches
		const existing = locationRequests.get(locationId);
		if (existing) return existing;

		const request = (async () => {
			try {
				loadingLocations.add(locationId);
				const response = await fetch(`/api/locations/${locationId}`);

				if (!response.ok) {
					throw new Error(`Failed to fetch location: ${response.statusText}`);
				}

				const location: Location = await response.json();
				locationCache.set(locationId, location);
				return location;
			} catch (error) {
				console.error('Error fetching location details:', error);
				return null;
			} finally {
				loadingLocations.delete(locationId);
				locationRequests.delete(locationId);
			}
		})();

		locationRequests.set(locationId, request);
		return request;
	}

	async function prefetchLocationDetailsForPopup(locationId: string) {
		hoveredPinId = locationId;
		hoveredLocationError = null;

		const cached = locationCache.get(locationId) ?? null;
		hoveredLocation = cached;

		// If we already have full data, no need to show a loading state.
		if (cached) {
			hoveredLocationLoading = false;
			return;
		}

		const seq = ++hoverRequestSeq;
		hoveredLocationLoading = true;

		const location = await fetchLocationDetails(locationId);
		if (seq !== hoverRequestSeq || hoveredPinId !== locationId) return;

		hoveredLocationLoading = false;
		if (!location) {
			hoveredLocationError = $t('errors.generic_error') ?? 'Failed to load details';
			hoveredLocation = cached;
			return;
		}

		hoveredLocation = location;
	}

	function clearHoverPopupIfActive(locationId: string) {
		if (hoveredPinId !== locationId) return;
		hoveredPinId = null;
		hoveredLocation = null;
		hoveredLocationLoading = false;
		hoveredLocationError = null;
	}

	function addMarker(e: CustomEvent<{ lngLat: { lng: any; lat: any } }>) {
		newMarker = null;
		newMarker = { lngLat: e.detail.lngLat };
		newLongitude = e.detail.lngLat.lng;
		newLatitude = e.detail.lngLat.lat;
	}

	function newAdventure() {
		initialLatLng = { lat: newLatitude, lng: newLongitude } as { lat: number; lng: number };
		createModalOpen = true;
	}

	function createNewAdventure(event: CustomEvent) {
		const location: Location = event.detail;

		// Add to pins array
		const newPin: Pin = {
			id: location.id,
			name: location.name,
			latitude: location.latitude?.toString() || '',
			longitude: location.longitude?.toString() || '',
			is_visited: location.is_visited,
			category: location.category
		};

		pins = [...pins, newPin];

		// Add to cache
		locationCache.set(location.id, location);

		newMarker = null;
		createModalOpen = false;
	}

	function clearMarker() {
		newMarker = null;
	}

	function zoomToFilteredPins() {
		// Collect all coordinates from all filtered items
		const allCoords: { lng: number; lat: number }[] = [];

		// Add location pins
		for (const pin of filteredPins) {
			const lng = parseCoordinate(pin.longitude);
			const lat = parseCoordinate(pin.latitude);
			if (lng !== null && lat !== null) {
				allCoords.push({ lng, lat });
			}
		}

		// Add lodging pins
		for (const lodging of filteredLodgingPins) {
			const lng = parseCoordinate(lodging.longitude);
			const lat = parseCoordinate(lodging.latitude);
			if (lng !== null && lat !== null) {
				allCoords.push({ lng, lat });
			}
		}

		// Add transportation pins (both origin and destination)
		for (const transport of filteredTransportationPins) {
			const originLng = parseCoordinate(transport.origin_longitude);
			const originLat = parseCoordinate(transport.origin_latitude);
			if (originLng !== null && originLat !== null) {
				allCoords.push({ lng: originLng, lat: originLat });
			}
			const destLng = parseCoordinate(transport.destination_longitude);
			const destLat = parseCoordinate(transport.destination_latitude);
			if (destLng !== null && destLat !== null) {
				allCoords.push({ lng: destLng, lat: destLat });
			}
		}

		if (allCoords.length === 0) return;

		const lngs = allCoords.map((c) => c.lng);
		const lats = allCoords.map((c) => c.lat);

		const minLng = Math.min(...lngs);
		const maxLng = Math.max(...lngs);
		const minLat = Math.min(...lats);
		const maxLat = Math.max(...lats);

		if (allCoords.length === 1) {
			// Single pin - center on it with a nice zoom level
			mapCenter = [lngs[0], lats[0]];
			mapZoom = 12;
		} else {
			// Multiple pins - fit bounds with padding
			const centerLng = (minLng + maxLng) / 2;
			const centerLat = (minLat + maxLat) / 2;
			mapCenter = [centerLng, centerLat];

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

	function updateUrlParams(lat: number, lng: number, zoom: number) {
		if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
		updateUrlTimeout = setTimeout(() => {
			const params = new URLSearchParams($page.url.searchParams);
			params.set('lat', lat.toFixed(6));
			params.set('lng', lng.toFixed(6));
			params.set('zoom', zoom.toFixed(2));
			goto(`?${params.toString()}`, { replaceState: true, noScroll: true, keepFocus: true });
		}, 500);
	}

	function handleMapMove(e: CustomEvent<{ center: { lng: number; lat: number }; zoom: number }>) {
		const { center, zoom } = e.detail;
		updateUrlParams(center.lat, center.lng, zoom);
	}

	onMount(() => {
		// Initialize from URL params
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
			}
		}

		if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
		const mql = window.matchMedia('(hover: none), (pointer: coarse)');
		const update = () => {
			isTouchLike = mql.matches;
		};
		update();
		if (typeof mql.addEventListener === 'function') {
			mql.addEventListener('change', update);
			return () => {
				mql.removeEventListener('change', update);
				if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
			};
		}
		// Safari < 14
		(mql as any).addListener?.(update);
		return () => {
			(mql as any).removeListener?.(update);
			if (updateUrlTimeout) clearTimeout(updateUrlTimeout);
		};
	});

	// FullMap handles cluster theme styling + cluster expansion on click.
</script>

<svelte:head>
	<title>Adventure Map</title>
	<meta name="description" content="View your travels on a map." />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="map-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<!-- Header Section -->
			<div class="sticky top-0 z-40 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4">
							<button
								class="btn btn-ghost btn-square lg:hidden"
								on:click={() => (sidebarOpen = !sidebarOpen)}
							>
								<Filter class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-xl">
									<MapIcon class="w-8 h-8 text-primary" />
								</div>
								<div>
									<h1 class="text-3xl font-bold bg-clip-text text-primary">
										{$t('map.location_map')}
									</h1>
									<p class="text-sm text-base-content/60">
										{filteredPins.length}
										{$t('worldtravel.of')}
										{totalAdventures}
										{$t('map.locations_shown')}
									</p>
								</div>
							</div>
						</div>

						<!-- Quick Stats -->
						<div class="hidden md:flex items-center gap-2">
							<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('adventures.visited')}</div>
									<div class="stat-value text-lg text-success">{visitedAdventures}</div>
								</div>
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('adventures.planned')}</div>
									<div class="stat-value text-lg text-info">{plannedAdventures}</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Controls -->
					<div class="mt-4 flex flex-wrap items-center gap-4">
						<!-- Search Bar -->
						<label class="input input-bordered input-sm flex items-center gap-2 flex-1 max-w-md">
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
									aria-label="Clear search"
								>
									✕
								</button>
							{/if}
						</label>

						<!-- Action Buttons -->
						<div class="flex items-center gap-2">
							{#if newMarker}
								<button type="button" class="btn btn-primary btn-sm gap-2" on:click={newAdventure}>
									<Plus class="w-4 h-4" />
									{$t('map.add_location_at_marker')}
								</button>
								<button type="button" class="btn btn-ghost btn-sm gap-2" on:click={clearMarker}>
									<Clear class="w-4 h-4" />
									{$t('map.clear_marker')}
								</button>
							{:else}
								<button
									type="button"
									class="btn btn-primary btn-sm gap-2"
									on:click={() => (createModalOpen = true)}
								>
									<Plus class="w-4 h-4" />
									{$t('map.add_location')}
								</button>
							{/if}
						</div>
					</div>
				</div>
			</div>

			<!-- Map Section -->
			<div class="container mx-auto px-6 py-4 flex-1">
				<div class="card bg-base-100 shadow-xl h-full relative">
					<div class="card-body p-0 h-full">
						<FullMap
							bind:basemapType
							sourceId={PIN_SOURCE_ID}
							items={allFilteredPins}
							toFeature={pinToFeatureUnknown}
							clusterEnabled={true}
							clusterOptions={pinClusterOptions}
							{getMarkerProps}
							mapClass="w-full h-full min-h-[70vh] rounded-lg"
							standardControls
							zoom={mapZoom}
							center={mapCenter}
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
									<Marker lngLat={markerLngLat} class={isActive ? 'map-pin-active' : 'map-pin'}>
										<div
											class="relative group z-[1000] group-hover:z-[10000] focus-within:z-[10000]"
										>
											<!-- Marker Pin -->
											<div
												class="map-pin-hit grid place-items-center rounded-full shadow-lg cursor-pointer group-hover:scale-110 transition-all duration-200 {markerClassResolver(
													markerProps
												)} {markerProps.groupedItems && markerProps.groupedItems.length > 0 ? 'w-10 h-10 text-sm font-bold' : 'w-8 h-8 text-base'}"
												class:scale-110={isActive}
												role="button"
												tabindex="0"
												aria-label={markerProps.name}
												title=""
												on:mouseenter={() => {
													setActive(true);
													// Only fetch location details for single location pins (not grouped)
													const isGrouped = markerProps.groupedItems && markerProps.groupedItems.length > 0;
													if (markerProps.pinType === 'location' && !isGrouped) {
														prefetchLocationDetailsForPopup(markerProps.id);
													} else {
														// Clear any previous error state for grouped/non-location pins
														hoveredLocationError = null;
													}
												}}
												on:mouseleave={() => {
													if (isTouchLike) return;
													setActive(false);
													if (markerProps.pinType === 'location') {
														clearHoverPopupIfActive(markerProps.id);
													}
												}}
												on:focus={() => {
													setActive(true);
													const isGrouped = markerProps.groupedItems && markerProps.groupedItems.length > 0;
													if (markerProps.pinType === 'location' && !isGrouped) {
														prefetchLocationDetailsForPopup(markerProps.id);
													} else {
														hoveredLocationError = null;
													}
												}}
												on:blur={() => {
													if (isTouchLike) return;
													setActive(false);
													if (markerProps.pinType === 'location') {
														clearHoverPopupIfActive(markerProps.id);
													}
												}}
												on:click={(e) => {
													e.stopPropagation();
													// For grouped pins, just show popup - don't navigate
													const isGrouped = markerProps.groupedItems && markerProps.groupedItems.length > 0;
													if (isGrouped) {
														setActive(true);
														return;
													}
													if (isTouchLike) {
														// On touch devices: first tap shows popup, second tap navigates
														if (isActive) {
															if (markerProps.pinType === 'location') {
																if (hoveredPinId === markerProps.id && hoveredLocation) {
																	handleViewDetails(markerProps);
																	return;
																}
																prefetchLocationDetailsForPopup(markerProps.id);
															} else {
																// For lodging/transport, navigate directly on second tap
																handleViewDetails(markerProps);
															}
															return;
														}
														setActive(true);
														if (markerProps.pinType === 'location') {
															prefetchLocationDetailsForPopup(markerProps.id);
														}
														return;
													}
													// Desktop: click navigates directly
													handleViewDetails(markerProps);
												}}
												on:keydown={(e) => {
													if (e.key !== 'Enter') return;
													e.stopPropagation();
													// For grouped pins, just toggle popup
													const isGrouped = markerProps.groupedItems && markerProps.groupedItems.length > 0;
													if (isGrouped) {
														setActive(!isActive);
														return;
													}
													handleViewDetails(markerProps);
												}}
											>
												{#if markerProps.groupedItems && markerProps.groupedItems.length > 0}
													<span class="flex items-center gap-0.5">
														<span class="text-xs">{markerProps.categoryIcon || '📚'}</span>
														<span>{markerProps.groupedItems.length}</span>
													</span>
												{:else}
													{markerLabelResolver(markerProps)}
												{/if}
											</div>

											<!-- Custom DaisyUI Popup -->
											<div
												class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:pointer-events-auto transition-all duration-200 z-[9999]"
												class:opacity-100={isActive}
												class:pointer-events-auto={isActive}
											>
												<div
													class="card card-compact bg-base-100 shadow-xl border border-base-300 min-w-56 max-w-80"
												>
													<div class="card-body gap-3">
														<!-- Always-visible content -->
														<div class="space-y-2">
															<div class="min-w-0">
																<h3 class="card-title text-sm leading-tight truncate">
																	{markerProps.locationName || markerProps.name}
																</h3>
																{#if markerProps.pinType !== 'location'}
																	<div class="text-xs text-base-content/60">
																		{getTypeLabel(markerProps.pinType)}
																	</div>
																{/if}
																{#if markerProps.groupedItems && markerProps.groupedItems.length > 0}
																	<!-- Grouped items list - clickable -->
																	<div class="mt-2 space-y-0 max-h-40 overflow-y-auto">
																		{#each markerProps.groupedItems as item}
																			<button
																				type="button"
																				class="flex items-center gap-2 text-xs py-1.5 px-1 -mx-1 w-full text-left rounded hover:bg-base-200 transition-colors cursor-pointer border-b border-base-200 last:border-0"
																				on:click|stopPropagation={() => goto(getGroupedItemUrl(item))}
																			>
																				{#if item.itemType === 'transport' && item.direction}
																					<span class="text-base-content/50" title={item.direction === 'departure' ? $t('transportation.departure') : $t('transportation.arrival')}>
																						{item.direction === 'departure' ? '↗' : '↙'}
																					</span>
																				{/if}
																				<span>{item.icon}</span>
																				<span class="flex-1 truncate font-medium">{item.name}</span>
																				{#if item.subInfo}
																					<span class="text-base-content/60">{item.subInfo}</span>
																				{/if}
																			</button>
																		{/each}
																	</div>
																{:else if markerProps.subInfo}
																	<div class="text-xs text-base-content/70 mt-1">
																		{markerProps.subInfo}
																	</div>
																{/if}
																<div class="mt-1 flex items-center gap-2">
																	<div
																		class="badge badge-sm {markerProps.visitStatus === 'visited'
																			? 'badge-success'
																			: 'badge-info'}"
																	>
																		{markerProps.visitStatus === 'visited'
																			? $t('adventures.visited')
																			: $t('adventures.planned')}
																	</div>
																	{#if markerProps.categoryIcon && !markerProps.groupedItems}
																		<div class="badge badge-ghost badge-sm">
																			{markerProps.categoryIcon}
																		</div>
																	{/if}
																	{#if markerProps.groupedItems}
																		<div class="badge badge-ghost badge-sm">
																			{markerProps.groupedItems.length} {$t('transportation.items') || 'items'}
																		</div>
																	{/if}
																</div>
															</div>
														</div>

														<!-- Location-specific progressive content (not for grouped pins) -->
														{#if isActive && markerProps.pinType === 'location' && !(markerProps.groupedItems && markerProps.groupedItems.length > 0)}
															{#if hoveredPinId !== markerProps.id}
																<div class="space-y-2">
																	<div class="flex items-center gap-2">
																		<span class="loading loading-spinner loading-xs"></span>
																		<span class="text-xs text-base-content/60">Loading more…</span>
																	</div>
																	<div class="skeleton h-3 w-3/4"></div>
																	<div class="skeleton h-3 w-full"></div>
																	<div class="skeleton h-3 w-2/3"></div>
																</div>
															{:else if hoveredLocationError}
																<div role="alert" class="alert alert-error alert-soft">
																	<span class="text-sm">{hoveredLocationError}</span>
																</div>
															{:else if hoveredLocationLoading && !hoveredLocation}
																<div class="space-y-2">
																	<div class="flex items-center gap-2">
																		<span class="loading loading-spinner loading-xs"></span>
																		<span class="text-xs text-base-content/60">Loading more…</span>
																	</div>
																	<div class="skeleton h-3 w-3/4"></div>
																	<div class="skeleton h-3 w-full"></div>
																	<div class="skeleton h-3 w-2/3"></div>
																</div>
															{:else if hoveredLocation}
																{#if hoveredLocation.category?.display_name}
																	<div class="badge badge-outline badge-sm">
																		{hoveredLocation.category.display_name}
																	</div>
																{/if}

																{#if hoveredLocation.location}
																	<div class="text-xs text-base-content/70">
																		{truncateForPopup(hoveredLocation.location, 90)}
																	</div>
																{/if}

																<div class="flex flex-wrap items-center gap-2">
																	{#if hoveredLocation.rating !== null && hoveredLocation.rating !== undefined}
																		<div class="badge badge-neutral badge-sm">
																			★ {hoveredLocation.rating}
																		</div>
																	{/if}
																	<div class="badge badge-ghost badge-sm">
																		Visits: {hoveredLocation.visits?.length ?? 0}
																	</div>
																	<div class="badge badge-ghost badge-sm">
																		Media: {hoveredLocation.images?.length ?? 0}
																	</div>
																</div>

																{#if hoveredLocation.visits && hoveredLocation.visits.length > 0}
																	<div class="text-xs text-base-content/70">
																		Last visit: {formatDateForPopup(
																			hoveredLocation.visits[0]?.start_date
																		)}
																	</div>
																{/if}

																{#if hoveredLocation.description}
																	<p class="text-xs leading-snug text-base-content/80">
																		{truncateForPopup(hoveredLocation.description, 100)}
																	</p>
																{/if}
															{/if}
														{/if}

														{#if !markerProps.groupedItems || markerProps.groupedItems.length === 0}
														<div class="card-actions justify-end">
															<button
																type="button"
																class="btn btn-primary btn-sm"
																on:click={(e) => {
																	e.stopPropagation();
																	handleViewDetails(markerProps);
																}}
															>
																{$t('map.view_details')}
															</button>
														</div>
													{/if}
													</div>
												</div>
												<!-- Arrow pointer -->
												<div
													class="absolute top-full left-1/2 -translate-x-1/2 -mt-px w-3 h-3 rotate-45 bg-base-100 border-r border-b border-base-300"
												></div>
											</div>
										</div>
									</Marker>
								{/if}
							</svelte:fragment>

							<svelte:fragment slot="overlays">
								{#if newMarker}
									<DefaultMarker lngLat={newMarker.lngLat} />
								{/if}

								{#each visitedRegions as region}
									{#if showRegions}
										<Marker
											lngLat={[region.longitude, region.latitude]}
											class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-green-300 hover:bg-green-400 text-black shadow-lg cursor-pointer transition-transform hover:scale-110"
										>
											<LocationIcon class="w-5 h-5 text-green-700" />
											<Popup openOn="click" offset={[0, -10]}>
												<div class="space-y-2">
													<div class="text-lg text-black font-bold">{region.name}</div>
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
											class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-blue-300 hover:bg-blue-400 text-black shadow-lg cursor-pointer transition-transform hover:scale-110"
										>
											<LocationIcon class="w-5 h-5 text-blue-700" />
											<Popup openOn="click" offset={[0, -10]}>
												<div class="space-y-2">
													<div class="text-lg text-black font-bold">{city.name}</div>
													<div class="badge badge-success badge-sm">{city.id}</div>
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
				</div>
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-50">
			<label for="map-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<!-- Sidebar Header -->
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<Filter class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('map.map_controls')}</h2>
					</div>

					<!-- Adventure Statistics -->
					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<MapIcon class="w-5 h-5" />
							{$t('map.adventure_stats')}
						</h3>

						<div class="space-y-4">
							<div class="stat p-0">
								<div class="stat-title text-sm">{$t('dashboard.total_adventures')}</div>
								<div class="stat-value text-2xl">{totalAdventures}</div>
							</div>

							<div class="grid grid-cols-2 gap-4">
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('adventures.visited')}</div>
									<div class="stat-value text-lg text-success">{visitedAdventures}</div>
								</div>
								<div class="stat p-0">
									<div class="stat-title text-xs">{$t('adventures.planned')}</div>
									<div class="stat-value text-lg text-info">{plannedAdventures}</div>
								</div>
							</div>

							<div class="stat p-0">
								<div class="stat-title text-xs">{$t('map.regions')}</div>
								<div class="stat-value text-lg text-accent">{totalRegions}</div>
							</div>

							<!-- Progress Bar -->
							<div class="space-y-2">
								<div class="flex justify-between text-sm">
									<span>{$t('map.completion')}</span>
									<span>{Math.round((visitedAdventures / totalAdventures) * 100)}%</span>
								</div>
								<progress
									class="progress progress-primary w-full"
									value={visitedAdventures}
									max={totalAdventures}
								></progress>
							</div>
						</div>
					</div>

					<!-- Display Options -->
					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Eye class="w-5 h-5" />
							{$t('map.display_options')}
						</h3>

						<div class="space-y-3">
							<!-- Visited/Planned Status Filters -->
							<div class="border-b border-base-300 pb-3 mb-3">
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="checkbox"
										bind:checked={showVisited}
										class="checkbox checkbox-success checkbox-sm"
									/>
									<span class="label-text flex items-center gap-2">
										<Eye class="w-4 h-4" />
										{$t('adventures.visited')}
										<span class="badge badge-success badge-xs">●</span>
									</span>
								</label>

								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="checkbox"
										bind:checked={showPlanned}
										class="checkbox checkbox-info checkbox-sm"
									/>
									<span class="label-text flex items-center gap-2">
										<Calendar class="w-4 h-4" />
										{$t('adventures.planned')}
										<span class="badge badge-info badge-xs border-dashed">○</span>
									</span>
								</label>
							</div>

							<!-- LOCATIONS (Blue) -->
							<div class="border-b border-base-300 pb-3">
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="checkbox"
										bind:checked={showLocations}
										class="checkbox checkbox-primary checkbox-sm"
									/>
									<span class="label-text flex items-center gap-2 flex-1">
										<PinIcon class="w-4 h-4 text-blue-500" />
										{$t('navbar.locations')} ({filteredPins.length}/{pins.length})
									</span>
									{#if showLocations && availableCategories.length > 0}
										<button
											type="button"
											class="btn btn-ghost btn-xs"
											on:click|stopPropagation|preventDefault={() => (expandLocationFilters = !expandLocationFilters)}
										>
											{#if expandLocationFilters}
												<ChevronUp class="w-4 h-4" />
											{:else}
												<ChevronDown class="w-4 h-4" />
											{/if}
										</button>
									{/if}
								</label>

								{#if showLocations && expandLocationFilters && availableCategories.length > 0}
									<div class="ml-6 mt-2 space-y-1">
										{#if hiddenCategories.size > 0}
											<button
												type="button"
												class="btn btn-ghost btn-xs text-error"
												on:click={clearCategoryFilters}
											>
												<Clear class="w-3 h-3" />
												{$t('map.clear_filters')}
											</button>
										{/if}
										<div class="flex flex-wrap gap-1">
											{#each availableCategories as category}
												<button
													type="button"
													class="badge badge-sm cursor-pointer transition-all {!hiddenCategories.has(category)
														? 'badge-primary'
														: 'badge-ghost hover:badge-primary/50'}"
													on:click={() => toggleCategory(category)}
												>
													{categoryIconMap[category] || '📍'} {category}
												</button>
											{/each}
										</div>
									</div>
								{/if}
							</div>

							<!-- LODGING (Pink) -->
							<div class="border-b border-base-300 pb-3">
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="checkbox"
										bind:checked={showLodging}
										class="checkbox checkbox-secondary checkbox-sm"
									/>
									<span class="label-text flex items-center gap-2 flex-1">
										<HotelIcon class="w-4 h-4 text-pink-500" />
										{$t('navbar.lodging')} ({filteredLodgingPins.length}/{lodgingPins.length})
									</span>
									{#if showLodging && availableLodgingTypes.length > 0}
										<button
											type="button"
											class="btn btn-ghost btn-xs"
											on:click|stopPropagation|preventDefault={() => (expandLodgingFilters = !expandLodgingFilters)}
										>
											{#if expandLodgingFilters}
												<ChevronUp class="w-4 h-4" />
											{:else}
												<ChevronDown class="w-4 h-4" />
											{/if}
										</button>
									{/if}
								</label>

								{#if showLodging && expandLodgingFilters && availableLodgingTypes.length > 0}
									<div class="ml-6 mt-2 space-y-1">
										{#if hiddenLodgingTypes.size > 0}
											<button
												type="button"
												class="btn btn-ghost btn-xs text-error"
												on:click={clearLodgingTypeFilters}
											>
												<Clear class="w-3 h-3" />
												{$t('map.clear_filters')}
											</button>
										{/if}
										<div class="flex flex-wrap gap-1">
											{#each availableLodgingTypes as type}
												<button
													type="button"
													class="badge badge-sm cursor-pointer transition-all {!hiddenLodgingTypes.has(type)
														? 'badge-secondary'
														: 'badge-ghost hover:badge-secondary/50'}"
													on:click={() => toggleLodgingType(type)}
												>
													{getLodgingIcon(type)} {type}
												</button>
											{/each}
										</div>
									</div>
								{/if}
							</div>

							<!-- TRANSPORTATION (Yellow/Amber) -->
							<div class="border-b border-base-300 pb-3">
								<label class="label cursor-pointer justify-start gap-3">
									<input
										type="checkbox"
										bind:checked={showTransportation}
										class="checkbox checkbox-warning checkbox-sm"
									/>
									<span class="label-text flex items-center gap-2 flex-1">
										<TransportIcon class="w-4 h-4 text-amber-500" />
										{$t('navbar.transportation')} ({filteredTransportationPins.length}/{transportationPins.length})
									</span>
									{#if showTransportation && availableTransportationTypes.length > 0}
										<button
											type="button"
											class="btn btn-ghost btn-xs"
											on:click|stopPropagation|preventDefault={() => (expandTransportationFilters = !expandTransportationFilters)}
										>
											{#if expandTransportationFilters}
												<ChevronUp class="w-4 h-4" />
											{:else}
												<ChevronDown class="w-4 h-4" />
											{/if}
										</button>
									{/if}
								</label>

								{#if showTransportation && expandTransportationFilters && availableTransportationTypes.length > 0}
									<div class="ml-6 mt-2 space-y-1">
										{#if hiddenTransportationTypes.size > 0}
											<button
												type="button"
												class="btn btn-ghost btn-xs text-error"
												on:click={clearTransportationTypeFilters}
											>
												<Clear class="w-3 h-3" />
												{$t('map.clear_filters')}
											</button>
										{/if}
										<div class="flex flex-wrap gap-1">
											{#each availableTransportationTypes as type}
												<button
													type="button"
													class="badge badge-sm cursor-pointer transition-all {!hiddenTransportationTypes.has(type)
														? 'badge-warning'
														: 'badge-ghost hover:badge-warning/50'}"
													on:click={() => toggleTransportationType(type)}
												>
													{getTransportationIcon(type)} {type}
												</button>
											{/each}
										</div>
									</div>
								{/if}
							</div>

							<!-- Rating Filter -->
							<div class="border-b border-base-300 pb-3">
								<div class="label">
									<span class="label-text flex items-center gap-2">
										<Star class="w-4 h-4 text-warning" />
										{$t('adventures.min_rating')}
									</span>
								</div>
								<div class="flex flex-col gap-2 mt-1">
									<!-- Interactive star selector -->
									<div
										class="flex items-center justify-center gap-0.5"
										on:mouseleave={() => ratingHover = null}
										role="group"
										aria-label="Rating filter"
									>
										{#each [1, 2, 3, 4, 5] as rating}
											{@const isActive = minRating > 0 && rating <= minRating}
											{@const isHovered = ratingHover !== null && rating <= ratingHover}
											<button
												type="button"
												class="btn btn-ghost btn-xs p-0.5 min-h-0 h-auto transition-transform hover:scale-125"
												on:click={() => {
													if (minRating === rating) {
														minRating = 0;
													} else {
														minRating = rating;
													}
												}}
												on:mouseenter={() => ratingHover = rating}
												aria-label="Filter by {rating}+ stars"
											>
												<Star
													class="w-6 h-6 transition-all duration-150"
													style="color: {isActive || isHovered ? '#FBBD23' : 'oklch(var(--bc) / 0.2)'};"
												/>
											</button>
										{/each}
									</div>
									<!-- Current filter display -->
									<div class="text-center">
										{#if minRating > 0}
											<span class="badge badge-warning badge-sm gap-1">
												{minRating}+ {$t('adventures.stars')}
												<button
													type="button"
													class="btn btn-ghost btn-xs p-0 min-h-0 h-auto ml-1"
													on:click={() => minRating = 0}
													aria-label="Clear rating filter"
												>
													✕
												</button>
											</span>
										{:else}
											<span class="text-xs text-base-content/50">{$t('adventures.all')}</span>
										{/if}
									</div>
								</div>
							</div>

							<!-- Price Tier Filter -->
							<div class="border-b border-base-300 pb-3">
								<div class="label">
									<span class="label-text flex items-center gap-2">
										<CashMultiple class="w-4 h-4 text-success" />
										{$t('adventures.min_price_tier')}
									</span>
								</div>
								<div class="flex flex-col gap-2 mt-1">
									<!-- Interactive price tier selector -->
									<div
										class="flex items-center justify-center gap-1"
										on:mouseleave={() => priceTierHover = null}
										role="group"
										aria-label="Price tier filter"
									>
										{#each [1, 2, 3, 4] as tier}
											{@const isActive = minPriceTier > 0 && tier <= minPriceTier}
											{@const isHovered = priceTierHover !== null && tier <= priceTierHover}
											<button
												type="button"
												class="btn btn-ghost btn-xs p-1 min-h-0 h-auto transition-transform hover:scale-110"
												on:click={() => {
													if (minPriceTier === tier) {
														minPriceTier = 0;
													} else {
														minPriceTier = tier;
													}
												}}
												on:mouseenter={() => priceTierHover = tier}
												aria-label="Filter by {tier}+ price tier"
											>
												<span
													class="text-lg transition-all duration-150"
													style="opacity: {isActive || isHovered ? '1' : '0.3'};"
												>💰</span>
											</button>
										{/each}
									</div>
									<!-- Current filter display -->
									<div class="text-center">
										{#if minPriceTier > 0}
											<span class="badge badge-success badge-sm gap-1">
												{'💰'.repeat(minPriceTier)}+
												<button
													type="button"
													class="btn btn-ghost btn-xs p-0 min-h-0 h-auto ml-1"
													on:click={() => minPriceTier = 0}
													aria-label="Clear price tier filter"
												>
													✕
												</button>
											</span>
										{:else}
											<span class="text-xs text-base-content/50">{$t('adventures.all')}</span>
										{/if}
									</div>
								</div>
							</div>

							<!-- Other display options -->
							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="checkbox"
									bind:checked={showRegions}
									class="checkbox checkbox-accent checkbox-sm"
								/>
								<span class="label-text flex items-center gap-2">
									<LocationIcon class="w-4 h-4" />
									{$t('profile.visited_regions')} ({totalRegions})
								</span>
							</label>

							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="checkbox"
									bind:checked={showCities}
									class="checkbox checkbox-accent checkbox-sm"
								/>
								<span class="label-text flex items-center gap-2">
									<LocationIcon class="w-4 h-4" />
									{$t('map.show_visited_cities')}
									{visitedCities.length > 0 ? ` (${visitedCities.length})` : ''}
								</span>
							</label>

							<label class="label cursor-pointer justify-start gap-3">
								<input
									type="checkbox"
									bind:checked={showActivities}
									class="checkbox checkbox-error checkbox-sm"
								/>
								<span class="label-text flex items-center gap-2">
									<ActivityIcon class="w-4 h-4" />
									{$t('settings.activities')}{activities.length > 0
										? ` (${activities.length})`
										: ''}
								</span>
							</label>
						</div>
					</div>

					<!-- New Location Section -->
					<div class="card bg-base-200/50 p-4">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<Plus class="w-5 h-5" />
							{$t('adventures.new_location')}
						</h3>

						{#if newMarker}
							<div class="space-y-3">
								<div class="alert alert-info">
									<PinIcon class="w-4 h-4" />
									<span class="text-sm">{$t('map.marker_placed_on_map')}</span>
								</div>
								<button type="button" class="btn btn-primary w-full gap-2" on:click={newAdventure}>
									<Plus class="w-4 h-4" />
									{$t('map.add_location_at_marker')}
								</button>
								<button type="button" class="btn btn-ghost w-full gap-2" on:click={clearMarker}>
									<Clear class="w-4 h-4" />
									{$t('map.clear_marker')}
								</button>
							</div>
						{:else}
							<div class="space-y-3">
								<p class="text-sm text-base-content/60">
									{$t('map.place_marker_desc_location')}
								</p>
								<button
									type="button"
									class="btn btn-primary w-full gap-2"
									on:click={() => (createModalOpen = true)}
								>
									<Plus class="w-4 h-4" />
									{$t('map.add_location')}
								</button>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

{#if createModalOpen}
	<NewLocationModal
		on:close={() => (createModalOpen = false)}
		on:save={createNewAdventure}
		{initialLatLng}
		user={data.user}
		bind:location={locationBeingUpdated}
	/>
{/if}

<style>
	/* Ensure only the explicit hit area handles pointer events to avoid unintended edge hover/tap popups */
	:global(.maplibregl-marker.map-pin),
	:global(.mapboxgl-marker.map-pin) {
		pointer-events: none;
	}

	:global(.maplibregl-marker.map-pin .map-pin-hit),
	:global(.mapboxgl-marker.map-pin .map-pin-hit) {
		pointer-events: auto;
	}

	/* Suppress any default map popups so only the custom rich popup shows */
	:global(.maplibregl-popup),
	:global(.mapboxgl-popup) {
		display: none !important;
	}
</style>
