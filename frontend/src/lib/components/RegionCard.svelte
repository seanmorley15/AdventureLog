<script lang="ts">
	import { goto } from '$app/navigation';
	import { addToast } from '$lib/toasts';
	import type { Region, VisitedRegion } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';

	export let region: Region;
	export let visited: boolean | undefined;

	function goToCity() {
		console.log(region);
		goto(`/worldtravel/${region.id.split('-')[0]}/${region.id}`);
	}

	async function markVisited() {
		let res = await fetch(`/api/visitedregion/`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'POST',
			body: JSON.stringify({ region: region.id })
		});
		if (res.ok) {
			visited = true;
			let data = await res.json();
			addToast(
				'success',
				`${$t('worldtravel.visit_to')} ${region.name} ${$t('worldtravel.marked_visited')}`
			);
			dispatch('visit', data);
		} else {
			console.error($t('worldtravel.region_failed_visited'));
			addToast('error', `${$t('worldtravel.failed_to_mark_visit')} ${region.name}`);
		}
	}
	async function removeVisit() {
		let res = await fetch(`/api/visitedregion/${region.id}`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'DELETE'
		});
		if (res.ok) {
			visited = false;
			addToast('info', `${$t('worldtravel.visit_to')} ${region.name} ${$t('worldtravel.removed')}`);
			dispatch('remove', region);
		} else {
			console.error($t('worldtravel.visit_remove_failed'));
			addToast('error', `${$t('worldtravel.failed_to_remove_visit')} ${region.name}`);
		}
	}
</script>

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-neutral text-neutral-content shadow-xl overflow-hidden"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{region.name}</h2>
		<div>
			<div class="badge badge-primary">
				<p>{region.country_name}</p>
			</div>
			<div class="badge badge-neutral-300">
				<p>{region.num_cities} {$t('worldtravel.cities')}</p>
			</div>
			<div class="badge badge-neutral-300">
				<p>{region.id}</p>
			</div>
		</div>
		<div class="card-actions justify-end">
			<!-- <button class="btn btn-info" on:click={moreInfo}>More Info</button> -->
			{#if !visited && visited !== undefined}
				<button class="btn btn-primary" on:click={markVisited}
					>{$t('adventures.mark_visited')}</button
				>
			{/if}
			{#if visited && visited !== undefined}
				<button class="btn btn-warning" on:click={removeVisit}>{$t('adventures.remove')}</button>
			{/if}
			{#if region.num_cities > 0}
				<button class="btn btn-neutral-300" on:click={goToCity}
					>{$t('worldtravel.view_cities')}</button
				>
			{/if}
		</div>
	</div>
</div>
