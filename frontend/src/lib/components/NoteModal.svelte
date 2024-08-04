<script lang="ts">
	import type { Note } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;

	export let note: Note;
	export let startDate: string | null = null;
	export let endDate: string | null = null;

	let initialName: string = note.name;

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	async function save() {}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">Note Editor</h3>
		{#if initialName !== note.name}
			<p>Editing note {initialName}</p>
		{/if}

		<form>
			<div class="form-control mb-2">
				<label for="name">Name</label>
				<input
					type="text"
					id="name"
					class="input input-bordered w-full max-w-xs"
					bind:value={note.name}
				/>
			</div>
			<div class="form-control mb-2">
				<label for="content">Date</label>
				<input
					type="date"
					id="date"
					name="date"
					min={startDate || ''}
					max={endDate || ''}
					bind:value={note.date}
					class="input input-bordered w-full max-w-xs mt-1"
				/>
			</div>
			<div class="form-control mb-2">
				<label for="content">Content</label>
				<textarea id="content" class="textarea textarea-bordered" bind:value={note.content} rows="5"
				></textarea>
			</div>

			<button class="btn btn-neutral" on:click={close}>Close</button>
			<button class="btn btn-primary" on:click={save}>Save</button>
		</form>
	</div>
</dialog>
