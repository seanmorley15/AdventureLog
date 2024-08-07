<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import Launch from '~icons/mdi/launch';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';

	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import ArchiveArrowDown from '~icons/mdi/archive-arrow-down';
	import ArchiveArrowUp from '~icons/mdi/archive-arrow-up';

	import { goto } from '$app/navigation';
	import type { Collection } from '$lib/types';
	import { addToast } from '$lib/toasts';

	import Plus from '~icons/mdi/plus';
	import { json } from '@sveltejs/kit';

	const dispatch = createEventDispatcher();

	export let type: String | undefined | null;

	//   export let type: String;

	function editAdventure() {
		dispatch('edit', collection);
	}

	async function archiveCollection(is_archived: boolean) {
		console.log(JSON.stringify({ is_archived: is_archived }));
		let res = await fetch(`/api/collections/${collection.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ is_archived: is_archived })
		});
		if (res.ok) {
			console.log(`Collection ${is_archived ? 'archived' : 'unarchived'}`);
			addToast('info', `Adventure ${is_archived ? 'archived' : 'unarchived'} successfully!`);
			dispatch('delete', collection.id);
		} else {
			console.log('Error archiving adventure');
		}
	}

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
		{#if collection.start_date && collection.end_date}
			<p>
				Dates: {new Date(collection.start_date).toLocaleDateString('en-US', { timeZone: 'UTC' })} - {new Date(
					collection.end_date
				).toLocaleDateString('en-US', { timeZone: 'UTC' })}
			</p>
			<!-- display the duration in days -->
			<p>
				Duration: {Math.floor(
					(new Date(collection.end_date).getTime() - new Date(collection.start_date).getTime()) /
						(1000 * 60 * 60 * 24)
				) + 1}{' '}
				days
			</p>{/if}
		<div class="inline-flex gap-2 mb-2">
			<div class="badge badge-neutral">{collection.is_public ? 'Public' : 'Private'}</div>
			{#if collection.is_archived}
				<div class="badge badge-warning">Archived</div>
			{/if}
		</div>
		<div class="card-actions justify-end">
			{#if type != 'link'}
				<button on:click={deleteCollection} class="btn btn-secondary"
					><TrashCanOutline class="w-5 h-5 mr-1" /></button
				>
				{#if !collection.is_archived}
					<button class="btn btn-primary" on:click={editAdventure}>
						<FileDocumentEdit class="w-6 h-6" />
					</button>
				{/if}
				<button class="btn btn-primary" on:click={() => goto(`/collections/${collection.id}`)}
					><Launch class="w-5 h-5 mr-1" /></button
				>
			{/if}
			{#if type == 'link'}
				<button class="btn btn-primary" on:click={() => dispatch('link', collection.id)}>
					<Plus class="w-5 h-5 mr-1" />
				</button>
			{/if}
			{#if collection.is_archived}
				<button class="btn btn-primary" on:click={() => archiveCollection(false)}>
					<ArchiveArrowUp class="w-5 h-5 mr-1" />
				</button>
			{:else}
				<button class="btn btn-primary" on:click={() => archiveCollection(true)}>
					<ArchiveArrowDown class="w-5 h-5 mr" />
				</button>
			{/if}
		</div>
	</div>
</div>
