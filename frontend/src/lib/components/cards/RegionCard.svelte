<script lang="ts">
	import { addToast } from '$lib/toasts';
	import type { Region } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';

	import Check from '~icons/mdi/check-circle-outline';
	import CheckFilled from '~icons/mdi/check-circle';
	import ChevronRight from '~icons/mdi/chevron-right';
	import City from '~icons/mdi/city';

	const dispatch = createEventDispatcher();

	interface Props {
		region: Region;
		visited: boolean | undefined;
	}

	let { region, visited = false }: Props = $props();
	let optimisticVisited = $state<boolean | null>(null);
	let isVisited = $derived(optimisticVisited ?? visited);

	let countryCode = $derived(region.id.split('-')[0]);
	let cityHref = $derived(`/worldtravel/${countryCode}/${region.id}`);

	async function markVisited(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		const res = await fetch(`/api/visitedregion/`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'POST',
			body: JSON.stringify({ region: region.id })
		});
		if (res.ok) {
			optimisticVisited = true;
			const data = await res.json();
			addToast(
				'success',
				`${$t('worldtravel.visit_to')} ${region.name} ${$t('worldtravel.marked_visited')}`
			);
			dispatch('visit', data);
		} else {
			addToast('error', `${$t('worldtravel.failed_to_mark_visit')} ${region.name}`);
		}
	}

	async function removeVisit(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		const res = await fetch(`/api/visitedregion/${region.id}`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'DELETE'
		});
		if (res.ok) {
			optimisticVisited = false;
			addToast('info', `${$t('worldtravel.visit_to')} ${region.name} ${$t('worldtravel.removed')}`);
			dispatch('remove', region);
		} else {
			addToast('error', `${$t('worldtravel.failed_to_remove_visit')} ${region.name}`);
		}
	}
</script>

<div class="grid items-center gap-3 px-4 py-3 hover:bg-base-200/60 transition-colors group region-row">
	<button
		type="button"
		class="btn btn-ghost btn-sm btn-square {isVisited
			? 'text-success'
			: 'text-base-content/30 hover:text-success'}"
		title={isVisited ? $t('adventures.remove') : $t('adventures.mark_visited')}
		onclick={isVisited ? removeVisit : markVisited}
	>
		{#if isVisited}
			<CheckFilled class="w-5 h-5" />
		{:else}
			<Check class="w-5 h-5" />
		{/if}
	</button>

	{#if region.num_cities > 0}
		<a href={cityHref} class="region-main text-inherit no-underline min-w-0">
			<span class="font-semibold truncate group-hover:text-primary transition-colors min-w-0">
				{region.name}
			</span>
			<span class="hidden sm:block text-sm text-base-content/60 truncate">
				{region.country_name}
			</span>
			<span class="inline-flex items-center gap-1.5 text-sm text-base-content/60 tabular-nums">
				<City class="w-4 h-4" />
				{region.num_cities}
			</span>
			<span class="btn btn-ghost btn-sm gap-1 hidden sm:flex justify-end pointer-events-none">
				{$t('worldtravel.view_cities')}
				<ChevronRight class="w-4 h-4" />
			</span>
		</a>
	{:else}
		<div class="region-main min-w-0">
			<span class="font-semibold truncate min-w-0">{region.name}</span>
			<span class="hidden sm:block text-sm text-base-content/60 truncate">
				{region.country_name}
			</span>
			<span class="inline-flex items-center gap-1.5 text-sm text-base-content/60 tabular-nums">
				<City class="w-4 h-4" />
				{region.num_cities}
			</span>
			<span></span>
		</div>
	{/if}
</div>

<style>
	.region-row {
		grid-template-columns: 2.5rem 1fr;
	}

	.region-main {
		display: grid;
		grid-template-columns: 1fr 7rem 5rem 8rem;
		align-items: center;
		gap: 0.75rem;
	}

	@media (max-width: 640px) {
		.region-main {
			grid-template-columns: 1fr 4rem;
		}
	}
</style>
