<script lang="ts">
	import { goto } from '$app/navigation';
	import { addToast } from '$lib/toasts';
	import type { Note, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import Launch from '~icons/mdi/launch';
	import TrashCan from '~icons/mdi/trash-can';

	export let note: Note;
	export let user: User | null = null;

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
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-primary-content shadow-xl overflow-hidden text-base-content"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{note.name}</h2>
		<div class="card-actions justify-end">
			<!-- <button class="btn btn-neutral mb-2" on:click={() => goto(`/notes/${note.id}`)}
				><Launch class="w-6 h-6" />Open Details</button
			> -->
			<button class="btn btn-neutral mb-2" on:click={editNote}>
				<Launch class="w-6 h-6" />Open
			</button>
			{#if note.user_id == user?.pk}
				<button
					id="delete_adventure"
					data-umami-event="Delete Adventure"
					class="btn btn-warning"
					on:click={deleteNote}><TrashCan class="w-6 h-6" />Delete</button
				>
			{/if}
		</div>
	</div>
</div>
