<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import Calendar from '~icons/mdi/calendar';
	import MapMarker from '~icons/mdi/map-marker';
	import Launch from '~icons/mdi/launch';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';

	import { goto } from '$app/navigation';
	import type { Collection } from '$lib/types';
	const dispatch = createEventDispatcher();

	//   export let type: String;

	export let collection: Collection;

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
		<h2 class="card-title overflow-ellipsis">{collection.name}</h2>
		<p>{collection.adventures.length} Adventures</p>
		<div class="card-actions justify-end">
			<button class="btn btn-secondary"><TrashCanOutline class="w-5 h-5 mr-1" /></button>
			<button class="btn btn-primary" on:click={() => goto(`/trip/${collection.id}`)}
				><Launch class="w-5 h-5 mr-1" /></button
			>
		</div>
	</div>
</div>
