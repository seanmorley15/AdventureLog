<script lang="ts">
	import { t } from 'svelte-i18n';
	import { isAllDayEntry } from '#lib';
	import { formatAllDayDate, formatDateInTimezone, timezoneInfo } from '#lib/dateUtils.js';
	import type { DateFormatPreference } from '#lib/dateFormat.js';
	import DetailFact from './DetailFact.svelte';
	import CalendarRange from '~icons/mdi/calendar-range';
	import type InformationOutline from '~icons/mdi/information-outline';

	interface Props {
		label: string;
		/** ISO date or datetime. UTC midnight with no time zone is a date without a time. */
		value: string;
		/** The zone the time was entered in. */
		timezone?: string | null;
		dateFormat: DateFormatPreference;
		icon?: typeof InformationOutline;
	}

	let { label, value, timezone = null, dateFormat, icon = CalendarRange }: Props = $props();

	let allDay = $derived(isAllDayEntry(value, timezone));
	let zone = $derived(
		timezoneInfo(timezone, {
			tripZone: $t('adventures.trip_timezone') ?? 'Trip TZ',
			yourTime: $t('adventures.your_time') ?? 'Your time'
		})
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
			class:tooltip={Boolean(zone.tip)}
			data-tip={zone.tip ?? undefined}
		>
			{zone.differs ? zone.label : ($t('adventures.local') ?? 'Local')}
		</span>
	{/if}
</DetailFact>
