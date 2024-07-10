<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import { goto } from '$app/navigation';
	import type { Trip } from '$lib/types';
	const dispatch = createEventDispatcher();

	//   export let type: String;

	export let trip: Trip;

	// function remove() {
	//   dispatch("remove", trip.id);
	// }
	// function edit() {}
	// function add() {
	//   dispatch("add", trip);
	// }

	// // TODO: Implement markVisited function
	// function markVisited() {
	//   console.log(trip.id);
	//   dispatch("markVisited", trip);
	// }
</script>

<div
	class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-primary-content shadow-xl overflow-hidden text-base-content"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{trip.name}</h2>
		{#if trip.date && trip.date !== ''}
			<div class="inline-flex items-center">
				<!-- <iconify-icon icon="mdi:calendar" class="text-xl"></iconify-icon> -->
				<p class="ml-1">{trip.date}</p>
			</div>
		{/if}
		{#if trip.location && trip.location !== ''}
			<div class="inline-flex items-center">
				<!-- <iconify-icon icon="mdi:map-marker" class="text-xl"></iconify-icon> -->
				<p class="ml-1">{trip.location}</p>
			</div>
		{/if}

		<div class="card-actions justify-end">
			<button class="btn btn-secondary"
				><iconify-icon icon="mdi:trash-can-outline" class="text-2xl"></iconify-icon></button
			>
			<button class="btn btn-primary" on:click={() => goto(`/trip/${trip.id}`)}
				><iconify-icon icon="mdi:launch" class="text-2xl"></iconify-icon></button
			>
		</div>
	</div>
</div>
