import inspirationalQuotes from './json/quotes.json';
import randomBackgrounds from './json/backgrounds.json';

// @ts-ignore
import { DateTime } from 'luxon';
import type {
	Location,
	Background,
	Checklist,
	Collection,
	Lodging,
	Note,
	Transportation,
	User
} from './types';

export function getRandomQuote() {
	const quotes = inspirationalQuotes.quotes;
	const randomIndex = Math.floor(Math.random() * quotes.length);
	let quoteString = quotes[randomIndex].quote;
	let authorString = quotes[randomIndex].author;
	return { quote: quoteString, author: authorString };
}

export function getFlag(size: number, country: string) {
	return `https://flagcdn.com/h${size}/${country}.png`;
}

export function checkLink(link: string) {
	if (link.startsWith('http://') || (link.startsWith('https://') && link.indexOf('.') !== -1)) {
		return link;
	} else {
		return 'http://' + link + '.com';
	}
}

export function isValidUrl(url: string) {
	try {
		new URL(url);
		return true;
	} catch (err) {
		return false;
	}
}

export function groupLocationsByDate(
	locations: Location[],
	startDate: Date,
	numberOfDays: number
): Record<string, Location[]> {
	const groupedLocations: Record<string, Location[]> = {};

	// Initialize all days in the range using DateTime
	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = DateTime.fromJSDate(startDate).plus({ days: i });
		const dateString = currentDate.toISODate(); // 'YYYY-MM-DD'
		groupedLocations[dateString] = [];
	}

	locations.forEach((location) => {
		location.visits.forEach((visit: { start_date: string; end_date: string; timezone: any }) => {
			if (visit.start_date) {
				// Check if it's all-day: start has 00:00:00 AND (no end OR end also has 00:00:00)
				const startHasZeros = isAllDay(visit.start_date);
				const endHasZeros = visit.end_date ? isAllDay(visit.end_date) : true;
				const isAllDayEvent = startHasZeros && endHasZeros;

				let startDT: DateTime;
				let endDT: DateTime;

				if (isAllDayEvent) {
					// For all-day events, extract just the date part and ignore timezone
					const dateOnly = visit.start_date.split('T')[0]; // Get 'YYYY-MM-DD'
					startDT = DateTime.fromISO(dateOnly); // This creates a date without time/timezone

					endDT = visit.end_date ? DateTime.fromISO(visit.end_date.split('T')[0]) : startDT;
				} else {
					// For timed events, use timezone conversion
					startDT = DateTime.fromISO(visit.start_date, {
						zone: visit.timezone ?? 'UTC'
					});

					endDT = visit.end_date
						? DateTime.fromISO(visit.end_date, {
								zone: visit.timezone ?? 'UTC'
							})
						: startDT;
				}

				const startDateStr = startDT.toISODate();
				const endDateStr = endDT.toISODate();

				// Loop through all days in range
				for (let i = 0; i < numberOfDays; i++) {
					const currentDate = DateTime.fromJSDate(startDate).plus({ days: i });
					const currentDateStr = currentDate.toISODate();

					// Include the current day if it falls within the location date range
					if (currentDateStr >= startDateStr && currentDateStr <= endDateStr) {
						if (groupedLocations[currentDateStr]) {
							groupedLocations[currentDateStr].push(location);
						}
					}
				}
			}
		});
	});

	return groupedLocations;
}

function getLocalDateString(date: Date): string {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

export function groupTransportationsByDate(
	transportations: Transportation[],
	startDate: Date,
	numberOfDays: number
): Record<string, Transportation[]> {
	const groupedTransportations: Record<string, Transportation[]> = {};

	// Initialize days
	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = DateTime.fromJSDate(startDate).plus({ days: i });
		const dateString = currentDate.toISODate(); // 'YYYY-MM-DD'
		groupedTransportations[dateString] = [];
	}

	transportations.forEach((transportation) => {
		if (transportation.date) {
			// Check if it's all-day: start has 00:00:00 AND (no end OR end also has 00:00:00)
			const startHasZeros = transportation.date.includes('T00:00:00');
			const endHasZeros = transportation.end_date
				? transportation.end_date.includes('T00:00:00')
				: true;
			const isTranspoAllDay = startHasZeros && endHasZeros;

			let startDT: DateTime;
			let endDT: DateTime;

			if (isTranspoAllDay) {
				// For all-day events, extract just the date part and ignore timezone
				const dateOnly = transportation.date.split('T')[0]; // Get 'YYYY-MM-DD'
				startDT = DateTime.fromISO(dateOnly); // This creates a date without time/timezone

				endDT = transportation.end_date
					? DateTime.fromISO(transportation.end_date.split('T')[0])
					: startDT;
			} else {
				// For timed events, use timezone conversion
				startDT = DateTime.fromISO(transportation.date, {
					zone: transportation.start_timezone ?? 'UTC'
				});

				endDT = transportation.end_date
					? DateTime.fromISO(transportation.end_date, {
							zone: transportation.end_timezone ?? transportation.start_timezone ?? 'UTC'
						})
					: startDT;
			}

			const startDateStr = startDT.toISODate();
			const endDateStr = endDT.toISODate();

			// Loop through all days in range
			for (let i = 0; i < numberOfDays; i++) {
				const currentDate = DateTime.fromJSDate(startDate).plus({ days: i });
				const currentDateStr = currentDate.toISODate();

				if (currentDateStr >= startDateStr && currentDateStr <= endDateStr) {
					groupedTransportations[currentDateStr]?.push(transportation);
				}
			}
		}
	});

	return groupedTransportations;
}
export function groupLodgingByDate(
	lodging: Lodging[],
	startDate: Date,
	numberOfDays: number
): Record<string, Lodging[]> {
	const groupedLodging: Record<string, Lodging[]> = {};

	// Initialize days (excluding last day for lodging)
	// If trip is 7/1 to 7/4 (4 days), show lodging only on 7/1, 7/2, 7/3
	const lodgingDays = numberOfDays - 1;

	for (let i = 0; i < lodgingDays; i++) {
		const currentDate = DateTime.fromJSDate(startDate).plus({ days: i });
		const dateString = currentDate.toISODate(); // 'YYYY-MM-DD'
		groupedLodging[dateString] = [];
	}

	lodging.forEach((hotel) => {
		if (hotel.check_in) {
			// Check if it's all-day: start has 00:00:00 AND (no end OR end also has 00:00:00)
			const startHasZeros = hotel.check_in.includes('T00:00:00');
			const endHasZeros = hotel.check_out ? hotel.check_out.includes('T00:00:00') : true;
			const isAllDay = startHasZeros && endHasZeros;

			let startDT: DateTime;
			let endDT: DateTime;

			if (isAllDay) {
				// For all-day events, extract just the date part and ignore timezone
				const dateOnly = hotel.check_in.split('T')[0]; // Get 'YYYY-MM-DD'
				startDT = DateTime.fromISO(dateOnly); // This creates a date without time/timezone

				endDT = hotel.check_out ? DateTime.fromISO(hotel.check_out.split('T')[0]) : startDT;
			} else {
				// For timed events, use timezone conversion
				startDT = DateTime.fromISO(hotel.check_in, {
					zone: hotel.timezone ?? 'UTC'
				});

				endDT = hotel.check_out
					? DateTime.fromISO(hotel.check_out, {
							zone: hotel.timezone ?? 'UTC'
						})
					: startDT;
			}

			const startDateStr = startDT.toISODate();
			const endDateStr = endDT.toISODate();

			// Loop through lodging days only (excluding last day)
			for (let i = 0; i < lodgingDays; i++) {
				const currentDate = DateTime.fromJSDate(startDate).plus({ days: i });
				const currentDateStr = currentDate.toISODate();

				// Show lodging on days where check-in occurs through the day before check-out
				// For lodging, we typically want to show it on the nights you're staying
				if (currentDateStr >= startDateStr && currentDateStr < endDateStr) {
					groupedLodging[currentDateStr]?.push(hotel);
				}
			}
		}
	});

	return groupedLodging;
}

export function groupNotesByDate(
	notes: Note[],
	startDate: Date,
	numberOfDays: number
): Record<string, Note[]> {
	const groupedNotes: Record<string, Note[]> = {};

	// Initialize all days in the range using local dates
	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = new Date(startDate);
		currentDate.setDate(startDate.getDate() + i);
		const dateString = getLocalDateString(currentDate);
		groupedNotes[dateString] = [];
	}

	notes.forEach((note) => {
		if (note.date) {
			// Use the date string as is since it's already in "YYYY-MM-DD" format.
			const noteDate = note.date;
			if (groupedNotes[noteDate]) {
				groupedNotes[noteDate].push(note);
			}
		}
	});

	return groupedNotes;
}

export function groupChecklistsByDate(
	checklists: Checklist[],
	startDate: Date,
	numberOfDays: number
): Record<string, Checklist[]> {
	const groupedChecklists: Record<string, Checklist[]> = {};

	// Initialize all days in the range using local dates
	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = new Date(startDate);
		currentDate.setDate(startDate.getDate() + i);
		const dateString = getLocalDateString(currentDate);
		groupedChecklists[dateString] = [];
	}

	checklists.forEach((checklist) => {
		if (checklist.date) {
			// Use the date string as is since it's already in "YYYY-MM-DD" format.
			const checklistDate = checklist.date;
			if (groupedChecklists[checklistDate]) {
				groupedChecklists[checklistDate].push(checklist);
			}
		}
	});

	return groupedChecklists;
}

// Helper to check if a given date string represents midnight (all-day)
// Improved isAllDay function to handle different ISO date formats
export function isAllDay(dateStr: string): boolean {
	// Check for various midnight formats in UTC
	return dateStr.endsWith('T00:00:00Z') || dateStr.endsWith('T00:00:00.000Z');
}

export function continentCodeToString(code: string) {
	switch (code) {
		case 'AF':
			return 'Africa';
		case 'AN':
			return 'Antarctica';
		case 'AS':
			return 'Asia';
		case 'EU':
			return 'Europe';
		case 'NA':
			return 'North America';
		case 'OC':
			return 'Oceania';
		case 'SA':
			return 'South America';
		default:
			return 'Unknown';
	}
}

export let ADVENTURE_TYPES = [
	{ type: 'general', label: 'General 🌍' },
	{ type: 'outdoor', label: 'Outdoor 🏞️' },
	{ type: 'lodging', label: 'Lodging 🛌' },
	{ type: 'dining', label: 'Dining 🍽️' },
	{ type: 'activity', label: 'Activity 🏄' },
	{ type: 'attraction', label: 'Attraction 🎢' },
	{ type: 'shopping', label: 'Shopping 🛍️' },
	{ type: 'nightlife', label: 'Nightlife 🌃' },
	{ type: 'event', label: 'Event 🎉' },
	{ type: 'transportation', label: 'Transportation 🚗' },
	{ type: 'culture', label: 'Culture 🎭' },
	{ type: 'water_sports', label: 'Water Sports 🚤' },
	{ type: 'hiking', label: 'Hiking 🥾' },
	{ type: 'wildlife', label: 'Wildlife 🦒' },
	{ type: 'historical_sites', label: 'Historical Sites 🏛️' },
	{ type: 'music_concerts', label: 'Music & Concerts 🎶' },
	{ type: 'fitness', label: 'Fitness 🏋️' },
	{ type: 'art_museums', label: 'Art & Museums 🎨' },
	{ type: 'festivals', label: 'Festivals 🎪' },
	{ type: 'spiritual_journeys', label: 'Spiritual Journeys 🧘‍♀️' },
	{ type: 'volunteer_work', label: 'Volunteer Work 🤝' },
	{ type: 'other', label: 'Other' }
];

// adventure type to icon mapping
export let ADVENTURE_TYPE_ICONS = {
	general: '🌍',
	outdoor: '🏞️',
	lodging: '🛌',
	dining: '🍽️',
	activity: '🏄',
	attraction: '🎢',
	shopping: '🛍️',
	nightlife: '🌃',
	event: '🎉',
	transportation: '🚗',
	culture: '🎭',
	water_sports: '🚤',
	hiking: '🥾',
	wildlife: '🦒',
	historical_sites: '🏛️',
	music_concerts: '🎶',
	fitness: '🏋️',
	art_museums: '🎨',
	festivals: '🎪',
	spiritual_journeys: '🧘‍♀️',
	volunteer_work: '🤝',
	other: '❓'
};

export let LODGING_TYPES_ICONS = {
	hotel: '🏨',
	hostel: '🛏️',
	resort: '🏝️',
	bnb: '🍳',
	campground: '🏕️',
	cabin: '🏚️',
	apartment: '🏢',
	house: '🏠',
	villa: '🏡',
	motel: '🚗🏨',
	other: '❓'
};

export let TRANSPORTATION_TYPES_ICONS = {
	car: '🚗',
	plane: '✈️',
	train: '🚆',
	bus: '🚌',
	boat: '⛵',
	bike: '🚲',
	walking: '🚶',
	other: '❓'
};

export function getRandomBackground() {
	const today = new Date();

	// Special dates for specific backgrounds
	// New Years week

	const newYearsStart = new Date(today.getFullYear() - 1, 11, 31);
	newYearsStart.setHours(0, 0, 0, 0);
	const newYearsEnd = new Date(today.getFullYear(), 0, 2);
	newYearsEnd.setHours(23, 59, 59, 999);
	if (today >= newYearsStart && today <= newYearsEnd) {
		return {
			url: 'backgrounds/adventurelog_new_year.webp',
			author: 'Roven Images',
			location: "Happy New Year's from the AdventureLog team!"
		} as Background;
	}

	// Christmas 12/24 - 12/25
	const christmasStart = new Date(today.getFullYear(), 11, 24);
	christmasStart.setHours(0, 0, 0, 0);
	const christmasEnd = new Date(today.getFullYear(), 11, 25);
	christmasEnd.setHours(23, 59, 59, 999);

	if (today >= christmasStart && today <= christmasEnd) {
		return {
			url: 'backgrounds/adventurelog_christmas.webp',
			author: 'Annie Spratt',
			location: 'Merry Christmas from the AdventureLog team!'
		} as Background;
	}

	const randomIndex = Math.floor(Math.random() * randomBackgrounds.backgrounds.length);
	return randomBackgrounds.backgrounds[randomIndex] as Background;
}

export function findFirstValue(obj: any): any {
	for (const key in obj) {
		if (typeof obj[key] === 'object' && obj[key] !== null) {
			const value = findFirstValue(obj[key]);
			if (value !== undefined) {
				return value;
			}
		} else {
			return obj[key];
		}
	}
}

export let themes = [
	{ name: 'light', label: 'Light' },
	{ name: 'dark', label: 'Dark' },
	{ name: 'dim', label: 'Dim' },
	{ name: 'night', label: 'Night' },
	{ name: 'forest', label: 'Forest' },
	{ name: 'aqua', label: 'Aqua' },
	{ name: 'aestheticLight', label: 'Aesthetic Light' },
	{ name: 'aestheticDark', label: 'Aesthetic Dark' },
	{ name: 'northernLights', label: 'Northern Lights' }
];

export function osmTagToEmoji(tag: string) {
	switch (tag) {
		case 'camp_site':
			return '🏕️';
		case 'slipway':
			return '🛳️';
		case 'playground':
			return '🛝';
		case 'viewpoint':
			return '👀';
		case 'cape':
			return '🏞️';
		case 'beach':
			return '🏖️';
		case 'park':
			return '🌳';
		case 'museum':
			return '🏛️';
		case 'theme_park':
			return '🎢';
		case 'nature_reserve':
			return '🌲';
		case 'memorial':
			return '🕊️';
		case 'monument':
			return '🗿';
		case 'wood':
			return '🌲';
		case 'zoo':
			return '🦁';
		case 'attraction':
			return '🎡';
		case 'ruins':
			return '🏚️';
		case 'bay':
			return '🌊';
		case 'hotel':
			return '🏨';
		case 'motel':
			return '🏩';
		case 'pub':
			return '🍺';
		case 'restaurant':
			return '🍽️';
		case 'cafe':
			return '☕';
		case 'bakery':
			return '🥐';
		case 'archaeological_site':
			return '🏺';
		case 'lighthouse':
			return '🗼';
		case 'tree':
			return '🌳';
		case 'cliff':
			return '⛰️';
		case 'water':
			return '💧';
		case 'fishing':
			return '🎣';
		case 'golf_course':
			return '⛳';
		case 'swimming_pool':
			return '🏊';
		case 'stadium':
			return '🏟️';
		case 'cave_entrance':
			return '🕳️';
		case 'anchor':
			return '⚓';
		case 'garden':
			return '🌼';
		case 'disc_golf_course':
			return '🥏';
		case 'natural':
			return '🌿';
		case 'ice_rink':
			return '⛸️';
		case 'horse_riding':
			return '🐎';
		case 'wreck':
			return '🚢';
		case 'water_park':
			return '💦';
		case 'picnic_site':
			return '🧺';
		case 'axe_throwing':
			return '🪓';
		case 'fort':
			return '🏰';
		case 'amusement_arcade':
			return '🕹️';
		case 'tepee':
			return '🏕️';
		case 'track':
			return '🏃';
		case 'trampoline_park':
			return '🤸';
		case 'dojo':
			return '🥋';
		case 'tree_stump':
			return '🪵';
		case 'peak':
			return '🏔️';
		case 'fitness_centre':
			return '🏋️';
		case 'artwork':
			return '🎨';
		case 'fast_food':
			return '🍔';
		case 'ice_cream':
			return '🍦';
		default:
			return '📍'; // Default placeholder emoji for unknown tags
	}
}

export function debounce(func: Function, timeout: number) {
	let timer: number | NodeJS.Timeout;
	return (...args: any) => {
		clearTimeout(timer);
		timer = setTimeout(() => {
			func(...args);
		}, timeout);
	};
}

export function getIsDarkMode() {
	const theme = document.documentElement.getAttribute('data-theme');

	if (theme) {
		const isDark =
			theme === 'dark' ||
			theme === 'night' ||
			theme === 'aestheticDark' ||
			theme === 'northernLights' ||
			theme === 'forest' ||
			theme === 'dim';
		return isDark;
	}

	// Fallback to browser preference if no theme cookie is set
	if (typeof window !== 'undefined' && window.matchMedia) {
		const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		return prefersDark;
	}

	return false;
}

// Enhanced basemap functions with 3D terrain support
export function getBasemapUrl(type = 'default'): any {
	switch (type) {
		// 3D Terrain Maps with elevation data
		case 'terrain-3d':
			return {
				version: 8,
				name: '3D Terrain',
				sources: {
					'raster-tiles': {
						type: 'raster',
						tiles: ['https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'],
						tileSize: 256,
						attribution: '© OpenStreetMap contributors, © CARTO'
					},
					terrain: {
						type: 'raster-dem',
						tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
						encoding: 'terrarium',
						tileSize: 256,
						maxzoom: 15
					}
				},
				layers: [
					{
						id: 'background',
						type: 'background',
						paint: {
							'background-color': '#b8dee6'
						}
					},
					{
						id: 'raster-layer',
						type: 'raster',
						source: 'raster-tiles'
					}
				],
				terrain: {
					source: 'terrain',
					exaggeration: 1.5
				}
			};

		case 'satellite-terrain-3d':
			return {
				version: 8,
				name: 'Satellite 3D Terrain',
				sources: {
					satellite: {
						type: 'raster',
						tiles: [
							'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
						],
						tileSize: 256,
						attribution: '© Esri, Maxar, Earthstar Geographics, USGS'
					},
					terrain: {
						type: 'raster-dem',
						tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
						encoding: 'terrarium',
						tileSize: 256,
						maxzoom: 15
					}
				},
				layers: [
					{
						id: 'background',
						type: 'background',
						paint: {
							'background-color': '#000'
						}
					},
					{
						id: 'satellite-layer',
						type: 'raster',
						source: 'satellite'
					}
				],
				terrain: {
					source: 'terrain',
					exaggeration: 2.0
				}
			};

		case 'topo-terrain-3d':
			return {
				version: 8,
				name: 'Topographic 3D Terrain',
				sources: {
					topo: {
						type: 'raster',
						tiles: [
							'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}'
						],
						tileSize: 256,
						attribution: '© Esri, HERE, Garmin, USGS, FAO, NOAA'
					},
					terrain: {
						type: 'raster-dem',
						tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
						encoding: 'terrarium',
						tileSize: 256,
						maxzoom: 15
					}
				},
				layers: [
					{
						id: 'background',
						type: 'background',
						paint: {
							'background-color': '#f5f5dc'
						}
					},
					{
						id: 'topo-layer',
						type: 'raster',
						source: 'topo'
					}
				],
				terrain: {
					source: 'terrain',
					exaggeration: 1.8
				}
			};

		// Alternative free terrain source using MapTiler (no key required for basic use)
		case 'maptiler-terrain-3d':
			return {
				version: 8,
				name: 'MapTiler 3D Terrain',
				sources: {
					maptiler: {
						type: 'raster',
						tiles: [
							'https://api.maptiler.com/maps/outdoor/256/{z}/{x}/{y}.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL'
						],
						tileSize: 256,
						attribution: '© MapTiler © OpenStreetMap contributors'
					},
					'terrain-rgb': {
						type: 'raster-dem',
						tiles: [
							'https://api.maptiler.com/tiles/terrain-rgb/{z}/{x}/{y}.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL'
						],
						encoding: 'mapbox',
						tileSize: 256,
						maxzoom: 12
					}
				},
				layers: [
					{
						id: 'background',
						type: 'background',
						paint: {
							'background-color': '#e8f4f8'
						}
					},
					{
						id: 'maptiler-layer',
						type: 'raster',
						source: 'maptiler'
					}
				],
				terrain: {
					source: 'terrain-rgb',
					exaggeration: 1.5
				}
			};

		// Existing non-3D maps...
		case 'satellite':
			return getXYZStyle(
				'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
				'© Esri, Maxar, Earthstar Geographics, USGS'
			);

		case 'satellite-labels':
			return getXYZStyle(
				'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
				'© Esri',
				'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
			);

		case 'elevation':
			return getXYZStyle(
				'https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}',
				'© Esri, USGS, NOAA'
			);

		case 'usgs-topo':
			return getXYZStyle(
				'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',
				'© USGS'
			);

		case 'esri-topo':
			return getXYZStyle(
				'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
				'© Esri, HERE, Garmin, USGS, FAO, NOAA'
			);

		case 'osm-standard':
			return getXYZStyle(
				'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
				'© OpenStreetMap contributors'
			);

		case 'osm-humanitarian':
			return getXYZStyle(
				'https://tile-{s}.openstreetmap.fr/hot/{z}/{x}/{y}.png',
				'© OpenStreetMap contributors, Humanitarian OSM Team'
			);

		case 'osm-france':
			return getXYZStyle(
				'https://tile-{s}.openstreetmap.fr/osmfr/{z}/{x}/{y}.png',
				'© OpenStreetMap France'
			);

		case 'carto-light':
			return getXYZStyle(
				'https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png',
				'© OpenStreetMap contributors, © CartoDB'
			);

		case 'carto-dark':
			return getXYZStyle(
				'https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png',
				'© OpenStreetMap contributors, © CartoDB'
			);

		case 'carto-positron':
			return getXYZStyle(
				'https://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
				'© OpenStreetMap contributors, © CARTO'
			);

		case 'carto-positron-labels':
			return getXYZStyle(
				'https://basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png',
				'© OpenStreetMap contributors, © CARTO',
				'https://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png'
			);

		case 'carto-voyager':
			return getXYZStyle(
				'https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
				'© OpenStreetMap contributors, © CARTO'
			);

		case 'wikimedia':
			return getXYZStyle(
				'https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png',
				'© OpenStreetMap contributors, Wikimedia Maps'
			);

		case 'usgs-imagery':
			return getXYZStyle(
				'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}',
				'© USGS'
			);

		case 'usgs-imagery-topo':
			return getXYZStyle(
				'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer/tile/{z}/{y}/{x}',
				'© USGS'
			);

		case 'esri-streets':
			return getXYZStyle(
				'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
				'© Esri, HERE, Garmin, USGS, EPA'
			);

		case 'esri-national-geographic':
			return getXYZStyle(
				'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
				'© Esri, National Geographic, Garmin, HERE, UNEP-WCMC'
			);

		case 'esri-oceans':
			return getXYZStyle(
				'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
				'© Esri, GEBCO, NOAA, National Geographic, Garmin, HERE'
			);

		case 'esri-gray':
			return getXYZStyle(
				'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
				'© Esri, HERE, Garmin, USGS, EPA'
			);

		case 'opentopomap':
			return getXYZStyle(
				[
					'https://a.tile.opentopomap.org/{z}/{x}/{y}.png',
					'https://b.tile.opentopomap.org/{z}/{x}/{y}.png',
					'https://c.tile.opentopomap.org/{z}/{x}/{y}.png'
				],
				'© OpenTopoMap (CC-BY-SA), © OpenStreetMap contributors'
			);

		default:
			return getIsDarkMode()
				? 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
				: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json';
	}
}

// Helper function for XYZ tile styles (updated to handle arrays and remove {s} placeholders)
function getXYZStyle(tileUrl: string | string[], attribution: string, baseUrl?: string) {
	// Convert single URL to array and expand any remaining {s} placeholders
	let tiles: string[];
	if (Array.isArray(tileUrl)) {
		tiles = tileUrl;
	} else {
		if (tileUrl.includes('{s}')) {
			// Fallback: expand {s} to common subdomains
			const subdomains = ['a', 'b', 'c'];
			tiles = subdomains.map((s) => tileUrl.replace('{s}', s));
		} else {
			tiles = [tileUrl];
		}
	}

	return {
		version: 8,
		sources: {
			'raster-tiles': {
				type: 'raster',
				tiles: tiles,
				tileSize: 256,
				attribution: attribution
			},
			...(baseUrl && {
				'base-tiles': {
					type: 'raster',
					tiles: [baseUrl],
					tileSize: 256
				}
			})
		},
		layers: [
			...(baseUrl
				? [
						{
							id: 'base-layer',
							type: 'raster' as const,
							source: 'base-tiles'
						}
					]
				: []),
			{
				id: 'raster-layer',
				type: 'raster' as const,
				source: 'raster-tiles'
			}
		]
	};
}

// Enhanced basemap options array
export const basemapOptions = [
	// 3D Terrain Maps (New Category)
	{ value: 'terrain-3d', label: '3D Terrain', icon: '🏔️', category: '3D Terrain' },
	{
		value: 'satellite-terrain-3d',
		label: '3D Satellite Terrain',
		icon: '🛰️',
		category: '3D Terrain'
	},
	{ value: 'topo-terrain-3d', label: '3D Topographic', icon: '🗻', category: '3D Terrain' },

	// Standard & Vector
	{ value: 'default', label: 'Default', icon: '🗺️', category: 'Standard' },
	{ value: 'osm-standard', label: 'OpenStreetMap', icon: '🌍', category: 'Standard' },
	{ value: 'wikimedia', label: 'Wikimedia', icon: '📖', category: 'Standard' },

	// Satellite & Imagery
	{ value: 'satellite', label: 'Satellite', icon: '🛰️', category: 'Satellite' },
	{ value: 'satellite-labels', label: 'Satellite + Labels', icon: '🏷️', category: 'Satellite' },
	{ value: 'usgs-imagery', label: 'USGS Imagery', icon: '📸', category: 'Satellite' },
	{ value: 'usgs-imagery-topo', label: 'USGS Imagery + Topo', icon: '🗻', category: 'Satellite' },

	// Topographic & Terrain
	{ value: 'elevation', label: 'Elevation', icon: '🏔️', category: 'Topographic' },
	{ value: 'usgs-topo', label: 'USGS Topo', icon: '📊', category: 'Topographic' },
	{ value: 'esri-topo', label: 'Esri Topo', icon: '🗾', category: 'Topographic' },
	{ value: 'opentopomap', label: 'OpenTopoMap', icon: '🧭', category: 'Topographic' },

	// Clean & Minimal
	{ value: 'carto-light', label: 'Light', icon: '☀️', category: 'Clean' },
	{ value: 'carto-dark', label: 'Dark', icon: '🌙', category: 'Clean' },
	{ value: 'carto-positron', label: 'Positron', icon: '⚡', category: 'Clean' },
	{ value: 'carto-positron-labels', label: 'Positron + Labels', icon: '🏷️', category: 'Clean' },
	{ value: 'esri-gray', label: 'Gray Canvas', icon: '⬜', category: 'Clean' },

	// Specialized
	{ value: 'carto-voyager', label: 'Voyager', icon: '🚢', category: 'Specialized' },
	{ value: 'osm-humanitarian', label: 'Humanitarian', icon: '🏥', category: 'Specialized' },
	{ value: 'esri-streets', label: 'Streets', icon: '🛣️', category: 'Specialized' },
	{
		value: 'esri-national-geographic',
		label: 'National Geographic',
		icon: '🌎',
		category: 'Specialized'
	},
	{ value: 'esri-oceans', label: 'Oceans', icon: '🌊', category: 'Specialized' },
	{ value: 'osm-france', label: 'France Style', icon: '🇫🇷', category: 'Specialized' }
];

export function getBasemapLabel(value: string) {
	const option = basemapOptions.find((opt) => opt.value === value);
	return option ? option.label : 'Default';
}

export function getDistance(measurementSystem: 'metric' | 'imperial', meters: number): string {
	if (measurementSystem === 'imperial') {
		const miles = meters / 1609.34;
		return miles.toFixed(2);
	} else {
		const km = meters / 1000;
		return km.toFixed(2);
	}
}

export function getElevation(measurementSystem: 'metric' | 'imperial', elevation: number): string {
	if (measurementSystem === 'imperial') {
		const feet = elevation * 3.28084;
		return Math.round(feet).toString();
	} else {
		return Math.round(elevation).toString();
	}
}

export function getActivityColor(activityType: string) {
	const colors: Record<string, string> = {
		Hike: '#10B981',
		Run: '#F59E0B',
		Bike: '#3B82F6',
		Walk: '#8B5CF6',
		AlpineSki: '#0EA5E9',
		StandUpPaddling: '#3B82F6',
		default: '#6B7280'
	};
	return colors[activityType] || colors.default;
}
