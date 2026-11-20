<script lang="ts" module>
	export type Endpoint = {
		/** Small caption above the date, e.g. Check in. */
		label: string;
		/** Short text above the caption, e.g. an airport code. */
		code?: string | null;
		/** A place name, used when there is no code. */
		place?: string | null;
		/** ISO date or datetime. */
		value?: string | null;
		timezone?: string | null;
	};
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import { t } from 'svelte-i18n';
	import { isAllDayEntry } from '#lib';
	import { formatAllDayDate, formatDateTimeParts, timezoneInfo } from '#lib/dateUtils.js';
	import type { DateFormatPreference } from '#lib/dateFormat.js';

	interface Props {
		start: Endpoint;
		end?: Endpoint | null;
		dateFormat: DateFormatPreference;
		/** What joins the two sides: a duration, a mode icon, a night count. */
		between?: Snippet;
	}

	let { start, end = null, dateFormat, between }: Props = $props();

	const zoneLabels = $derived({
		tripZone: $t('adventures.trip_timezone') ?? 'Trip TZ',
		yourTime: $t('adventures.your_time') ?? 'Your time'
	});

	function parts(endpoint: Endpoint) {
		if (!endpoint.value) return null;
		if (isAllDayEntry(endpoint.value, endpoint.timezone)) {
			return {
				date: formatAllDayDate(endpoint.value, dateFormat),
				time: '',
				zone: null as ReturnType<typeof timezoneInfo> | null
			};
		}
		const { date, time } = formatDateTimeParts(
			endpoint.value,
			endpoint.timezone ?? null,
			dateFormat
		);
		return { date, time, zone: timezoneInfo(endpoint.timezone, zoneLabels) };
	}

	let startParts = $derived(parts(start));
	let endParts = $derived(end ? parts(end) : null);
</script>

{#snippet side(endpoint: Endpoint, p: ReturnType<typeof parts>, align: 'left' | 'right')}
	<div class="min-w-0 {align === 'right' ? 'text-right' : ''}">
		{#if endpoint.code}
			<p class="truncate text-xl font-bold leading-none">{endpoint.code}</p>
		{:else if endpoint.place}
			<p class="truncate text-base font-semibold leading-tight">{endpoint.place}</p>
		{/if}
		<p
			class="text-xs font-medium text-base-content/60 {endpoint.code || endpoint.place
				? 'mt-1'
				: ''}"
		>
			{endpoint.label}
		</p>
		{#if p}
			<p class="mt-0.5 text-sm font-semibold leading-tight">{p.date}</p>
			{#if p.time}
				<p class="text-sm text-base-content/70">
					{p.time}
					{#if p.zone?.differs}
						<span
							class="tooltip badge badge-ghost badge-xs ml-1 align-middle"
							data-tip={p.zone.tip ?? undefined}>{p.zone.label}</span
						>
					{/if}
				</p>
			{/if}
		{:else}
			<p class="mt-0.5 text-sm text-base-content/40">—</p>
		{/if}
	</div>
{/snippet}

<div
	class="grid items-center gap-3 rounded-xl bg-base-200 p-3 {end
		? 'grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]'
		: 'grid-cols-1'}"
>
	{@render side(start, startParts, 'left')}
	{#if end}
		<div class="flex flex-col items-center gap-1 text-xs text-base-content/60">
			{#if between}
				{@render between()}
			{:else}
				<span class="h-px w-6 bg-base-content/25"></span>
			{/if}
		</div>
		{@render side(end, endParts, 'right')}
	{/if}
</div>
