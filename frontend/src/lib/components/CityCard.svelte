<script lang="ts">
	import { goto } from '$app/navigation';
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
	class="card w-full max-w-md bg-base-300 text-base-content shadow-2xl hover:shadow-3xl transition-all duration-300 border border-base-300 hover:border-primary/20 group overflow-hidden"
>
	<div class="card-body p-6 space-y-4">
		<!-- Header -->
		<h2 class="text-xl font-bold truncate">{city.name}</h2>

		<!-- Metadata Badges -->
		<div class="flex flex-wrap gap-2">
			<div class="badge badge-primary">
				{city.region_name}, {city.country_name}
			</div>
			<div class="badge badge-neutral-300">Region ID: {city.region}</div>
		</div>

		<!-- Actions -->
		<div class="pt-4 border-t border-base-300 flex justify-end gap-2">
			{#if visited === false}
				<button class="btn btn-primary btn-sm" on:click={markVisited}>
					{$t('adventures.mark_visited')}
				</button>
			{/if}
			{#if visited === true}
				<button class="btn btn-warning btn-sm" on:click={removeVisit}>
					{$t('adventures.remove')}
				</button>
			{/if}
		</div>
	</div>
</div>

<style>
	.truncate {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
