<script lang="ts">
	import { t } from 'svelte-i18n';
	import Calendar from '~icons/mdi/calendar';
	import { formatAllDayDate, formatDateInTimezone } from '$lib/dateUtils';
	import { isAllDay } from '$lib';

	export let date: string | null;
	export let timezone: string | null = null;
	export let label: string | null = null; // Optional custom label like "Last stay", "Last trip"
</script>

{#if date}
	<div class="flex items-center gap-1.5 text-sm text-base-content/70">
		<Calendar class="w-4 h-4 flex-shrink-0" />
		{#if label}
			<span class="text-xs">{label}:</span>
		{/if}
		<span class="font-medium">
			{#if isAllDay(date)}
				{formatAllDayDate(date)}
			{:else}
				{formatDateInTimezone(date, timezone)}
			{/if}
		</span>
	</div>
{/if}
