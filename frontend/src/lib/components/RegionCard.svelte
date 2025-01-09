<script lang="ts">
	import { goto } from '$app/navigation';
	import { addToast } from '$lib/toasts';
	import type { Region, VisitedRegion } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';

	export let region: Region;
	export let visited: boolean;

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
			addToast('success', `Visit to ${region.name} marked`);
			dispatch('visit', data);
		} else {
			console.error('Failed to mark region as visited');
			addToast('error', `Failed to mark visit to ${region.name}`);
		}
	}
	async function removeVisit() {
		let res = await fetch(`/api/visitedregion/${region.id}`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'DELETE'
		});
		if (res.ok) {
			visited = false;
			addToast('info', `Visit to ${region.name} removed`);
			dispatch('remove', region);
		} else {
			console.error('Failed to remove visit');
			addToast('error', `Failed to remove visit to ${region.name}`);
		}
	}
</script>

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-neutral text-neutral-content shadow-xl overflow-hidden"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{region.name}</h2>
		<p>{region.id}</p>
		<div class="card-actions justify-end">
			<!-- <button class="btn btn-info" on:click={moreInfo}>More Info</button> -->
			{#if !visited}
				<button class="btn btn-primary" on:click={markVisited}
					>{$t('adventures.mark_visited')}</button
				>
			{/if}
			{#if visited}
				<button class="btn btn-warning" on:click={removeVisit}>{$t('adventures.remove')}</button>
			{/if}
			<button class="btn btn-neutral-300" on:click={goToCity}
				>{$t('worldtravel.view_cities')}</button
			>
		</div>
	</div>
</div>
