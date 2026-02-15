<script lang="ts">
	// @ts-nocheck
	import type {
		Collection,
		CollectionItineraryItem,
		CollectionItineraryDay,
		Location,
		Transportation,
		Lodging,
		Note,
		Checklist
	} from '$lib/types';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import { dndzone, TRIGGERS, SHADOW_ITEM_MARKER_PROPERTY_NAME } from 'svelte-dnd-action';
	import { flip } from 'svelte/animate';
	import CalendarBlank from '~icons/mdi/calendar-blank';
	import Bed from '~icons/mdi/bed';
	import Info from '~icons/mdi/information';
	import Plus from '~icons/mdi/plus';
	import LocationCard from '$lib/components/cards/LocationCard.svelte';
	import TransportationCard from '$lib/components/cards/TransportationCard.svelte';
	import LodgingCard from '$lib/components/cards/LodgingCard.svelte';
	import NoteCard from '$lib/components/cards/NoteCard.svelte';
	import ChecklistCard from '$lib/components/cards/ChecklistCard.svelte';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';
	import LodgingModal from '../lodging/LodgingModal.svelte';
	import TransportationModal from '../transportation/TransportationModal.svelte';
	import NoteModal from '$lib/components/NoteModal.svelte';
	import ChecklistModal from '$lib/components/ChecklistModal.svelte';
	import ItineraryLinkModal from '$lib/components/collections/ItineraryLinkModal.svelte';
	import ItineraryDayPickModal from '$lib/components/collections/ItineraryDayPickModal.svelte';
	import Car from '~icons/mdi/car';
	import LocationMarker from '~icons/mdi/map-marker';
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import Globe from '~icons/mdi/globe';

	export let collection: Collection;
	export let user: any;
	// Whether the current user can modify this collection (owner or shared user)
	export let canModify: boolean = false;

	const flipDurationMs = 200;

	// Extended itinerary item with resolved object
	type ResolvedItineraryItem = CollectionItineraryItem & {
		resolvedObject: Location | Transportation | Lodging | Note | Checklist | null;
	};

	// Group itinerary items by day
	type DayGroup = {
		date: string;
		displayDate: string;
		items: ResolvedItineraryItem[];
		overnightLodging: Lodging[]; // Lodging where guest is staying overnight (not check-in day)
		globalDatedItems: ResolvedItineraryItem[]; // Trip-wide items that still carry a date
		dayMetadata: CollectionItineraryDay | null; // Day name and description
	};

	$: days = groupItemsByDay(collection);
	$: unscheduledItems = getUnscheduledItems(collection);
	// Trip-wide (global) itinerary items
	$: globalItems = (collection.itinerary || [])
		.filter((it) => it.is_global)
		.map((it) => resolveItineraryItem(it, collection))
		.sort((a, b) => a.order - b.order);

	// Auto-generate state
	let isAutoGenerating = false;

	// Saving state for itinerary reorders. When true, disable drag interactions.
	let isSavingOrder = false;
	// Which day (ISO date string) is currently being saved. Used to show per-day spinner.
	let savingDay: string | null = null;

	// Check if auto-generate is available (only for users with modify permission)
	$: canAutoGenerate =
		canModify && collection.itinerary?.length === 0 && hasDatedRecords(collection);

	function hasDatedRecords(collection: Collection): boolean {
		// Check if collection has any dated records
		const hasVisits =
			collection.locations?.some((loc) => loc.visits?.some((v) => v.start_date)) || false;
		const hasLodging = collection.lodging?.some((l) => l.check_in) || false;
		const hasTransportation = collection.transportations?.some((t) => t.date) || false;
		const hasNotes = collection.notes?.some((n) => n.date) || false;
		const hasChecklists = collection.checklists?.some((c) => c.date) || false;

		return hasVisits || hasLodging || hasTransportation || hasNotes || hasChecklists;
	}

	async function handleAutoGenerate() {
		if (!canAutoGenerate || isAutoGenerating) return;

		isAutoGenerating = true;

		try {
			const response = await fetch('/api/itineraries/auto-generate/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					collection_id: collection.id
				})
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || error.error || 'Failed to auto-generate itinerary');
			}

			const data = await response.json();

			// Refresh the page to load the updated itinerary
			window.location.reload();
		} catch (error) {
			console.error('Auto-generate error:', error);
			alert(error.message || 'Failed to auto-generate itinerary');
			isAutoGenerating = false;
		}
	}

	function handleRemoveItineraryItem(event: CustomEvent<CollectionItineraryItem>) {
		const itemToRemove = event.detail;
		collection.itinerary = collection.itinerary?.filter((it) => it.id !== itemToRemove.id);
		days = groupItemsByDay(collection);
	}

	let locationToEdit: Location | null = null;
	let isLocationModalOpen: boolean = false;
	function handleEditLocation(event: CustomEvent<Location>) {
		locationToEdit = event.detail;
		isLocationModalOpen = true;
	}

	function handleDuplicateLocation(event: CustomEvent<Location>) {
		const duplicated = event.detail;
		if (!duplicated || !duplicated.id) return;

		const collectionId = collection?.id ? String(collection.id) : null;
		if (collectionId) {
			const existingCollections = Array.isArray((duplicated as any).collections)
				? (duplicated as any).collections.map((id: string) => String(id))
				: [];
			if (!existingCollections.includes(collectionId)) {
				(duplicated as any).collections = [...existingCollections, collectionId];
			}
		}

		collection = {
			...collection,
			locations: [
				duplicated,
				...(collection.locations || []).filter((loc) => String(loc.id) !== String(duplicated.id))
			]
		};

		days = groupItemsByDay(collection);
		unscheduledItems = getUnscheduledItems(collection);
	}

	let lodgingToEdit: Lodging | null = null;
	let isLodgingModalOpen: boolean = false;
	function handleEditLodging(event: CustomEvent<Lodging>) {
		lodgingToEdit = event.detail;
		isLodgingModalOpen = true;
	}

	let transportationToEdit: Transportation | null = null;
	let isTransportationModalOpen: boolean = false;
	function handleEditTransportation(event: CustomEvent<Transportation>) {
		transportationToEdit = event.detail;
		isTransportationModalOpen = true;
	}

	function handleEditNote(event: CustomEvent<Note>) {
		noteToEdit = event.detail;
		isNoteModalOpen = true;
		pendingAddDate = null;
	}

	function handleEditChecklist(event: CustomEvent<Checklist>) {
		checklistToEdit = event.detail;
		isChecklistModalOpen = true;
		pendingAddDate = null;
	}

	/**
	 * Move an item to the global (trip-wide) itinerary.
	 * Removes all dated entries for this item and adds it to the global view instead.
	 */
	async function moveItemToGlobal(objectType: string, objectId: string) {
		if (!collection.id) return;

		try {
			// Remove all dated itinerary entries for this item
			const entriesToRemove = (collection.itinerary || [])
				.filter((it) => it.object_id === objectId && it.date && !it.is_global)
				.map((it) => it.id);

			// Delete the dated entries, but preserve visits
			for (const entryId of entriesToRemove) {
				await fetch(`/api/itineraries/${entryId}?preserve_visits=true`, { method: 'DELETE' });
			}

			// Add as global if not already there
			const alreadyGlobal = (collection.itinerary || []).some(
				(it) => it.object_id === objectId && it.is_global
			);

			if (!alreadyGlobal) {
				const order = globalItems.length;
				const res = await fetch('/api/itineraries/', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						collection: collection.id,
						content_type: objectType,
						object_id: objectId,
						is_global: true,
						order
					})
				});

				if (!res.ok) throw new Error('Failed to add to global itinerary');
				const created = await res.json();
				collection.itinerary = [...(collection.itinerary || []), created];
			}

			// Remove dated entries from local state
			collection.itinerary = (collection.itinerary || []).filter(
				(it) => !entriesToRemove.includes(it.id)
			);

			// Refresh reactive variables
			days = groupItemsByDay(collection);
			globalItems = (collection.itinerary || [])
				.filter((it) => it.is_global)
				.map((it) => resolveItineraryItem(it, collection))
				.sort((a, b) => a.order - b.order);

			addToast('success', $t('itinerary.moved_to_trip_context'));
		} catch (error) {
			console.error('Error moving item to context:', error);
			addToast('error', $t('itinerary.failed_to_move_to_trip_context'));
		}
	}

	/**
	 * Add an unscheduled item directly to the global (trip-wide) itinerary.
	 */
	async function addUnscheduledItemToGlobal(type: string, itemId: string) {
		if (!collection.id) return;

		try {
			// Check if already in global view
			const alreadyGlobal = (collection.itinerary || []).some(
				(it) => it.object_id === itemId && it.is_global
			);

			if (alreadyGlobal) {
				addToast('info', $t('itinerary.item_already_in_trip_context'));
				return;
			}

			const order = globalItems.length;
			const res = await fetch('/api/itineraries/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					collection: collection.id,
					content_type: type,
					object_id: itemId,
					is_global: true,
					order
				})
			});

			if (!res.ok) throw new Error('Failed to add to global itinerary');

			const created = await res.json();
			collection.itinerary = [...(collection.itinerary || []), created];

			// Remove from unscheduled by moving it to itinerary
			unscheduledItems = unscheduledItems.filter((item) => !(item.item.id === itemId));

			// Refresh global items
			globalItems = (collection.itinerary || [])
				.filter((it) => it.is_global)
				.map((it) => resolveItineraryItem(it, collection))
				.sort((a, b) => a.order - b.order);

			addToast('success', $t('itinerary.added_to_trip_context'));
		} catch (error) {
			console.error('Error adding item to global:', error);
			addToast('error', $t('itinerary.failed_to_add_to_trip_context'));
		}
	}

	function handleItemDelete(event: CustomEvent<CollectionItineraryItem | string | number>) {
		const payload = event.detail;

		// Support both cases:
		// 1) Card components dispatch a primitive id (string/number) when deleting the underlying object
		// 2) Some callers may dispatch a full itinerary item object
		if (typeof payload === 'string' || typeof payload === 'number') {
			const objectId = payload;

			// Remove any itinerary entries that reference this object
			collection.itinerary = collection.itinerary?.filter(
				(it) => String(it.object_id) !== String(objectId)
			);

			// Remove the object from all possible collections (location/transportation/lodging/note/checklist)
			if (collection.locations) {
				collection.locations = collection.locations.filter(
					(loc) => String(loc.id) !== String(objectId)
				);
			}
			if (collection.transportations) {
				collection.transportations = collection.transportations.filter(
					(t) => String(t.id) !== String(objectId)
				);
			}
			if (collection.lodging) {
				collection.lodging = collection.lodging.filter((l) => String(l.id) !== String(objectId));
			}
			if (collection.notes) {
				collection.notes = collection.notes.filter((n) => String(n.id) !== String(objectId));
			}
			if (collection.checklists) {
				collection.checklists = collection.checklists.filter(
					(c) => String(c.id) !== String(objectId)
				);
			}

			// Re-group days and return
			days = groupItemsByDay(collection);
			return;
		}

		// Otherwise expect a full itinerary-like object
		const itemToDelete = payload as CollectionItineraryItem;
		collection.itinerary = collection.itinerary?.filter((it) => it.id !== itemToDelete.id);
		// Also remove the associated object from the collection
		const objectType = itemToDelete.item?.type || '';
		if (objectType === 'location') {
			collection.locations = collection.locations?.filter(
				(loc) => loc.id !== itemToDelete.object_id
			);
		} else if (objectType === 'transportation') {
			collection.transportations = collection.transportations?.filter(
				(t) => t.id !== itemToDelete.object_id
			);
		} else if (objectType === 'lodging') {
			collection.lodging = collection.lodging?.filter((l) => l.id !== itemToDelete.object_id);
		} else if (objectType === 'note') {
			collection.notes = collection.notes?.filter((n) => n.id !== itemToDelete.object_id);
		} else if (objectType === 'checklist') {
			collection.checklists = collection.checklists?.filter((c) => c.id !== itemToDelete.object_id);
		}
		days = groupItemsByDay(collection);
	}

	let locationBeingUpdated: Location | null = null;
	let lodgingBeingUpdated: Lodging | null = null;
	let transportationBeingUpdated: Transportation | null = null;

	let isNoteModalOpen = false;
	let isChecklistModalOpen = false;
	let isItineraryLinkModalOpen = false;

	let noteToEdit: Note | null = null;
	let checklistToEdit: Checklist | null = null;

	// Store the target date and display date for the link modal
	let linkModalTargetDate: string = '';
	let linkModalDisplayDate: string = '';

	// Day picker modal state for unscheduled items
	let isDayPickModalOpen = false;
	let dayPickItemToAdd: { type: string; item: any } | null = null;
	let dayPickScheduledDates: string[] = [];
	let dayPickSourceVisit: { id: string; start_date: string } | null = null;
	let dayPickSourceItineraryItemId: string | null = null; // Track which specific itinerary item is being moved

	// When opening a "create new item" modal we store the target date here
	let pendingAddDate: string | null = null;
	// Track if we've already added this location to the itinerary
	let addedToItinerary: Set<string> = new Set();

	function normalizeDateOnly(value: string | null | undefined): string | null {
		if (!value) return null;
		return value.includes('T') ? value.split('T')[0] : value;
	}

	function upsertNote(note: Note) {
		const notes = collection.notes ? [...collection.notes] : [];
		const idx = notes.findIndex((n) => n.id === note.id);
		if (idx >= 0) {
			notes[idx] = note;
		} else {
			notes.push(note);
		}
		collection = { ...collection, notes };
	}

	function upsertChecklist(checklist: Checklist) {
		const checklists = collection.checklists ? [...collection.checklists] : [];
		const idx = checklists.findIndex((c) => c.id === checklist.id);
		if (idx >= 0) {
			checklists[idx] = checklist;
		} else {
			checklists.push(checklist);
		}
		collection = { ...collection, checklists };
	}

	async function handleNoteUpsert(note: Note) {
		// Get the old note to compare dates
		const oldNote = collection.notes?.find((n) => n.id === note.id);
		const oldDate = oldNote ? normalizeDateOnly(oldNote.date) : null;
		const newDate = normalizeDateOnly(note.date);

		upsertNote(note);

		const targetDate = newDate || pendingAddDate;

		try {
			// If the date changed, remove old itinerary items for this note on the old date
			if (oldDate && newDate && oldDate !== newDate) {
				// Remove itinerary items from the old date
				const itemsToRemove =
					collection.itinerary?.filter(
						(it) => it.item?.type === 'note' && it.object_id === note.id && it.date === oldDate
					) || [];

				for (const item of itemsToRemove) {
					await fetch(`/api/itinerary/${item.id}`, { method: 'DELETE' });
				}

				collection.itinerary =
					collection.itinerary?.filter(
						(it) => !(it.item?.type === 'note' && it.object_id === note.id && it.date === oldDate)
					) || [];
			}

			const isAlreadyScheduled = collection.itinerary?.some(
				(it) => it.item?.type === 'note' && it.object_id === note.id && it.date === targetDate
			);

			if (targetDate && !isAlreadyScheduled) {
				await addItineraryItemForObject('note', note.id, targetDate, !newDate && !!pendingAddDate);
			}
		} finally {
			pendingAddDate = null;
			isNoteModalOpen = false;
		}
	}

	async function handleChecklistUpsert(checklist: Checklist) {
		// Get the old checklist to compare dates
		const oldChecklist = collection.checklists?.find((c) => c.id === checklist.id);
		const oldDate = oldChecklist ? normalizeDateOnly(oldChecklist.date) : null;
		const newDate = normalizeDateOnly(checklist.date);

		upsertChecklist(checklist);

		const targetDate = newDate || pendingAddDate;

		try {
			// If the date changed, remove old itinerary items for this checklist on the old date
			if (oldDate && newDate && oldDate !== newDate) {
				// Remove itinerary items from the old date
				const itemsToRemove =
					collection.itinerary?.filter(
						(it) =>
							it.item?.type === 'checklist' && it.object_id === checklist.id && it.date === oldDate
					) || [];

				for (const item of itemsToRemove) {
					await fetch(`/api/itinerary/${item.id}`, { method: 'DELETE' });
				}

				collection.itinerary =
					collection.itinerary?.filter(
						(it) =>
							!(
								it.item?.type === 'checklist' &&
								it.object_id === checklist.id &&
								it.date === oldDate
							)
					) || [];
			}

			const isAlreadyScheduled = collection.itinerary?.some(
				(it) =>
					it.item?.type === 'checklist' && it.object_id === checklist.id && it.date === targetDate
			);

			if (targetDate && !isAlreadyScheduled) {
				await addItineraryItemForObject(
					'checklist',
					checklist.id,
					targetDate,
					!newDate && !!pendingAddDate
				);
			}
		} finally {
			pendingAddDate = null;
			isChecklistModalOpen = false;
		}
	}

	// Sync the
	//  with the collection.locations array
	$: if (locationBeingUpdated && locationBeingUpdated.id && collection) {
		// Make a shallow copy of locations (ensure array exists)
		const locs = collection.locations ? [...collection.locations] : [];

		const index = locs.findIndex((loc) => loc.id === locationBeingUpdated.id);

		if (index !== -1) {
			// Ensure visits are properly synced and replace the item immutably
			locs[index] = {
				...locs[index],
				...locationBeingUpdated,
				visits: locationBeingUpdated.visits || locs[index].visits || []
			};
		} else {
			// Prepend new/updated location
			locs.unshift({ ...locationBeingUpdated });
		}

		// Assign back to collection immutably to trigger reactivity
		collection = { ...collection, locations: locs };
	}

	// If a new location was just created and we have a pending add-date,
	// attach it to that date in the itinerary.
	$: if (
		locationBeingUpdated?.id &&
		pendingAddDate &&
		!addedToItinerary.has(locationBeingUpdated.id)
	) {
		addItineraryItemForObject('location', locationBeingUpdated.id, pendingAddDate);
		// Mark this location as added to prevent duplicates
		addedToItinerary.add(locationBeingUpdated.id);
		addedToItinerary = addedToItinerary; // trigger reactivity
	}

	// Sync the lodgingBeingUpdated with the collection.lodging array
	$: if (lodgingBeingUpdated && lodgingBeingUpdated.id && collection) {
		// Make a shallow copy of lodging (ensure array exists)
		const lodgings = collection.lodging ? [...collection.lodging] : [];

		const index = lodgings.findIndex((lodge) => lodge.id === lodgingBeingUpdated.id);

		if (index !== -1) {
			// Replace the item immutably
			lodgings[index] = {
				...lodgings[index],
				...lodgingBeingUpdated
			};
		} else {
			// Prepend new/updated lodging
			lodgings.unshift({ ...lodgingBeingUpdated });
		}

		// Assign back to collection immutably to trigger reactivity
		collection = { ...collection, lodging: lodgings };
	}

	// If a new lodging was just created and we have a pending add-date,
	// attach it to that date in the itinerary.
	$: if (
		lodgingBeingUpdated?.id &&
		pendingAddDate &&
		!addedToItinerary.has(lodgingBeingUpdated.id)
	) {
		// Normalize check_in to date-only (YYYY-MM-DD) if present
		const lodgingCheckInDate = lodgingBeingUpdated.check_in
			? String(lodgingBeingUpdated.check_in).split('T')[0]
			: null;
		const targetDate = lodgingCheckInDate || pendingAddDate;

		addItineraryItemForObject('lodging', lodgingBeingUpdated.id, targetDate);
		// Mark this lodging as added to prevent duplicates
		addedToItinerary.add(lodgingBeingUpdated.id);
		addedToItinerary = addedToItinerary; // trigger reactivity
	}

	// Sync the transportationBeingUpdated with the collection.transportations array
	$: if (transportationBeingUpdated && transportationBeingUpdated.id && collection) {
		// Make a shallow copy of transportations (ensure array exists)
		const transports = collection.transportations ? [...collection.transportations] : [];

		const index = transports.findIndex((t) => t.id === transportationBeingUpdated.id);

		if (index !== -1) {
			// Replace the item immutably
			transports[index] = {
				...transports[index],
				...transportationBeingUpdated
			};
		} else {
			// Prepend new/updated transportation
			transports.unshift({ ...transportationBeingUpdated });
		}

		// Assign back to collection immutably to trigger reactivity
		collection = { ...collection, transportations: transports };
	}

	// If a new transportation was just created and we have a pending add-date,
	// attach it to that date in the itinerary.
	$: if (
		transportationBeingUpdated?.id &&
		pendingAddDate &&
		!addedToItinerary.has(transportationBeingUpdated.id)
	) {
		addItineraryItemForObject('transportation', transportationBeingUpdated.id, pendingAddDate);
		// Mark this transportation as added to prevent duplicates
		addedToItinerary.add(transportationBeingUpdated.id);
		addedToItinerary = addedToItinerary; // trigger reactivity
	}

	/**
	 * Get lodging items where the guest is staying overnight on a given date
	 * (i.e., the date is between check_in and check_out, but NOT the check_in date itself)
	 */
	function getOvernightLodgingForDate(collection: Collection, dateISO: string): Lodging[] {
		if (!collection.lodging) return [];

		const targetDate = DateTime.fromISO(dateISO).startOf('day');

		// Helper: only include lodging that has been added to the itinerary
		function isLodgingScheduled(lodgingId: any): boolean {
			return !!collection.itinerary?.some((it) => {
				const objectType = it.item?.type || '';
				return objectType === 'lodging' && it.object_id === lodgingId;
			});
		}

		return collection.lodging.filter((lodging) => {
			// Only consider lodging entries that have both check-in and check-out
			if (!lodging.check_in || !lodging.check_out) return false;

			// Skip lodgings that are not scheduled in the itinerary
			if (!isLodgingScheduled(lodging.id)) return false;

			// Extract just the date portion (YYYY-MM-DD) to avoid timezone shifts
			const checkInDateStr = lodging.check_in.split('T')[0];
			const checkOutDateStr = lodging.check_out.split('T')[0];

			const checkIn = DateTime.fromISO(checkInDateStr).startOf('day');
			const checkOut = DateTime.fromISO(checkOutDateStr).startOf('day');

			// The guest is staying overnight if the target date is between
			// check-in (inclusive) and check-out (exclusive). This includes the
			// check-in night as requested.
			return targetDate >= checkIn && targetDate < checkOut;
		});
	}

	function getGlobalItemsByDate(collection: Collection): Map<string, ResolvedItineraryItem[]> {
		const grouped = new Map<string, ResolvedItineraryItem[]>();

		// Filter for global items only (no date filter - extract from resolved object)
		// Determine collection date range for filtering visits
		let collectionStart: DateTime | null = null;
		let collectionEnd: DateTime | null = null;
		if (collection.start_date)
			collectionStart = DateTime.fromISO(collection.start_date).startOf('day');
		if (collection.end_date) collectionEnd = DateTime.fromISO(collection.end_date).startOf('day');

		collection.itinerary
			?.filter((item) => item.is_global)
			.forEach((item) => {
				const resolved = resolveItineraryItem(item, collection);
				const objectType = resolved.item?.type || '';
				const datesToAdd = new Set<string>();

				// Helper to clamp dates to collection range and dedupe
				function addDateIfInRange(date: DateTime) {
					if (collectionStart && date < collectionStart) return;
					if (collectionEnd && date > collectionEnd) return;
					const iso = date.toISODate();
					if (iso) datesToAdd.add(iso);
				}

				// Extract date(s) from the resolved object based on its type
				if (objectType === 'location') {
					const location = resolved.resolvedObject as Location | null;
					if (location?.visits && location.visits.length > 0) {
						location.visits.forEach((visit) => {
							if (!visit.start_date) return;
							const start = DateTime.fromISO(visit.start_date.split('T')[0]).startOf('day');
							const end = visit.end_date
								? DateTime.fromISO(visit.end_date.split('T')[0]).startOf('day')
								: start;

							let cursor = start;
							// If end is before start, treat as single day
							const last = end < start ? start : end;
							while (cursor <= last) {
								addDateIfInRange(cursor);
								cursor = cursor.plus({ days: 1 });
							}
						});
					}
				} else if (objectType === 'transportation') {
					const transport = resolved.resolvedObject as Transportation | null;
					if (transport?.date) {
						addDateIfInRange(DateTime.fromISO(transport.date.split('T')[0]).startOf('day'));
					}
				} else if (objectType === 'lodging') {
					const lodging = resolved.resolvedObject as Lodging | null;
					if (lodging?.check_in) {
						const start = DateTime.fromISO(lodging.check_in.split('T')[0]).startOf('day');
						const end = lodging.check_out
							? DateTime.fromISO(lodging.check_out.split('T')[0]).startOf('day').minus({ days: 1 })
							: start;
						const last = end < start ? start : end;

						let cursor = start;
						while (cursor <= last) {
							addDateIfInRange(cursor);
							cursor = cursor.plus({ days: 1 });
						}
					}
				} else if (objectType === 'note') {
					const note = resolved.resolvedObject as Note | null;
					if (note?.date) {
						addDateIfInRange(DateTime.fromISO(note.date.split('T')[0]).startOf('day'));
					}
				} else if (objectType === 'checklist') {
					const checklist = resolved.resolvedObject as Checklist | null;
					if (checklist?.date) {
						addDateIfInRange(DateTime.fromISO(checklist.date.split('T')[0]).startOf('day'));
					}
				}

				// Add the item to each applicable date
				datesToAdd.forEach((dateISO) => {
					if (!grouped.has(dateISO)) grouped.set(dateISO, []);
					grouped.get(dateISO)!.push(resolved);
				});
			});

		// Sort items within each date group by order
		grouped.forEach((items) => items.sort((a, b) => a.order - b.order));

		return grouped;
	}

	function resolveItineraryItem(
		item: CollectionItineraryItem,
		collection: Collection
	): ResolvedItineraryItem {
		let resolvedObject = null;

		// Resolve based on item.type which tells us the object type
		const objectType = item.item?.type || '';

		if (objectType === 'location') {
			// Find location by ID
			resolvedObject = collection.locations?.find((loc) => loc.id === item.object_id) || null;
		} else if (objectType === 'transportation') {
			resolvedObject = collection.transportations?.find((t) => t.id === item.object_id) || null;
		} else if (objectType === 'lodging') {
			resolvedObject = collection.lodging?.find((l) => l.id === item.object_id) || null;
		} else if (objectType === 'note') {
			resolvedObject = collection.notes?.find((n) => n.id === item.object_id) || null;
		} else if (objectType === 'checklist') {
			resolvedObject = collection.checklists?.find((c) => c.id === item.object_id) || null;
		}

		return {
			...item,
			resolvedObject
		};
	}

	function groupItemsByDay(collection: Collection): DayGroup[] {
		const globalByDate = getGlobalItemsByDate(collection);

		// Build a map of date -> resolved items from existing itinerary entries
		const grouped = new Map<string, ResolvedItineraryItem[]>();

		collection.itinerary?.forEach((item) => {
			if (item.date) {
				if (!grouped.has(item.date)) grouped.set(item.date, []);
				const resolved = resolveItineraryItem(item, collection);
				grouped.get(item.date)!.push(resolved);
			}
		});

		// Determine a date range to display. Prefer explicit collection start/end if present,
		// otherwise use min/max dates found in itinerary items. If no dates at all, return []
		let startDateISO: string | null = null;
		let endDateISO: string | null = null;

		if (collection.start_date && collection.end_date) {
			startDateISO = collection.start_date;
			endDateISO = collection.end_date;
		} else {
			// derive from itinerary dates if available
			const dates = Array.from(grouped.keys()).sort();
			if (dates.length > 0) {
				startDateISO = dates[0];
				endDateISO = dates[dates.length - 1];
			}
		}

		if (!startDateISO || !endDateISO) return [];

		const start = DateTime.fromISO(startDateISO).startOf('day');
		const end = DateTime.fromISO(endDateISO).startOf('day');

		const days: DayGroup[] = [];
		for (let dt = start; dt <= end; dt = dt.plus({ days: 1 })) {
			const iso = dt.toISODate();
			const items = (grouped.get(iso) || []).sort((a, b) => a.order - b.order);
			const overnightLodging = getOvernightLodgingForDate(collection, iso);
			const globalDatedItems = globalByDate.get(iso) || [];

			// Find day metadata for this date
			const dayMetadata = collection.itinerary_days?.find((d) => d.date === iso) || null;

			days.push({
				date: iso,
				displayDate: dt.toFormat('cccc, LLLL d, yyyy'),
				items,
				overnightLodging,
				globalDatedItems,
				dayMetadata
			});
		}

		return days;
	}

	function getUnscheduledItems(collection: Collection): any[] {
		// Get all items that are linked to collection but not in itinerary
		const scheduledIds = new Set(collection.itinerary?.map((item) => item.object_id) || []);

		const unscheduled: any[] = [];

		// Check locations
		collection.locations?.forEach((location) => {
			if (!scheduledIds.has(location.id)) {
				unscheduled.push({ type: 'location', item: location });
			}
		});

		// Check transportation
		collection.transportations?.forEach((transport) => {
			if (!scheduledIds.has(transport.id)) {
				unscheduled.push({ type: 'transportation', item: transport });
			}
		});

		// Check lodging
		collection.lodging?.forEach((lodge) => {
			if (!scheduledIds.has(lodge.id)) {
				unscheduled.push({ type: 'lodging', item: lodge });
			}
		});

		// Check notes
		collection.notes?.forEach((note) => {
			if (!scheduledIds.has(note.id)) {
				unscheduled.push({ type: 'note', item: note });
			}
		});

		// Check checklists
		collection.checklists?.forEach((checklist) => {
			if (!scheduledIds.has(checklist.id)) {
				unscheduled.push({ type: 'checklist', item: checklist });
			}
		});

		return unscheduled;
	}

	function isMultiDay(item: ResolvedItineraryItem): boolean {
		if (item.start_datetime && item.end_datetime) {
			const start = DateTime.fromISO(item.start_datetime);
			const end = DateTime.fromISO(item.end_datetime);
			return !start.hasSame(end, 'day');
		}
		return false;
	}

	function handleDndConsider(dayIndex: number, e: CustomEvent) {
		const { items: newItems } = e.detail;
		// Update the local state immediately for smooth drag feedback
		days[dayIndex].items = newItems;
		days = [...days];
	}

	function handleDndConsiderGlobal(e: CustomEvent) {
		const { items: newItems } = e.detail;
		globalItems = newItems;
	}

	async function handleDndFinalizeGlobal(e: CustomEvent) {
		const { items: newItems, info } = e.detail;
		globalItems = newItems;
		if (
			info.trigger === TRIGGERS.DROPPED_INTO_ZONE ||
			info.trigger === TRIGGERS.DROPPED_INTO_ANOTHER
		) {
			if (!isSavingOrder) {
				isSavingOrder = true;
				try {
					await saveReorderedItems();
				} finally {
					isSavingOrder = false;
				}
			}
		}
	}

	async function handleDndFinalize(dayIndex: number, e: CustomEvent) {
		const { items: newItems, info } = e.detail;

		// Update local state
		days[dayIndex].items = newItems;
		days = [...days];

		// Save to backend if item was actually moved (not just considered)
		if (
			info.trigger === TRIGGERS.DROPPED_INTO_ZONE ||
			info.trigger === TRIGGERS.DROPPED_INTO_ANOTHER
		) {
			// Prevent further dragging while we persist the new order
			if (!isSavingOrder) {
				isSavingOrder = true;
				// mark this day as saving so we can show a spinner on that day's header
				savingDay = days[dayIndex]?.date || null;
				try {
					await saveReorderedItems();
				} finally {
					isSavingOrder = false;
					savingDay = null;
				}
			}
		}
	}

	async function saveReorderedItems() {
		try {
			// Collect all items across all days with their new positions
			const dayUpdates = days.flatMap((day) =>
				day.items
					.filter((item) => item.id && !item[SHADOW_ITEM_MARKER_PROPERTY_NAME])
					.map((item, index) => ({
						id: item.id,
						date: day.date,
						order: index
					}))
			);

			const globalUpdates = globalItems
				.filter((item) => item.id && !item[SHADOW_ITEM_MARKER_PROPERTY_NAME])
				.map((item, index) => ({ id: item.id, is_global: true, date: null, order: index }));

			const itemsToUpdate = [...dayUpdates, ...globalUpdates];

			if (itemsToUpdate.length === 0) {
				return;
			}

			const response = await fetch('/api/itineraries/reorder/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					items: itemsToUpdate
				})
			});

			if (!response.ok) {
				throw new Error('Failed to save item order');
			}

			// Optionally show success feedback
			// console.log('Itinerary order saved successfully');
			// Make sure to sync the collection.itinerary with the new order
			const updatedItinerary = collection.itinerary?.map((it) => {
				const updatedItem = itemsToUpdate.find((upd) => upd.id === it.id);
				if (updatedItem) {
					return {
						...it,
						date: updatedItem.date,
						is_global: updatedItem.is_global ?? it.is_global,
						order: updatedItem.order
					};
				}
				return it;
			});
			collection.itinerary = updatedItinerary;
		} catch (error) {
			console.error('Error saving itinerary order:', error);
			// Optionally show error notification to user
			alert('Failed to save itinerary order. Please try again.');
		}
	}

	// Add a trip-wide (global) itinerary item
	async function addGlobalItineraryItemForObject(objectType: string, objectId: string) {
		const tempId = `temp-global-${Date.now()}`;
		const order = globalItems.length;

		const newIt = {
			id: tempId,
			collection: collection.id,
			content_type: objectType,
			object_id: objectId,
			item: { id: objectId, type: objectType },
			date: null,
			is_global: true,
			order,
			created_at: new Date().toISOString()
		};

		collection.itinerary = [...(collection.itinerary || []), newIt];
		// trigger reactive globals and days
		days = groupItemsByDay(collection);
		globalItems = (collection.itinerary || [])
			.filter((it) => it.is_global)
			.map((it) => resolveItineraryItem(it, collection))
			.sort((a, b) => a.order - b.order);

		try {
			const res = await fetch('/api/itineraries/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					collection: collection.id,
					content_type: objectType,
					object_id: objectId,
					is_global: true,
					order
				})
			});

			if (!res.ok) {
				const j = await res.json().catch(() => ({}));
				throw new Error(j.detail || 'Failed to add global itinerary item');
			}

			const created = await res.json();
			collection.itinerary = collection.itinerary.map((it) => (it.id === tempId ? created : it));
			// refresh
			days = groupItemsByDay(collection);
			globalItems = (collection.itinerary || [])
				.filter((it) => it.is_global)
				.map((it) => resolveItineraryItem(it, collection))
				.sort((a, b) => a.order - b.order);
		} catch (err) {
			console.error('Error creating global itinerary item:', err);
			alert('Failed to add item to trip-wide itinerary.');
			collection.itinerary = collection.itinerary.filter((it) => it.id !== tempId);
			days = groupItemsByDay(collection);
			globalItems = (collection.itinerary || [])
				.filter((it) => it.is_global)
				.map((it) => resolveItineraryItem(it, collection))
				.sort((a, b) => a.order - b.order);
		}
	}

	// Handle opening the day picker modal for an item (scheduled or unscheduled)
	// currentItineraryDate: the date of the itinerary entry being moved (if any)
	function handleOpenDayPickerForItem(
		type: string,
		item: any,
		forcePicker: boolean = false,
		currentItineraryDate: string | null = null
	) {
		// Check if the item already has a date, and if so, add it directly
		let itemDate: string | null = null;
		// Track all itinerary dates this item is already scheduled on (non-global)
		const scheduledDates = (collection.itinerary || [])
			.filter((it) => it.object_id === item.id && it.date && !it.is_global)
			.map((it) => it.date as string);

		// If moving from a specific itinerary date, track which itinerary item it is
		if (currentItineraryDate) {
			const sourceItineraryItem = (collection.itinerary || []).find(
				(it) => it.object_id === item.id && it.date === currentItineraryDate && !it.is_global
			);
			dayPickSourceItineraryItemId = sourceItineraryItem?.id || null;
		} else {
			dayPickSourceItineraryItemId = null;
		}

		if (type === 'location') {
			// For locations, prefer the visit matching the current itinerary date
			let matchedVisit = null;
			if (currentItineraryDate) {
				matchedVisit = item.visits?.find((v) => v.start_date?.startsWith(currentItineraryDate));
			}
			const firstVisit = matchedVisit || item.visits?.[0];
			if (firstVisit?.start_date) {
				itemDate = firstVisit.start_date.split('T')[0]; // Extract date only (YYYY-MM-DD)
				dayPickSourceVisit = { id: firstVisit.id, start_date: firstVisit.start_date };
			}
		} else if (type === 'transportation') {
			if (item.date) {
				itemDate = item.date.split('T')[0]; // Extract date only (YYYY-MM-DD)
			}
		} else if (type === 'lodging') {
			if (item.check_in) {
				itemDate = item.check_in.split('T')[0]; // Extract date only (YYYY-MM-DD)
			}
		} else if (type === 'note') {
			if (item.date) {
				itemDate = item.date.split('T')[0]; // Extract date only (YYYY-MM-DD)
			}
		} else if (type === 'checklist') {
			if (item.date) {
				itemDate = item.date.split('T')[0]; // Extract date only (YYYY-MM-DD)
			}
		}

		// If caller explicitly wants the picker, bypass auto-add
		if (forcePicker) {
			dayPickItemToAdd = { type, item };
			dayPickScheduledDates = scheduledDates;
			// Capture source visit for locations (match itinerary date first)
			dayPickSourceVisit = null;
			if (type === 'location') {
				const matchedVisit = currentItineraryDate
					? item.visits?.find((v) => v.start_date?.startsWith(currentItineraryDate))
					: null;
				const firstVisit = matchedVisit || item.visits?.[0];
				if (firstVisit?.start_date) {
					dayPickSourceVisit = { id: firstVisit.id, start_date: firstVisit.start_date };
				}
			}
			isDayPickModalOpen = true;
			return;
		}

		// If we found a date, add it directly to that date
		// Helper: check if a date is within collection start/end bounds (if set)
		function isDateWithinCollectionRange(dateISO: string | null) {
			if (!dateISO) return false;
			if (!collection) return true; // no collection context -> allow
			try {
				const d = DateTime.fromISO(dateISO).startOf('day');
				if (collection.start_date) {
					const s = DateTime.fromISO(collection.start_date).startOf('day');
					if (d < s) return false;
				}
				if (collection.end_date) {
					const e = DateTime.fromISO(collection.end_date).startOf('day');
					if (d > e) return false;
				}
				return true;
			} catch (err) {
				return false;
			}
		}

		if (itemDate) {
			// If the item's date is outside the collection range, prompt the day picker
			if (!isDateWithinCollectionRange(itemDate)) {
				dayPickItemToAdd = { type, item };
				dayPickScheduledDates = scheduledDates;
				dayPickSourceVisit = null;
				if (type === 'location') {
					// Prefer the visit that matches itemDate if present
					const source = item.visits?.find((v) => v.start_date?.startsWith(itemDate));
					const useVisit = source || item.visits?.[0];
					if (useVisit?.start_date) {
						dayPickSourceVisit = { id: useVisit.id, start_date: useVisit.start_date };
					}
				}
				isDayPickModalOpen = true;
				return;
			}

			// We have a valid date; ensure dayPickSourceVisit is aligned for locations with multiple visits
			if (type === 'location' && !dayPickSourceVisit) {
				const source = item.visits?.find((v) => v.start_date?.startsWith(itemDate));
				if (source?.start_date) {
					dayPickSourceVisit = { id: source.id, start_date: source.start_date };
				}
			}

			addItineraryItemForObject(type, item.id, itemDate, false);
		} else {
			// Otherwise, show the day picker modal
			dayPickItemToAdd = { type, item };
			dayPickScheduledDates = scheduledDates;
			dayPickSourceVisit = null;
			if (type === 'location') {
				const matchedVisit = currentItineraryDate
					? item.visits?.find((v) => v.start_date?.startsWith(currentItineraryDate))
					: item.visits?.[0];
				if (matchedVisit?.start_date) {
					dayPickSourceVisit = { id: matchedVisit.id, start_date: matchedVisit.start_date };
				}
			}
			isDayPickModalOpen = true;
		}
	}

	// Handle day selection from the day picker modal
	async function handleDaySelected(
		event: CustomEvent<{ date: string; updateDate: boolean; deleteSourceVisit?: boolean }>
	) {
		const { date: selectedDate, updateDate, deleteSourceVisit } = event.detail;
		if (!dayPickItemToAdd) return;

		const { type, item } = dayPickItemToAdd;
		const objectType = type; // 'location', 'transportation', 'lodging', 'note', 'checklist'
		const objectId = item.id;

		// Identify existing dated itinerary entries for this object
		const existingDatedItems = (collection.itinerary || []).filter(
			(it) => it.object_id === objectId && it.date && !it.is_global
		);

		// Avoid duplicate add if already scheduled for the selected date
		const alreadyScheduledForSelectedDate = existingDatedItems.some(
			(it) => it.date === selectedDate
		);

		try {
			if (!alreadyScheduledForSelectedDate) {
				// Add the item to the selected day
				await addItineraryItemForObject(objectType, objectId, selectedDate, updateDate);
			}

			// Optionally delete the source visit (for locations) — skip if we're updating it
			if (deleteSourceVisit && objectType === 'location' && dayPickSourceVisit?.id && !updateDate) {
				try {
					await fetch(`/api/visits/${dayPickSourceVisit.id}/`, { method: 'DELETE' });
					// Update local state: remove visit from the location
					if (collection.locations) {
						collection.locations = collection.locations.map((loc) => {
							if (loc.id === objectId) {
								return {
									...loc,
									visits: (loc.visits || []).filter((v) => v.id !== dayPickSourceVisit?.id)
								};
							}
							return loc;
						});
					}
				} catch (e) {
					console.error('Failed to delete source visit', dayPickSourceVisit.id, e);
				}
			}

			// Only remove the specific itinerary entry being moved, not all occurrences
			if (updateDate && dayPickSourceItineraryItemId) {
				// Only delete the specific itinerary item that was being moved
				try {
					await fetch(`/api/itineraries/${dayPickSourceItineraryItemId}`, { method: 'DELETE' });
					// Update local state to reflect removal
					collection.itinerary = (collection.itinerary || []).filter(
						(it) => it.id !== dayPickSourceItineraryItemId
					);
					days = groupItemsByDay(collection);
				} catch (e) {
					console.error('Failed to remove source itinerary item', dayPickSourceItineraryItemId, e);
				}
			}
		} finally {
			// Reset state regardless of success/failure
			dayPickItemToAdd = null;
			dayPickScheduledDates = [];
			dayPickSourceVisit = null;
			dayPickSourceItineraryItemId = null;
			isDayPickModalOpen = false;
		}
	}

	// Helper: validate UUID format to avoid sending temporary IDs to backend
	function isValidUUID(id: string | undefined | null): boolean {
		if (!id) return false;
		const uuidRegex =
			/^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/;
		return uuidRegex.test(id);
	}

	// Add an itinerary item locally and attempt to persist to backend
	async function addItineraryItemForObject(
		objectType: string,
		objectId: string,
		dateISO: string,
		updateItemDate: boolean = false
	) {
		const tempId = `temp-${Date.now()}`;
		const day = days.find((d) => d.date === dateISO);
		const order = day ? day.items.length : 0;

		const newIt = {
			id: tempId,
			collection: collection.id,
			content_type: objectType,
			object_id: objectId,
			item: { id: objectId, type: objectType },
			date: dateISO,
			order,
			created_at: new Date().toISOString()
		};

		collection.itinerary = [...(collection.itinerary || []), newIt];
		days = groupItemsByDay(collection);

		try {
			const res = await fetch('/api/itineraries/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					collection: collection.id,
					content_type: objectType,
					object_id: objectId,
					date: dateISO,
					order,
					update_item_date: updateItemDate,
					// Pass source visit ID so backend can update the existing visit
					source_visit_id:
						objectType === 'location' && updateItemDate && isValidUUID(dayPickSourceVisit?.id)
							? dayPickSourceVisit!.id
							: undefined
				})
			});

			if (!res.ok) {
				const j = await res.json().catch(() => ({}));
				throw new Error(j.detail || 'Failed to add itinerary item');
			}

			const created = await res.json();
			collection.itinerary = collection.itinerary.map((it) => (it.id === tempId ? created : it));
			pendingAddDate = null;

			// If we updated the item's date, sync the updated object from server response
			if (updateItemDate && created.updated_object) {
				if (objectType === 'transportation') {
					if (collection.transportations) {
						collection.transportations = collection.transportations.map((t) =>
							t.id === objectId ? { ...t, ...created.updated_object } : t
						);
					}
				} else if (objectType === 'lodging') {
					if (collection.lodging) {
						collection.lodging = collection.lodging.map((l) =>
							l.id === objectId ? { ...l, ...created.updated_object } : l
						);
					}
				}
			} else if (updateItemDate) {
				// Fallback: if server didn't return updated_object, do manual update for other types
				const isoDate = `${dateISO}T00:00:00`;

				if (objectType === 'location') {
					// Shift the existing visit dates locally to match the new itinerary date
					if (collection.locations) {
						collection.locations = collection.locations.map((loc) => {
							if (loc.id !== objectId) return loc;

							const visits = loc.visits || [];
							// Prefer matching by visit id (source_visit) then by old date
							const sourceId = dayPickSourceVisit?.id;
							const oldDate = dayPickSourceVisit?.start_date
								? dayPickSourceVisit.start_date.split('T')[0]
								: null;
							let idx = sourceId ? visits.findIndex((v) => v.id === sourceId) : -1;
							if (idx === -1 && oldDate) {
								idx = visits.findIndex((v) => v.start_date?.startsWith(oldDate));
							}

							if (idx === -1) return loc;

							const v = visits[idx];
							const startDT = v.start_date ? DateTime.fromISO(v.start_date) : null;
							const endDT = v.end_date ? DateTime.fromISO(v.end_date) : null;
							const baseStart = DateTime.fromISO(dateISO);
							const newStart = startDT
								? baseStart
										.set({
											second: startDT.second,
											minute: startDT.minute,
											hour: startDT.hour,
											millisecond: startDT.millisecond
										})
										.toISO()
								: `${dateISO}T00:00:00`;
							const newEnd = endDT
								? DateTime.fromISO(dateISO)
										.set({
											second: endDT.second,
											minute: endDT.minute,
											hour: endDT.hour,
											millisecond: endDT.millisecond
										})
										.toISO()
								: `${dateISO}T23:59:59`;

							const nextVisits = [...visits];
							nextVisits[idx] = { ...v, start_date: newStart, end_date: newEnd };
							return { ...loc, visits: nextVisits };
						});
					}
				} else if (objectType === 'lodging') {
					if (collection.lodging) {
						// Set check_in to selected day, check_out to next day
						const checkOutDate = DateTime.fromISO(dateISO).plus({ days: 1 }).toISODate();
						collection.lodging = collection.lodging.map((l) =>
							l.id === objectId
								? { ...l, check_in: `${dateISO}T00:00:00`, check_out: `${checkOutDate}T00:00:00` }
								: l
						);
					}
				} else if (objectType === 'note') {
					if (collection.notes) {
						collection.notes = collection.notes.map((n) =>
							n.id === objectId ? { ...n, date: isoDate } : n
						);
					}
				} else if (objectType === 'checklist') {
					if (collection.checklists) {
						collection.checklists = collection.checklists.map((c) =>
							c.id === objectId ? { ...c, date: isoDate } : c
						);
					}
				}
			}

			days = groupItemsByDay(collection);
		} catch (err) {
			console.error('Error creating itinerary item:', err);
			alert('Failed to add item to itinerary.');
			collection.itinerary = collection.itinerary.filter((it) => it.id !== tempId);
			days = groupItemsByDay(collection);
		}
	}

	// Save or update day metadata (name and description)
	async function saveDayMetadata(date: string, name: string | null, description: string | null) {
		if (!canModify) return;

		try {
			// Find existing day metadata for this date
			const existing = collection.itinerary_days?.find((d) => d.date === date);

			if (existing) {
				// Update existing day metadata
				const response = await fetch(`/api/itinerary-days/${existing.id}/`, {
					method: 'PATCH',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({
						name: name || null,
						description: description || null
					})
				});

				if (!response.ok) throw new Error('Failed to update day metadata');

				const updated = await response.json();

				// Update collection.itinerary_days immutably
				collection.itinerary_days = collection.itinerary_days?.map((d) =>
					d.id === existing.id ? updated : d
				);
			} else {
				// Create new day metadata
				const response = await fetch('/api/itinerary-days/', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({
						collection: collection.id,
						date,
						name: name || null,
						description: description || null
					})
				});

				if (!response.ok) throw new Error('Failed to create day metadata');

				const newDay = await response.json();

				// Add to collection.itinerary_days immutably
				collection.itinerary_days = [...(collection.itinerary_days || []), newDay];
			}

			// Trigger reactivity by reassigning collection
			collection = { ...collection };
			days = groupItemsByDay(collection);
		} catch (err) {
			console.error('Error saving day metadata:', err);
		}
	}
</script>

{#if isLocationModalOpen}
	<NewLocationModal
		on:close={() => {
			isLocationModalOpen = false;
			locationToEdit = null;
			locationBeingUpdated = null;
			pendingAddDate = null;
			addedToItinerary.clear();
			addedToItinerary = addedToItinerary;
		}}
		{user}
		{locationToEdit}
		bind:location={locationBeingUpdated}
		{collection}
		initialVisitDate={pendingAddDate}
	/>
{/if}

{#if isLodgingModalOpen}
	<LodgingModal
		on:close={() => {
			isLodgingModalOpen = false;
			lodgingToEdit = null;
			lodgingBeingUpdated = null;
			pendingAddDate = null;
			addedToItinerary.clear();
			addedToItinerary = addedToItinerary;
		}}
		{user}
		{lodgingToEdit}
		bind:lodging={lodgingBeingUpdated}
		{collection}
		initialVisitDate={pendingAddDate}
	/>
{/if}

{#if isTransportationModalOpen}
	<TransportationModal
		on:close={() => {
			isTransportationModalOpen = false;
			transportationToEdit = null;
			transportationBeingUpdated = null;
			pendingAddDate = null;
			addedToItinerary.clear();
			addedToItinerary = addedToItinerary;
		}}
		{user}
		{transportationToEdit}
		bind:transportation={transportationBeingUpdated}
		{collection}
		initialVisitDate={pendingAddDate}
	/>
{/if}

{#if isNoteModalOpen}
	<NoteModal
		on:close={() => {
			pendingAddDate = null;
			noteToEdit = null;
			isNoteModalOpen = false;
		}}
		{collection}
		{user}
		note={noteToEdit}
		on:create={(e) => void handleNoteUpsert(e.detail)}
		on:save={(e) => void handleNoteUpsert(e.detail)}
		initialVisitDate={pendingAddDate}
	/>
{/if}

{#if isChecklistModalOpen}
	<ChecklistModal
		on:close={() => {
			pendingAddDate = null;
			checklistToEdit = null;
			isChecklistModalOpen = false;
		}}
		{collection}
		{user}
		checklist={checklistToEdit}
		on:create={(e) => void handleChecklistUpsert(e.detail)}
		on:save={(e) => void handleChecklistUpsert(e.detail)}
		initialVisitDate={pendingAddDate}
	/>
{/if}

{#if isItineraryLinkModalOpen}
	<ItineraryLinkModal
		{collection}
		{user}
		targetDate={linkModalTargetDate}
		displayDate={linkModalDisplayDate}
		on:close={() => (isItineraryLinkModalOpen = false)}
		on:addItem={(e) => {
			const { type, itemId, updateDate } = e.detail;
			addItineraryItemForObject(type, itemId, linkModalTargetDate, updateDate);
		}}
	/>
{/if}

{#if isDayPickModalOpen}
	<ItineraryDayPickModal
		isOpen={isDayPickModalOpen}
		{days}
		itemName={dayPickItemToAdd?.item?.name || `${$t('checklist.item')}`}
		scheduledDates={dayPickScheduledDates}
		sourceVisitDate={dayPickSourceVisit ? dayPickSourceVisit.start_date.split('T')[0] : null}
		on:daySelected={handleDaySelected}
		on:close={() => {
			isDayPickModalOpen = false;
			dayPickItemToAdd = null;
			dayPickScheduledDates = [];
			dayPickSourceVisit = null;
			dayPickSourceItineraryItemId = null;
		}}
	/>
{/if}

{#if canAutoGenerate}
	<div class="alert alert-info shadow-lg mb-6">
		<div class="flex-1 flex items-center gap-3 min-w-0">
			<Info class="w-6 h-6 stroke-current flex-shrink-0" />
			<div class="min-w-0">
				<div class="flex items-baseline gap-3">
					<h3 class="font-bold truncate">{$t('itinerary.auto_generate_itinerary')}</h3>
				</div>
				<div class="text-sm opacity-90 truncate">
					{$t('itinerary.auto_generate_itinerary_desc')}
				</div>
			</div>
		</div>
		<div class="flex-none ml-3">
			<button
				class="btn btn-sm btn-primary"
				disabled={isAutoGenerating}
				on:click={handleAutoGenerate}
			>
				{#if isAutoGenerating}
					<span class="loading loading-spinner loading-sm"></span>
					{$t('itinerary.generating')}...
				{:else}
					{$t('itinerary.auto_generate')}
				{/if}
			</button>
		</div>
	</div>
{/if}

{#if days.length === 0 && unscheduledItems.length === 0}
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body text-center py-12">
			<CalendarBlank class="w-16 h-16 mx-auto mb-4 opacity-50" />
			<h3 class="text-2xl font-bold mb-2">{$t('itinerary.no_itinerary_yet')}</h3>
			<p class="opacity-70">{$t('itinerary.start_planning')}</p>
		</div>
	</div>
{:else}
	<div class="space-y-6">
		<!-- Trip-wide (Global) Items -->
		{#if globalItems.length > 0 || canModify}
			<div class="card bg-base-200 shadow-xl">
				<div class="card-body">
					<div class="flex items-center gap-3 mb-4 pb-4 border-b border-base-300">
						<div
							class="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-primary"
						>
							<CalendarBlank class="w-4 h-4" />
						</div>
						<h3 class="text-xl font-bold">
							{$t('itinerary.trip_context') || 'Trip Context'}
						</h3>
						<!-- Info bubble explaining trip context -->
						<div class="ml-2 tooltip tooltip-right" data-tip={$t('itinerary.trip_context_info')}>
							<button
								type="button"
								class="btn btn-ghost btn-sm btn-square p-1"
								aria-label="Trip context info"
							>
								<Info class="w-4 h-4" />
							</button>
						</div>
					</div>

					{#if globalItems.length === 0}
						<div
							class="card bg-base-100 shadow-sm border border-dashed border-base-300 p-4 text-center"
						>
							<div class="card-body p-2">
								<CalendarBlank class="w-8 h-8 mx-auto mb-2 opacity-40" />
								<p class="opacity-70">
									{$t('itinerary.no_trip_context_items')}
								</p>
							</div>
						</div>
					{:else}
						<div
							use:dndzone={{
								items: globalItems,
								flipDurationMs,
								dropTargetStyle: { outline: 'none', border: 'none' },
								dragDisabled: isSavingOrder || !canModify,
								dropFromOthersDisabled: true
							}}
							on:consider={handleDndConsiderGlobal}
							on:finalize={handleDndFinalizeGlobal}
							class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3"
						>
							{#each globalItems as item (item.id)}
								{@const objectType = item.item?.type || ''}
								{@const resolvedObj = item.resolvedObject}
								<div
									class="group relative transition-all duration-200 pointer-events-auto h-full"
									animate:flip={{ duration: flipDurationMs }}
								>
									{#if resolvedObj}
										{#if canModify}
											<div
												class="absolute left-2 top-2 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
												title={$t('itinerary.drag_to_reorder')}
											>
												<div
													class="itinerary-drag-handle btn btn-circle btn-xs btn-ghost bg-base-100/80 backdrop-blur-sm shadow-sm hover:bg-base-200 cursor-grab active:cursor-grabbing"
													aria-label={$t('itinerary.drag_to_reorder')}
													role="button"
													tabindex="0"
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														class="h-3 w-3"
														fill="none"
														viewBox="0 0 24 24"
														stroke="currentColor"
														><path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M4 8h16M4 16h16"
														/></svg
													>
												</div>
											</div>
										{/if}
										{#if objectType === 'location'}
											<LocationCard
												adventure={resolvedObj}
												on:edit={handleEditLocation}
												on:delete={handleItemDelete}
												on:duplicate={handleDuplicateLocation}
												itineraryItem={item}
												on:removeFromItinerary={handleRemoveItineraryItem}
												on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
												{user}
												{collection}
												compact={true}
											/>
										{:else if objectType === 'transportation'}
											<TransportationCard
												transportation={resolvedObj}
												{user}
												{collection}
												on:delete={handleItemDelete}
												itineraryItem={item}
												on:removeFromItinerary={handleRemoveItineraryItem}
												on:edit={handleEditTransportation}
												on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
											/>
										{:else if objectType === 'lodging'}
											<LodgingCard
												lodging={resolvedObj}
												{user}
												{collection}
												itineraryItem={item}
												on:delete={handleItemDelete}
												on:removeFromItinerary={handleRemoveItineraryItem}
												on:edit={handleEditLodging}
												on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
											/>
										{:else if objectType === 'note'}
											<NoteCard
												note={resolvedObj}
												{user}
												{collection}
												on:delete={handleItemDelete}
												itineraryItem={item}
												on:removeFromItinerary={handleRemoveItineraryItem}
												on:edit={handleEditNote}
												on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
											/>
										{:else if objectType === 'checklist'}
											<ChecklistCard
												checklist={resolvedObj}
												{user}
												{collection}
												on:delete={handleItemDelete}
												itineraryItem={item}
												on:removeFromItinerary={handleRemoveItineraryItem}
												on:edit={handleEditChecklist}
												on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
											/>
										{/if}
									{:else}
										<div class="alert alert-warning">
											<span>⚠️ {$t('itinerary.item_not_found')} (ID: {item.object_id})</span>
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		{/if}
		<!-- Scheduled Days -->
		{#each days as day, dayIndex}
			{@const dayNumber = dayIndex + 1}
			{@const totalDays = days.length}
			{@const weekday = DateTime.fromISO(day.date).toFormat('ccc')}
			{@const dayOfMonth = DateTime.fromISO(day.date).toFormat('d')}
			{@const monthAbbrev = DateTime.fromISO(day.date).toFormat('LLL')}

			<div class="card bg-base-200 shadow-xl">
				<div class="card-body">
					<!-- Day Header (compact, shows date pill + Day X of Y + items + add/save) -->

					<div class="flex items-start gap-4 mb-4 pb-4 border-b border-base-300">
						<!-- Date pill -->
						<div class="flex-none">
							<div class="text-center bg-base-300 rounded-lg px-3 py-2 w-20">
								<div class="text-xs opacity-70">{weekday}</div>
								<div class="text-2xl font-bold -mt-1">{dayOfMonth}</div>
								<div class="text-xs opacity-70">{monthAbbrev}</div>
							</div>
						</div>

						<!-- Title and meta -->
						<div class="flex-1 min-w-0 space-y-1">
							<!-- Main date title + optional day name -->
							<div class="flex items-baseline gap-2 flex-wrap">
								<h3 class="text-lg md:text-xl font-bold">{day.displayDate}</h3>

								<!-- Day name - inline with date -->
								{#if canModify}
									{#if day.dayMetadata?.name}
										<input
											type="text"
											class="input input-ghost text-base font-medium px-1 py-0 -ml-1 focus:bg-base-100 focus:px-2 transition-all flex-shrink min-w-0"
											style="width: {(day.dayMetadata.name.length + 5) * 8}px; max-width: 300px;"
											value={day.dayMetadata.name}
											placeholder="Day name"
											on:blur={(e) => {
												const newName = e.currentTarget.value.trim() || null;
												if (newName !== day.dayMetadata?.name) {
													saveDayMetadata(day.date, newName, day.dayMetadata?.description || null);
												}
											}}
										/>
									{:else}
										<button
											type="button"
											class="text-sm opacity-40 hover:opacity-100 transition-opacity px-1"
											on:click={(e) => {
												const input = e.currentTarget.nextElementSibling;
												if (input) input.focus();
											}}
										>
											+ {$t('adventures.name')}
										</button>
										<input
											type="text"
											class="input input-ghost text-base font-medium px-1 py-0 opacity-0 focus:opacity-100 focus:bg-base-100 focus:px-2 transition-all w-0 focus:w-auto"
											style="max-width: 300px;"
											placeholder="Day name"
											value=""
											on:blur={(e) => {
												const newName = e.currentTarget.value.trim() || null;
												if (newName) {
													saveDayMetadata(day.date, newName, day.dayMetadata?.description || null);
												} else {
													e.currentTarget.classList.add('w-0');
													e.currentTarget.classList.remove('w-auto');
												}
											}}
											on:focus={(e) => {
												e.currentTarget.classList.remove('w-0');
												e.currentTarget.classList.add('w-auto');
											}}
										/>
									{/if}
								{:else if day.dayMetadata?.name}
									<span class="text-base font-medium opacity-90">— {day.dayMetadata.name}</span>
								{/if}
							</div>

							<!-- Day meta info -->
							<div class="text-sm opacity-70 flex items-center gap-3">
								<span class="font-medium"
									>{$t('calendar.day')} {dayNumber} {$t('worldtravel.of')} {totalDays}</span
								>
								<span class="opacity-50">•</span>
								<span
									>{day.items.length}
									{day.items.length === 1 ? $t('checklist.item') : $t('checklist.items')}</span
								>
								{#if day.overnightLodging.length > 0}
									<span class="badge badge-info badge-outline badge-sm"
										>{$t('adventures.overnight')}</span
									>
								{/if}
							</div>

							<!-- Description - shows when present, ghost input when editing -->
							{#if canModify}
								<textarea
									class="textarea textarea-ghost w-full px-2 py-1 text-sm leading-relaxed resize-none focus:bg-base-100 transition-all {day
										.dayMetadata?.description
										? ''
										: 'opacity-40 hover:opacity-70 focus:opacity-100'}"
									rows="2"
									placeholder={'+ ' + $t('itinerary.add_description') + '...'}
									value={day.dayMetadata?.description || ''}
									on:blur={(e) => {
										const newDesc = e.currentTarget.value.trim() || null;
										if (newDesc !== day.dayMetadata?.description) {
											saveDayMetadata(day.date, day.dayMetadata?.name || null, newDesc);
										}
									}}
								/>
							{:else if day.dayMetadata?.description}
								<p class="text-sm leading-relaxed opacity-80 whitespace-pre-wrap px-2 py-1">
									{day.dayMetadata.description}
								</p>
							{/if}
						</div>

						<!-- Actions: saving indicator + Add dropdown -->
						<div class="flex-none ml-3 flex items-start gap-2">
							{#if savingDay === day.date}
								<div>
									<div class="badge badge-neutral-300 gap-2 p-2">
										<span class="loading loading-spinner loading-sm"></span>
										{$t('adventures.saving')}...
									</div>
								</div>
							{/if}

							{#if canModify}
								<div class="dropdown z-30">
									<button
										type="button"
										class="btn btn-square btn-sm btn-outline p-1"
										aria-haspopup="menu"
										aria-expanded="false"
										title={$t('adventures.add')}
									>
										<Plus class="w-5 h-5" />
									</button>
									<ul
										class="dropdown-content menu p-2 shadow bg-base-300 rounded-box w-56"
										role="menu"
									>
										<li>
											<button
												type="button"
												role="menuitem"
												class="w-full text-left"
												on:click={() => {
													linkModalTargetDate = day.date;
													linkModalDisplayDate = day.displayDate;
													isItineraryLinkModalOpen = true;
												}}
											>
												{$t('itinerary.link_existing_item')}
											</button>
										</li>
										<li class="menu-title">{$t('adventures.create_new')}</li>
										<li>
											<button
												type="button"
												role="menuitem"
												class="w-full text-left"
												on:click={() => {
													pendingAddDate = day.date;
													locationToEdit = null;
													locationBeingUpdated = null;
													isLocationModalOpen = true;
												}}
											>
												{$t('locations.location')}
											</button>
										</li>
										<li>
											<button
												type="button"
												role="menuitem"
												class="w-full text-left"
												on:click={() => {
													pendingAddDate = day.date;
													lodgingToEdit = null;
													lodgingBeingUpdated = null;
													isLodgingModalOpen = true;
												}}
											>
												{$t('adventures.lodging')}
											</button>
										</li>
										<li>
											<button
												type="button"
												role="menuitem"
												class="w-full text-left"
												on:click={() => {
													pendingAddDate = day.date;
													isTransportationModalOpen = true;
												}}
											>
												{$t('adventures.transportation')}
											</button>
										</li>
										<li>
											<button
												type="button"
												role="menuitem"
												class="w-full text-left"
												on:click={() => {
													pendingAddDate = day.date;
													isNoteModalOpen = true;
												}}
											>
												{$t('adventures.note')}
											</button>
										</li>
										<li>
											<button
												type="button"
												role="menuitem"
												class="w-full text-left"
												on:click={() => {
													pendingAddDate = day.date;
													isChecklistModalOpen = true;
												}}
											>
												{$t('adventures.checklist')}
											</button>
										</li>
									</ul>
								</div>
							{/if}
						</div>
					</div>

					<!-- Day Items -->
					<div>
						{#if day.items.length === 0}
							<div
								class="card bg-base-100 shadow-sm border border-dashed border-base-300 p-4 text-center"
							>
								<div class="card-body p-2">
									<CalendarBlank class="w-8 h-8 mx-auto mb-2 opacity-40" />
									<p class="opacity-70">{$t('itinerary.no_plans_for_day')}</p>
								</div>
							</div>
						{:else}
							<div
								use:dndzone={{
									items: day.items,
									flipDurationMs,
									dropTargetStyle: { outline: 'none', border: 'none' },
									dragDisabled: isSavingOrder || !canModify,
									dropFromOthersDisabled: true
								}}
								on:consider={(e) => handleDndConsider(dayIndex, e)}
								on:finalize={(e) => handleDndFinalize(dayIndex, e)}
								class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3"
							>
								{#each day.items as item, index (item.id)}
									{@const objectType = item.item?.type || ''}
									{@const resolvedObj = item.resolvedObject}
									{@const multiDay = isMultiDay(item)}
									{@const isDraggingShadow = item[SHADOW_ITEM_MARKER_PROPERTY_NAME]}

									<div
										class="group relative transition-all duration-200 pointer-events-auto h-full {isDraggingShadow
											? 'opacity-40 scale-95'
											: ''}"
										animate:flip={{ duration: flipDurationMs }}
									>
										{#if resolvedObj}
											<!-- Drag Handle Container -->
											{#if canModify}
												<div
													class="absolute left-2 top-2 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
													title={$t('itinerary.drag_to_reorder')}
												>
													<div
														class="itinerary-drag-handle btn btn-circle btn-xs btn-ghost bg-base-100/80 backdrop-blur-sm shadow-sm hover:bg-base-200 cursor-grab active:cursor-grabbing"
														aria-label={$t('itinerary.drag_to_reorder')}
														role="button"
														tabindex="0"
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															class="h-3 w-3"
															fill="none"
															viewBox="0 0 24 24"
															stroke="currentColor"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M4 8h16M4 16h16"
															/>
														</svg>
													</div>
												</div>
											{/if}

											<!-- Order Badge
											<div class="absolute right-2 top-2 z-10">
												<div
													class="badge badge-primary badge-sm font-bold shadow-md"
													title="Item order"
												>
													#{index + 1}
												</div>
											</div> -->

											<!-- Multi-day indicator for lodging -->
											{#if multiDay && objectType === 'lodging'}
												<div class="absolute left-2 bottom-2 z-10">
													<div class="badge badge-info badge-xs gap-1 shadow-sm">
														<svg
															xmlns="http://www.w3.org/2000/svg"
															class="h-3 w-3"
															fill="none"
															viewBox="0 0 24 24"
															stroke="currentColor"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
															/>
														</svg>
														<span class="text-xs">{$t('itinerary.multi_day')}</span>
													</div>
												</div>
											{/if}

											<!-- Card with smooth transition and proper sizing for grid -->
											<div class="transition-all duration-200 h-full">
												<!-- Display the appropriate card based on type -->
												{#if objectType === 'location'}
													<LocationCard
														adventure={resolvedObj}
														on:edit={handleEditLocation}
														on:delete={handleItemDelete}
														on:duplicate={handleDuplicateLocation}
														itineraryItem={item}
														on:removeFromItinerary={handleRemoveItineraryItem}
														on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
														{user}
														{collection}
														compact={true}
														on:changeDay={(e) =>
															handleOpenDayPickerForItem(
																e.detail.type,
																e.detail.item,
																e.detail.forcePicker,
																day.date
															)}
													/>
												{:else if objectType === 'transportation'}
													<TransportationCard
														transportation={resolvedObj}
														{user}
														{collection}
														on:delete={handleItemDelete}
														itineraryItem={item}
														on:removeFromItinerary={handleRemoveItineraryItem}
														on:edit={handleEditTransportation}
														on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
														on:changeDay={(e) =>
															handleOpenDayPickerForItem(
																e.detail.type,
																e.detail.item,
																e.detail.forcePicker,
																day.date
															)}
													/>
												{:else if objectType === 'lodging'}
													<LodgingCard
														lodging={resolvedObj}
														{user}
														{collection}
														itineraryItem={item}
														on:delete={handleItemDelete}
														on:removeFromItinerary={handleRemoveItineraryItem}
														on:edit={handleEditLodging}
														on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
														on:changeDay={(e) =>
															handleOpenDayPickerForItem(
																e.detail.type,
																e.detail.item,
																e.detail.forcePicker,
																day.date
															)}
													/>
												{:else if objectType === 'note'}
													<!-- @ts-ignore - TypeScript can't narrow union type properly -->
													<NoteCard
														note={resolvedObj}
														{user}
														{collection}
														on:delete={handleItemDelete}
														itineraryItem={item}
														on:removeFromItinerary={handleRemoveItineraryItem}
														on:edit={handleEditNote}
														on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
														on:changeDay={(e) =>
															handleOpenDayPickerForItem(
																e.detail.type,
																e.detail.item,
																e.detail.forcePicker,
																day.date
															)}
													/>
												{:else if objectType === 'checklist'}
													<!-- @ts-ignore - TypeScript can't narrow union type properly -->
													<ChecklistCard
														checklist={resolvedObj}
														{user}
														{collection}
														on:delete={handleItemDelete}
														itineraryItem={item}
														on:removeFromItinerary={handleRemoveItineraryItem}
														on:edit={handleEditChecklist}
														on:moveToGlobal={(e) => moveItemToGlobal(e.detail.type, e.detail.id)}
														on:changeDay={(e) =>
															handleOpenDayPickerForItem(
																e.detail.type,
																e.detail.item,
																e.detail.forcePicker,
																day.date
															)}
													/>
												{/if}
											</div>
										{:else}
											<!-- Fallback for unresolved items -->
											<div class="alert alert-warning">
												<span>⚠️ {$t('itinerary.item_not_found')} (ID: {item.object_id})</span>
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>

					<!-- Overnight Lodging + Dated Trip-wide Indicators (share row to save space) -->
					{#if day.overnightLodging.length > 0 || day.globalDatedItems.length > 0}
						<div class="mt-4 pt-4 border-t border-base-300 border-dashed">
							<div class="flex flex-wrap gap-6 items-start">
								{#if day.overnightLodging.length > 0}
									<div class="space-y-2 min-w-[240px] flex-1">
										<div class="flex items-center gap-2 mb-1 opacity-70">
											<Bed class="w-4 h-4" />
											<span class="text-sm font-medium">{$t('itinerary.staying_overnight')}</span>
										</div>
										<div class="space-y-2">
											{#each day.overnightLodging as lodging}
												{@const checkOut = lodging.check_out
													? DateTime.fromISO(lodging.check_out.split('T')[0]).toFormat('LLL d')
													: null}
												<div
													class="flex items-center gap-3 bg-base-100 rounded-lg px-4 py-3 border border-base-300"
												>
													<div
														class="flex items-center justify-center w-8 h-8 rounded-full bg-info/20 text-info"
													>
														<Bed class="w-4 h-4" />
													</div>
													<div class="flex-1 min-w-0">
														<a
															href={`/lodging/${lodging.id}`}
															class="hover:text-primary transition-colors duration-200 line-clamp-2 text-md font-semibold"
														>
															{lodging.name}
														</a>
														{#if lodging.location}
															<p class="text-xs opacity-60 truncate">{lodging.location}</p>
														{/if}
													</div>
													{#if checkOut}
														<div class="badge badge-ghost badge-sm">
															{$t('adventures.check_out')}: {checkOut}
														</div>
													{/if}
												</div>
											{/each}
										</div>
									</div>
								{/if}

								{#if day.globalDatedItems.length > 0}
									<div class="space-y-2 min-w-[220px] flex-1">
										<div class="flex items-center gap-2 mb-1 opacity-70">
											<Globe class="w-4 h-4" />
											<span class="text-sm font-medium"
												>{$t('itinerary.trip_context') || 'Trip Context'}</span
											>
										</div>
										<div class="space-y-2">
											{#each day.globalDatedItems as globalItem (globalItem.id)}
												{@const type = globalItem.item?.type || ''}
												{@const obj = globalItem.resolvedObject}
												{@const name = obj?.name || globalItem.item?.type || 'Item'}
												{@const secondary =
													type === 'location'
														? obj?.location
														: type === 'transportation'
															? obj?.to_location || obj?.from_location
															: type === 'lodging'
																? obj?.location
																: type === 'note' || type === 'checklist'
																	? obj?.name
																	: null}
												<div
													class="flex items-center gap-3 bg-base-100 rounded-lg px-4 py-3 border border-base-300"
												>
													<div
														class="flex items-center justify-center w-8 h-8 rounded-full bg-base-300 text-base-content"
													>
														{#if type === 'lodging'}
															<Bed class="w-4 h-4" />
														{:else if type === 'location'}
															{#if obj?.category?.icon}
																<span class="text-lg">{obj.category.icon}</span>
															{:else}
																<LocationMarker class="w-4 h-4" />
															{/if}
														{:else if type === 'transportation'}
															<Car class="w-4 h-4" />
														{:else}
															<Info class="w-4 h-4" />
														{/if}
													</div>
													<div class="flex-1 min-w-0">
														{#if type === 'location' && obj?.id}
															<a
																href={`/locations/${obj.id}`}
																class="hover:text-primary transition-colors text-md font-semibold line-clamp-2 block"
																>{name}</a
															>
														{:else if type === 'lodging' && obj?.id}
															<a
																href={`/lodging/${obj.id}`}
																class="hover:text-primary transition-colors text-md font-semibold line-clamp-2 block"
																>{name}</a
															>
														{:else if type === 'transportation' && obj?.id}
															<a
																href={`/transportations/${obj.id}`}
																class="hover:text-primary transition-colors text-md font-semibold line-clamp-2 block"
																>{name}</a
															>
														{:else}
															<p class="text-md font-semibold line-clamp-2">{name}</p>
														{/if}
														{#if secondary}
															<p class="text-xs opacity-60 truncate">{secondary}</p>
														{/if}
													</div>
												</div>
											{/each}
										</div>
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/each}

		<!-- Unscheduled Items -->
		{#if unscheduledItems.length > 0}
			<div class="card bg-base-200 shadow-xl border-2 border-dashed border-base-300">
				<div class="card-body">
					<!-- Unscheduled Header -->
					<div class="flex items-center gap-3 mb-4 pb-4 border-b border-base-300">
						<div class="w-6 h-6 rounded-full border-2 border-dashed border-base-content/30"></div>
						<h3 class="text-xl font-bold opacity-70">{$t('itinerary.unscheduled_items')}</h3>
						<div class="badge badge-ghost ml-auto">
							{unscheduledItems.length}
							{unscheduledItems.length === 1 ? $t('checklist.item') : $t('checklist.items')}
						</div>
					</div>

					<p class="text-sm opacity-70 mb-4">
						{$t('itinerary.unscheduled_items_desc')}
					</p>

					<!-- Unscheduled Items List -->
					<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
						{#each unscheduledItems as { type, item }}
							<div class="relative group opacity-60 hover:opacity-100 transition-opacity h-full">
								<!-- "Add to itinerary" indicator -->
								{#if canModify}
									<div
										class="absolute left-2 top-2 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
									>
										<div
											class="join bg-base-100/80 rounded-md p-1 shadow-sm backdrop-blur-sm border border-base-300"
										>
											<button
												aria-label={$t('itinerary.add_to_day')}
												class="btn btn-circle btn-xs btn-primary join-item shadow-sm"
												title={$t('itinerary.add_to_day')}
												on:click={() => handleOpenDayPickerForItem(type, item)}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													class="h-4 w-4"
													fill="none"
													viewBox="0 0 24 24"
													stroke="currentColor"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M12 4v16m8-8H4"
													/>
												</svg>
											</button>
											<button
												aria-label={$t('itinerary.add_to_trip_context')}
												class="btn btn-circle btn-xs btn-outline join-item shadow-sm"
												title={$t('itinerary.add_to_trip_context')}
												on:click={() => addGlobalItineraryItemForObject(type, item.id)}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													class="h-4 w-4"
													fill="none"
													viewBox="0 0 24 24"
													stroke="currentColor"
													><path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M8 17l4 4 4-4m-4-13v17"
													/></svg
												>
											</button>
										</div>
									</div>
								{/if}

								<!-- Display the appropriate card -->
								{#if type === 'location'}
									<LocationCard
										adventure={item}
										on:edit={handleEditLocation}
										on:delete={handleItemDelete}
										on:duplicate={handleDuplicateLocation}
										{user}
										{collection}
										compact={true}
									/>
								{:else if type === 'transportation'}
									<TransportationCard
										transportation={item}
										{user}
										{collection}
										on:delete={handleItemDelete}
										on:edit={handleEditTransportation}
									/>
								{:else if type === 'lodging'}
									<LodgingCard
										lodging={item}
										{user}
										{collection}
										on:delete={handleItemDelete}
										on:edit={handleEditLodging}
									/>
								{:else if type === 'note'}
									<NoteCard
										note={item}
										{user}
										{collection}
										on:delete={handleItemDelete}
										on:edit={handleEditNote}
									/>
								{:else if type === 'checklist'}
									<ChecklistCard
										checklist={item}
										{user}
										{collection}
										on:delete={handleItemDelete}
										on:edit={handleEditChecklist}
									/>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}
