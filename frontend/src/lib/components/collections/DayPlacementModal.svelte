<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { CollectionItineraryDay } from '#lib/types.js';
	import { formatDisplayDate, type DateFormatPreference } from '#lib/dateFormat.js';
	import {
		clockValue,
		GLOBAL_TYPES,
		SPAN_TYPES,
		type PlacementPayload,
		type PlanRow
	} from '#lib/collections/plan.js';
	import Close from '~icons/mdi/close';
	import CalendarPlus from '~icons/mdi/calendar-plus';
	import MapMarker from '~icons/mdi/map-marker';

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
	const name = $derived(row.object && 'name' in row.object ? row.object.name : '');

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
	class="modal modal-bottom backdrop-blur-xs md:modal-middle"
	{@attach (node) => node.showModal()}
	onclose={onClose}
>
	<div
		class="modal-box flex w-11/12 max-w-xl flex-col overflow-hidden rounded-none border border-base-300 bg-base-100 p-0 shadow-2xl md:rounded-2xl"
		role="dialog"
		aria-labelledby="placement-title"
	>
		<div class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-3 md:px-6 md:py-4">
			<div class="flex items-center justify-between gap-3">
				<div class="flex min-w-0 items-center gap-3">
					<div class="shrink-0 rounded-xl bg-primary/10 p-2 text-primary">
						<CalendarPlus class="h-8 w-8" />
					</div>
					<div class="min-w-0">
						<h1 id="placement-title" class="truncate text-2xl font-bold text-primary md:text-3xl">
							{mode === 'add' ? $t('itinerary.add_to_plan') : $t('itinerary.edit_placement')}
						</h1>
						{#if name}
							<p class="truncate text-sm text-base-content/80">{name}</p>
						{/if}
					</div>
				</div>
				<button
					type="button"
					class="btn btn-ghost btn-square shrink-0"
					aria-label={$t('about.close')}
					onclick={onClose}
				>
					<Close class="h-5 w-5" />
				</button>
			</div>
		</div>

		<form class="flex flex-col" onsubmit={submit}>
			<div class="px-4 py-4 md:px-6 md:py-5">
				<div class="card border border-base-300 bg-base-100">
					<div class="card-body gap-4 p-6">
						<div class="mb-2 flex items-center gap-3">
							<div class="rounded-lg bg-primary/10 p-2 text-primary">
								<MapMarker class="h-5 w-5" />
							</div>
							<h2 class="text-xl font-bold">{$t('itinerary.where')}</h2>
						</div>

						<label class="flex flex-col">
							<select
								class="select w-full"
								aria-label={$t('itinerary.where')}
								bind:value={where}
								onchange={handleWhereChange}
							>
								<option value="ideas">{$t('itinerary.ideas')}</option>
								{#if canBeGlobal}
									<option value="global">{$t('itinerary.trip_wide')}</option>
								{/if}
								{#each days as day (day.id)}
									<option value={`day:${day.index}`}>{dayLabel(day)}</option>
								{/each}
							</select>
						</label>

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
							<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
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

						{#if where !== 'global'}
							<label class="field-toggle" for="placement-optional">
								<input
									id="placement-optional"
									type="checkbox"
									class="toggle toggle-primary"
									bind:checked={isOptional}
								/>
								<span class="font-semibold text-base-content">{$t('itinerary.mark_optional')}</span>
							</label>
						{/if}
					</div>
				</div>
			</div>

			<div
				class="flex shrink-0 items-center justify-end gap-2 border-t border-base-300 px-4 py-3 md:px-6"
			>
				<button type="button" class="btn btn-ghost" onclick={onClose}>{$t('about.close')}</button>
				<button type="submit" class="btn btn-primary" disabled={saving}>
					{#if saving}
						<span class="loading loading-spinner loading-sm"></span>
					{/if}
					{$t('notes.save')}
				</button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button type="button" aria-label={$t('about.close')} onclick={onClose}
			>{$t('about.close')}</button
		>
	</form>
</dialog>
