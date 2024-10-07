import inspirationalQuotes from './json/quotes.json';
import type { Adventure, Checklist, Collection, Note, Transportation, User } from './types';

export function getRandomQuote() {
	const quotes = inspirationalQuotes.quotes;
	const randomIndex = Math.floor(Math.random() * quotes.length);
	let quoteString = quotes[randomIndex].quote;
	let authorString = quotes[randomIndex].author;
	return '"' + quoteString + '" - ' + authorString;
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

	// Initialize all days in the range
	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = new Date(startDate);
		currentDate.setUTCDate(startDate.getUTCDate() + i);
		const dateString = currentDate.toISOString().split('T')[0];
		groupedAdventures[dateString] = [];
	}

	adventures.forEach((adventure) => {
		adventure.visits.forEach((visit) => {
			if (visit.start_date) {
				const adventureDate = new Date(visit.start_date).toISOString().split('T')[0];
				if (visit.end_date) {
					const endDate = new Date(visit.end_date).toISOString().split('T')[0];

					// Loop through all days and include adventure if it falls within the range
					for (let i = 0; i < numberOfDays; i++) {
						const currentDate = new Date(startDate);
						currentDate.setUTCDate(startDate.getUTCDate() + i);
						const dateString = currentDate.toISOString().split('T')[0];

						// Include the current day if it falls within the adventure date range
						if (dateString >= adventureDate && dateString <= endDate) {
							if (groupedAdventures[dateString]) {
								groupedAdventures[dateString].push(adventure);
							}
						}
					}
				} else if (groupedAdventures[adventureDate]) {
					// If there's no end date, add adventure to the start date only
					groupedAdventures[adventureDate].push(adventure);
				}
			}
		});
	});

	return groupedAdventures;
}

export function groupTransportationsByDate(
	transportations: Transportation[],
	startDate: Date,
	numberOfDays: number
): Record<string, Transportation[]> {
	const groupedTransportations: Record<string, Transportation[]> = {};

	// Initialize all days in the range
	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = new Date(startDate);
		currentDate.setUTCDate(startDate.getUTCDate() + i);
		const dateString = currentDate.toISOString().split('T')[0];
		groupedTransportations[dateString] = [];
	}

	transportations.forEach((transportation) => {
		if (transportation.date) {
			const transportationDate = new Date(transportation.date).toISOString().split('T')[0];
			if (transportation.end_date) {
				const endDate = new Date(transportation.end_date).toISOString().split('T')[0];

				// Loop through all days and include transportation if it falls within the range
				for (let i = 0; i < numberOfDays; i++) {
					const currentDate = new Date(startDate);
					currentDate.setUTCDate(startDate.getUTCDate() + i);
					const dateString = currentDate.toISOString().split('T')[0];

					// Include the current day if it falls within the transportation date range
					if (dateString >= transportationDate && dateString <= endDate) {
						if (groupedTransportations[dateString]) {
							groupedTransportations[dateString].push(transportation);
						}
					}
				}
			} else if (groupedTransportations[transportationDate]) {
				// If there's no end date, add transportation to the start date only
				groupedTransportations[transportationDate].push(transportation);
			}
		}
	});

	return groupedTransportations;
}

export function groupNotesByDate(
	notes: Note[],
	startDate: Date,
	numberOfDays: number
): Record<string, Note[]> {
	const groupedNotes: Record<string, Note[]> = {};

	// Initialize all days in the range
	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = new Date(startDate);
		currentDate.setUTCDate(startDate.getUTCDate() + i);
		const dateString = currentDate.toISOString().split('T')[0];
		groupedNotes[dateString] = [];
	}

	notes.forEach((note) => {
		if (note.date) {
			const noteDate = new Date(note.date).toISOString().split('T')[0];

			// Add note to the appropriate date group if it exists
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

	// Initialize all days in the range
	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = new Date(startDate);
		currentDate.setUTCDate(startDate.getUTCDate() + i);
		const dateString = currentDate.toISOString().split('T')[0];
		groupedChecklists[dateString] = [];
	}

	checklists.forEach((checklist) => {
		if (checklist.date) {
			const checklistDate = new Date(checklist.date).toISOString().split('T')[0];

			// Add checklist to the appropriate date group if it exists
			if (groupedChecklists[checklistDate]) {
				groupedChecklists[checklistDate].push(checklist);
			}
		}
	});

	return groupedChecklists;
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

export function typeToString(type: string) {
	const typeObj = ADVENTURE_TYPES.find((t) => t.type === type);
	if (typeObj) {
		return typeObj.label;
	} else {
		return 'Unknown';
	}
}

/**
 * Checks if an adventure has been visited.
 *
 * This function determines if the `adventure.visits` array contains at least one visit
 * with a `start_date` that is before the current date.
 *
 * @param adventure - The adventure object to check.
 * @returns `true` if the adventure has been visited, otherwise `false`.
 */
export function isAdventureVisited(adventure: Adventure) {
	const currentTime = Date.now();

	// Check if any visit's start_date is before the current time.
	return (
		adventure.visits &&
		adventure.visits.some((visit) => {
			const visitStartTime = new Date(visit.start_date).getTime();
			return visit.start_date && visitStartTime <= currentTime;
		})
	);
}
