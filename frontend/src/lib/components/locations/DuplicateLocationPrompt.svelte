<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { t } from 'svelte-i18n';
	import type { DuplicateLocationMatch } from '$lib/types';

	import AlertIcon from '~icons/mdi/alert-circle-outline';
	import OpenIcon from '~icons/mdi/open-in-new';

	interface Props {
		matches?: DuplicateLocationMatch[];
		checking?: boolean;
	}

	let { matches = [], checking = false }: Props = $props();

	const dispatch = createEventDispatcher<{
		openExisting: DuplicateLocationMatch;
	}>();

	const measurementSystem = $derived(
		page.data?.user?.measurement_system === 'imperial' ? 'imperial' : 'metric'
	);
	const primaryMatch = $derived(matches[0] ?? null);
	const meta = $derived.by(() => {
		if (!primaryMatch) return '';
		const parts: string[] = [];
		const distance = formatDistance(primaryMatch.distance_meters, measurementSystem);
		if (distance) parts.push(distance);
		if (primaryMatch.location) parts.push(primaryMatch.location);
		return parts.join(' · ');
	});

	function formatDistance(
		meters: number | null | undefined,
		system: 'metric' | 'imperial'
	): string {
		if (meters === null || meters === undefined || !Number.isFinite(meters)) {
			return '';
		}

		if (system === 'imperial') {
			const miles = meters / 1609.34;
			if (miles < 0.1) {
				return $t('adventures.feet_away', { values: { distance: Math.round(miles * 5280) } });
			}
			return $t('adventures.miles_away', { values: { distance: miles.toFixed(1) } });
		}

		if (meters < 1000) {
			return $t('adventures.meters_away', { values: { distance: Math.round(meters) } });
		}
		return $t('adventures.kilometers_away', {
			values: { distance: (meters / 1000).toFixed(1) }
		});
	}

	async function openExisting() {
		if (!primaryMatch) return;
		dispatch('openExisting', primaryMatch);
		await goto(`/locations/${primaryMatch.id}`);
	}
</script>

{#if checking || primaryMatch}
	<div class="alert alert-warning alert-soft alert-sm py-2 px-3 gap-2 items-center" role="status">
		{#if checking && !primaryMatch}
			<span class="loading loading-spinner loading-xs text-warning shrink-0"></span>
			<span class="text-sm">{$t('adventures.checking_duplicates')}</span>
		{:else if primaryMatch}
			<AlertIcon class="w-4 h-4 text-warning shrink-0" />
			<div class="min-w-0 flex-1">
				<p class="text-sm font-medium truncate">
					{$t('adventures.did_you_mean', { values: { name: primaryMatch.name } })}
				</p>
				{#if meta}
					<p class="text-xs text-base-content/60 truncate">{meta}</p>
				{/if}
			</div>
			<button type="button" class="btn btn-sm btn-outline gap-1 shrink-0" onclick={openExisting}>
				<OpenIcon class="w-4 h-4" />
				{$t('adventures.open_existing_location')}
			</button>
		{/if}
	</div>
{/if}
