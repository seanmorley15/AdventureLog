<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Collection } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import {
		DEFAULT_PLAN_DAYS,
		MAX_PLAN_DAYS,
		daysBetween,
		errorMessage,
		planRequest
	} from '$lib/dayPlan';
	import CalendarRange from '~icons/mdi/calendar-range';

	interface Props {
		collection: Collection;
		onConverted: (collection: Collection) => void;
	}

	let { collection, onConverted }: Props = $props();

	let open = $state(false);
	let count = $state(DEFAULT_PLAN_DAYS);
	let saving = $state(false);

	const spanDays = $derived(daysBetween(collection.start_date, collection.end_date) + 1);
	const tooMany = $derived(count > MAX_PLAN_DAYS);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (tooMany || count < 1) return;
		saving = true;
		try {
			const res = await planRequest('/api/itineraries/plan-by-days/', 'POST', {
				collection: collection.id,
				day_count: count
			});
			if (!res.ok) {
				addToast('error', errorMessage(res.data, $t('itinerary.save_failed')));
				return;
			}
			const refreshed = await planRequest<Collection>(`/api/collections/${collection.id}/`, 'GET');
			if (refreshed.ok) onConverted(refreshed.data);
		} finally {
			saving = false;
		}
	}
</script>

<div class="alert mb-6 flex flex-col items-stretch gap-3 shadow-sm sm:flex-row sm:items-center">
	<CalendarRange class="hidden h-6 w-6 shrink-0 sm:block" />
	<div class="min-w-0 flex-1">
		<h3 class="font-bold">{$t('itinerary.plan_by_days')}</h3>
		<p class="text-sm opacity-80">
			{$t('itinerary.plan_by_days_desc', { values: { days: spanDays } })}
		</p>
		{#if open && tooMany}
			<p class="mt-1 text-sm text-error">
				{$t('itinerary.plan_by_days_max', { values: { max: MAX_PLAN_DAYS } })}
			</p>
		{/if}
	</div>
	{#if open}
		<form class="join" onsubmit={submit}>
			<label class="input input-sm join-item w-40">
				<span class="label text-xs">{$t('itinerary.days_label')}</span>
				<input
					type="number"
					min="1"
					max={MAX_PLAN_DAYS}
					bind:value={count}
					aria-label={$t('itinerary.plan_by_days_count')}
					required
				/>
			</label>
			<button type="submit" class="btn btn-sm btn-primary join-item" disabled={saving || tooMany}>
				{#if saving}
					<span class="loading loading-spinner loading-xs"></span>
				{/if}
				{$t('itinerary.apply')}
			</button>
		</form>
	{:else}
		<button type="button" class="btn btn-sm btn-primary" onclick={() => (open = true)}>
			{$t('itinerary.plan_by_days')}
		</button>
	{/if}
</div>
