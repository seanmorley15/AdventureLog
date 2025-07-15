import inspirationalQuotes from './json/quotes.json';
import randomBackgrounds from './json/backgrounds.json';

// @ts-ignore
import { DateTime } from 'luxon';
import type {
	Adventure,
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

export async function exportData() {
	let res = await fetch('/api/adventures/all');
	let adventures = (await res.json()) as Adventure[];

	res = await fetch('/api/collections/all');
	let collections = (await res.json()) as Collection[];

	res = await fetch('/api/visitedregion');
	let visitedRegions = await res.json();

	const data = {
		adventures,
		collections,
		visitedRegions
	};

	const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
	return URL.createObjectURL(blob);
}

export function isValidUrl(url: string) {
	try {
		new URL(url);
		return true;
	} catch (err) {
		return false;
	}
}

export function groupAdventuresByDate(
	adventures: Adventure[],
	startDate: Date,
	numberOfDays: number
): Record<string, Adventure[]> {
	const groupedAdventures: Record<string, Adventure[]> = {};

	// Initialize all days in the range using DateTime
	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = DateTime.fromJSDate(startDate).plus({ days: i });
		const dateString = currentDate.toISODate(); // 'YYYY-MM-DD'
		groupedAdventures[dateString] = [];
	}

	adventures.forEach((adventure) => {
		adventure.visits.forEach((visit) => {
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

					// Include the current day if it falls within the adventure date range
					if (currentDateStr >= startDateStr && currentDateStr <= endDateStr) {
						if (groupedAdventures[currentDateStr]) {
							groupedAdventures[currentDateStr].push(adventure);
						}
					}
				}
			}
		});
	});

	return groupedAdventures;
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

export function getAdventureTypeLabel(type: string) {
	// return the emoji ADVENTURE_TYPE_ICONS label for the given type if not found return ? emoji
	if (type in ADVENTURE_TYPE_ICONS) {
		return ADVENTURE_TYPE_ICONS[type as keyof typeof ADVENTURE_TYPE_ICONS];
	} else {
		return '❓';
	}
}

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
	{ name: 'northernLights', label: 'Northern Lights' },
	{ name: 'traveler', label: 'Traveler' }
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

export function getBasemapUrl() {
	if (getIsDarkMode()) {
		return 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
	}
	return 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json';
}
