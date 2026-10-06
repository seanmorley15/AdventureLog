<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { CollectionItineraryDay } from '$lib/types';
	import { formatDisplayDate, type DateFormatPreference } from '$lib/dateFormat';
	import {
		clockValue,
		GLOBAL_TYPES,
		SPAN_TYPES,
		type PlacementPayload,
		type PlanRow
	} from '$lib/dayPlan';
	import Close from '~icons/mdi/close';

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

<dialog {@attach (node) => node.showModal()} class="modal" onclose={onClose}>
	<div class="modal-box max-w-md">
		<div class="mb-4 flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h3 class="text-lg font-bold">
					{mode === 'add' ? $t('itinerary.add_to_plan') : $t('itinerary.edit_placement')}
				</h3>
				{#if name}
					<p class="truncate text-sm opacity-70">{name}</p>
				{/if}
			</div>
			<button
				type="button"
				class="btn btn-sm btn-ghost btn-square"
				aria-label={$t('about.close')}
				onclick={onClose}
			>
				<Close class="h-4 w-4" />
			</button>
		</div>

		<form class="space-y-4" onsubmit={submit}>
			<label class="flex flex-col gap-1">
				<span class="field-label">{$t('itinerary.where')}</span>
				<select class="select w-full" bind:value={where} onchange={handleWhereChange}>
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
				<label class="flex flex-col gap-1">
					<span class="field-label">{$t('itinerary.ends_on')}</span>
					<select class="select w-full" bind:value={spanEnd}>
						<option value={null}>{$t('itinerary.same_day')}</option>
						{#each laterDays as day (day.id)}
							<option value={day.index}>{dayLabel(day)}</option>
						{/each}
					</select>
				</label>
			{/if}

			{#if dayIndex !== null}
				<div class="grid grid-cols-2 gap-3">
					<label class="flex flex-col gap-1">
						<span class="field-label">{$t('itinerary.start_time')}</span>
						<input type="time" class="input w-full" bind:value={startTime} />
					</label>
					<label class="flex flex-col gap-1">
						<span class="field-label">{$t('itinerary.end_time')}</span>
						<input type="time" class="input w-full" bind:value={endTime} />
					</label>
				</div>
			{/if}

			{#if where !== 'global'}
				<label class="field-toggle">
					<input type="checkbox" class="toggle toggle-primary" bind:checked={isOptional} />
					<span class="font-medium">{$t('itinerary.optional')}</span>
				</label>
			{/if}

			<div class="modal-action">
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
		<button aria-label={$t('about.close')}>close</button>
	</form>
</dialog>
