<script lang="ts">
	import { t } from 'svelte-i18n';
	import { dragHandle } from 'svelte-dnd-action';
	import type { Checklist, Location, Lodging, Note, Transportation } from '$lib/types';
	import { formatDisplayTime, type DateFormatPreference } from '$lib/dateFormat';
	import { applyDropdownFlip } from '$lib/utils/flipDropdown';
	import { clockValue, recordedVisitId, type LogVisitResult, type PlanRow } from '$lib/dayPlan';
	import type { Collection } from '$lib/types';
	import MapMarker from '~icons/mdi/map-marker';
	import Bed from '~icons/mdi/bed';
	import Car from '~icons/mdi/car';
	import Airplane from '~icons/mdi/airplane';
	import Train from '~icons/mdi/train';
	import Bus from '~icons/mdi/bus';
	import Ferry from '~icons/mdi/ferry';
	import NoteText from '~icons/mdi/note-text';
	import ListChecks from '~icons/mdi/format-list-checks';
	import DotsVertical from '~icons/mdi/dots-vertical';
	import DragVertical from '~icons/mdi/drag-vertical';
	import CheckCircle from '~icons/mdi/check-circle';
	import Close from '~icons/mdi/close';
	import Plus from '~icons/mdi/plus';

	interface Props {
		row: PlanRow;
		canModify: boolean;
		dateFormat: DateFormatPreference;
		/** True when the visit date can come from the anchor, so Log visit needs no prompt. */
		hasProjectedDate: boolean;
		/** Rendered on a later day of a span; not draggable and not loggable. */
		continuation?: boolean;
		draggable?: boolean;
		readMode?: boolean;
		collection?: Collection;
		onLogVisit?: (row: PlanRow, date?: string) => Promise<LogVisitResult>;
		onEditObject?: (row: PlanRow) => void;
		onEditPlacement?: (row: PlanRow) => void;
		onToggleOptional?: (row: PlanRow) => void;
		onAddAgain?: (row: PlanRow) => void;
		onRemove?: (row: PlanRow) => void;
		onAddToPlan?: (row: PlanRow) => void;
	}

	let {
		row,
		canModify,
		dateFormat,
		hasProjectedDate,
		continuation = false,
		draggable = false,
		readMode = false,
		collection,
		onLogVisit,
		onEditObject,
		onEditPlacement,
		onToggleOptional,
		onAddAgain,
		onRemove,
		onAddToPlan
	}: Props = $props();

	let askingDate = $state(false);
	let visitDate = $state(new Date().toISOString().slice(0, 10));
	let logging = $state(false);

	const item = $derived(row.item);
	const name = $derived(
		(row.object && 'name' in row.object ? row.object.name : '') || $t('itinerary.item_not_found')
	);
	const href = $derived.by(() => {
		if (!row.object) return null;
		if (row.type === 'location') return `/locations/${row.objectId}`;
		if (row.type === 'lodging') return `/lodging/${row.objectId}`;
		if (row.type === 'transportation') return `/transportations/${row.objectId}`;
		return null;
	});
	const secondary = $derived.by(() => {
		const obj = row.object;
		if (!obj) return null;
		if (row.type === 'location') return (obj as Location).location ?? null;
		if (row.type === 'lodging') return (obj as Lodging).location ?? null;
		if (row.type === 'transportation') {
			const transport = obj as Transportation;
			const parts = [transport.from_location, transport.to_location].filter(Boolean);
			return parts.length ? parts.join(' → ') : null;
		}
		if (row.type === 'note') {
			const content = (obj as Note).content?.trim();
			return content ? content.slice(0, 120) : null;
		}
		if (row.type === 'checklist') {
			const items = (obj as Checklist).items ?? [];
			if (!items.length) return null;
			return `${items.filter((entry) => entry.is_checked).length}/${items.length}`;
		}
		return null;
	});
	const categoryIcon = $derived(
		row.type === 'location' ? ((row.object as Location | null)?.category?.icon ?? null) : null
	);
	const transportType = $derived(
		row.type === 'transportation' ? ((row.object as Transportation | null)?.type ?? '') : ''
	);
	const spanLabel = $derived.by(() => {
		if (!item?.day_index || !item.span_end_index || item.span_end_index <= item.day_index) {
			return null;
		}
		return $t('itinerary.span', { values: { start: item.day_index, end: item.span_end_index } });
	});
	const timeLabel = $derived.by(() => {
		const start = clockValue(item?.start_time);
		const end = clockValue(item?.end_time);
		if (!start && !end) return null;
		const parts = [start, end].filter(Boolean).map((value) => formatDisplayTime(value, dateFormat));
		return parts.join(' – ');
	});
	const recordedVisit = $derived(
		row.type === 'location' && collection
			? recordedVisitId(collection, item)
			: (item?.logged_visit ?? null)
	);
	const canLog = $derived(
		canModify && !continuation && row.type === 'location' && Boolean(item) && !recordedVisit
	);
	const isVisited = $derived(row.type === 'location' && Boolean(recordedVisit));

	async function logVisit(date?: string) {
		if (!onLogVisit || logging) return;
		logging = true;
		try {
			const result = await onLogVisit(row, date);
			if (result === 'date_required') {
				askingDate = true;
			} else if (result === 'ok') {
				askingDate = false;
			}
		} finally {
			logging = false;
		}
	}

	function handleLogClick() {
		if (hasProjectedDate) {
			void logVisit();
		} else {
			askingDate = true;
		}
	}

	function confirmDate(event: SubmitEvent) {
		event.preventDefault();
		if (visitDate) void logVisit(visitDate);
	}
</script>

<div
	id={!continuation && row.type
		? `plan-${row.type}-${row.objectId}-day-${item?.day_index ?? 'ideas'}`
		: undefined}
	class={[
		'flex items-center gap-2 rounded-xl border px-3 py-2.5',
		continuation
			? 'border-dashed border-base-300 bg-base-100/70'
			: 'border-base-300/80 bg-base-100 shadow-sm'
	]}
>
	<div class={['flex min-w-0 flex-1 items-center gap-2', item?.is_optional && 'opacity-80']}>
		{#if draggable && canModify}
			<span
				use:dragHandle
				class="flex h-8 w-6 shrink-0 items-center justify-center rounded text-base-content/40 hover:text-base-content"
				aria-label={$t('itinerary.drag_to_reorder')}
				title={$t('itinerary.drag_to_reorder')}
			>
				<DragVertical class="h-5 w-5" />
			</span>
		{/if}

		<div
			class={[
				'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
				row.type === 'lodging' && 'bg-info/15 text-info',
				row.type === 'transportation' && 'bg-secondary/15 text-secondary',
				row.type === 'location' && 'bg-primary/15 text-primary',
				(row.type === 'note' || row.type === 'checklist') && 'bg-base-300 text-base-content'
			]}
		>
			{#if row.type === 'location'}
				{#if categoryIcon}
					<span class="text-base leading-none">{categoryIcon}</span>
				{:else}
					<MapMarker class="h-4 w-4" />
				{/if}
			{:else if row.type === 'lodging'}
				<Bed class="h-4 w-4" />
			{:else if row.type === 'transportation'}
				{#if transportType === 'plane'}
					<Airplane class="h-4 w-4" />
				{:else if transportType === 'train'}
					<Train class="h-4 w-4" />
				{:else if transportType === 'bus'}
					<Bus class="h-4 w-4" />
				{:else if transportType === 'boat'}
					<Ferry class="h-4 w-4" />
				{:else}
					<Car class="h-4 w-4" />
				{/if}
			{:else if row.type === 'note'}
				<NoteText class="h-4 w-4" />
			{:else}
				<ListChecks class="h-4 w-4" />
			{/if}
		</div>

		<div class="min-w-0 flex-1">
			<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
				{#if href}
					<a {href} class="truncate font-semibold hover:text-primary">{name}</a>
				{:else if onEditObject && row.object}
					<button
						type="button"
						class="truncate text-left font-semibold hover:text-primary"
						onclick={() => onEditObject?.(row)}
					>
						{name}
					</button>
				{:else}
					<span class="truncate font-semibold">{name}</span>
				{/if}
				{#if item?.is_optional}
					<span class="badge badge-outline badge-sm">{$t('itinerary.optional')}</span>
				{/if}
				{#if timeLabel}
					<span class="badge badge-ghost badge-sm">{timeLabel}</span>
				{/if}
				{#if spanLabel}
					<span class="badge badge-info badge-outline badge-sm">{spanLabel}</span>
				{/if}
			</div>
			{#if continuation && item?.day_index}
				<p class="truncate text-xs opacity-60">
					{row.type === 'lodging'
						? $t('itinerary.staying_overnight')
						: $t('itinerary.continues_from', { values: { n: item.day_index } })}
				</p>
			{:else if secondary}
				<p class="truncate text-xs opacity-60">{secondary}</p>
			{/if}
		</div>
	</div>

	<div class="flex shrink-0 items-center gap-1">
		{#if isVisited}
			<a
				href={`/locations/${row.objectId}#visit-${recordedVisit}`}
				class="badge badge-success gap-1 px-2 py-3 font-medium"
			>
				<CheckCircle class="h-3.5 w-3.5" />
				{$t('itinerary.visited')}
			</a>
		{:else if canLog && askingDate}
			<form class="join" onsubmit={confirmDate}>
				<input
					type="date"
					class="input input-sm join-item w-36"
					bind:value={visitDate}
					aria-label={$t('itinerary.visit_date')}
					required
				/>
				<button type="submit" class="btn btn-sm btn-primary join-item" disabled={logging}>
					{#if logging}
						<span class="loading loading-spinner loading-xs"></span>
					{/if}
					{$t('itinerary.log')}
				</button>
				<button
					type="button"
					class="btn btn-sm btn-ghost join-item"
					aria-label={$t('about.close')}
					onclick={() => (askingDate = false)}
				>
					<Close class="h-4 w-4" />
				</button>
			</form>
		{:else if canLog}
			<button
				type="button"
				class="btn btn-sm btn-ghost"
				disabled={logging}
				onclick={handleLogClick}
			>
				{#if logging}
					<span class="loading loading-spinner loading-xs"></span>
				{/if}
				{$t('itinerary.log_visit')}
			</button>
		{/if}

		{#if canModify && !readMode && !item && onAddToPlan}
			<button type="button" class="btn btn-sm btn-ghost gap-1" onclick={() => onAddToPlan?.(row)}>
				<Plus class="h-4 w-4" />
				<span class="hidden sm:inline">{$t('itinerary.add_to_plan')}</span>
			</button>
		{/if}

		{#if canModify && !readMode && (item || onEditObject)}
			<div
				class="dropdown dropdown-end relative z-50 focus-within:z-[200]"
				role="group"
				onpointerdown={(e) => applyDropdownFlip(e.currentTarget)}
			>
				<div
					tabindex="0"
					role="button"
					class="btn btn-sm btn-ghost btn-square"
					aria-label={$t('itinerary.item_actions')}
					title={$t('itinerary.item_actions')}
				>
					<DotsVertical class="h-4 w-4" />
				</div>
				<ul
					tabindex="-1"
					class="dropdown-content menu z-[9999] w-56 rounded-box border border-base-300 bg-base-100 p-2 shadow-lg max-h-[min(24rem,calc(100vh-2rem))] overflow-y-auto"
					role="menu"
				>
					{#if row.object && onEditObject}
						<li>
							<button type="button" role="menuitem" onclick={() => onEditObject?.(row)}>
								{$t('itinerary.edit_details')}
							</button>
						</li>
					{/if}
					{#if item}
						<li>
							<button type="button" role="menuitem" onclick={() => onEditPlacement?.(row)}>
								{$t('itinerary.edit_placement')}
							</button>
						</li>
						{#if !continuation && !item.is_global}
							<li>
								<button type="button" role="menuitem" onclick={() => onToggleOptional?.(row)}>
									{item.is_optional ? $t('itinerary.mark_required') : $t('itinerary.mark_optional')}
								</button>
							</li>
						{/if}
						{#if row.type === 'location'}
							<li>
								<button type="button" role="menuitem" onclick={() => onAddAgain?.(row)}>
									{$t('itinerary.add_again')}
								</button>
							</li>
						{/if}
						<li>
							<button
								type="button"
								role="menuitem"
								class="text-error"
								onclick={() => onRemove?.(row)}
							>
								{$t('itinerary.remove_from_plan')}
							</button>
						</li>
					{/if}
				</ul>
			</div>
		{/if}
	</div>
</div>
