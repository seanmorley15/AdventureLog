<script lang="ts">
	import { t } from 'svelte-i18n';
	import { isAllDay } from '$lib';
	import { formatAllDayDate, formatDateInTimezone } from '$lib/dateUtils';
	import type { DateFormatPreference } from '$lib/dateFormat';
	import DetailFact from './DetailFact.svelte';
	import CalendarRange from '~icons/mdi/calendar-range';
	import type InformationOutline from '~icons/mdi/information-outline';

	interface Props {
		label: string;
		/** ISO date or datetime. A UTC-midnight value is treated as a date without a time. */
		value: string;
		/** The zone the time was entered in. */
		timezone?: string | null;
		dateFormat: DateFormatPreference;
		icon?: typeof InformationOutline;
	}

	let { label, value, timezone = null, dateFormat, icon = CalendarRange }: Props = $props();

	const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';
	let allDay = $derived(isAllDay(value));
	let zoneLabel = $derived(timezone ?? localTimeZone);
	let differs = $derived(!!timezone && timezone !== localTimeZone);
	let tip = $derived(
		zoneLabel === localTimeZone
			? null
			: `${$t('adventures.trip_timezone') ?? 'Trip TZ'}: ${zoneLabel}. ${
					$t('adventures.your_time') ?? 'Your time'
				}: ${localTimeZone}.`
	);
</script>

<DetailFact {label} {icon}>
	<span class="font-semibold">
		{#if allDay}
			{formatAllDayDate(value, dateFormat)}
		{:else}
			{formatDateInTimezone(value, timezone, dateFormat)}
		{/if}
	</span>
	{#if !allDay}
		<span
			class="badge badge-ghost badge-sm ml-1 align-middle"
			class:tooltip={Boolean(tip)}
			data-tip={tip ?? undefined}
		>
			{differs ? zoneLabel : ($t('adventures.local') ?? 'Local')}
		</span>
	{/if}
</DetailFact>
