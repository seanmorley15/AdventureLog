<script lang="ts">
	import { goto } from '$app/navigation';
	import { addToast } from '$lib/toasts';
	import type { Region } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';

	import Check from '~icons/mdi/check-circle-outline';
	import CheckFilled from '~icons/mdi/check-circle';
	import ChevronRight from '~icons/mdi/chevron-right';
	import City from '~icons/mdi/city';

	const dispatch = createEventDispatcher();

	export let region: Region;
	export let visited: boolean | undefined;

	const countryCode = region.id.split('-')[0];

	function goToCity(e: MouseEvent) {
		e.stopPropagation();
		goto(`/worldtravel/${countryCode}/${region.id}`);
	}

	function nav() {
		if (region.num_cities > 0) {
			goto(`/worldtravel/${countryCode}/${region.id}`);
		}
	}

	async function markVisited(e: MouseEvent) {
		e.stopPropagation();
		const res = await fetch(`/api/visitedregion/`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'POST',
			body: JSON.stringify({ region: region.id })
		});
		if (res.ok) {
			visited = true;
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
		e.stopPropagation();
		const res = await fetch(`/api/visitedregion/${region.id}`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'DELETE'
		});
		if (res.ok) {
			visited = false;
			addToast('info', `${$t('worldtravel.visit_to')} ${region.name} ${$t('worldtravel.removed')}`);
			dispatch('remove', region);
		} else {
			addToast('error', `${$t('worldtravel.failed_to_remove_visit')} ${region.name}`);
		}
	}
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
	class="grid items-center gap-3 px-4 py-3 hover:bg-base-200/60 transition-colors group region-row {region.num_cities >
	0
		? 'cursor-pointer'
		: ''}"
	on:click={nav}
	on:keydown={(e) => e.key === 'Enter' && nav()}
	role={region.num_cities > 0 ? 'button' : undefined}
	tabindex={region.num_cities > 0 ? 0 : undefined}
>
	<button
		type="button"
		class="btn btn-ghost btn-sm btn-square {visited
			? 'text-success'
			: 'text-base-content/30 hover:text-success'}"
		title={visited ? $t('adventures.remove') : $t('adventures.mark_visited')}
		on:click={visited ? removeVisit : markVisited}
	>
		{#if visited}
			<CheckFilled class="w-5 h-5" />
		{:else}
			<Check class="w-5 h-5" />
		{/if}
	</button>

	<a
		href="/worldtravel/{countryCode}/{region.id}"
		class="font-semibold truncate group-hover:text-primary transition-colors min-w-0"
		on:click|stopPropagation
	>
		{region.name}
	</a>

	<span class="hidden sm:block text-sm text-base-content/60 truncate">
		{region.country_name}
	</span>

	<span class="inline-flex items-center gap-1.5 text-sm text-base-content/60 tabular-nums">
		<City class="w-4 h-4" />
		{region.num_cities}
	</span>

	{#if region.num_cities > 0}
		<button
			type="button"
			class="btn btn-ghost btn-sm gap-1 hidden sm:flex justify-end"
			on:click={goToCity}
		>
			{$t('worldtravel.view_cities')}
			<ChevronRight class="w-4 h-4" />
		</button>
	{:else}
		<span></span>
	{/if}
</div>

<style>
	.region-row {
		grid-template-columns: 2.5rem 1fr 7rem 5rem 8rem;
	}

	@media (max-width: 640px) {
		.region-row {
			grid-template-columns: 2.5rem 1fr 4rem;
		}
	}
</style>
