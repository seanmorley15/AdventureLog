<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { isVisitAllDay, allDayDatePart } from '#lib';
	import type { StravaActivity } from '#lib/types.js';
	import StravaActivityCard from '#lib/components/StravaActivityCard.svelte';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import LoadingIcon from '~icons/mdi/loading';

	interface Props {
		provider: 'strava' | 'endurain';
		/** The visit or day the activity belongs to; activities near it are listed. */
		dateStart?: string | null;
		dateEnd?: string | null;
		/** `external_service_id`s already saved here, so they are marked rather than imported twice. */
		importedIds?: string[];
		measurementSystem?: 'metric' | 'imperial';
		/** The id being fetched right now. */
		importingId?: string | null;
		onImport: (activity: StravaActivity) => void;
		onBack: () => void;
	}

	let {
		provider,
		dateStart = null,
		dateEnd = null,
		importedIds = [],
		measurementSystem = 'metric',
		importingId = null,
		onImport,
		onBack
	}: Props = $props();

	const providerName = $derived(provider === 'endurain' ? 'Endurain' : 'Strava');
	let activities = $state<StravaActivity[]>([]);
	let loading = $state(true);
	let failed = $state(false);

	/** The visit or day, plus half a day either side for timezones and late uploads. */
	function window() {
		const startMs = dateStart ? Date.parse(dateStart) : Date.now() - 30 * 86400000;
		let endMs = dateEnd ? Date.parse(dateEnd) : Date.now();
		if (dateStart && dateEnd && isVisitAllDay(dateStart, dateEnd)) {
			endMs = Date.parse(`${allDayDatePart(dateEnd)}T23:59:59Z`);
		}
		return {
			start: new Date(startMs - 12 * 60 * 60 * 1000).toISOString(),
			end: new Date(endMs + 12 * 60 * 60 * 1000).toISOString()
		};
	}

	onMount(async () => {
		try {
			const { start, end } = window();
			const response = await fetch(
				`/api/integrations/${provider}/activities/?start_date=${start}&end_date=${end}`
			);
			if (!response.ok) throw new Error(String(response.status));
			activities = (await response.json()).activities ?? [];
		} catch (error) {
			console.error(error);
			failed = true;
		} finally {
			loading = false;
		}
	});
</script>

<div class="space-y-3">
	<div class="flex items-center gap-2">
		<button
			type="button"
			class="btn btn-ghost btn-sm btn-circle"
			aria-label={$t('adventures.back')}
			onclick={onBack}
		>
			<ArrowLeftIcon class="h-4 w-4" />
		</button>
		<h3 class="font-semibold">
			{$t('activities.import_from', { values: { provider: providerName } })}
		</h3>
	</div>

	{#if loading}
		<div class="flex justify-center py-8">
			<LoadingIcon class="h-8 w-8 animate-spin text-primary" />
		</div>
	{:else if failed}
		<div class="alert alert-error">
			{$t('activities.import_list_failed', { values: { provider: providerName } })}
		</div>
	{:else if activities.length === 0}
		<p class="py-6 text-center text-base-content/70">
			{$t('activities.import_list_empty', { values: { provider: providerName } })}
		</p>
	{:else}
		<div class="space-y-3">
			{#each activities as activity (activity.id)}
				<StravaActivityCard
					{activity}
					{provider}
					{measurementSystem}
					importing={importingId === String(activity.id)}
					imported={importedIds.includes(String(activity.id))}
					{onImport}
				/>
			{/each}
		</div>
	{/if}
</div>
