<script lang="ts">
	import { goto } from '$app/navigation';
	import { addToast } from '$lib/toasts';
	import type { Region, VisitedRegion } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	export let region: Region;
	export let visited: boolean;

	export let visit_id: number | undefined | null;

	async function markVisited() {
		let res = await fetch(`/worldtravel?/markVisited`, {
			method: 'POST',
			body: JSON.stringify({ regionId: region.id })
		});
		if (res.ok) {
			// visited = true;
			const result = await res.json();
			const data = JSON.parse(result.data);
			if (data[1] !== undefined) {
				console.log('New adventure created with id:', data[3]);
				let visit_id = data[3];
				let region_id = data[5];
				let user_id = data[4];

				let newVisit: VisitedRegion = {
					id: visit_id,
					region: region_id,
					user_id: user_id
				};
				addToast('success', `Visit to ${region.name} marked`);
				dispatch('visit', newVisit);
			}
		} else {
			console.error('Failed to mark region as visited');
			addToast('error', `Failed to mark visit to ${region.name}`);
		}
	}
	async function removeVisit() {
		let res = await fetch(`/worldtravel?/removeVisited`, {
			method: 'POST',
			body: JSON.stringify({ visitId: visit_id })
		});
		if (res.ok) {
			visited = false;
			addToast('info', `Visit to ${region.name} removed`);
			dispatch('remove', null);
		} else {
			console.error('Failed to remove visit');
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
				<button class="btn btn-primary" on:click={markVisited}>Mark Visited</button>
			{/if}
			{#if visited}
				<button class="btn btn-warning" on:click={removeVisit}>Remove</button>
			{/if}
		</div>
	</div>
</div>
