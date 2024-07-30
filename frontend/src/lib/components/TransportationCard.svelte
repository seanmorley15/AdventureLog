<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import Launch from '~icons/mdi/launch';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';

	import FileDocumentEdit from '~icons/mdi/file-document-edit';

	import { goto } from '$app/navigation';
	import type { Collection, Transportation, User } from '$lib/types';
	import { addToast } from '$lib/toasts';

	import Plus from '~icons/mdi/plus';

	const dispatch = createEventDispatcher();

	export let transportation: Transportation;
	export let user: User | null = null;

	function editTransportation() {
		dispatch('edit', transportation);
	}

	async function deleteTransportation() {
		let res = await fetch(`/api/transportations/${transportation.id}`, {
			method: 'DELETE',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (!res.ok) {
			console.log('Error deleting transportation');
		} else {
			console.log('Collection deleted');
			addToast('info', 'Transportation deleted successfully!');
			dispatch('delete', transportation.id);
		}
	}
</script>

<div
	class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-primary-content shadow-xl overflow-hidden text-base-content"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{transportation.name}</h2>
		<div class="badge badge-secondary">{transportation.type}</div>
		{#if transportation.from_location && transportation.to_location}
			<p class="text-sm">
				{transportation.from_location} to {transportation.to_location}
			</p>
		{/if}
		{#if transportation.date}
			{new Date(transportation.date).toLocaleString()}
		{/if}
		{#if user}
			<div class="card-actions justify-end">
				<button on:click={deleteTransportation} class="btn btn-secondary"
					><TrashCanOutline class="w-5 h-5 mr-1" /></button
				>
				<button class="btn btn-primary" on:click={editTransportation}>
					<FileDocumentEdit class="w-6 h-6" />
				</button>
			</div>
		{/if}
	</div>
</div>
