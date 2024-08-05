import inspirationalQuotes from './json/quotes.json';
import type { Adventure, Collection, Note, Transportation } from './types';

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

	async function convertImages() {
		const promises = data.adventures.map(async (adventure, i) => {
			if (adventure.image) {
				const res = await fetch(adventure.image);
				const blob = await res.blob();
				const base64 = await blobToBase64(blob);
				adventure.image = base64;
				data.adventures[i].image = adventure.image;
			}
		});

		await Promise.all(promises);
	}

	function blobToBase64(blob: Blob): Promise<string> {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.readAsDataURL(blob);
			reader.onloadend = () => resolve(reader.result as string);
			reader.onerror = (error) => reject(error);
		});
	}

	await convertImages();

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

	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = new Date(startDate);
		currentDate.setDate(startDate.getDate() + i);
		const dateString = currentDate.toISOString().split('T')[0];
		groupedAdventures[dateString] = [];
	}

	adventures.forEach((adventure) => {
		if (adventure.date) {
			const adventureDate = new Date(adventure.date).toISOString().split('T')[0];
			if (groupedAdventures[adventureDate]) {
				groupedAdventures[adventureDate].push(adventure);
			}
		}
	});

	return groupedAdventures;
}

export function groupTransportationsByDate(
	transportations: Transportation[],
	startDate: Date,
	numberOfDays: number
): Record<string, Transportation[]> {
	const groupedTransportations: Record<string, Transportation[]> = {};

	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = new Date(startDate);
		currentDate.setDate(startDate.getDate() + i);
		const dateString = currentDate.toISOString().split('T')[0];
		groupedTransportations[dateString] = [];
	}

	transportations.forEach((transportation) => {
		if (transportation.date) {
			const transportationDate = new Date(transportation.date).toISOString().split('T')[0];
			if (groupedTransportations[transportationDate]) {
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

	for (let i = 0; i < numberOfDays; i++) {
		const currentDate = new Date(startDate);
		currentDate.setDate(startDate.getDate() + i);
		const dateString = currentDate.toISOString().split('T')[0];
		groupedNotes[dateString] = [];
	}

	notes.forEach((note) => {
		if (note.date) {
			const noteDate = new Date(note.date).toISOString().split('T')[0];
			if (groupedNotes[noteDate]) {
				groupedNotes[noteDate].push(note);
			}
		}
	});

	return groupedNotes;
}
