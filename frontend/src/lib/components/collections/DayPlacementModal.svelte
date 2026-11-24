<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { CollectionItineraryDay } from '#lib/types.js';
	import { formatDisplayDate, type DateFormatPreference } from '#lib/dateFormat.js';
	import {
		clockValue,
		GLOBAL_TYPES,
		SPAN_TYPES,
		type PlacementPayload,
		type PlanRow,
		dayPinColor
	} from '#lib/collections/plan.js';
	import Close from '~icons/mdi/close';
	import CalendarPlus from '~icons/mdi/calendar-plus';
	import MapMarker from '~icons/mdi/map-marker';
	import LightbulbOutline from '~icons/mdi/lightbulb-outline';
	import Earth from '~icons/mdi/earth';
	import Check from '~icons/mdi/check';
	import ChevronDown from '~icons/mdi/chevron-down';

	interface Props {
		mode: 'edit' | 'add';
		row: PlanRow;
		days: CollectionItineraryDay[];
		dateFormat: DateFormatPreference;
		initialDayIndex?: number | null;
		onSave: (payload: PlacementPayload) => Promise<boolean>;
		onClose: () => void;
	}

	let { mode, row, days, dateFormat, initialDayIndex = null, onSave, onClose }: Props = $props();

	let saving = $state(false);

	// The dialog is mounted per edit, so the form starts from the props once.
	function initialForm() {
		const item = mode === 'edit' ? row.item : null;
		const index = item ? item.day_index : initialDayIndex;
		return {
			where: item?.is_global ? 'global' : index ? `day:${index}` : 'ideas',
			index: item?.is_global ? null : (index ?? null),
			spanEnd: item?.span_end_index ?? null,
			isOptional: Boolean(item?.is_optional),
			startTime: clockValue(item?.start_time),
			endTime: clockValue(item?.end_time)
		};
	}

	const initial = initialForm();
	let where = $state(initial.where);
	let spanEnd = $state<number | null>(initial.spanEnd);
	let isOptional = $state(initial.isOptional);
	let startTime = $state(initial.startTime);
	let endTime = $state(initial.endTime);

	const dayIndex = $derived(where.startsWith('day:') ? Number(where.slice(4)) : null);
	const canSpan = $derived(Boolean(row.type && SPAN_TYPES.includes(row.type)) && dayIndex !== null);
	const canBeGlobal = $derived(Boolean(row.type && GLOBAL_TYPES.includes(row.type)));
	const laterDays = $derived(
		dayIndex === null ? [] : days.filter((d) => (d.index ?? 0) > dayIndex)
	);
	const dense = $derived(days.length > 10);
	const name = $derived(row.object && 'name' in row.object ? row.object.name : '');

	function pick(value: string) {
		if (where === value) return;
		where = value;
		handleWhereChange();
	}

	const summary = $derived.by(() => {
		if (where === 'ideas') return $t('itinerary.ideas');
		if (where === 'global') return $t('itinerary.trip_wide');
		const day = days.find((d) => d.index === dayIndex);
		return day ? dayLabel(day) : '';
	});

	function dayLabel(day: CollectionItineraryDay): string {
		const title = $t('itinerary.day_n', { values: { n: day.index } });
		const date = day.date ? formatDisplayDate(day.date, dateFormat) : '';
		return [title, date, day.name].filter(Boolean).join(' · ');
	}

	let previousIndex: number | null = initial.index;

	// Moving a span keeps its length, clamped to the last day.
	function handleWhereChange() {
		const next = dayIndex;
		if (next === null) {
			spanEnd = null;
		} else if (spanEnd !== null && previousIndex !== null) {
			const length = spanEnd - previousIndex;
			const shifted = Math.min(next + length, days.length);
			spanEnd = length > 0 && shifted > next ? shifted : null;
		}
		previousIndex = next;
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		saving = true;
		try {
			const onDay = dayIndex !== null;
			const ok = await onSave({
				day_index: dayIndex,
				is_global: where === 'global',
				span_end_index:
					canSpan && spanEnd && dayIndex !== null && spanEnd > dayIndex ? spanEnd : null,
				is_optional: where === 'global' ? false : isOptional,
				start_time: onDay && startTime ? startTime : null,
				end_time: onDay && endTime ? endTime : null
			});
			if (ok) onClose();
		} finally {
			saving = false;
		}
	}
</script>

<dialog
	class="modal modal-bottom backdrop-blur-xs sm:modal-middle"
	{@attach (node) => node.showModal()}
	onclose={onClose}
>
	<div
		class="modal-box flex max-h-[90dvh] w-full max-w-lg flex-col overflow-hidden rounded-t-3xl border border-base-300 bg-base-100 p-0 shadow-2xl sm:rounded-3xl"
		role="dialog"
		aria-labelledby="placement-title"
	>
		<form class="flex min-h-0 flex-1 flex-col" onsubmit={submit}>
			<header class="flex items-start gap-3 px-5 pt-5 pb-3">
				<div class="shrink-0 rounded-2xl bg-primary/10 p-2.5 text-primary">
					<CalendarPlus class="h-6 w-6" />
				</div>
				<div class="min-w-0 flex-1">
					<p
						id="placement-title"
						class="text-xs font-semibold tracking-wide text-base-content/60 uppercase"
					>
						{mode === 'add' ? $t('itinerary.add_to_plan') : $t('itinerary.edit_placement')}
					</p>
					{#if name}
						<h1 class="truncate text-xl leading-tight font-bold">{name}</h1>
					{/if}
				</div>
				<button
					type="button"
					class="btn btn-ghost btn-circle btn-sm shrink-0"
					aria-label={$t('about.close')}
					onclick={onClose}
				>
					<Close class="h-5 w-5" />
				</button>
			</header>

			<div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 pb-4">
				<section class="space-y-2">
					<h2 class="flex items-center gap-1.5 text-sm font-semibold text-base-content/70">
						<MapMarker class="h-4 w-4" />
						{$t('itinerary.where')}
					</h2>

					<div class="flex flex-wrap gap-2" role="radiogroup" aria-label={$t('itinerary.where')}>
						<button
							type="button"
							role="radio"
							aria-checked={where === 'ideas'}
							class="btn btn-sm rounded-full {where === 'ideas' ? 'btn-primary' : 'btn-outline'}"
							onclick={() => pick('ideas')}
						>
							<LightbulbOutline class="h-4 w-4" />
							{$t('itinerary.ideas')}
						</button>
						{#if canBeGlobal}
							<button
								type="button"
								role="radio"
								aria-checked={where === 'global'}
								class="btn btn-sm rounded-full {where === 'global' ? 'btn-primary' : 'btn-outline'}"
								onclick={() => pick('global')}
							>
								<Earth class="h-4 w-4" />
								{$t('itinerary.trip_wide')}
							</button>
						{/if}
					</div>

					{#if days.length}
						<div
							class="grid max-h-56 gap-2 overflow-y-auto overscroll-contain p-1 {dense
								? 'grid-cols-3 sm:grid-cols-4'
								: 'grid-cols-2 sm:grid-cols-3'}"
							role="radiogroup"
							aria-label={$t('itinerary.jump_to_day')}
						>
							{#each days as day (day.id)}
								{@const selected = where === `day:${day.index}`}
								{@const color = dayPinColor(day.index ?? 1)}
								<button
									type="button"
									role="radio"
									aria-checked={selected}
									{@attach (node) => {
										if (selected) node.scrollIntoView({ block: 'nearest' });
									}}
									style="--day-color: {color}; border-color: {color}; {selected
										? `background-color: color-mix(in oklab, ${color} 18%, transparent); box-shadow: 0 0 0 2px ${color};`
										: ''}"
									class="relative flex min-w-0 flex-col items-start rounded-xl border-2 text-left transition hover:bg-base-200 {dense
										? 'px-2 py-1.5'
										: 'px-3 py-2'} {selected ? '' : 'bg-base-100 opacity-80 hover:opacity-100'}"
									onclick={() => pick(`day:${day.index}`)}
								>
									<span class="text-sm font-bold">
										{$t('itinerary.day_n', { values: { n: day.index } })}
									</span>
									<span class="w-full truncate text-xs text-base-content/70">
										{day.date
											? formatDisplayDate(day.date, dateFormat, dense ? { year: '2-digit' } : {})
											: (day.name ?? '')}
									</span>
									{#if !dense && day.date && day.name}
										<span class="w-full truncate text-xs text-base-content/50">{day.name}</span>
									{/if}
									{#if selected}
										<Check class="absolute top-1.5 right-1.5 h-4 w-4" style="color: {color}" />
									{/if}
								</button>
							{/each}
						</div>
					{/if}
				</section>

				{#if where !== 'global'}
					<details class="group rounded-xl border border-base-300 bg-base-200/40">
						<summary
							class="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-semibold"
						>
							<span>{$t('itinerary.time_and_options')}</span>
							<ChevronDown class="h-4 w-4 transition group-open:rotate-180" />
						</summary>
						<div class="space-y-4 px-4 pb-4">
							{#if canSpan}
								<label class="flex flex-col" for="placement-end">
									<span class="field-label">{$t('itinerary.ends_on')}</span>
									<select id="placement-end" class="select w-full" bind:value={spanEnd}>
										<option value={null}>{$t('itinerary.same_day')}</option>
										{#each laterDays as day (day.id)}
											<option value={day.index}>{dayLabel(day)}</option>
										{/each}
									</select>
								</label>
							{/if}

							{#if dayIndex !== null}
								<div class="grid grid-cols-2 gap-3">
									<label class="flex flex-col" for="placement-start">
										<span class="field-label">{$t('itinerary.start_time')}</span>
										<input
											id="placement-start"
											type="time"
											class="input w-full"
											bind:value={startTime}
										/>
									</label>
									<label class="flex flex-col" for="placement-end-time">
										<span class="field-label">{$t('itinerary.end_time')}</span>
										<input
											id="placement-end-time"
											type="time"
											class="input w-full"
											bind:value={endTime}
										/>
									</label>
								</div>
							{/if}

							<label class="field-toggle" for="placement-optional">
								<input
									id="placement-optional"
									type="checkbox"
									class="toggle toggle-primary"
									bind:checked={isOptional}
								/>
								<span class="font-semibold text-base-content">{$t('itinerary.mark_optional')}</span>
							</label>
						</div>
					</details>
				{/if}
			</div>

			<footer
				class="flex shrink-0 items-center justify-between gap-3 border-t border-base-300 bg-base-100 px-5 py-3"
			>
				<p class="min-w-0 truncate text-sm text-base-content/70">{summary}</p>
				<button type="submit" class="btn btn-primary shrink-0 px-6" disabled={saving}>
					{#if saving}
						<span class="loading loading-spinner loading-sm"></span>
					{/if}
					{mode === 'add' ? $t('itinerary.add_to_plan') : $t('notes.save')}
				</button>
			</footer>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button type="button" aria-label={$t('about.close')} onclick={onClose}
			>{$t('about.close')}</button
		>
	</form>
</dialog>
