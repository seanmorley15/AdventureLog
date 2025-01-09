<script lang="ts">
	import { addToast } from '$lib/toasts';
	import type { City } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';

	export let city: City;
	export let visited: boolean;

	async function markVisited() {
		let res = await fetch(`/api/visitedcity/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ city: city.id })
		});
		if (res.ok) {
			visited = true;
			let data = await res.json();
			addToast('success', `Visit to ${city.name} marked`);
			dispatch('visit', data);
		} else {
			console.error('Failed to mark city as visited');
			addToast('error', `Failed to mark visit to ${city.name}`);
		}
	}
	async function removeVisit() {
		let res = await fetch(`/api/visitedcity/${city.id}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			visited = false;
			addToast('info', `Visit to ${city.name} removed`);
			dispatch('remove', city);
		} else {
			console.error('Failed to remove visit');
			addToast('error', `Failed to remove visit to ${city.name}`);
		}
	}
</script>

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-neutral text-neutral-content shadow-xl overflow-hidden"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{city.name}</h2>
		<div class="flex flex-wrap gap-2">
			<div class="badge badge-neutral-300">{city.id}</div>
		</div>
		<div class="card-actions justify-end">
			{#if !visited}
				<button class="btn btn-primary" on:click={markVisited}
					>{$t('adventures.mark_visited')}</button
				>
			{/if}
			{#if visited}
				<button class="btn btn-warning" on:click={removeVisit}>{$t('adventures.remove')}</button>
			{/if}
		</div>
	</div>
</div>
