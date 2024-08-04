<script lang="ts">
	import { goto } from '$app/navigation';
	import { addToast } from '$lib/toasts';
	import type { Note } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import Launch from '~icons/mdi/launch';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';

	export let note: Note;

	function editNote() {
		dispatch('edit', note);
	}
</script>

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-primary-content shadow-xl overflow-hidden text-base-content"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{note.name}</h2>
		<div class="card-actions justify-end">
			<button class="btn btn-neutral mb-2" on:click={() => goto(`/notes/${note.id}`)}
				><Launch class="w-6 h-6" />Open Details</button
			>
			<button class="btn btn-neutral mb-2" on:click={editNote}>
				<FileDocumentEdit class="w-6 h-6" />Edit note
			</button>
		</div>
	</div>
</div>
