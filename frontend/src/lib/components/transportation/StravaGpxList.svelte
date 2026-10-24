<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { StravaActivity, User } from '$lib/types';
	import StravaActivityCard from '$lib/components/StravaActivityCard.svelte';
	import LoadingIcon from '~icons/mdi/loading';
	import RunIcon from '~icons/mdi/run';

	interface Props {
		start_date?: string | null;
		end_date?: string | null;
		user?: User | null;
	}

	let { start_date = null, end_date = null, user = null }: Props = $props();

	let activities: StravaActivity[] = $state([]);
	let isLoading = $state(false);
	let error: string | null = $state(null);
	let showActivities = $state(false);

	async function fetchStravaActivities() {
		if (!start_date || !end_date) {
			return;
		}

		// Add 1 day buffer before start and after end to catch activities near the dates
		const startDateObj = new Date(start_date);
		startDateObj.setDate(startDateObj.getDate() - 1);
		const bufferedStart = startDateObj.toISOString().split('T')[0];

		const endDateObj = new Date(end_date);
		endDateObj.setDate(endDateObj.getDate() + 1);
		const bufferedEnd = endDateObj.toISOString().split('T')[0];

		isLoading = true;
		error = null;

		try {
			const response = await fetch(
				`/api/integrations/strava/activities/?start_date=${bufferedStart}&end_date=${bufferedEnd}`
			);

			if (!response.ok) {
				if (response.status === 404) {
					throw new Error($t('adventures.strava_not_connected'));
				}
				throw new Error($t('adventures.failed_to_fetch_activities'));
			}

			const data = await response.json();
			activities = data.activities || [];
		} catch (err) {
			console.error('Error fetching Strava activities:', err);
			error = err instanceof Error ? err.message : $t('adventures.failed_to_fetch_activities');
		} finally {
			isLoading = false;
		}
	}

	function toggleActivities() {
		showActivities = !showActivities;
		if (showActivities && activities.length === 0 && !error) {
			fetchStravaActivities();
		}
	}

	async function handleDownloadGpx(activity: StravaActivity) {
		try {
			const response = await fetch(activity.export_gpx);
			const blob = await response.blob();
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${activity.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.gpx`;
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);
		} catch (err) {
			console.error('Error downloading GPX:', err);
		}
	}

	onMount(() => {
		if (start_date && end_date) {
			fetchStravaActivities();
		}
	});
</script>

{#if start_date && end_date}
	<div class="mt-4">
		<button
			type="button"
			class="btn btn-outline btn-sm gap-2"
			onclick={toggleActivities}
			disabled={isLoading}
		>
			<RunIcon class="w-4 h-4" />
			{showActivities
				? $t('adventures.hide_strava_activities')
				: $t('adventures.show_strava_activities')}
			{#if isLoading}
				<LoadingIcon class="w-4 h-4 animate-spin" />
			{/if}
		</button>

		{#if showActivities}
			<div class="mt-4">
				{#if error}
					<div class="alert alert-error">
						<span class="text-sm">{error}</span>
					</div>
				{:else if isLoading}
					<div class="flex justify-center items-center p-8">
						<LoadingIcon class="w-8 h-8 animate-spin text-primary" />
					</div>
				{:else if activities.length > 0}
					<div class="space-y-3">
						<div class="text-sm text-base-content/70 mb-2">
							{$t('adventures.found_activities', { values: { count: activities.length } })}
						</div>
						{#each activities as activity (activity.id)}
							<StravaActivityCard
								{activity}
								measurementSystem={user?.measurement_system || 'metric'}
								downloadOnly={true}
							/>
						{/each}
					</div>
				{:else}
					<div class="bg-base-200/50 rounded-lg p-6 text-center">
						<div class="text-base-content/60 text-sm">
							{$t('adventures.no_strava_activities_found')}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
