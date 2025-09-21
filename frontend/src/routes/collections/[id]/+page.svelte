<script lang="ts">
	import type { Location, Checklist, Collection, Lodging, Note, Transportation } from '$lib/types';
	import { onMount, onDestroy } from 'svelte';
	import type { PageData } from './$types';
	import { marked } from 'marked'; // Import the markdown parser

	import { t } from 'svelte-i18n';
	import Lost from '$lib/assets/undraw_lost.svg';

	// @ts-ignore
	import Calendar from '@event-calendar/core';
	// @ts-ignore
	import TimeGrid from '@event-calendar/time-grid';
	// @ts-ignore
	import DayGrid from '@event-calendar/day-grid';

	import Plus from '~icons/mdi/plus';
	import LocationCard from '$lib/components/LocationCard.svelte';
	import AdventureLink from '$lib/components/LocationLink.svelte';
	import { MapLibre, Marker, Popup, LineLayer, GeoJSON } from 'svelte-maplibre';
	import TransportationCard from '$lib/components/TransportationCard.svelte';
	import NoteCard from '$lib/components/NoteCard.svelte';
	import NoteModal from '$lib/components/NoteModal.svelte';

	const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

	import {
		groupLocationsByDate,
		groupNotesByDate,
		groupTransportationsByDate,
		groupChecklistsByDate,
		osmTagToEmoji,
		groupLodgingByDate,
		LODGING_TYPES_ICONS,
		getBasemapUrl,
		isAllDay,
		getActivityColor
	} from '$lib';
	import { formatDateInTimezone, formatAllDayDate } from '$lib/dateUtils';

	import ChecklistCard from '$lib/components/ChecklistCard.svelte';
	import ChecklistModal from '$lib/components/ChecklistModal.svelte';
	import TransportationModal from '$lib/components/TransportationModal.svelte';
	import CardCarousel from '$lib/components/CardCarousel.svelte';
	import { goto } from '$app/navigation';
	import LodgingModal from '$lib/components/LodgingModal.svelte';
	import LodgingCard from '$lib/components/LodgingCard.svelte';
	import CollectionAllView from '$lib/components/CollectionAllView.svelte';
	import NewLocationModal from '$lib/components/NewLocationModal.svelte';

	export let data: PageData;
	console.log(data);

	const renderMarkdown = (markdown: string) => {
		return marked(markdown);
	};

	function getLodgingIcon(type: string) {
		if (type in LODGING_TYPES_ICONS) {
			return LODGING_TYPES_ICONS[type as keyof typeof LODGING_TYPES_ICONS];
		} else {
			return '🏨';
		}
	}

	let collection: Collection;

	let dates: Array<{
		id: string;
		start: string;
		end: string;
		title: string;
		backgroundColor?: string;
	}> = [];

	// Initialize calendar plugins and options
	let plugins = [TimeGrid, DayGrid];
	let options = {
		view: 'dayGridMonth',
		events: dates // Assign `dates` reactively
	};

	// Compute `dates` array reactively
	$: {
		dates = [];

		if (adventures) {
			adventures.forEach((adventure) => {
				adventure.visits.forEach((visit) => {
					if (visit.start_date) {
						let startDate = visit.start_date;
						let endDate = visit.end_date || visit.start_date;
						const targetTimezone = visit.timezone || userTimezone;
						const allDay = isAllDay(visit.start_date);

						// Handle timezone conversion for non-all-day events
						if (!allDay) {
							// Convert UTC dates to target timezone
							const startDateTime = new Date(visit.start_date);
							const endDateTime = new Date(visit.end_date || visit.start_date);

							// Format for calendar (ISO string in target timezone)
							startDate = new Intl.DateTimeFormat('sv-SE', {
								timeZone: targetTimezone,
								year: 'numeric',
								month: '2-digit',
								day: '2-digit',
								hour: '2-digit',
								minute: '2-digit',
								hourCycle: 'h23'
							})
								.format(startDateTime)
								.replace(' ', 'T');

							endDate = new Intl.DateTimeFormat('sv-SE', {
								timeZone: targetTimezone,
								year: 'numeric',
								month: '2-digit',
								day: '2-digit',
								hour: '2-digit',
								minute: '2-digit',
								hourCycle: 'h23'
							})
								.format(endDateTime)
								.replace(' ', 'T');
						} else {
							// For all-day events, use just the date part
							startDate = visit.start_date.split('T')[0];

							// For all-day events, add one day to end date to make it inclusive
							const endDateObj = new Date(visit.end_date || visit.start_date);
							endDateObj.setDate(endDateObj.getDate() + 1);
							endDate = endDateObj.toISOString().split('T')[0];
						}

						// Create detailed title with timezone info
						let detailedTitle = adventure.name;
						if (adventure.category?.icon) {
							detailedTitle = `${adventure.category.icon} ${detailedTitle}`;
						}

						// Add time info to title for non-all-day events
						if (!allDay) {
							const startTime = formatDateInTimezone(visit.start_date, targetTimezone);
							detailedTitle += ` (${startTime.split(' ').slice(-2).join(' ')})`;
							if (targetTimezone !== userTimezone) {
								detailedTitle += ` ${targetTimezone}`;
							}
						}

						dates.push({
							id: adventure.id,
							start: startDate,
							end: endDate,
							title: detailedTitle,
							backgroundColor: '#3b82f6'
						});
					}
				});
			});
		}

		if (transportations) {
			dates = dates.concat(
				transportations
					.filter((i) => i.date)
					.map((transportation) => ({
						id: transportation.id,
						start: transportation.date || '', // Ensure it's a string
						end: transportation.end_date || transportation.date || '', // Ensure it's a string
						title: transportation.name + (transportation.type ? ` (${transportation.type})` : ''),
						backgroundColor: '#10b981'
					}))
			);
		}

		if (lodging) {
			dates = dates.concat(
				lodging
					.filter((i) => i.check_in)
					.map((lodging) => {
						const checkIn = lodging.check_in;
						const checkOut = lodging.check_out || lodging.check_in;
						if (!checkIn) return null;

						const isAlldayLodging: boolean = isAllDay(checkIn as string);

						let startDate: string;
						let endDate: string;

						if (isAlldayLodging) {
							// For all-day, use date part only, no timezone conversion
							startDate = (checkIn as string).split('T')[0];

							const endDateObj = new Date(checkOut as string);
							endDateObj.setDate(endDateObj.getDate());
							endDate = endDateObj.toISOString().split('T')[0];

							return {
								id: lodging.id,
								start: startDate,
								end: endDate,
								title: `${getLodgingIcon(lodging.type)} ${lodging.name}`,
								backgroundColor: '#f59e0b'
							};
						} else {
							// Only use timezone if not all-day
							const lodgingTimezone = lodging.timezone || userTimezone;
							const checkInDateTime = new Date(checkIn as string);
							const checkOutDateTime = new Date(checkOut as string);

							startDate = new Intl.DateTimeFormat('sv-SE', {
								timeZone: lodgingTimezone,
								year: 'numeric',
								month: '2-digit',
								day: '2-digit'
							}).format(checkInDateTime);

							endDate = new Intl.DateTimeFormat('sv-SE', {
								timeZone: lodgingTimezone,
								year: 'numeric',
								month: '2-digit',
								day: '2-digit'
							}).format(checkOutDateTime);

							return {
								id: lodging.id,
								start: startDate,
								end: endDate,
								title: lodging.name,
								backgroundColor: '#f59e0b'
							};
						}
					})
					.filter((item) => item !== null)
			);
		}

		// Update `options.events` when `dates` changes
		options = { ...options, events: dates };
	}

	let currentView: string = 'itinerary';
	let currentItineraryView: string = 'date';

	let adventures: Location[] = [];

	$: lineData = createLineData(orderedItems);

	// Function to create GeoJSON line data from ordered items
	function createLineData(
		items: Array<{
			item: Location | Transportation | Lodging | Note | Checklist;
			start: string;
			end: string;
		}>
	) {
		if (items.length < 2) return null;

		const coordinates: [number, number][] = [];

		// Extract coordinates from each item
		for (const orderItem of items) {
			const item = orderItem.item;

			if (
				'origin_longitude' in item &&
				'origin_latitude' in item &&
				'destination_longitude' in item &&
				'destination_latitude' in item &&
				item.origin_longitude &&
				item.origin_latitude &&
				item.destination_longitude &&
				item.destination_latitude
			) {
				// For Transportation, add both origin and destination points
				coordinates.push([item.origin_longitude, item.origin_latitude]);
				coordinates.push([item.destination_longitude, item.destination_latitude]);
			} else if ('longitude' in item && 'latitude' in item && item.longitude && item.latitude) {
				// Handle Adventure and Lodging types
				coordinates.push([item.longitude, item.latitude]);
			}
		}

		// Only create line data if we have at least 2 coordinates
		if (coordinates.length >= 2) {
			return {
				type: 'Feature' as const,
				properties: {
					name: 'Itinerary Path',
					description: 'Path connecting chronological items'
				},
				geometry: {
					type: 'LineString' as const,
					coordinates: coordinates
				}
			};
		}

		return null;
	}

	let numVisited: number = 0;
	let numAdventures: number = 0;

	let transportations: Transportation[] = [];
	let lodging: Lodging[] = [];
	let notes: Note[] = [];
	let checklists: Checklist[] = [];

	let numberOfDays: number = NaN;

	function getTransportationEmoji(type: string): string {
		switch (type) {
			case 'car':
				return '🚗';
			case 'plane':
				return '✈️';
			case 'train':
				return '🚆';
			case 'bus':
				return '🚌';
			case 'boat':
				return '⛵';
			case 'bike':
				return '🚲';
			case 'walking':
				return '🚶';
			case 'other':
				return '🚀';
			default:
				return '🚀';
		}
	}

	let orderedItems: Array<{
		item: Location | Transportation | Lodging;
		type: 'adventure' | 'transportation' | 'lodging';
		start: string; // ISO date string
		end: string; // ISO date string
	}> = [];

	$: {
		// Reset ordered items
		orderedItems = [];

		// Add Adventures (using visit dates)
		adventures.forEach((adventure) => {
			adventure.visits.forEach((visit) => {
				orderedItems.push({
					item: adventure,
					start: visit.start_date,
					end: visit.end_date,
					type: 'adventure'
				});
			});
		});

		// Add Transportation
		transportations.forEach((transport) => {
			if (transport.date) {
				// Only add if date exists
				orderedItems.push({
					item: transport,
					start: transport.date,
					end: transport.end_date || transport.date, // Use end_date if available, otherwise use date,
					type: 'transportation'
				});
			}
		});

		// Add Lodging
		lodging.forEach((lodging) => {
			if (lodging.check_in) {
				// Only add if check_in exists
				orderedItems.push({
					item: lodging,
					start: lodging.check_in,
					end: lodging.check_out || lodging.check_in, // Use check_out if available, otherwise use check_in,
					type: 'lodging'
				});
			}
		});

		// Sort all items chronologically by start date
		orderedItems.sort((a, b) => {
			const dateA = new Date(a.start).getTime();
			const dateB = new Date(b.start).getTime();
			return dateA - dateB;
		});
	}

	$: filteredOrderedItems = orderedItems.filter((item) => {
		if (!collection?.start_date || !collection?.end_date) {
			return true; // If no date range is set, show all items
		}

		const collectionStart = new Date(collection.start_date);
		const collectionEnd = new Date(collection.end_date);
		const itemStart = new Date(item.start);
		const itemEnd = new Date(item.end);

		// Check if item overlaps with collection date range
		// Item is included if it starts before collection ends AND ends after collection starts
		return itemStart <= collectionEnd && itemEnd >= collectionStart;
	});

	$: {
		numAdventures = adventures.length;
		numVisited = adventures.filter((adventure) => adventure.is_visited).length;
	}

	let notFound: boolean = false;
	let isShowingLinkModal: boolean = false;
	let isShowingTransportationModal: boolean = false;
	let isShowingChecklistModal: boolean = false;

	function handleHashChange() {
		const hash = window.location.hash.replace('#', '');
		if (hash) {
			currentView = hash;
		} else if (!collection.start_date) {
			currentView = 'all';
		} else {
			currentView = 'itinerary';
		}
	}

	function changeHash(event: any) {
		window.location.hash = '#' + event.target.value;
	}

	onMount(() => {
		if (data.props.adventure) {
			collection = data.props.adventure;
			adventures = collection.locations as Location[];
		} else {
			notFound = true;
		}

		if (!collection) {
			return;
		}

		if (collection.start_date && collection.end_date) {
			numberOfDays =
				Math.floor(
					(new Date(collection.end_date).getTime() - new Date(collection.start_date).getTime()) /
						(1000 * 60 * 60 * 24)
				) + 1;

			// Update `options.events` when `collection.start_date` changes
			// @ts-ignore
			options = { ...options, date: collection.start_date };
		}
		if (collection.transportations) {
			transportations = collection.transportations;
		}
		if (collection.lodging) {
			lodging = collection.lodging;
		}
		if (collection.notes) {
			notes = collection.notes;
		}
		if (collection.checklists) {
			checklists = collection.checklists;
		}
		window.addEventListener('hashchange', handleHashChange);
		handleHashChange();
	});

	onDestroy(() => {
		window.removeEventListener('hashchange', handleHashChange);
	});

	function deleteAdventure(event: CustomEvent<string>) {
		adventures = adventures.filter((a) => a.id !== event.detail);
	}

	async function addAdventure(event: CustomEvent<Location>) {
		console.log(event.detail);
		if (adventures.find((a) => a.id === event.detail.id)) {
			return;
		} else {
			let adventure = event.detail;

			// add the collection id to the adventure collections array
			if (!adventure.collections) {
				adventure.collections = [collection.id];
			} else {
				if (!adventure.collections.includes(collection.id)) {
					adventure.collections.push(collection.id);
				}
			}

			let res = await fetch(`/api/locations/${adventure.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ collections: adventure.collections })
			});

			if (res.ok) {
				console.log('Adventure added to collection');
				adventure = await res.json();
				adventures = [...adventures, adventure];
			} else {
				console.log('Error adding adventure to collection');
			}
		}
	}

	function recomendationToAdventure(recomendation: any) {
		adventureToEdit = {
			id: '',
			user: null,
			name: recomendation.name,
			latitude: recomendation.latitude,
			longitude: recomendation.longitude,
			images: [],
			is_visited: false,
			is_public: false,
			visits: [],
			category: {
				display_name: recomendation.tag
					.replace(/_/g, ' ')
					.replace(/\b\w/g, (char: string) => char.toUpperCase()),
				icon: osmTagToEmoji(recomendation.tag),
				id: '',
				name: recomendation.tag,
				user: ''
			},
			attachments: [],
			trails: []
		};
		isLocationModalOpen = true;
	}

	let adventureToEdit: Location | null = null;
	let transportationToEdit: Transportation | null = null;
	let isShowingLodgingModal: boolean = false;
	let lodgingToEdit: Lodging | null = null;
	let isLocationModalOpen: boolean = false;
	let isNoteModalOpen: boolean = false;
	let noteToEdit: Note | null;
	let checklistToEdit: Checklist | null;

	let locationBeingUpdated: Location | undefined = undefined;

	// Sync the locationBeingUpdated with the adventures array
	$: {
		if (locationBeingUpdated && locationBeingUpdated.id) {
			const index = adventures.findIndex((adventure) => adventure.id === locationBeingUpdated?.id);

			if (index !== -1) {
				// Ensure visits are properly synced
				adventures[index] = {
					...adventures[index],
					...locationBeingUpdated,
					visits: locationBeingUpdated.visits || adventures[index].visits || []
				};
				adventures = adventures; // Trigger reactivity
			} else {
				adventures = [{ ...locationBeingUpdated }, ...adventures];
				if (data.props.adventure) {
					data.props.adventure.locations = adventures;
				}
			}
		}
	}

	function editAdventure(event: CustomEvent<Location>) {
		adventureToEdit = event.detail;
		isLocationModalOpen = true;
	}

	function editTransportation(event: CustomEvent<Transportation>) {
		transportationToEdit = event.detail;
		isShowingTransportationModal = true;
	}

	function editLodging(event: CustomEvent<Lodging>) {
		lodgingToEdit = event.detail;
		isShowingLodgingModal = true;
	}

	function saveOrCreateAdventure(event: CustomEvent<Location>) {
		if (adventures.find((adventure) => adventure.id === event.detail.id)) {
			adventures = adventures.map((adventure) => {
				if (adventure.id === event.detail.id) {
					return event.detail;
				}
				return adventure;
			});
		} else {
			adventures = [event.detail, ...adventures];
		}
		isLocationModalOpen = false;
	}

	let isPopupOpen = false;

	function togglePopup() {
		isPopupOpen = !isPopupOpen;
	}

	let recomendationsData: any;
	let loadingRecomendations: boolean = false;
	let recomendationsRange: number = 1000;
	let recomendationType: string = 'tourism';
	let recomendationTags: { name: string; display_name: string }[] = [];
	let selectedRecomendationTag: string = '';
	let filteredRecomendations: any[] = [];

	$: {
		if (recomendationsData && selectedRecomendationTag) {
			filteredRecomendations = recomendationsData.filter(
				(r: any) => r.tag === selectedRecomendationTag
			);
		} else {
			filteredRecomendations = recomendationsData;
		}
		console.log(filteredRecomendations);
		console.log(selectedRecomendationTag);
	}
	async function getRecomendations(adventure: Location) {
		recomendationsData = null;
		selectedRecomendationTag = '';
		loadingRecomendations = true;
		let res = await fetch(
			`/api/recommendations/query/?lat=${adventure.latitude}&lon=${adventure.longitude}&radius=${recomendationsRange}&category=${recomendationType}`
		);
		if (!res.ok) {
			console.log('Error fetching recommendations');
			return;
		}
		let data = await res.json();
		recomendationsData = data;

		if (recomendationsData && recomendationsData.some((r: any) => r.longitude && r.latitude)) {
			const tagMap = new Map();
			recomendationsData.forEach((r: any) => {
				const tag = formatTag(r.tag);
				if (tag) {
					tagMap.set(r.tag, { name: r.tag, display_name: tag });
				}
			});
			recomendationTags = Array.from(tagMap.values());

			function formatTag(tag: string): string {
				if (tag) {
					return (
						tag
							.split('_')
							.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
							.join(' ') + osmTagToEmoji(tag)
					);
				} else {
					return '';
				}
			}
		}
		loadingRecomendations = false;
		console.log(recomendationTags);
	}

	function saveOrCreateTransportation(event: CustomEvent<Transportation>) {
		if (transportations.find((transportation) => transportation.id === event.detail.id)) {
			// Update existing transportation
			transportations = transportations.map((transportation) => {
				if (transportation.id === event.detail.id) {
					return event.detail;
				}
				return transportation;
			});
		} else {
			// Create new transportation
			transportations = [event.detail, ...transportations];
		}
		isShowingTransportationModal = false;
	}

	function saveOrCreateLodging(event: CustomEvent<Lodging>) {
		if (lodging.find((lodging) => lodging.id === event.detail.id)) {
			// Update existing hotel
			lodging = lodging.map((lodging) => {
				if (lodging.id === event.detail.id) {
					return event.detail;
				}
				return lodging;
			});
		} else {
			// Create new lodging
			lodging = [event.detail, ...lodging];
		}
		isShowingLodgingModal = false;
	}
</script>

{#if isShowingLinkModal}
	<AdventureLink
		user={data?.user ?? null}
		on:close={() => {
			isShowingLinkModal = false;
		}}
		collectionId={collection.id}
		on:add={addAdventure}
	/>
{/if}

{#if isShowingTransportationModal}
	<TransportationModal
		{transportationToEdit}
		on:close={() => (isShowingTransportationModal = false)}
		on:save={saveOrCreateTransportation}
		{collection}
	/>
{/if}

{#if isShowingLodgingModal}
	<LodgingModal
		{lodgingToEdit}
		on:close={() => (isShowingLodgingModal = false)}
		on:save={saveOrCreateLodging}
		{collection}
	/>
{/if}

{#if isLocationModalOpen}
	<NewLocationModal
		on:close={() => (isLocationModalOpen = false)}
		user={data.user}
		locationToEdit={adventureToEdit}
		bind:location={locationBeingUpdated}
		{collection}
	/>
{/if}

{#if isNoteModalOpen}
	<NoteModal
		note={noteToEdit}
		user={data.user}
		on:close={() => (isNoteModalOpen = false)}
		{collection}
		on:save={(event) => {
			notes = notes.map((note) => {
				if (note.id === event.detail.id) {
					return event.detail;
				}
				return note;
			});
			isNoteModalOpen = false;
		}}
		on:close={() => (isNoteModalOpen = false)}
		on:create={(event) => {
			notes = [event.detail, ...notes];
			isNoteModalOpen = false;
		}}
	/>
{/if}

{#if isShowingChecklistModal}
	<ChecklistModal
		{collection}
		user={data.user}
		checklist={checklistToEdit}
		on:close={() => (isShowingChecklistModal = false)}
		on:create={(event) => {
			checklists = [event.detail, ...checklists];
			isShowingChecklistModal = false;
		}}
		on:save={(event) => {
			checklists = checklists.map((checklist) => {
				if (checklist.id === event.detail.id) {
					return event.detail;
				}
				return checklist;
			});
			isShowingChecklistModal = false;
		}}
	/>
{/if}

{#if !collection && !notFound}
	<div class="flex justify-center items-center w-full mt-16">
		<span class="loading loading-spinner w-24 h-24"></span>
	</div>
{/if}
{#if collection && collection.id}
	{#if data.user && data.user.uuid && (data.user.uuid == collection.user || (collection.shared_with && collection.shared_with.includes(data.user.uuid))) && !collection.is_archived}
		<div class="fixed bottom-4 right-4 z-[999]">
			<div class="flex flex-row items-center justify-center gap-4">
				<div class="dropdown dropdown-top dropdown-end z-[999]">
					<div tabindex="0" role="button" class="btn m-1 size-16 btn-primary">
						<Plus class="w-8 h-8" />
					</div>
					<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
					<ul
						tabindex="0"
						class="dropdown-content z-[1] menu p-4 shadow bg-base-300 text-base-content rounded-box w-52 gap-4"
					>
						{#if collection.user === data.user.uuid || (collection.shared_with && collection.shared_with.includes(data.user.uuid))}
							<p class="text-center font-bold text-lg">{$t('adventures.link_new')}</p>
							<button
								class="btn btn-primary"
								on:click={() => {
									isShowingLinkModal = true;
								}}
							>
								{$t('locations.location')}</button
							>
						{/if}
						<p class="text-center font-bold text-lg">{$t('adventures.add_new')}</p>
						<button
							class="btn btn-primary"
							on:click={() => {
								isLocationModalOpen = true;
								adventureToEdit = null;
							}}
						>
							{$t('locations.location')}</button
						>

						<button
							class="btn btn-primary"
							on:click={() => {
								// Reset the transportation object for creating a new one
								transportationToEdit = null;
								isShowingTransportationModal = true;
							}}
						>
							{$t('adventures.transportation')}</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isNoteModalOpen = true;

								noteToEdit = null;
							}}
						>
							{$t('adventures.note')}</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isShowingChecklistModal = true;

								checklistToEdit = null;
							}}
						>
							{$t('adventures.checklist')}</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isShowingLodgingModal = true;

								lodgingToEdit = null;
							}}
						>
							{$t('adventures.lodging')}</button
						>

						<!-- <button
			class="btn btn-primary"
			on:click={() => (isShowingNewTrip = true)}>Trip Planner</button
		  > -->
					</ul>
				</div>
			</div>
		</div>
	{/if}
	{#if collection.is_archived}
		<div class="flex items-center justify-center mt-4 mb-4">
			<div role="alert" class="alert alert-warning w-96 inline-flex items-center justify-center">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-6 w-6 shrink-0 stroke-current"
					fill="none"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
					/>
				</svg>
				<span>{$t('adventures.collection_archived')}</span>
			</div>
		</div>
	{/if}
	{#if collection.name}
		<h1 class="text-center font-extrabold text-4xl mb-2">{collection.name}</h1>
	{/if}
	{#if collection.link}
		<div class="flex items-center justify-center mb-2">
			<a href={collection.link} target="_blank" rel="noopener noreferrer" class="btn btn-primary">
				{$t('adventures.visit_link')}
			</a>
		</div>
	{/if}

	{#if collection.description}
		<div class="flex justify-center mt-4 max-w-screen-lg mx-auto">
			<article
				class="prose overflow-auto max-h-96 max-w-full p-4 border border-base-300 rounded-lg bg-base-300 mb-4"
				style="overflow-y: auto;"
			>
				{@html renderMarkdown(collection.description)}
			</article>
		</div>
	{/if}

	{#if adventures.length > 0}
		<div class="flex items-center justify-center mb-4">
			<div class="stats shadow bg-base-300">
				<div class="stat">
					<div class="stat-title">{$t('adventures.collection_stats')}</div>
					<div class="stat-value">{numVisited}/{numAdventures} Visited</div>
					{#if numAdventures === numVisited}
						<div class="stat-desc">{$t('adventures.collection_completed')}</div>
					{:else}
						<div class="stat-desc">{$t('adventures.keep_exploring')}</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}

	{#if collection.id}
		<select
			class="select select-bordered border-primary md:hidden w-full"
			value={currentView}
			on:change={changeHash}
		>
			<option value="itinerary">📅 {$t('adventures.itinerary')}</option>
			<option value="all">🗒️ {$t('adventures.all_linked_items')}</option>
			<option value="calendar">🗓️ {$t('navbar.calendar')}</option>
			<option value="map">🗺️ {$t('navbar.map')}</option>
			<option value="recommendations">👍️ {$t('recomendations.recommendations')}</option>
		</select>
		<div class="md:flex justify-center mx-auto hidden">
			<!-- svelte-ignore a11y-missing-attribute -->
			<div role="tablist" class="tabs tabs-boxed tabs-lg max-w-full">
				<!-- svelte-ignore a11y-missing-attribute -->
				{#if collection.start_date}
					<a
						href="#itinerary"
						role="tab"
						class="tab {currentView === 'itinerary' ? 'tab-active' : ''}"
						tabindex="0">{$t('adventures.itinerary')}</a
					>
				{/if}
				<a
					href="#all"
					role="tab"
					class="tab {currentView === 'all' ? 'tab-active' : ''}"
					tabindex="0">{$t('adventures.all_linked_items')}</a
				>
				<a
					href="#calendar"
					role="tab"
					class="tab {currentView === 'calendar' ? 'tab-active' : ''}"
					tabindex="0">{$t('navbar.calendar')}</a
				>
				<a
					href="#map"
					role="tab"
					class="tab {currentView === 'map' ? 'tab-active' : ''}"
					tabindex="0">{$t('navbar.map')}</a
				>
				<a
					href="#recommendations"
					role="tab"
					class="tab {currentView === 'recommendations' ? 'tab-active' : ''}"
					tabindex="0">{$t('recomendations.recommendations')}</a
				>
			</div>
		</div>
	{/if}

	{#if currentView == 'all'}
		<CollectionAllView
			{adventures}
			{transportations}
			{lodging}
			{notes}
			{checklists}
			user={data.user}
			{collection}
			on:editAdventure={editAdventure}
			on:deleteAdventure={deleteAdventure}
			on:editTransportation={editTransportation}
			on:deleteTransportation={(event) => {
				transportations = transportations.filter((t) => t.id != event.detail);
			}}
			on:editLodging={editLodging}
			on:deleteLodging={(event) => {
				lodging = lodging.filter((t) => t.id != event.detail);
			}}
			on:editNote={(event) => {
				noteToEdit = event.detail;
				isNoteModalOpen = true;
			}}
			on:deleteNote={(event) => {
				notes = notes.filter((n) => n.id != event.detail);
			}}
			on:editChecklist={(event) => {
				checklistToEdit = event.detail;
				isShowingChecklistModal = true;
			}}
			on:deleteChecklist={(event) => {
				checklists = checklists.filter((n) => n.id != event.detail);
			}}
		/>
	{/if}

	{#if collection.start_date && collection.end_date}
		{#if currentView == 'itinerary'}
			<div class="hero bg-base-200 py-8 mt-8">
				<div class="hero-content text-center">
					<div class="max-w-md">
						<h1 class="text-5xl font-bold mb-4">{$t('adventures.itineary_by_date')}</h1>
						{#if numberOfDays}
							<p class="text-lg mb-2">
								{$t('adventures.duration')}:
								<span class="badge badge-primary">{numberOfDays} {$t('adventures.days')}</span>
							</p>
						{/if}
						<p class="text-lg">
							Dates: <span class="font-semibold"
								>{new Date(collection.start_date).toLocaleDateString(undefined, {
									timeZone: 'UTC'
								})} -
								{new Date(collection.end_date).toLocaleDateString(undefined, {
									timeZone: 'UTC'
								})}</span
							>
						</p>
						<div class="join mt-2">
							<input
								class="join-item btn btn-neutral"
								type="radio"
								name="options"
								aria-label={$t('adventures.date_itinerary')}
								checked={currentItineraryView == 'date'}
								on:change={() => (currentItineraryView = 'date')}
							/>
							<input
								class="join-item btn btn-neutral"
								type="radio"
								name="options"
								aria-label={$t('adventures.ordered_itinerary')}
								checked={currentItineraryView == 'ordered'}
								on:change={() => (currentItineraryView = 'ordered')}
							/>
						</div>
					</div>
				</div>
			</div>

			{#if currentItineraryView == 'date'}
				<div class="container mx-auto px-4">
					{#each Array(numberOfDays) as _, i}
						{@const startDate = new Date(collection.start_date)}
						{@const tempDate = new Date(startDate.getTime())}
						{@const adjustedDate = new Date(tempDate.setUTCDate(tempDate.getUTCDate() + i))}
						{@const dateString = adjustedDate.toISOString().split('T')[0]}

						{@const dayAdventures =
							groupLocationsByDate(adventures, new Date(collection.start_date), numberOfDays + 1)[
								dateString
							] || []}
						{@const dayTransportations =
							groupTransportationsByDate(
								transportations,
								new Date(collection.start_date),
								numberOfDays + 1
							)[dateString] || []}
						{@const dayLodging =
							groupLodgingByDate(lodging, new Date(collection.start_date), numberOfDays + 1)[
								dateString
							] || []}
						{@const dayNotes =
							groupNotesByDate(notes, new Date(collection.start_date), numberOfDays + 1)[
								dateString
							] || []}
						{@const dayChecklists =
							groupChecklistsByDate(checklists, new Date(collection.start_date), numberOfDays + 1)[
								dateString
							] || []}

						<div class="card bg-base-100 shadow-xl my-8">
							<div class="card-body bg-base-200">
								<h2 class="card-title text-3xl justify-center g">
									{$t('adventures.day')}
									{i + 1}
									<div class="badge badge-lg">
										{adjustedDate.toLocaleDateString(undefined, { timeZone: 'UTC' })}
									</div>
								</h2>

								<div class="divider"></div>

								<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
									{#if dayAdventures.length > 0}
										{#each dayAdventures as adventure}
											<LocationCard
												user={data.user}
												on:edit={editAdventure}
												on:delete={deleteAdventure}
												{adventure}
												{collection}
											/>
										{/each}
									{/if}
									{#if dayTransportations.length > 0}
										{#each dayTransportations as transportation}
											<TransportationCard
												{transportation}
												user={data?.user}
												on:delete={(event) => {
													transportations = transportations.filter((t) => t.id != event.detail);
												}}
												on:edit={(event) => {
													transportationToEdit = event.detail;
													isShowingTransportationModal = true;
												}}
												{collection}
											/>
										{/each}
									{/if}
									{#if dayNotes.length > 0}
										{#each dayNotes as note}
											<NoteCard
												{note}
												user={data.user || null}
												on:edit={(event) => {
													noteToEdit = event.detail;
													isNoteModalOpen = true;
												}}
												on:delete={(event) => {
													notes = notes.filter((n) => n.id != event.detail);
												}}
												{collection}
											/>
										{/each}
									{/if}
									{#if dayLodging.length > 0}
										{#each dayLodging as hotel}
											<LodgingCard
												lodging={hotel}
												user={data?.user}
												on:delete={(event) => {
													lodging = lodging.filter((t) => t.id != event.detail);
												}}
												on:edit={editLodging}
												{collection}
											/>
										{/each}
									{/if}
									{#if dayChecklists.length > 0}
										{#each dayChecklists as checklist}
											<ChecklistCard
												{checklist}
												user={data.user || null}
												on:delete={(event) => {
													notes = notes.filter((n) => n.id != event.detail);
												}}
												on:edit={(event) => {
													checklistToEdit = event.detail;
													isShowingChecklistModal = true;
												}}
												{collection}
											/>
										{/each}
									{/if}
								</div>

								{#if dayAdventures.length == 0 && dayTransportations.length == 0 && dayNotes.length == 0 && dayChecklists.length == 0 && dayLodging.length == 0}
									<p class="text-center text-lg mt-2 italic">{$t('adventures.nothing_planned')}</p>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="container mx-auto px-4 py-8">
					<div class="flex flex-col items-center">
						<div class="w-full max-w-4xl relative">
							<!-- Vertical timeline line that spans the entire height -->
							{#if filteredOrderedItems.length > 0}
								<div class="absolute left-8 top-0 bottom-0 w-1 bg-primary"></div>
							{/if}
							<ul class="relative">
								{#each filteredOrderedItems as orderedItem, index}
									<li class="relative pl-20 mb-8">
										<!-- Timeline Icon -->
										<div
											class="absolute left-0 top-0 flex items-center justify-center w-16 h-16 bg-base-200 rounded-full border-2 border-primary"
										>
											{#if orderedItem.type === 'adventure' && orderedItem.item && 'category' in orderedItem.item && orderedItem.item.category && 'icon' in orderedItem.item.category}
												<span class="text-2xl">{orderedItem.item.category.icon}</span>
											{:else if orderedItem.type === 'transportation' && orderedItem.item && 'origin_latitude' in orderedItem.item}
												<span class="text-2xl">{getTransportationEmoji(orderedItem.item.type)}</span
												>
											{:else if orderedItem.type === 'lodging' && orderedItem.item && 'reservation_number' in orderedItem.item}
												<span class="text-2xl">{getLodgingIcon(orderedItem.item.type)}</span>
											{/if}
										</div>
										<!-- Card Content -->
										<div class="bg-base-200 p-6 rounded-lg shadow-lg">
											<div class="flex justify-between items-center mb-4">
												<span class="badge badge-lg">{$t(`adventures.${orderedItem.type}`)}</span>
												<div class="text-sm opacity-80 text-right">
													{#if orderedItem.start !== orderedItem.end}
														{new Date(orderedItem.start).toLocaleDateString(undefined, {})}
														<div>
															{new Date(orderedItem.start).toLocaleTimeString(undefined, {
																hour: '2-digit',
																minute: '2-digit'
															})}
															-
															{new Date(orderedItem.end).toLocaleTimeString(undefined, {
																hour: '2-digit',
																minute: '2-digit'
															})}
														</div>
														<div>
															<!-- Duration -->
															{Math.floor(
																(new Date(orderedItem.end).getTime() -
																	new Date(orderedItem.start).getTime()) /
																	1000 /
																	60 /
																	60
															)}h
															{Math.round(
																((new Date(orderedItem.end).getTime() -
																	new Date(orderedItem.start).getTime()) /
																	1000 /
																	60 /
																	60 -
																	Math.floor(
																		(new Date(orderedItem.end).getTime() -
																			new Date(orderedItem.start).getTime()) /
																			1000 /
																			60 /
																			60
																	)) *
																	60
															)}m
														</div>
													{:else}
														<div>
															{new Date(orderedItem.start).toLocaleDateString(undefined, {
																timeZone: 'UTC'
															})}
														</div>
														<div>{$t('adventures.all_day')} ⏱️</div>
													{/if}
												</div>
											</div>
											{#if orderedItem.type === 'adventure' && orderedItem.item && 'visits' in orderedItem.item}
												<LocationCard
													user={data.user}
													on:edit={editAdventure}
													on:delete={deleteAdventure}
													adventure={orderedItem.item}
													{collection}
												/>
											{:else if orderedItem.type === 'transportation' && orderedItem.item && 'origin_latitude' in orderedItem.item}
												<TransportationCard
													transportation={orderedItem.item}
													user={data?.user}
													on:delete={(event) => {
														transportations = transportations.filter((t) => t.id != event.detail);
													}}
													on:edit={editTransportation}
													{collection}
												/>
											{:else if orderedItem.type === 'lodging' && orderedItem.item && 'reservation_number' in orderedItem.item}
												<LodgingCard
													lodging={orderedItem.item}
													user={data?.user}
													on:delete={(event) => {
														lodging = lodging.filter((t) => t.id != event.detail);
													}}
													on:edit={editLodging}
													{collection}
												/>
											{/if}
										</div>
									</li>
								{/each}
							</ul>
							{#if filteredOrderedItems.length === 0}
								<div class="alert alert-info">
									<p class="text-center text-lg">{$t('adventures.no_ordered_items')}</p>
								</div>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		{/if}
	{/if}

	{#if currentView == 'map'}
		<div class="card bg-base-200 shadow-xl my-8 mx-auto w-10/12">
			<div class="card-body">
				<h2 class="card-title text-3xl justify-center mb-4">Trip Map</h2>
				<MapLibre
					style={getBasemapUrl()}
					class="aspect-[9/16] max-h-[70vh] sm:aspect-video sm:max-h-full w-full rounded-lg"
					standardControls
				>
					{#each adventures as adventure}
						{#if adventure.longitude && adventure.latitude}
							<Marker
								lngLat={[adventure.longitude, adventure.latitude]}
								class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 {adventure.is_visited
									? 'bg-red-300'
									: 'bg-blue-300'} text-black focus:outline-6 focus:outline-black"
								on:click={togglePopup}
							>
								<span class="text-xl">
									{adventure.category?.icon}
								</span>
								{#if isPopupOpen}
									<Popup openOn="click" offset={[0, -10]} on:close={() => (isPopupOpen = false)}>
										{#if adventure.images && adventure.images.length > 0}
											<CardCarousel
												images={adventure.images}
												name={adventure.name}
												icon={adventure?.category?.icon}
											/>
										{/if}
										<div class="text-lg text-black font-bold">{adventure.name}</div>
										<p class="font-semibold text-black text-md">
											{adventure.is_visited ? $t('adventures.visited') : $t('adventures.planned')}
										</p>
										<p class="font-semibold text-black text-md">
											{adventure.category?.display_name + ' ' + adventure.category?.icon}
										</p>
										{#if adventure.visits && adventure.visits.length > 0}
											<p class="text-black text-sm">
												{#each adventure.visits as visit}
													{visit.start_date
														? new Date(visit.start_date).toLocaleDateString(undefined, {
																timeZone: 'UTC'
															})
														: ''}
													{visit.end_date &&
													visit.end_date !== '' &&
													visit.end_date !== visit.start_date
														? ' - ' +
															new Date(visit.end_date).toLocaleDateString(undefined, {
																timeZone: 'UTC'
															})
														: ''}
													<br />
												{/each}
											</p>
										{/if}
										<button
											class="btn btn-neutral btn-wide btn-sm mt-4"
											on:click={() => goto(`/locations/${adventure.id}`)}
											>{$t('map.view_details')}</button
										>
									</Popup>
								{/if}
							</Marker>
						{/if}
					{/each}

					<!-- Shows activity GPX on the map -->
					{#each adventures as adventure}
						{#each adventure.visits as visit}
							{#each visit.activities as activity}
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
						{/each}
						{#each adventure.attachments as attachment}
							{#if attachment.geojson}
								<GeoJSON data={attachment.geojson}>
									<LineLayer
										paint={{
											'line-color': '#00FF00',
											'line-width': 2,
											'line-opacity': 0.6
										}}
									/>
								</GeoJSON>
							{/if}
						{/each}
					{/each}

					{#if lineData && collection.start_date && collection.end_date}
						<GeoJSON data={lineData}>
							<LineLayer
								layout={{ 'line-cap': 'round', 'line-join': 'round' }}
								paint={{
									'line-width': 4,
									'line-color': '#0088CC', // Blue line to distinguish from transportation lines
									'line-opacity': 0.8,
									'line-dasharray': [2, 1] // Dashed line to differentiate from direct transportation lines
								}}
							/>
						</GeoJSON>
					{/if}
					{#each transportations as transportation}
						{#if transportation.origin_latitude && transportation.origin_longitude && transportation.destination_latitude && transportation.destination_longitude}
							<!-- Origin Marker -->
							<Marker
								lngLat={{
									lng: transportation.origin_longitude,
									lat: transportation.origin_latitude
								}}
								class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 
			bg-green-300 text-black focus:outline-6 focus:outline-black"
							>
								<span class="text-xl">
									{getTransportationEmoji(transportation.type)}
								</span>
								<Popup openOn="click" offset={[0, -10]}>
									<div class="text-lg text-black font-bold">{transportation.name}</div>
									<p class="font-semibold text-black text-md">
										{transportation.type}
									</p>
								</Popup>
							</Marker>

							<!-- Destination Marker -->
							<Marker
								lngLat={{
									lng: transportation.destination_longitude,
									lat: transportation.destination_latitude
								}}
								class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 
			bg-red-300 text-black focus:outline-6 focus:outline-black"
							>
								<span class="text-xl">
									{getTransportationEmoji(transportation.type)}
								</span>
								<Popup openOn="click" offset={[0, -10]}>
									<div class="text-lg text-black font-bold">{transportation.name}</div>
									<p class="font-semibold text-black text-md">
										{transportation.type}
									</p>
								</Popup>
							</Marker>
						{/if}
					{/each}

					{#each lodging as hotel}
						{#if hotel.longitude && hotel.latitude}
							<Marker
								lngLat={{
									lng: hotel.longitude,
									lat: hotel.latitude
								}}
								class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 
								bg-yellow-300 text-black focus:outline-6 focus:outline-black"
							>
								<span class="text-xl">
									{getLodgingIcon(hotel.type)}
								</span>
								<Popup openOn="click" offset={[0, -10]}>
									<div class="text-lg text-black font-bold">{hotel.name}</div>
									<p class="font-semibold text-black text-md">
										{hotel.type}
									</p>
								</Popup>
							</Marker>
						{/if}
					{/each}
				</MapLibre>
			</div>
		</div>
	{/if}
	{#if currentView == 'calendar'}
		<div class="card bg-base-200 shadow-xl my-8 mx-auto w-10/12">
			<div class="card-body">
				<h2 class="card-title text-3xl justify-center mb-4">
					{$t('adventures.visit_calendar')}
				</h2>
				<Calendar {plugins} {options} />
			</div>
		</div>
	{/if}
	{#if currentView == 'recommendations' && data.user}
		<div class="card bg-base-200 shadow-xl my-8 mx-auto w-10/12">
			<div class="card-body">
				<h2 class="card-title text-3xl justify-center mb-4">
					{$t('recomendations.location_recommendations')}
				</h2>
				{#each adventures as adventure}
					{#if adventure.longitude && adventure.latitude}
						<button on:click={() => getRecomendations(adventure)} class="btn btn-neutral"
							>{adventure.name}</button
						>
					{/if}
				{/each}
				{#if adventures.length == 0}
					<div class="alert alert-info">
						<p class="text-center text-lg">{$t('adventures.no_locations_to_recommendations')}</p>
					</div>
				{/if}
				<div class="mt-4">
					<input
						type="range"
						min="1000"
						max="50000"
						class="range"
						step="1000"
						bind:value={recomendationsRange}
					/>
					<div class="flex w-full justify-between px-2">
						<span class="text-lg">
							{(recomendationsRange / 1609.344).toFixed(1)} mi ({(
								recomendationsRange / 1000
							).toFixed(1)} km)
						</span>
					</div>
					<div class="join flex items-center justify-center mt-4">
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="options"
							aria-label={$t('recomendations.tourism')}
							checked={recomendationType == 'tourism'}
							on:click={() => (recomendationType = 'tourism')}
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="options"
							aria-label={$t('recomendations.food')}
							checked={recomendationType == 'food'}
							on:click={() => (recomendationType = 'food')}
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="options"
							aria-label={$t('adventures.lodging')}
							checked={recomendationType == 'lodging'}
							on:click={() => (recomendationType = 'lodging')}
						/>
					</div>
					{#if recomendationTags.length > 0}
						<select
							class="select select-bordered w-full max-w-xs"
							bind:value={selectedRecomendationTag}
						>
							<option value="">All</option>
							{#each recomendationTags as tag}
								<option value={tag.name}>{tag.display_name}</option>
							{/each}
						</select>
					{/if}
				</div>

				{#if recomendationsData}
					<MapLibre
						style={getBasemapUrl()}
						class="aspect-[9/16] max-h-[70vh] sm:aspect-video sm:max
						-h-full w-full rounded-lg"
						standardControls
						center={{ lng: recomendationsData[0].longitude, lat: recomendationsData[0].latitude }}
						zoom={12}
					>
						{#each filteredRecomendations as recomendation}
							{#if recomendation.longitude && recomendation.latitude && recomendation.name}
								<Marker
									lngLat={[recomendation.longitude, recomendation.latitude]}
									class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-blue-300 text-black focus:outline-6 focus:outline-black"
									on:click={togglePopup}
								>
									<span class="text-xl">
										{osmTagToEmoji(recomendation.tag)}
									</span>
									{#if isPopupOpen}
										<Popup openOn="click" offset={[0, -10]} on:close={() => (isPopupOpen = false)}>
											<div class="text-lg text-black font-bold">{recomendation.name}</div>

											<p class="font-semibold text-black text-md">
												{`${recomendation.tag} ${osmTagToEmoji(recomendation.tag)}`}
											</p>
											<button
												class="btn btn-neutral btn-wide btn-sm mt-4"
												on:click={() => recomendationToAdventure(recomendation)}
												>{$t('adventures.create_location')}</button
											>
										</Popup>
									{/if}
								</Marker>
							{/if}
						{/each}
					</MapLibre>
					{#each filteredRecomendations as recomendation}
						{#if recomendation.name && recomendation.longitude && recomendation.latitude}
							<div class="card bg-base-100 shadow-xl my-4 w-full">
								<div class="card-body">
									<h2 class="card-title text-xl font-bold">
										{recomendation.name || $t('recomendations.recommendation')}
									</h2>
									{#if recomendation.address}
										<p class="text-sm">{recomendation.address}</p>
									{/if}
									<!-- badge with recomendation.distance_km also show in miles -->
									{#if recomendation.distance_km}
										<p class="text-sm">
											{$t('adventures.distance')}: {recomendation.distance_km.toFixed(1)} km ({(
												recomendation.distance_km / 1.609344
											).toFixed(1)} miles)
										</p>
									{/if}
									<p class="text-sm"></p>
									<div class="badge badge-primary">{recomendation.tag}</div>
									<button
										class="btn btn-primary"
										on:click={() => recomendationToAdventure(recomendation)}
									>
										{$t('adventures.create_location')}
									</button>
								</div>
							</div>
						{/if}
					{/each}
				{/if}
				{#if loadingRecomendations}
					<div class="card bg-base-100 shadow-xl my-4 w-full">
						<div class="card-body">
							<div class="flex flex-col items-center justify-center">
								<span class="loading loading-ring loading-lg"></span>
								<div class="mt-2">
									<p class="text-center text-lg">
										{$t('adventures.finding_recommendations')}...
									</p>
								</div>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}
{:else}
	<div class="hero min-h-screen bg-gradient-to-br from-base-200 to-base-300 overflow-x-hidden">
		<div class="hero-content text-center">
			<div class="max-w-md">
				<img src={Lost} alt="Lost" class="w-64 mx-auto mb-8 opacity-80" />
				<h1 class="text-5xl font-bold text-primary mb-4">{$t('adventures.location_not_found')}</h1>
				<p class="text-lg opacity-70 mb-8">{$t('adventures.location_not_found_desc')}</p>
				<button class="btn btn-primary btn-lg" on:click={() => goto('/')}>
					{$t('adventures.homepage')}
				</button>
			</div>
		</div>
	</div>
{/if}

<svelte:head>
	<title
		>{data.props.adventure && data.props.adventure.name
			? `${data.props.adventure.name}`
			: $t('adventures.collection')}</title
	>
	<meta
		name="description"
		content="Learn more about {data.props.adventure && data.props.adventure.name
			? `${data.props.adventure.name}.`
			: 'your adventures.'}"
	/>
</svelte:head>
