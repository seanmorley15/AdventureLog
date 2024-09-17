<script lang="ts">
	import { goto } from '$app/navigation';
	import { addToast } from '$lib/toasts';
	import type { Collection, Note, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import Launch from '~icons/mdi/launch';
	import TrashCan from '~icons/mdi/trash-can';
	import Calendar from '~icons/mdi/calendar';

	export let note: Note;
	export let user: User | null = null;
	export let collection: Collection | null = null;

	function editNote() {
		dispatch('edit', note);
	}

	async function deleteNote() {
		const res = await fetch(`/api/notes/${note.id}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('success', 'Note deleted successfully');
			dispatch('delete', note.id);
		} else {
			addToast('Failed to delete note', 'error');
		}
	}
</script>

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md overflow-hidden bg-neutral text-neutral-content shadow-xl"
>
	<div class="card-body">
		<div class="flex justify-between">
			<h2 class="text-2xl font-semibold -mt-2 break-words text-wrap">
				{note.name}
			</h2>
		</div>
		<div class="badge badge-primary">Note</div>
		{#if note.links && note.links.length > 0}
			<p>{note.links.length} {note.links.length > 1 ? 'Links' : 'Link'}</p>
		{/if}
		{#if note.date && note.date !== ''}
			<div class="inline-flex items-center">
				<Calendar class="w-5 h-5 mr-1" />
				<p>{new Date(note.date).toLocaleDateString(undefined, { timeZone: 'UTC' })}</p>
			</div>
		{/if}
		<div class="card-actions justify-end">
			<!-- <button class="btn btn-neutral mb-2" on:click={() => goto(`/notes/${note.id}`)}
				><Launch class="w-6 h-6" />Open Details</button
			> -->
			<button class="btn btn-neutral-200 mb-2" on:click={editNote}>
				<Launch class="w-6 h-6" />Open
			</button>
			{#if note.user_id == user?.pk || (collection && user && collection.shared_with.includes(user.uuid))}
				<button
					id="delete_adventure"
					data-umami-event="Delete Adventure"
					class="btn btn-warning"
					on:click={deleteNote}><TrashCan class="w-6 h-6" /></button
				>
			{/if}
		</div>
	</div>
</div>
