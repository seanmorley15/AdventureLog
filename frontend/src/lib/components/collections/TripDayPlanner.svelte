<script lang="ts">
	import { t } from 'svelte-i18n';
	import { flip } from 'svelte/animate';
	import type { Attachment } from 'svelte/attachments';
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
	} from '#lib/types.js';
	import { addToast } from '#lib/toasts.js';
	import { unlinkLocationFromCollection } from '#lib/collection-membership.js';
	import { dateFormatFromUser, formatDisplayDate } from '#lib/dateFormat.js';
	import { applyDropdownFlip } from '#lib/utils/flipDropdown.js';
	import { createEmptyLocation } from '#lib/location-draft.js';
	import {
		addDays,
		browserTimezone,
		daysBetween,
		errorMessage,
		findObject,
		dayPinColor,
		indexedDays,
		recordedVisitId,
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
	} from '#lib/collections/plan.js';
	import DayPlanRow from './DayPlanRow.svelte';
	import DayFileDialog from './DayFileDialog.svelte';
	import DayFileRows from './DayFileRows.svelte';
	import DayPlacementModal from './DayPlacementModal.svelte';
	import type { LinkScope } from './LinkItemsModal.svelte';
	import LocationModal from '#lib/components/locations/LocationModal.svelte';
	import LodgingModal from '#lib/components/lodging/LodgingModal.svelte';
	import TransportationModal, {
		createEmptyTransportation
	} from '#lib/components/transportation/TransportationModal.svelte';
	import NoteModal from '#lib/components/NoteModal.svelte';
	import ChecklistModal from '#lib/components/ChecklistModal.svelte';
	import Plus from '~icons/mdi/plus';
	import RenameOutline from '~icons/mdi/rename-outline';
	import TextBoxOutline from '~icons/mdi/text-box-outline';
	import DotsVertical from '~icons/mdi/dots-vertical';
	import Lightbulb from '~icons/mdi/lightbulb-outline';
	import Earth from '~icons/mdi/earth';
	import CalendarEdit from '~icons/mdi/calendar-edit';
	import CalendarArrowRight from '~icons/mdi/calendar-arrow-right';
	import CheckAll from '~icons/mdi/check-all';
	import Close from '~icons/mdi/close';

	interface Props {
		collection: Collection;
		user: any;
		canModify?: boolean;
		/** Read keeps Log visit and hides drag, Add, and reorder. */
		readMode?: boolean;
		selectedDay?: number | null;
		onSelectDay?: (dayIndex: number) => void;
		onHighlightDay?: (dayIndex: number | null) => void;
		onOpenLink?: (scope: LinkScope) => void;
	}

	let {
		collection = $bindable(),
		user,
		canModify = false,
		readMode = false,
		selectedDay = null,
		onSelectDay,
		onHighlightDay,
		onOpenLink
	}: Props = $props();

	const planning = $derived(canModify && !readMode);

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

	function dayTitle(day: CollectionItineraryDay): string {
		return $t('itinerary.day_n', { values: { n: day.index } });
	}

	function shortDayDate(iso: string): string {
		return new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, {
			weekday: 'short',
			month: 'short',
			day: 'numeric'
		});
	}

	let sectionsRoot: HTMLElement | null = $state(null);
	let jumpNav: HTMLElement | null = $state(null);
	let activeSection = $state('ideas');

	function nearestScroller(node: HTMLElement): HTMLElement | null {
		let current: HTMLElement | null = node.parentElement;
		while (current) {
			const overflow = getComputedStyle(current).overflowY;
			if (overflow === 'auto' || overflow === 'scroll') return current;
			current = current.parentElement;
		}
		return null;
	}

	function jumpLabel(id: string): string {
		if (id === 'ideas') return $t('itinerary.ideas');
		if (id === 'global') return $t('itinerary.trip_wide');
		const day = days.find((entry) => String(entry.index) === id);
		if (!day) return id;
		const date = day.date ? formatDisplayDate(day.date, dateFormat) : '';
		return [dayTitle(day), date, day.name].filter(Boolean).join(' · ');
	}

	function revealInRail(id: string) {
		const nav = jumpNav;
		const button = nav?.querySelector(`[data-jump="${id}"]`);
		if (!nav || !(button instanceof HTMLElement)) return;
		const navRect = nav.getBoundingClientRect();
		const buttonRect = button.getBoundingClientRect();
		if (buttonRect.top < navRect.top) nav.scrollTop -= navRect.top - buttonRect.top + 4;
		else if (buttonRect.bottom > navRect.bottom)
			nav.scrollTop += buttonRect.bottom - navRect.bottom + 4;
	}

	let jumpFrame = 0;

	function scrollPlannerTo(scroller: HTMLElement, top: number) {
		cancelAnimationFrame(jumpFrame);
		const start = scroller.scrollTop;
		const distance = top - start;
		if (Math.abs(distance) < 2) {
			scroller.scrollTop = top;
			return;
		}
		const duration = 280;
		const started = performance.now();
		const step = (now: number) => {
			const progress = Math.min(1, (now - started) / duration);
			const eased = 1 - (1 - progress) ** 3;
			scroller.scrollTop = start + distance * eased;
			if (progress < 1) jumpFrame = requestAnimationFrame(step);
		};
		jumpFrame = requestAnimationFrame(step);
	}

	function jumpTo(id: string) {
		const section = document.getElementById(`plan-section-${id}`);
		const scroller = sectionsRoot ? nearestScroller(sectionsRoot) : null;
		if (!section) return;
		activeSection = id;
		revealInRail(id);
		if (!scroller) {
			section.scrollIntoView({ behavior: 'smooth', block: 'start' });
			return;
		}
		const top =
			section.getBoundingClientRect().top -
			scroller.getBoundingClientRect().top +
			scroller.scrollTop -
			8;
		scrollPlannerTo(scroller, top);
	}

	const trackSections: Attachment = (node) => {
		sectionsRoot = node;
		const scroller = nearestScroller(node);
		let frame = 0;
		const update = () => {
			const anchor = (scroller?.getBoundingClientRect().top ?? 0) + 56;
			const sections = node.querySelectorAll<HTMLElement>('[data-plan-section]');
			const atEnd =
				scroller != null && scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8;
			let current = sections[0]?.dataset.planSection ?? 'ideas';
			if (atEnd && sections.length > 0) {
				current = sections[sections.length - 1].dataset.planSection ?? current;
			} else {
				for (const section of sections) {
					if (section.getBoundingClientRect().top <= anchor) {
						current = section.dataset.planSection ?? current;
					}
				}
			}
			if (current !== activeSection) {
				activeSection = current;
				revealInRail(current);
			}
		};
		const onScroll = () => {
			cancelAnimationFrame(frame);
			frame = requestAnimationFrame(update);
		};
		update();
		const target: HTMLElement | Window = scroller ?? window;
		target.addEventListener('scroll', onScroll, { passive: true });
		return () => {
			cancelAnimationFrame(frame);
			if (sectionsRoot === node) sectionsRoot = null;
			target.removeEventListener('scroll', onScroll);
		};
	};

	const fitRail: Attachment = (node) => {
		jumpNav = node;
		const scroller = nearestScroller(node);
		const apply = () => {
			const height = Math.max(160, (scroller?.clientHeight ?? window.innerHeight) - 24);
			node.style.maxHeight = `${height}px`;
		};
		apply();
		const observer = new ResizeObserver(apply);
		if (scroller) observer.observe(scroller);
		window.addEventListener('resize', apply);
		return () => {
			observer.disconnect();
			if (jumpNav === node) jumpNav = null;
			window.removeEventListener('resize', apply);
		};
	};

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
			const byId = new Map((location.visits ?? []).map((visit) => [visit.id, visit]));
			for (const visit of added) byId.set(visit.id, visit);
			return {
				...location,
				visits: [...byId.values()],
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
			transportations: state.transportations,
			day_activities: state.day_activities ?? collection.day_activities,
			day_trails: state.day_trails ?? collection.day_trails,
			day_images: state.day_images ?? collection.day_images
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
		if (Date.now() - lastFetchAt > 60_000) void refetch(true);
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
		const res = await send(`/api/collections/${collection.id}/itinerary-items/`, 'POST', {
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

	let highlightKey = $state<string | null>(null);

	function handleConsider(key: string, event: CustomEvent<DndEvent<PlanRow>>) {
		dragging = true;
		zones = { ...zones, [key]: event.detail.items };
		if (event.detail.items.some(isShadow)) {
			highlightKey = key;
			onHighlightDay?.(zoneDayIndex(key));
		}
	}

	function handleFinalize(key: string, event: CustomEvent<DndEvent<PlanRow>>) {
		highlightKey = null;
		onHighlightDay?.(null);
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
		}>(`/api/collections/${collection.id}/itinerary/reorder/`, 'POST', { items: entries });
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
			dragDisabled: !planning,
			delayTouchStart: 250,
			dropTargetStyle: {},
			dropTargetClasses: ['ring-2', 'ring-primary', 'rounded-lg']
		};
	}

	// ---------------------------------------------------------------- rows

	async function logVisit(row: PlanRow, date?: string): Promise<LogVisitResult> {
		const res = await send<{ item: CollectionItineraryItem; visit: Visit }>(
			`/api/collections/${collection.id}/itinerary-items/${row.id}/log-visit/`,
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
		const res = await send(
			`/api/collections/${collection.id}/itinerary-items/${row.id}/`,
			'PATCH',
			{
				is_optional: !row.item.is_optional
			}
		);
		if (res.ok) applyItemResponse(res.data);
	}

	async function removePlacement(row: PlanRow) {
		const res = await send(
			`/api/collections/${collection.id}/itinerary-items/${row.id}/`,
			'DELETE'
		);
		if (res.ok) removeItem(row.id);
	}

	async function removeFromCollection(row: PlanRow) {
		const placements = (collection.itinerary ?? []).filter(
			(item) => String(item.object_id) === String(row.objectId)
		).length;
		if (
			placements > 1 &&
			!confirm(
				$t('collection.unlink_plan_warning', {
					values: { days: String(placements), name: collection.name }
				})
			)
		) {
			return;
		}
		const removed = await unlinkLocationFromCollection(row.objectId, collection.id);
		if (removed === null) {
			addToast('error', $t('adventures.collection_remove_location_error'));
			return;
		}
		collection = {
			...collection,
			locations: (collection.locations ?? []).filter(
				(item) => String(item.id) !== String(row.objectId)
			),
			itinerary: (collection.itinerary ?? []).filter(
				(item) => String(item.object_id) !== String(row.objectId)
			)
		};
		addToast('info', $t('adventures.collection_remove_location_success'));
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
		const res = await send(
			`/api/collections/${collection.id}/itinerary-items/${item.id}/`,
			'PATCH',
			body
		);
		if (res.ok) applyItemResponse(res.data);
		return res.ok;
	}

	// ---------------------------------------------------------------- day actions

	type DestinationPrompt =
		| { kind: 'delete'; day: CollectionItineraryDay; count: number }
		| { kind: 'duration'; body: Record<string, unknown>; dayIndexes: number[]; keep: number };

	let destinationPrompt = $state<DestinationPrompt | null>(null);
	let destinationChoice = $state('ideas');

	/** Where each day-plan change goes: `days/...` act on one day, the rest on the whole plan. */
	function dayActionRequest(
		action: string,
		body: Record<string, unknown>
	): [string, 'POST' | 'DELETE', Record<string, unknown> | undefined] {
		const base = `/api/collections/${collection.id}`;
		const { day, ...rest } = body;
		switch (action) {
			case 'days/insert':
				return [`${base}/days/`, 'POST', rest];
			case 'days/duplicate':
				return [`${base}/days/${day}/duplicate/`, 'POST', rest];
			case 'days/move':
				return [`${base}/days/${day}/move/`, 'POST', rest];
			case 'days/delete': {
				const query = new URLSearchParams(rest as Record<string, string>).toString();
				return [`${base}/days/${day}/${query ? `?${query}` : ''}`, 'DELETE', undefined];
			}
			default:
				return [`${base}/itinerary/${action}/`, 'POST', rest];
		}
	}

	async function dayAction(action: string, body: Record<string, unknown>, quiet = false) {
		const [url, method, payload] = dayActionRequest(action, body);
		const res = await send<DayPlanState>(url, method, payload, quiet);
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
		shiftingDates = false;
		editingDuration = true;
	}

	// Shift moves the anchor by whole days. Indexes and clock faces stay on the server.
	let shiftingDates = $state(false);
	let shiftDays = $state(0);
	let shiftStart = $state('');

	function openShift() {
		shiftDays = 0;
		shiftStart = collection.start_date ?? '';
		editingDuration = false;
		shiftingDates = true;
	}

	function setShiftDays(value: number) {
		shiftDays = Number.isFinite(value) ? Math.trunc(value) : 0;
		if (collection.start_date) shiftStart = addDays(collection.start_date, shiftDays);
	}

	function setShiftStart(value: string) {
		shiftStart = value;
		shiftDays = daysBetween(collection.start_date, value);
	}

	async function applyShift(event: SubmitEvent) {
		event.preventDefault();
		if (!shiftDays) {
			shiftingDates = false;
			return;
		}
		const res = await dayAction('shift', { days: shiftDays }, true);
		if (res.ok) {
			shiftingDates = false;
		} else if (res.status !== 409) {
			addToast('error', errorMessage(res.data, $t('itinerary.save_failed')));
		}
	}

	async function applyDuration(event: SubmitEvent) {
		event.preventDefault();
		if (durationCount < 1) {
			addToast('error', $t('collection.day_count_required'));
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
		const res = await send<CollectionItineraryDay>(
			`/api/collections/${collection.id}/days/${day.id}/`,
			'PATCH',
			{
				[field]: next
			}
		);
		if (res.ok) {
			collection.itinerary_days = (collection.itinerary_days ?? []).map((existing) =>
				existing.id === day.id ? res.data : existing
			);
		}
	}

	let openDayFields = $state<Record<string, boolean>>({});

	function dayFieldKey(dayId: string, field: 'name' | 'description') {
		return `${dayId}:${field}`;
	}

	function dayFieldEditing(day: CollectionItineraryDay, field: 'name' | 'description') {
		return Boolean(openDayFields[dayFieldKey(day.id, field)]);
	}

	function openDayField(dayId: string, field: 'name' | 'description') {
		openDayFields[dayFieldKey(dayId, field)] = true;
	}

	function commitDayField(
		day: CollectionItineraryDay,
		field: 'name' | 'description',
		value: string
	) {
		delete openDayFields[dayFieldKey(day.id, field)];
		saveDayField(day, field, value);
	}

	const focusField: Attachment = (node) => {
		node.focus();
	};

	// ---------------------------------------------------------------- log day

	let logDayPromptFor = $state<string | null>(null);
	let logDayDate = $state(today);
	let loggingDay = $state<string | null>(null);

	function locationStops(day: CollectionItineraryDay) {
		return (collection.itinerary ?? []).filter((item) => {
			if (placementType(item) !== 'location') return false;
			if (item.day === day.id) return true;
			return Boolean(
				item.day_index &&
				item.span_end_index &&
				day.index &&
				item.day_index <= day.index &&
				day.index <= item.span_end_index
			);
		});
	}

	function loggableCount(day: CollectionItineraryDay): number {
		const unloggedStops = (zones[dayZone(day.id)] ?? []).filter(
			(row) =>
				row.type === 'location' &&
				row.item &&
				!row.item.is_optional &&
				!recordedVisitId(collection, row.item)
		).length;
		const stops = locationStops(day);
		const unloggedActivities = stops.length
			? (collection.day_activities ?? []).filter(
					(activity) => activity.day === day.id && !activity.promoted_activity
				).length
			: 0;
		return unloggedStops + unloggedActivities;
	}

	async function logDay(day: CollectionItineraryDay, date?: string) {
		if (!anchored && !date) {
			logDayPromptFor = day.id;
			return;
		}
		loggingDay = day.id;
		try {
			const res = await send<{
				items: CollectionItineraryItem[];
				visits: Visit[];
				day_activities?: Collection['day_activities'];
				activities_need_stop?: string[];
			}>(
				`/api/collections/${collection.id}/days/${day.id}/log-visit/`,
				'POST',
				date ? { date } : {},
				true
			);
			if (res.ok) {
				upsertItems(res.data.items);
				addVisits(res.data.visits);
				if (res.data.day_activities) collection.day_activities = res.data.day_activities;
				logDayPromptFor = null;
				if (res.data.activities_need_stop?.length) {
					addToast('info', $t('itinerary.activity_needs_stop'));
				}
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
	let fileDialog = $state<{
		kind: 'trail' | 'activity' | 'photos';
		day: CollectionItineraryDay;
	} | null>(null);

	function openFile(kind: 'trail' | 'activity' | 'photos', dayIndex: number | null) {
		const day = days.find((entry) => entry.index === dayIndex);
		if (day) fileDialog = { kind, day };
	}

	let openModal = $state<PlanObjectType | null>(null);
	let createTarget = $state<CreateTarget | null>(null);
	let locationToEdit = $state<Location | null>(null);
	let lodgingToEdit = $state<Lodging | null>(null);
	let transportationToEdit = $state<Transportation | null>(null);
	let noteToEdit = $state<Note | null>(null);
	let checklistToEdit = $state<Checklist | null>(null);
	let locationDraft = $state(createEmptyLocation());
	let lodgingDraft = $state<Lodging | null>(null);
	let transportationDraft = $state<Transportation>(createEmptyTransportation());
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
		transportationDraft = createEmptyTransportation();
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
			transportationDraft = createEmptyTransportation();
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
</script>

<svelte:document onvisibilitychange={handleVisibilityChange} />

{#snippet addMenu(target: CreateTarget)}
	<div
		class="dropdown dropdown-end relative z-50 focus-within:z-[200]"
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
			class="dropdown-content menu z-[9999] w-56 rounded-box border border-base-300 bg-base-100 p-2 shadow-lg max-h-[min(24rem,calc(100vh-2rem))] overflow-y-auto"
			role="menu"
		>
			<li>
				<button
					type="button"
					role="menuitem"
					onclick={() =>
						onOpenLink?.(
							target.isGlobal
								? { kind: 'global' }
								: target.dayIndex
									? { kind: 'day', index: target.dayIndex }
									: { kind: 'ideas' }
						)}
				>
					{$t('itinerary.add_existing')}
				</button>
			</li>
			<li class="menu-title">{$t('adventures.create_new')}</li>
			{#if !target.isGlobal}
				<li>
					<button type="button" role="menuitem" onclick={() => startCreate('location', target)}>
						{$t('adventures.location')}
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
			{#if target.dayIndex}
				<li class="menu-title">{$t('itinerary.day_n', { values: { n: target.dayIndex } })}</li>
				<li>
					<button type="button" role="menuitem" onclick={() => openFile('trail', target.dayIndex)}>
						{$t('itinerary.day_trail')}
					</button>
				</li>
				<li>
					<button
						type="button"
						role="menuitem"
						onclick={() => openFile('activity', target.dayIndex)}
					>
						{$t('itinerary.day_activity')}
					</button>
				</li>
				<li>
					<button type="button" role="menuitem" onclick={() => openFile('photos', target.dayIndex)}>
						{$t('itinerary.day_photos')}
					</button>
				</li>
			{/if}
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
		{readMode}
		{collection}
		onLogVisit={logVisit}
		onEditObject={editObject}
		onEditPlacement={(target) =>
			(placementEdit = { mode: 'edit', row: target, dayIndex: target.item?.day_index ?? null })}
		onToggleOptional={toggleOptional}
		onAddAgain={(target) => (placementEdit = { mode: 'add', row: target, dayIndex: null })}
		onRemove={removePlacement}
		onRemoveFromCollection={removeFromCollection}
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
					{@render planRow(row, { draggable: planning, projected })}
				</div>
			{/each}
		</div>
		{#if rows.length === 0}
			<p
				class="pointer-events-none absolute inset-0 flex items-center justify-center rounded-xl border border-dashed border-base-300 bg-base-100/40 text-sm text-base-content/60"
			>
				{emptyText}
			</p>
		{/if}
	</div>
{/snippet}

<div class="flex gap-2">
	<div class="plan-sections min-w-0 flex-1 space-y-4" {@attach trackSections}>
		<!-- Trip summary and duration -->
		<div class="rounded-xl bg-base-200 px-3 py-1.5">
			<div class="flex min-h-8 items-center gap-2">
				<p class="min-w-0 truncate text-sm">
					<span class="font-medium tabular-nums">{dayCount}</span>
					<span class="text-base-content/70"> {$t('itinerary.days_label')}</span>
					<span class="mx-1.5 text-base-content/30" aria-hidden="true">·</span>
					{#if anchored}
						<span class="text-base-content/70">
							{formatDisplayDate(collection.start_date, dateFormat)} – {formatDisplayDate(
								collection.end_date,
								dateFormat
							)}
						</span>
					{:else}
						<span class="text-base-content/50">{$t('itinerary.dates_not_set')}</span>
					{/if}
				</p>
				{#if anchored && collection.timezone && collection.timezone !== 'UTC'}
					<span class="hidden shrink-0 text-xs text-base-content/45 sm:inline">
						{$t('itinerary.times_in', { values: { zone: collection.timezone } })}
					</span>
				{/if}
				<div class="ml-auto flex shrink-0 items-center">
					{#if saving}
						<span class="loading loading-spinner loading-xs opacity-70"></span>
					{/if}
					{#if planning && anchored}
						<button
							type="button"
							class="btn btn-sm btn-square btn-ghost tooltip tooltip-bottom"
							aria-label={$t('itinerary.shift_dates')}
							aria-expanded={shiftingDates}
							data-tip={$t('itinerary.shift_dates')}
							onclick={() => (shiftingDates ? (shiftingDates = false) : openShift())}
						>
							{#if shiftingDates}
								<Close class="h-4 w-4" />
							{:else}
								<CalendarArrowRight class="h-4 w-4" />
							{/if}
						</button>
					{/if}
					{#if planning}
						<button
							type="button"
							class="btn btn-sm btn-square btn-ghost tooltip tooltip-bottom"
							aria-label={$t('itinerary.edit_days')}
							aria-expanded={editingDuration}
							data-tip={$t('itinerary.edit_days')}
							onclick={() => (editingDuration ? (editingDuration = false) : openDuration())}
						>
							{#if editingDuration}
								<Close class="h-4 w-4" />
							{:else}
								<CalendarEdit class="h-4 w-4" />
							{/if}
						</button>
					{/if}
				</div>
			</div>

			{#if editingDuration}
				<form
					class="mt-1.5 flex flex-wrap items-end gap-2 border-t border-base-300/70 pt-2"
					onsubmit={applyDuration}
				>
					<label class="flex flex-col gap-1">
						<span class="text-xs text-base-content/60">{$t('itinerary.days_label')}</span>
						<input
							type="number"
							class="input input-xs w-20 bg-base-100"
							min="1"
							bind:value={durationCount}
							required
						/>
					</label>
					<label class="flex flex-col gap-1">
						<span class="text-xs text-base-content/60">{$t('itinerary.start_date_optional')}</span>
						<input type="date" class="input input-xs w-40 bg-base-100" bind:value={durationStart} />
					</label>
					<button type="submit" class="btn btn-xs btn-primary" disabled={saving}>
						{$t('itinerary.apply')}
					</button>
				</form>
			{/if}

			{#if shiftingDates}
				<form
					class="mt-1.5 flex flex-wrap items-end gap-2 border-t border-base-300/70 pt-2"
					onsubmit={applyShift}
				>
					<label class="flex flex-col gap-1">
						<span class="text-xs text-base-content/60">{$t('itinerary.shift_by_days')}</span>
						<input
							type="number"
							class="input input-xs w-20 bg-base-100"
							step="1"
							value={shiftDays}
							oninput={(e) => setShiftDays(e.currentTarget.valueAsNumber)}
						/>
					</label>
					<label class="flex flex-col gap-1">
						<span class="text-xs text-base-content/60">{$t('itinerary.new_start_date')}</span>
						<input
							type="date"
							class="input input-xs w-40 bg-base-100"
							value={shiftStart}
							required
							oninput={(e) => setShiftStart(e.currentTarget.value)}
						/>
					</label>
					<button type="submit" class="btn btn-xs btn-primary" disabled={saving || !shiftDays}>
						{$t('itinerary.shift')}
					</button>
					<p class="w-full text-xs text-base-content/60">{$t('itinerary.shift_dates_hint')}</p>
				</form>
			{/if}
		</div>

		<!-- Trip-wide notes and checklists -->
		{#if zones.global.length > 0 || planning}
			<section
				id="plan-section-global"
				data-plan-section="global"
				class="card bg-base-200 shadow-xl"
			>
				<div class="card-body gap-3 p-4 sm:p-5">
					<div class="flex items-center gap-3">
						<Earth class="h-5 w-5 text-primary" />
						<div class="min-w-0 flex-1">
							<h3 class="text-lg font-bold">{$t('itinerary.trip_wide')}</h3>
							<p class="text-sm opacity-70">{$t('itinerary.trip_wide_desc')}</p>
						</div>
						{#if planning}
							{@render addMenu({ dayIndex: null, isGlobal: true })}
						{/if}
					</div>
					{@render zone('global', zones.global, false, $t('itinerary.no_trip_context_items'))}
				</div>
			</section>
		{/if}

		<!-- Ideas -->
		<section
			id="plan-section-ideas"
			data-plan-section="ideas"
			class="card bg-base-200 shadow-xl"
			class:ring-2={highlightKey === 'ideas'}
			class:ring-primary={highlightKey === 'ideas'}
		>
			<div class="card-body gap-3 p-4 sm:p-5">
				<div class="flex items-center gap-3">
					<Lightbulb class="h-5 w-5 text-warning" />
					<div class="min-w-0 flex-1">
						<h3 class="text-lg font-bold">{$t('itinerary.ideas')}</h3>
						<p class="text-sm opacity-70">{$t('itinerary.ideas_desc')}</p>
					</div>
					{#if planning}
						{@render addMenu({ dayIndex: null, isGlobal: false })}
					{/if}
				</div>
				{@render zone('ideas', zones.ideas, false, $t('itinerary.ideas_empty'))}
				<DayFileRows bind:collection day={null} {canModify} {readMode} {anchored} />
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
			<section
				id={`plan-section-${day.index}`}
				data-plan-section={String(day.index)}
				class="card bg-base-200 shadow-xl"
				class:ring-2={highlightKey === key || selectedDay === day.index}
				class:ring-primary={highlightKey === key || selectedDay === day.index}
			>
				<div class="card-body gap-3 p-4 sm:p-5">
					<div class="flex items-center gap-3">
						<div class="flex min-w-0 flex-1 items-baseline gap-x-1.5">
							<h3 class="shrink-0 text-base font-bold">
								<button
									type="button"
									class="hover:text-primary"
									onclick={() => onSelectDay?.(day.index ?? 0)}
								>
									{dayTitle(day)}
								</button>
							</h3>
							{#if planning && dayFieldEditing(day, 'name')}
								<input
									type="text"
									class="input input-xs h-7 w-40 max-w-[40%] border-base-300 bg-base-100"
									placeholder={$t('adventures.name')}
									value={day.name ?? ''}
									{@attach focusField}
									onblur={(e) => commitDayField(day, 'name', e.currentTarget.value)}
								/>
							{:else if day.name}
								<span class="text-base-content/25" aria-hidden="true">·</span>
								{#if planning}
									<button
										type="button"
										class="max-w-[34%] truncate text-left text-sm font-medium hover:text-primary"
										title={day.name}
										onclick={() => openDayField(day.id, 'name')}
									>
										{day.name}
									</button>
								{:else}
									<span class="max-w-[34%] truncate text-sm font-medium" title={day.name}
										>{day.name}</span
									>
								{/if}
							{/if}
							{#if day.date}
								<span class="text-base-content/25" aria-hidden="true">·</span>
								<span class="shrink-0 text-sm text-base-content/60">{shortDayDate(day.date)}</span>
							{/if}
							{#if planning && dayFieldEditing(day, 'description')}
								<input
									type="text"
									class="input input-xs h-7 min-w-0 flex-1 border-base-300 bg-base-100"
									placeholder={$t('itinerary.add_description')}
									value={day.description ?? ''}
									{@attach focusField}
									onblur={(e) => commitDayField(day, 'description', e.currentTarget.value)}
								/>
							{:else if day.description}
								<span class="text-base-content/25" aria-hidden="true">·</span>
								{#if planning}
									<button
										type="button"
										class="min-w-0 flex-1 truncate text-left text-sm text-base-content/60 hover:text-primary"
										title={day.description}
										onclick={() => openDayField(day.id, 'description')}
									>
										{day.description.replace(/\s+/g, ' ')}
									</button>
								{:else}
									<span
										class="min-w-0 flex-1 truncate text-sm text-base-content/60"
										title={day.description}
									>
										{day.description.replace(/\s+/g, ' ')}
									</span>
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
								{#if planning}
									{#if !day.name && !dayFieldEditing(day, 'name')}
										<button
											type="button"
											class="btn btn-sm btn-square btn-ghost tooltip tooltip-bottom"
											aria-label={$t('adventures.name')}
											data-tip={$t('adventures.name')}
											onclick={() => openDayField(day.id, 'name')}
										>
											<RenameOutline class="h-4 w-4" />
										</button>
									{/if}
									{#if !day.description && !dayFieldEditing(day, 'description')}
										<button
											type="button"
											class="btn btn-sm btn-square btn-ghost tooltip tooltip-bottom"
											aria-label={$t('itinerary.add_description')}
											data-tip={$t('itinerary.add_description')}
											onclick={() => openDayField(day.id, 'description')}
										>
											<TextBoxOutline class="h-4 w-4" />
										</button>
									{/if}
									{@render addMenu({ dayIndex: day.index ?? null, isGlobal: false })}
									<div
										class="dropdown dropdown-end relative z-50 focus-within:z-[200]"
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
											class="dropdown-content menu z-[9999] w-56 rounded-box border border-base-300 bg-base-100 p-2 shadow-lg max-h-[min(24rem,calc(100vh-2rem))] overflow-y-auto"
											role="menu"
										>
											<li>
												<button
													type="button"
													role="menuitem"
													onclick={() => insertDay(day.index ?? 1)}
												>
													{$t('itinerary.insert_day_before')}
												</button>
											</li>
											<li>
												<button
													type="button"
													role="menuitem"
													onclick={() => insertDay((day.index ?? 0) + 1)}
												>
													{$t('itinerary.insert_day_after')}
												</button>
											</li>
											<li>
												<button type="button" role="menuitem" onclick={() => duplicateDay(day)}>
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
								{/if}
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
								{@render planRow(row, {
									draggable: false,
									projected: anchored,
									continuation: true
								})}
							{/each}
						</div>
					{/if}

					{@render zone(
						key,
						rows,
						anchored,
						carried.length > 0 ? $t('itinerary.drop_plans_here') : $t('itinerary.no_plans_for_day')
					)}
					<DayFileRows
						bind:collection
						{day}
						{canModify}
						{readMode}
						{anchored}
						onLogged={(result) => {
							if (result.item) upsertItems([result.item]);
							if (result.visit) addVisits([result.visit]);
						}}
					/>
				</div>
			</section>
		{/each}

		{#if planning}
			<div class="flex justify-center">
				<button type="button" class="btn btn-outline gap-2" onclick={() => insertDay()}>
					<Plus class="h-5 w-5" />
					{$t('itinerary.add_day')}
				</button>
			</div>
		{/if}
	</div>

	{#if days.length > 0}
		<div class="w-8 shrink-0">
			<nav
				class="day-rail sticky top-2 z-30 flex w-8 flex-col items-center gap-1 overflow-x-hidden overflow-y-auto rounded-full border border-base-300 bg-base-100/90 p-1 shadow-lg backdrop-blur-lg"
				aria-label={$t('itinerary.jump_to_day')}
				{@attach fitRail}
			>
				{#if zones.global.length > 0 || planning}
					<button
						type="button"
						data-jump="global"
						class={[
							'grid h-6 w-6 shrink-0 place-items-center rounded-full text-primary',
							activeSection === 'global' ? 'bg-primary/15 ring-2 ring-primary' : 'hover:bg-base-200'
						]}
						aria-current={activeSection === 'global' ? 'true' : undefined}
						title={jumpLabel('global')}
						onmousedown={(e) => e.preventDefault()}
						onclick={() => jumpTo('global')}
					>
						<Earth class="h-3.5 w-3.5" />
					</button>
				{/if}
				<button
					type="button"
					data-jump="ideas"
					class={[
						'grid h-6 w-6 shrink-0 place-items-center rounded-full text-warning',
						activeSection === 'ideas' ? 'bg-warning/15 ring-2 ring-warning' : 'hover:bg-base-200'
					]}
					aria-current={activeSection === 'ideas' ? 'true' : undefined}
					title={jumpLabel('ideas')}
					onmousedown={(e) => e.preventDefault()}
					onclick={() => jumpTo('ideas')}
				>
					<Lightbulb class="h-3.5 w-3.5" />
				</button>
				{#each days as day (day.id)}
					{@const id = String(day.index)}
					<button
						type="button"
						data-jump={id}
						class={[
							'grid h-6 w-6 shrink-0 place-items-center rounded-full text-[10px] font-bold text-white',
							activeSection === id && 'ring-2 ring-inset ring-base-content',
							activeSection !== id && selectedDay === day.index && 'ring-2 ring-inset ring-primary'
						]}
						style:background={day.index ? dayPinColor(day.index) : undefined}
						aria-current={activeSection === id ? 'true' : undefined}
						title={jumpLabel(id)}
						onmousedown={(e) => e.preventDefault()}
						onclick={() => jumpTo(id)}
					>
						{day.index}
					</button>
				{/each}
			</nav>
		</div>
	{/if}
</div>

{#if fileDialog}
	<DayFileDialog
		bind:collection
		day={fileDialog.day}
		kind={fileDialog.kind}
		onClose={() => (fileDialog = null)}
	/>
{/if}

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

<style>
	.plan-sections {
		padding-bottom: 70vh;
		overflow-anchor: none;
	}
	.day-rail {
		scrollbar-width: none;
	}
	.day-rail::-webkit-scrollbar {
		display: none;
	}
</style>
