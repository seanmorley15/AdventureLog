<script lang="ts">
	import { addToast } from '$lib/toasts';
	import type { City } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';

	import Check from '~icons/mdi/check-circle-outline';
	import CheckFilled from '~icons/mdi/check-circle';

	const dispatch = createEventDispatcher();

	export let city: City;
	export let visited: boolean;

	async function markVisited(e: MouseEvent) {
		e.stopPropagation();
		const res = await fetch(`/api/visitedcity/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ city: city.id })
		});
		if (res.ok) {
			visited = true;
			const data = await res.json();
			addToast(
				'success',
				`${$t('worldtravel.visit_to')} ${city.name} ${$t('worldtravel.marked_visited')}`
			);
			dispatch('visit', data);
		} else {
			addToast('error', `${$t('worldtravel.failed_to_mark_visit')} ${city.name}`);
		}
	}

	async function removeVisit(e: MouseEvent) {
		e.stopPropagation();
		const res = await fetch(`/api/visitedcity/${city.id}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			visited = false;
			addToast('info', `${$t('worldtravel.visit_to')} ${city.name} ${$t('worldtravel.removed')}`);
			dispatch('remove', city);
		} else {
			addToast('error', `${$t('worldtravel.failed_to_remove_visit')} ${city.name}`);
		}
	}
</script>

<div class="grid items-center gap-3 px-4 py-3 hover:bg-base-200/60 transition-colors city-row">
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

	<span class="font-semibold truncate min-w-0">{city.name}</span>

	<span class="hidden sm:block text-sm text-base-content/60 truncate">
		{city.region_name}
	</span>

	<span class="hidden md:block text-sm text-base-content/50 truncate">
		{city.country_name}
	</span>
</div>

<style>
	.city-row {
		grid-template-columns: 2.5rem 1fr 9rem 7rem;
	}

	@media (max-width: 768px) {
		.city-row {
			grid-template-columns: 2.5rem 1fr;
		}
	}
</style>
