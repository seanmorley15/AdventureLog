<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import Calendar from '~icons/mdi/calendar';
	import MapMarker from '~icons/mdi/map-marker';
	import Launch from '~icons/mdi/launch';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';

	import { goto } from '$app/navigation';
	import type { Collection } from '$lib/types';
	import { addToast } from '$lib/toasts';
	const dispatch = createEventDispatcher();

	//   export let type: String;

	export let collection: Collection;

	async function deleteCollection() {
		let res = await fetch(`/collections/${collection.id}?/delete`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded'
			}
		});
		if (res.ok) {
			console.log('Collection deleted');
			addToast('info', 'Adventure deleted successfully!');
			dispatch('delete', collection.id);
		} else {
			console.log('Error deleting adventure');
		}
	}
</script>

<div
	class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-primary-content shadow-xl overflow-hidden text-base-content"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{collection.name}</h2>
		<p>{collection.adventures.length} Adventures</p>
		<div class="card-actions justify-end">
			<button on:click={deleteCollection} class="btn btn-secondary"
				><TrashCanOutline class="w-5 h-5 mr-1" /></button
			>
			<button class="btn btn-primary" on:click={() => goto(`/collections/${collection.id}`)}
				><Launch class="w-5 h-5 mr-1" /></button
			>
		</div>
	</div>
</div>
