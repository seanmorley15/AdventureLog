<script lang="ts">
	import { t } from 'svelte-i18n';
	import { flip } from 'svelte/animate';
	import {
		dragHandleZone,
		SHADOW_ITEM_MARKER_PROPERTY_NAME,
		type DndEvent
	} from 'svelte-dnd-action';
	import type {
		Checklist,
		Collection,
		CollectionItineraryDay,
		CollectionItineraryItem,
		DayPlanState,
		Location,
		Lodging,
		Note,
		Transportation,
		Visit
	} from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { dateFormatFromUser, formatDisplayDate } from '$lib/dateFormat';
	import { applyDropdownFlip } from '$lib/utils/flipDropdown';
	import { createEmptyLocation } from '$lib/location-draft';
	import {
		MAX_PLAN_DAYS,
		browserTimezone,
		errorMessage,
		findObject,
		indexedDays,
		objectsOfType,
		placementType,
		planFingerprint,
		planRequest,
		spanEndFromRecord,
		type LogVisitResult,
		type PlacementPayload,
		type PlanObject,
		type PlanObjectType,
		type PlanResponse,
		type PlanRow
	} from '$lib/dayPlan';
	import DayPlanRow from './DayPlanRow.svelte';
	import DayPlacementModal from './DayPlacementModal.svelte';
	import DayItemPickerModal from './DayItemPickerModal.svelte';
	import LocationModal from '$lib/components/locations/LocationModal.svelte';
	import LodgingModal from '$lib/components/lodging/LodgingModal.svelte';
	import TransportationModal from '$lib/components/transportation/TransportationModal.svelte';
	import NoteModal from '$lib/components/NoteModal.svelte';
	import ChecklistModal from '$lib/components/ChecklistModal.svelte';
	import Plus from '~icons/mdi/plus';
	import DotsVertical from '~icons/mdi/dots-vertical';
	import Lightbulb from '~icons/mdi/lightbulb-outline';
	import Earth from '~icons/mdi/earth';
	import CalendarEdit from '~icons/mdi/calendar-edit';
	import CheckAll from '~icons/mdi/check-all';
	import Close from '~icons/mdi/close';

	interface Props {
		collection: Collection;
		user: any;
		canModify?: boolean;
	}

	let { collection = $bindable(), user, canModify = false }: Props = $props();

	const FLIP_MS = 150;
	const OBJECT_LISTS: Record<
		PlanObjectType,
		'locations' | 'lodging' | 'transportations' | 'notes' | 'checklists'
	> = {
		location: 'locations',
		lodging: 'lodging',
		transportation: 'transportations',
		note: 'notes',
		checklist: 'checklists'
	};
	const ALL_TYPES: PlanObjectType[] = [
		'location',
		'lodging',
		'transportation',
		'note',
		'checklist'
	];

	const dateFormat = $derived(dateFormatFromUser(user));
	const days = $derived(indexedDays(collection));
	const dayCount = $derived(days.length);
	const anchored = $derived(Boolean(collection.start_date));
	const today = new Date().toISOString().slice(0, 10);

	function toRow(item: CollectionItineraryItem): PlanRow {
		const type = placementType(item);
		const objectId = String(item.object_id);
		return {
			id: String(item.id),
			item,
			type,
			objectId,
			object: findObject(collection, type, objectId)
		};
	}

	function dayZone(dayId: string): string {
		return `day:${dayId}`;
	}

	function byOrder(a: PlanRow, b: PlanRow): number {
		return (a.item?.order ?? 0) - (b.item?.order ?? 0);
	}

	function buildZones(): Record<string, PlanRow[]> {
		const result: Record<string, PlanRow[]> = { global: [], ideas: [] };
		for (const day of days) result[dayZone(day.id)] = [];
		for (const item of collection.itinerary ?? []) {
			const row = toRow(item);
			const key = item.day ? dayZone(String(item.day)) : null;
			if (item.is_global) result.global.push(row);
			else if (key && result[key]) result[key].push(row);
			else result.ideas.push(row);
		}
		for (const rows of Object.values(result)) rows.sort(byOrder);
		return result;
	}

	// Writable derived: drag previews assign to it, and it rebuilds whenever the plan changes.
	let zones = $derived(buildZones());

	const continuing = $derived.by(() => {
		const map = new Map<number, PlanRow[]>();
		const spans = (collection.itinerary ?? [])
			.filter(
				(item) => item.day_index && item.span_end_index && item.span_end_index > item.day_index
			)
			.sort((a, b) => (a.day_index ?? 0) - (b.day_index ?? 0) || a.order - b.order);
		for (const item of spans) {
			const row = toRow(item);
			for (let index = (item.day_index ?? 0) + 1; index <= (item.span_end_index ?? 0); index++) {
				if (!map.has(index)) map.set(index, []);
				map.get(index)!.push(row);
			}
		}
		return map;
	});

	const unplaced = $derived.by(() => {
		const placed = new Set(
			(collection.itinerary ?? []).map((item) => `${placementType(item)}:${item.object_id}`)
		);
		const rows: PlanRow[] = [];
		for (const type of ALL_TYPES) {
			for (const obj of objectsOfType(collection, type)) {
				if (placed.has(`${type}:${obj.id}`)) continue;
				rows.push({
					id: `unplaced-${type}-${obj.id}`,
					item: null,
					type,
					objectId: String(obj.id),
					object: obj
				});
			}
		}
		return rows;
	});

	const placementLabels = $derived.by(() => {
		const labels = new Map<string, string[]>();
		for (const item of collection.itinerary ?? []) {
			const label = item.is_global
				? $t('itinerary.trip_wide')
				: item.day_index
					? $t('itinerary.on_day', { values: { n: item.day_index } })
					: $t('itinerary.in_ideas');
			const key = String(item.object_id);
			labels.set(key, [...(labels.get(key) ?? []), label]);
		}
		return new Map([...labels].map(([key, list]) => [key, list.join(', ')]));
	});

	function dayTitle(day: CollectionItineraryDay): string {
		return $t('itinerary.day_n', { values: { n: day.index } });
	}

	function weekday(iso: string): string {
		return new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long' });
	}

	// ---------------------------------------------------------------- state sync

	function upsertItems(items: CollectionItineraryItem[]) {
		const byId = new Map((collection.itinerary ?? []).map((item) => [String(item.id), item]));
		for (const item of items) byId.set(String(item.id), item);
		collection.itinerary = [...byId.values()];
	}

	function removeItem(id: string) {
		collection.itinerary = (collection.itinerary ?? []).filter((item) => String(item.id) !== id);
	}

	function upsertObject(type: PlanObjectType, obj: PlanObject) {
		const key = OBJECT_LISTS[type];
		const list = [...((collection[key] as PlanObject[] | undefined) ?? [])];
		const index = list.findIndex((existing) => String(existing.id) === String(obj.id));
		if (index >= 0) {
			const merged = { ...list[index], ...obj } as PlanObject;
			if (type === 'location' && !(obj as Location).visits) {
				(merged as Location).visits = (list[index] as Location).visits ?? [];
			}
			list[index] = merged;
		} else {
			list.unshift(obj);
		}
		(collection as Record<string, unknown>)[key] = list;
	}

	function mergeUpdatedObjects(objects: (Lodging | Transportation | null)[]) {
		for (const obj of objects) {
			if (!obj) continue;
			upsertObject('check_in' in obj ? 'lodging' : 'transportation', obj);
		}
	}

	function applyItemResponse(
		data: CollectionItineraryItem & { updated_object?: Lodging | Transportation }
	) {
		const { updated_object, ...item } = data;
		upsertItems([item as CollectionItineraryItem]);
		if (updated_object) mergeUpdatedObjects([updated_object]);
	}

	function addVisits(visits: Visit[]) {
		if (!visits.length) return;
		collection.locations = (collection.locations ?? []).map((location) => {
			const added = visits.filter((visit) => String(visit.location) === String(location.id));
			if (!added.length) return location;
			const known = new Set((location.visits ?? []).map((visit) => visit.id));
			return {
				...location,
				visits: [...(location.visits ?? []), ...added.filter((visit) => !known.has(visit.id))],
				is_visited:
					location.is_visited || added.some((visit) => visit.start_date.slice(0, 10) <= today)
			};
		});
	}

	function applyState(state: DayPlanState) {
		collection = {
			...collection,
			start_date: state.collection.start_date,
			end_date: state.collection.end_date,
			timezone: state.collection.timezone,
			day_count: state.collection.day_count,
			itinerary: state.itinerary,
			itinerary_days: state.itinerary_days,
			lodging: state.lodging,
			transportations: state.transportations
		};
	}

	// ---------------------------------------------------------------- requests

	let saving = $state(false);
	let dragging = false;
	let refetching = false;
	let lastFetchAt = Date.now();

	async function refetch(announce: boolean) {
		if (refetching) return;
		refetching = true;
		try {
			const res = await planRequest<Collection>(`/api/collections/${collection.id}/`, 'GET');
			if (!res.ok || !res.data?.id) return;
			lastFetchAt = Date.now();
			if (announce && planFingerprint(res.data) !== planFingerprint(collection)) {
				addToast('info', $t('itinerary.plan_updated_elsewhere'));
			}
			collection = res.data;
		} finally {
			refetching = false;
		}
	}

	function handleVisibilityChange() {
		if (document.visibilityState !== 'visible' || dragging || saving) return;
		if (Date.now() - lastFetchAt > 15_000) void refetch(true);
	}

	async function send<T = any>(
		url: string,
		method: 'POST' | 'PATCH' | 'DELETE',
		body?: unknown,
		quiet = false
	): Promise<PlanResponse<T>> {
		saving = true;
		try {
			const res = await planRequest<T>(url, method, body);
			if (res.status === 409) {
				addToast('warning', $t('itinerary.order_conflict'));
				await refetch(false);
			} else if (!res.ok && !quiet) {
				addToast('error', errorMessage(res.data, $t('itinerary.save_failed')));
			}
			return res;
		} finally {
			saving = false;
		}
	}

	async function createPlacement(
		type: PlanObjectType,
		objectId: string,
		payload: Partial<PlacementPayload> = {}
	): Promise<boolean> {
		const res = await send('/api/itineraries/', 'POST', {
			collection: collection.id,
			content_type: type,
			object_id: objectId,
			day_index: payload.day_index ?? null,
			is_global: payload.is_global ?? false,
			span_end_index: payload.span_end_index ?? null,
			is_optional: payload.is_optional ?? false,
			start_time: payload.start_time ?? null,
			end_time: payload.end_time ?? null
		});
		if (res.ok) applyItemResponse(res.data);
		return res.ok;
	}

	// ---------------------------------------------------------------- drag and drop

	const pendingZones = new Set<string>();
	let flushTimer: ReturnType<typeof setTimeout> | null = null;

	function isShadow(row: PlanRow): boolean {
		return Boolean((row as PlanRow & Record<string, unknown>)[SHADOW_ITEM_MARKER_PROPERTY_NAME]);
	}

	function zoneDayIndex(key: string): number | null {
		if (!key.startsWith('day:')) return null;
		const id = key.slice(4);
		return days.find((day) => String(day.id) === id)?.index ?? null;
	}

	function handleConsider(key: string, event: CustomEvent<DndEvent<PlanRow>>) {
		dragging = true;
		zones = { ...zones, [key]: event.detail.items };
	}

	function handleFinalize(key: string, event: CustomEvent<DndEvent<PlanRow>>) {
		zones = { ...zones, [key]: event.detail.items };
		pendingZones.add(key);
		if (flushTimer) clearTimeout(flushTimer);
		flushTimer = setTimeout(() => {
			flushTimer = null;
			void saveZones();
		}, 0);
	}

	async function saveZones() {
		const keys = [...pendingZones];
		pendingZones.clear();
		dragging = false;
		const entries = keys.flatMap((key) =>
			(zones[key] ?? [])
				.filter((row) => row.item && !isShadow(row))
				.map((row, order) => ({
					id: row.id,
					day_index: zoneDayIndex(key),
					is_global: key === 'global',
					order
				}))
		);
		if (!entries.length) return;
		const res = await send<{
			items: CollectionItineraryItem[];
			updated_objects: (Lodging | Transportation | null)[];
		}>('/api/itineraries/reorder/', 'POST', { items: entries });
		if (res.ok) {
			upsertItems(res.data.items);
			mergeUpdatedObjects(res.data.updated_objects ?? []);
		} else if (res.status !== 409) {
			await refetch(false);
		}
	}

	function zoneOptions(key: string, rows: PlanRow[]) {
		return {
			items: rows,
			flipDurationMs: FLIP_MS,
			type: key === 'global' ? 'global' : 'plan',
			dragDisabled: !canModify,
			dropTargetStyle: {},
			dropTargetClasses: ['ring-2', 'ring-primary/40', 'rounded-lg']
		};
	}

	// ---------------------------------------------------------------- rows

	async function logVisit(row: PlanRow, date?: string): Promise<LogVisitResult> {
		const res = await send<{ item: CollectionItineraryItem; visit: Visit }>(
			`/api/itineraries/${row.id}/log-visited/`,
			'POST',
			date ? { date } : {},
			true
		);
		if (res.ok) {
			upsertItems([res.data.item]);
			addVisits([res.data.visit]);
			addToast('success', $t('itinerary.visit_logged'));
			return 'ok';
		}
		if (res.data?.code === 'date_required') return 'date_required';
		if (res.status !== 409) addToast('error', errorMessage(res.data, $t('itinerary.save_failed')));
		return 'error';
	}

	async function toggleOptional(row: PlanRow) {
		if (!row.item) return;
		const res = await send(`/api/itineraries/${row.id}/`, 'PATCH', {
			is_optional: !row.item.is_optional
		});
		if (res.ok) applyItemResponse(res.data);
	}

	async function removePlacement(row: PlanRow) {
		const res = await send(`/api/itineraries/${row.id}/`, 'DELETE');
		if (res.ok) removeItem(row.id);
	}

	let placementEdit = $state<{
		mode: 'edit' | 'add';
		row: PlanRow;
		dayIndex: number | null;
	} | null>(null);

	async function savePlacement(payload: PlacementPayload): Promise<boolean> {
		const target = placementEdit;
		if (!target?.row.type) return false;
		if (target.mode === 'add') {
			return createPlacement(target.row.type, target.row.objectId, payload);
		}
		const item = target.row.item;
		if (!item) return false;
		const body: Record<string, unknown> = {};
		const currentWhere = item.is_global ? 'global' : (item.day_index ?? null);
		const nextWhere = payload.is_global ? 'global' : payload.day_index;
		if (
			currentWhere !== nextWhere ||
			(payload.span_end_index ?? null) !== (item.span_end_index ?? null)
		) {
			body.day_index = payload.day_index;
			body.is_global = payload.is_global;
			body.span_end_index = payload.span_end_index;
		}
		if (payload.is_optional !== Boolean(item.is_optional)) body.is_optional = payload.is_optional;
		if ((payload.start_time ?? '') !== (item.start_time ?? '').slice(0, 5))
			body.start_time = payload.start_time;
		if ((payload.end_time ?? '') !== (item.end_time ?? '').slice(0, 5))
			body.end_time = payload.end_time;
		if (!Object.keys(body).length) return true;
		const res = await send(`/api/itineraries/${item.id}/`, 'PATCH', body);
		if (res.ok) applyItemResponse(res.data);
		return res.ok;
	}

	// ---------------------------------------------------------------- day actions

	type DestinationPrompt =
		| { kind: 'delete'; day: CollectionItineraryDay; count: number }
		| { kind: 'duration'; body: Record<string, unknown>; dayIndexes: number[]; keep: number };

	let destinationPrompt = $state<DestinationPrompt | null>(null);
	let destinationChoice = $state('ideas');

	async function dayAction(path: string, body: Record<string, unknown>, quiet = false) {
		const res = await send<DayPlanState>(
			`/api/itineraries/${path}/`,
			'POST',
			{ collection: collection.id, ...body },
			quiet
		);
		if (res.ok) applyState(res.data);
		return res;
	}

	function insertDay(position?: number) {
		void dayAction('days/insert', position ? { position } : {});
	}

	function duplicateDay(day: CollectionItineraryDay) {
		void dayAction('days/duplicate', { day: day.id });
	}

	function moveDay(day: CollectionItineraryDay, position: number) {
		void dayAction('days/move', { day: day.id, position });
	}

	async function deleteDay(day: CollectionItineraryDay) {
		const res = await dayAction('days/delete', { day: day.id }, true);
		if (res.ok || res.status === 409) return;
		if (res.data?.code === 'destination_required') {
			destinationChoice = 'ideas';
			destinationPrompt = { kind: 'delete', day, count: res.data.item_count ?? 0 };
		} else {
			addToast('error', errorMessage(res.data, $t('itinerary.save_failed')));
		}
	}

	const destinationDays = $derived.by(() => {
		const prompt = destinationPrompt;
		if (!prompt) return [];
		if (prompt.kind === 'delete') return days.filter((day) => day.id !== prompt.day.id);
		return days.filter((day) => (day.index ?? 0) <= prompt.keep);
	});

	async function resolveDestination(event: SubmitEvent) {
		event.preventDefault();
		const prompt = destinationPrompt;
		if (!prompt) return;
		const extra =
			destinationChoice === 'ideas'
				? { destination: 'ideas' }
				: { destination: 'day', target_day: destinationChoice };
		const res =
			prompt.kind === 'delete'
				? await dayAction('days/delete', { day: prompt.day.id, ...extra })
				: await dayAction('duration', { ...prompt.body, ...extra });
		if (res.ok) {
			destinationPrompt = null;
			if (prompt.kind === 'duration') editingDuration = false;
		}
	}

	let editingDuration = $state(false);
	let durationCount = $state(1);
	let durationStart = $state('');

	function openDuration() {
		durationCount = dayCount;
		durationStart = collection.start_date ?? '';
		editingDuration = true;
	}

	async function applyDuration(event: SubmitEvent) {
		event.preventDefault();
		if (durationCount < 1 || durationCount > MAX_PLAN_DAYS) {
			addToast('error', $t('collection.day_count_required', { values: { max: MAX_PLAN_DAYS } }));
			return;
		}
		const body: Record<string, unknown> = { day_count: durationCount };
		const nextStart = durationStart || null;
		if (nextStart !== (collection.start_date ?? null)) {
			body.start_date = nextStart;
			if (nextStart) body.timezone = browserTimezone();
		}
		const res = await dayAction('duration', body, true);
		if (res.ok) {
			editingDuration = false;
		} else if (res.data?.code === 'destination_required') {
			destinationChoice = 'ideas';
			destinationPrompt = {
				kind: 'duration',
				body,
				dayIndexes: res.data.day_indexes ?? [],
				keep: durationCount
			};
		} else if (res.status !== 409) {
			addToast('error', errorMessage(res.data, $t('itinerary.save_failed')));
		}
	}

	async function saveDayField(
		day: CollectionItineraryDay,
		field: 'name' | 'description',
		value: string
	) {
		const next = value.trim() || null;
		if (next === (day[field] ?? null)) return;
		const res = await send<CollectionItineraryDay>(`/api/itinerary-days/${day.id}/`, 'PATCH', {
			[field]: next
		});
		if (res.ok) {
			collection.itinerary_days = (collection.itinerary_days ?? []).map((existing) =>
				existing.id === day.id ? res.data : existing
			);
		}
	}

	// ---------------------------------------------------------------- log day

	let logDayPromptFor = $state<string | null>(null);
	let logDayDate = $state(today);
	let loggingDay = $state<string | null>(null);

	function loggableCount(day: CollectionItineraryDay): number {
		return (zones[dayZone(day.id)] ?? []).filter(
			(row) =>
				row.type === 'location' && row.item && !row.item.is_optional && !row.item.logged_visit
		).length;
	}

	async function logDay(day: CollectionItineraryDay, date?: string) {
		if (!anchored && !date) {
			logDayPromptFor = day.id;
			return;
		}
		loggingDay = day.id;
		try {
			const res = await send<{ items: CollectionItineraryItem[]; visits: Visit[] }>(
				'/api/itineraries/log-day/',
				'POST',
				{ collection: collection.id, day: day.id, ...(date ? { date } : {}) },
				true
			);
			if (res.ok) {
				upsertItems(res.data.items);
				addVisits(res.data.visits);
				logDayPromptFor = null;
				addToast(
					'success',
					res.data.visits.length
						? $t('itinerary.day_logged', { values: { count: res.data.visits.length } })
						: $t('itinerary.nothing_to_log')
				);
			} else if (res.data?.code === 'date_required') {
				logDayPromptFor = day.id;
			} else if (res.status !== 409) {
				addToast('error', errorMessage(res.data, $t('itinerary.save_failed')));
			}
		} finally {
			loggingDay = null;
		}
	}

	// ---------------------------------------------------------------- object modals

	type CreateTarget = { dayIndex: number | null; isGlobal: boolean };

	let openModal = $state<PlanObjectType | null>(null);
	let createTarget = $state<CreateTarget | null>(null);
	let pickerTarget = $state<{ dayIndex: number | null; isGlobal: boolean; title: string } | null>(
		null
	);
	let locationToEdit = $state<Location | null>(null);
	let lodgingToEdit = $state<Lodging | null>(null);
	let transportationToEdit = $state<Transportation | null>(null);
	let noteToEdit = $state<Note | null>(null);
	let checklistToEdit = $state<Checklist | null>(null);
	let locationDraft = $state(createEmptyLocation());
	let lodgingDraft = $state<Lodging | null>(null);
	let transportationDraft = $state<Transportation | undefined>(undefined);
	const placedFromModal = new Set<string>();

	const createDate = $derived.by(() => {
		const index = createTarget?.dayIndex;
		if (!index) return null;
		return days.find((day) => day.index === index)?.date ?? null;
	});

	function startCreate(type: PlanObjectType, target: CreateTarget) {
		createTarget = target;
		locationToEdit = null;
		lodgingToEdit = null;
		transportationToEdit = null;
		noteToEdit = null;
		checklistToEdit = null;
		locationDraft = createEmptyLocation();
		lodgingDraft = null;
		transportationDraft = undefined;
		openModal = type;
	}

	function editObject(row: PlanRow) {
		if (!row.object || !row.type) return;
		createTarget = null;
		if (row.type === 'location') {
			locationToEdit = row.object as Location;
			locationDraft = createEmptyLocation();
		} else if (row.type === 'lodging') {
			lodgingToEdit = row.object as Lodging;
			lodgingDraft = null;
		} else if (row.type === 'transportation') {
			transportationToEdit = row.object as Transportation;
			transportationDraft = undefined;
		} else if (row.type === 'note') {
			noteToEdit = row.object as Note;
		} else {
			checklistToEdit = row.object as Checklist;
		}
		openModal = row.type;
	}

	async function placeCreated(type: PlanObjectType, record: PlanObject) {
		const target = createTarget;
		const id = String(record.id);
		if (!target || placedFromModal.has(id)) return;
		placedFromModal.add(id);
		const span =
			target.dayIndex && (type === 'lodging' || type === 'transportation')
				? spanEndFromRecord(type, record, target.dayIndex, dayCount)
				: null;
		await createPlacement(type, id, {
			day_index: target.dayIndex,
			is_global: target.isGlobal,
			span_end_index: span
		});
	}

	function finishModal() {
		openModal = null;
		createTarget = null;
		locationToEdit = null;
		lodgingToEdit = null;
		transportationToEdit = null;
		noteToEdit = null;
		checklistToEdit = null;
	}

	async function closeLocationModal() {
		const saved = locationDraft?.id ? ($state.snapshot(locationDraft) as Location) : null;
		const creating = !locationToEdit;
		if (saved) {
			upsertObject('location', saved);
			if (creating) await placeCreated('location', saved);
		}
		finishModal();
	}

	function handleQuickAdd(
		type: 'location' | 'lodging',
		event: CustomEvent<{ location: PlanObject; itineraryItem?: CollectionItineraryItem | null }>
	) {
		const record = event.detail?.location;
		if (!record) return;
		upsertObject(type, record);
		if (event.detail.itineraryItem) {
			upsertItems([event.detail.itineraryItem]);
			placedFromModal.add(String(record.id));
		}
	}

	async function closeLodgingModal() {
		const saved = lodgingDraft?.id ? ($state.snapshot(lodgingDraft) as Lodging) : null;
		const creating = !lodgingToEdit;
		if (saved) {
			upsertObject('lodging', saved);
			if (creating) await placeCreated('lodging', saved);
		}
		finishModal();
	}

	async function closeTransportationModal() {
		const saved = transportationDraft?.id
			? ($state.snapshot(transportationDraft) as Transportation)
			: null;
		const creating = !transportationToEdit;
		if (saved) {
			upsertObject('transportation', saved);
			if (creating) await placeCreated('transportation', saved);
		}
		finishModal();
	}

	async function handleNoteSaved(
		type: 'note' | 'checklist',
		record: Note | Checklist,
		created: boolean
	) {
		upsertObject(type, record);
		if (created) await placeCreated(type, record);
		finishModal();
	}

	async function pickExisting(type: PlanObjectType, objectId: string) {
		const target = pickerTarget;
		if (!target) return;
		const ok = await createPlacement(type, objectId, {
			day_index: target.dayIndex,
			is_global: target.isGlobal
		});
		if (ok) pickerTarget = null;
	}
</script>

<svelte:document onvisibilitychange={handleVisibilityChange} />

{#snippet addMenu(target: CreateTarget, pickerTitle: string)}
	<div
		class="dropdown dropdown-end"
		role="group"
		onpointerdown={(e) => applyDropdownFlip(e.currentTarget)}
	>
		<div
			tabindex="0"
			role="button"
			class="btn btn-sm btn-square btn-outline"
			aria-haspopup="menu"
			title={$t('adventures.add')}
			aria-label={$t('adventures.add')}
		>
			<Plus class="h-5 w-5" />
		</div>
		<ul
			tabindex="-1"
			class="dropdown-content menu z-40 w-56 rounded-box bg-base-300 p-2 shadow-sm"
			role="menu"
		>
			<li>
				<button
					type="button"
					role="menuitem"
					onclick={() => (pickerTarget = { ...target, title: pickerTitle })}
				>
					{$t('itinerary.add_existing')}
				</button>
			</li>
			<li class="menu-title">{$t('adventures.create_new')}</li>
			{#if !target.isGlobal}
				<li>
					<button type="button" role="menuitem" onclick={() => startCreate('location', target)}>
						{$t('locations.location')}
					</button>
				</li>
				<li>
					<button type="button" role="menuitem" onclick={() => startCreate('lodging', target)}>
						{$t('adventures.lodging')}
					</button>
				</li>
				<li>
					<button
						type="button"
						role="menuitem"
						onclick={() => startCreate('transportation', target)}
					>
						{$t('adventures.transportation')}
					</button>
				</li>
			{/if}
			<li>
				<button type="button" role="menuitem" onclick={() => startCreate('note', target)}>
					{$t('adventures.note')}
				</button>
			</li>
			<li>
				<button type="button" role="menuitem" onclick={() => startCreate('checklist', target)}>
					{$t('adventures.checklist')}
				</button>
			</li>
		</ul>
	</div>
{/snippet}

{#snippet planRow(
	row: PlanRow,
	options: { draggable: boolean; projected: boolean; continuation?: boolean }
)}
	<DayPlanRow
		{row}
		{canModify}
		{dateFormat}
		hasProjectedDate={options.projected}
		draggable={options.draggable}
		continuation={options.continuation}
		onLogVisit={logVisit}
		onEditObject={editObject}
		onEditPlacement={(target) =>
			(placementEdit = { mode: 'edit', row: target, dayIndex: target.item?.day_index ?? null })}
		onToggleOptional={toggleOptional}
		onAddAgain={(target) => (placementEdit = { mode: 'add', row: target, dayIndex: null })}
		onRemove={removePlacement}
		onAddToPlan={(target) => (placementEdit = { mode: 'add', row: target, dayIndex: null })}
	/>
{/snippet}

{#snippet zone(key: string, rows: PlanRow[], projected: boolean, emptyText: string)}
	<div class="relative">
		<div
			class={['flex flex-col gap-2', rows.length === 0 && 'min-h-14']}
			use:dragHandleZone={zoneOptions(key, rows)}
			onconsider={(e) => handleConsider(key, e)}
			onfinalize={(e) => handleFinalize(key, e)}
		>
			{#each rows as row (row.id)}
				<div animate:flip={{ duration: FLIP_MS }} class={[isShadow(row) && 'opacity-40']}>
					{@render planRow(row, { draggable: true, projected })}
				</div>
			{/each}
		</div>
		{#if rows.length === 0}
			<p
				class="pointer-events-none absolute inset-0 flex items-center justify-center rounded-lg border border-dashed border-base-300 text-sm opacity-60"
			>
				{emptyText}
			</p>
		{/if}
	</div>
{/snippet}

<div class="space-y-6">
	<!-- Trip summary and duration -->
	<div class="card bg-base-200 shadow-sm">
		<div class="card-body gap-3 p-4 sm:p-5">
			<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
				<span class="font-semibold">{$t('itinerary.days_label')}: {dayCount}</span>
				<span class="opacity-40">•</span>
				{#if anchored}
					<span class="text-sm opacity-80">
						{formatDisplayDate(collection.start_date, dateFormat)} – {formatDisplayDate(
							collection.end_date,
							dateFormat
						)}
					</span>
					{#if collection.timezone && collection.timezone !== 'UTC'}
						<span class="badge badge-ghost badge-sm">
							{$t('itinerary.times_in', { values: { zone: collection.timezone } })}
						</span>
					{/if}
				{:else}
					<span class="text-sm opacity-70">{$t('itinerary.dates_not_set')}</span>
				{/if}
				<div class="ml-auto flex items-center gap-2">
					{#if saving}
						<span class="loading loading-spinner loading-sm opacity-70"></span>
					{/if}
					{#if canModify && !editingDuration}
						<button type="button" class="btn btn-sm btn-ghost gap-1" onclick={openDuration}>
							<CalendarEdit class="h-4 w-4" />
							{$t('itinerary.edit_days')}
						</button>
					{/if}
				</div>
			</div>

			{#if editingDuration}
				<form class="flex flex-wrap items-end gap-3" onsubmit={applyDuration}>
					<label class="flex flex-col gap-1">
						<span class="field-label">{$t('itinerary.days_label')}</span>
						<input
							type="number"
							class="input input-sm w-28"
							min="1"
							max={MAX_PLAN_DAYS}
							bind:value={durationCount}
							required
						/>
					</label>
					<label class="flex flex-col gap-1">
						<span class="field-label">{$t('itinerary.start_date_optional')}</span>
						<input type="date" class="input input-sm w-44" bind:value={durationStart} />
					</label>
					<div class="flex gap-2">
						<button type="submit" class="btn btn-sm btn-primary" disabled={saving}>
							{$t('itinerary.apply')}
						</button>
						<button
							type="button"
							class="btn btn-sm btn-ghost"
							onclick={() => (editingDuration = false)}
						>
							{$t('about.close')}
						</button>
					</div>
				</form>
			{/if}
		</div>
	</div>

	<!-- Trip-wide notes and checklists -->
	{#if zones.global.length > 0 || canModify}
		<section class="card bg-base-200 shadow-sm">
			<div class="card-body gap-3 p-4 sm:p-5">
				<div class="flex items-center gap-3">
					<Earth class="h-5 w-5 text-primary" />
					<div class="min-w-0 flex-1">
						<h3 class="text-lg font-bold">{$t('itinerary.trip_wide')}</h3>
						<p class="text-sm opacity-70">{$t('itinerary.trip_wide_desc')}</p>
					</div>
					{#if canModify}
						{@render addMenu({ dayIndex: null, isGlobal: true }, $t('itinerary.trip_wide'))}
					{/if}
				</div>
				{@render zone('global', zones.global, false, $t('itinerary.no_trip_context_items'))}
			</div>
		</section>
	{/if}

	<!-- Ideas -->
	<section class="card border border-dashed border-base-300 bg-base-200 shadow-sm">
		<div class="card-body gap-3 p-4 sm:p-5">
			<div class="flex items-center gap-3">
				<Lightbulb class="h-5 w-5 text-warning" />
				<div class="min-w-0 flex-1">
					<h3 class="text-lg font-bold">{$t('itinerary.ideas')}</h3>
					<p class="text-sm opacity-70">{$t('itinerary.ideas_desc')}</p>
				</div>
				{#if canModify}
					{@render addMenu({ dayIndex: null, isGlobal: false }, $t('itinerary.ideas'))}
				{/if}
			</div>
			{@render zone('ideas', zones.ideas, false, $t('itinerary.ideas_empty'))}
			{#if unplaced.length > 0}
				<div class="space-y-2 pt-2">
					<h4 class="text-xs font-semibold uppercase tracking-wide opacity-60">
						{$t('itinerary.not_on_plan')}
					</h4>
					{#each unplaced as row (row.id)}
						{@render planRow(row, { draggable: false, projected: false })}
					{/each}
				</div>
			{/if}
		</div>
	</section>

	<!-- Days -->
	{#each days as day (day.id)}
		{@const key = dayZone(day.id)}
		{@const rows = zones[key] ?? []}
		{@const carried = continuing.get(day.index ?? 0) ?? []}
		{@const loggable = loggableCount(day)}
		<section class="card bg-base-200 shadow-sm">
			<div class="card-body gap-3 p-4 sm:p-5">
				<div class="flex items-start gap-3">
					<div class="min-w-0 flex-1 space-y-1">
						<div class="flex flex-wrap items-baseline gap-x-3">
							<h3 class="text-lg font-bold md:text-xl">{dayTitle(day)}</h3>
							{#if day.date}
								<span class="text-sm opacity-70">
									{weekday(day.date)}, {formatDisplayDate(day.date, dateFormat, { month: 'long' })}
								</span>
							{/if}
						</div>
						{#if canModify}
							<input
								type="text"
								class="input input-ghost input-sm -ml-2 w-full max-w-md font-medium"
								placeholder={`+ ${$t('adventures.name')}`}
								value={day.name ?? ''}
								onchange={(e) => saveDayField(day, 'name', e.currentTarget.value)}
							/>
							<textarea
								class="textarea textarea-ghost textarea-sm -ml-2 min-h-8 w-full resize-none field-sizing-content"
								rows="1"
								placeholder={`+ ${$t('itinerary.add_description')}`}
								value={day.description ?? ''}
								onchange={(e) => saveDayField(day, 'description', e.currentTarget.value)}
							></textarea>
						{:else}
							{#if day.name}
								<p class="font-medium">{day.name}</p>
							{/if}
							{#if day.description}
								<p class="whitespace-pre-wrap text-sm opacity-80">{day.description}</p>
							{/if}
						{/if}
					</div>

					{#if canModify}
						<div class="flex shrink-0 items-center gap-1">
							{#if loggable > 0 && logDayPromptFor !== day.id}
								<button
									type="button"
									class="btn btn-sm btn-ghost gap-1"
									disabled={loggingDay === day.id}
									onclick={() => logDay(day)}
								>
									{#if loggingDay === day.id}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<CheckAll class="h-4 w-4" />
									{/if}
									{$t('itinerary.log_day')}
								</button>
							{/if}
							{@render addMenu({ dayIndex: day.index ?? null, isGlobal: false }, dayTitle(day))}
							<div
								class="dropdown dropdown-end"
								role="group"
								onpointerdown={(e) => applyDropdownFlip(e.currentTarget)}
							>
								<div
									tabindex="0"
									role="button"
									class="btn btn-sm btn-square btn-ghost"
									aria-label={$t('itinerary.day_actions')}
									title={$t('itinerary.day_actions')}
								>
									<DotsVertical class="h-5 w-5" />
								</div>
								<ul
									tabindex="-1"
									class="dropdown-content menu z-40 w-56 rounded-box bg-base-300 p-2 shadow-sm"
									role="menu"
								>
									<li>
										<button
											type="button"
											role="menuitem"
											disabled={dayCount >= MAX_PLAN_DAYS}
											onclick={() => insertDay(day.index ?? 1)}
										>
											{$t('itinerary.insert_day_before')}
										</button>
									</li>
									<li>
										<button
											type="button"
											role="menuitem"
											disabled={dayCount >= MAX_PLAN_DAYS}
											onclick={() => insertDay((day.index ?? 0) + 1)}
										>
											{$t('itinerary.insert_day_after')}
										</button>
									</li>
									<li>
										<button
											type="button"
											role="menuitem"
											disabled={dayCount >= MAX_PLAN_DAYS}
											onclick={() => duplicateDay(day)}
										>
											{$t('itinerary.duplicate_day')}
										</button>
									</li>
									<li>
										<button
											type="button"
											role="menuitem"
											disabled={day.index === 1}
											onclick={() => moveDay(day, (day.index ?? 1) - 1)}
										>
											{$t('itinerary.move_day_earlier')}
										</button>
									</li>
									<li>
										<button
											type="button"
											role="menuitem"
											disabled={day.index === dayCount}
											onclick={() => moveDay(day, (day.index ?? 0) + 1)}
										>
											{$t('itinerary.move_day_later')}
										</button>
									</li>
									<li>
										<button
											type="button"
											role="menuitem"
											class="text-error"
											disabled={dayCount <= 1}
											onclick={() => deleteDay(day)}
										>
											{$t('itinerary.delete_day')}
										</button>
									</li>
								</ul>
							</div>
						</div>
					{/if}
				</div>

				{#if logDayPromptFor === day.id}
					<form
						class="flex flex-wrap items-center gap-2"
						onsubmit={(e) => {
							e.preventDefault();
							void logDay(day, logDayDate);
						}}
					>
						<span class="text-sm">{$t('itinerary.visit_date')}</span>
						<div class="join">
							<input
								type="date"
								class="input input-sm join-item"
								bind:value={logDayDate}
								required
							/>
							<button
								type="submit"
								class="btn btn-sm btn-primary join-item"
								disabled={loggingDay === day.id}
							>
								{$t('itinerary.log_day')}
							</button>
							<button
								type="button"
								class="btn btn-sm btn-ghost join-item"
								aria-label={$t('about.close')}
								onclick={() => (logDayPromptFor = null)}
							>
								<Close class="h-4 w-4" />
							</button>
						</div>
					</form>
				{/if}

				{#if carried.length > 0}
					<div class="flex flex-col gap-2">
						{#each carried as row (row.id)}
							{@render planRow(row, { draggable: false, projected: anchored, continuation: true })}
						{/each}
					</div>
				{/if}

				{@render zone(
					key,
					rows,
					anchored,
					carried.length > 0 ? $t('itinerary.drop_plans_here') : $t('itinerary.no_plans_for_day')
				)}
			</div>
		</section>
	{/each}

	{#if canModify}
		<div class="flex justify-center">
			<button
				type="button"
				class="btn btn-outline gap-2"
				disabled={dayCount >= MAX_PLAN_DAYS}
				onclick={() => insertDay()}
			>
				<Plus class="h-5 w-5" />
				{$t('itinerary.add_day')}
			</button>
		</div>
	{/if}
</div>

{#if destinationPrompt}
	<div class="modal modal-open" role="dialog" aria-modal="true">
		<div class="modal-box max-w-md">
			<h3 class="text-lg font-bold">{$t('itinerary.destination_title')}</h3>
			<p class="mt-1 text-sm opacity-80">
				{destinationPrompt.kind === 'delete'
					? $t('itinerary.destination_desc_day', { values: { count: destinationPrompt.count } })
					: $t('itinerary.destination_desc_days', {
							values: { days: destinationPrompt.dayIndexes.join(', ') }
						})}
			</p>
			<form class="mt-4 space-y-4" onsubmit={resolveDestination}>
				<select class="select w-full" bind:value={destinationChoice}>
					<option value="ideas">{$t('itinerary.ideas')}</option>
					{#each destinationDays as day (day.id)}
						<option value={day.id}>{dayTitle(day)}</option>
					{/each}
				</select>
				<div class="modal-action">
					<button type="button" class="btn btn-ghost" onclick={() => (destinationPrompt = null)}>
						{$t('about.close')}
					</button>
					<button type="submit" class="btn btn-primary" disabled={saving}>
						{$t('itinerary.apply')}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

{#if placementEdit}
	<DayPlacementModal
		mode={placementEdit.mode}
		row={placementEdit.row}
		{days}
		{dateFormat}
		initialDayIndex={placementEdit.dayIndex}
		onSave={savePlacement}
		onClose={() => (placementEdit = null)}
	/>
{/if}

{#if pickerTarget}
	<DayItemPickerModal
		{collection}
		title={`${$t('itinerary.add_existing')} · ${pickerTarget.title}`}
		types={pickerTarget.isGlobal ? ['note', 'checklist'] : undefined}
		{placementLabels}
		onPick={pickExisting}
		onClose={() => (pickerTarget = null)}
	/>
{/if}

{#if openModal === 'location'}
	<LocationModal
		on:close={closeLocationModal}
		on:quickAddCreated={(e) => handleQuickAdd('location', e)}
		{user}
		locationToEdit={locationToEdit ?? undefined}
		bind:location={locationDraft}
		{collection}
		initialVisitDate={null}
	/>
{/if}

{#if openModal === 'lodging'}
	<LodgingModal
		on:close={closeLodgingModal}
		on:quickAddCreated={(e) => handleQuickAdd('lodging', e)}
		{user}
		{lodgingToEdit}
		bind:lodging={lodgingDraft}
		{collection}
		initialVisitDate={lodgingToEdit ? null : createDate}
	/>
{/if}

{#if openModal === 'transportation'}
	<TransportationModal
		on:close={closeTransportationModal}
		{user}
		transportationToEdit={transportationToEdit ?? undefined}
		bind:transportation={transportationDraft}
		{collection}
		initialVisitDate={transportationToEdit ? null : createDate}
	/>
{/if}

{#if openModal === 'note'}
	<NoteModal
		on:close={finishModal}
		{collection}
		{user}
		note={noteToEdit}
		on:create={(e) => void handleNoteSaved('note', e.detail, true)}
		on:save={(e) => void handleNoteSaved('note', e.detail, false)}
		initialVisitDate={noteToEdit ? null : createDate}
	/>
{/if}

{#if openModal === 'checklist'}
	<ChecklistModal
		on:close={finishModal}
		{collection}
		{user}
		checklist={checklistToEdit}
		on:create={(e) => void handleNoteSaved('checklist', e.detail, true)}
		on:save={(e) => void handleNoteSaved('checklist', e.detail, false)}
		initialVisitDate={checklistToEdit ? null : createDate}
	/>
{/if}
