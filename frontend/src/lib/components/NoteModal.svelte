<script lang="ts">
	import type { Collection, Note } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;

	export let note: Note | null = null;
	export let collection: Collection;

	let newNote = {
		name: note?.name || '',
		content: note?.content || '',
		date: note?.date || '',
		links: note?.links || [],
		collection: collection.id,
		is_public: collection.is_public
	};

	let initialName: string = note?.name || '';

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

	async function save() {
		if (note && note.id) {
			const res = await fetch(`/api/notes/${note.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newNote)
			});
			if (res.ok) {
				let data = await res.json();
				if (data) {
					dispatch('save', data);
				}
			} else {
				console.error('Failed to save note');
			}
		} else {
			const res = await fetch(`/api/notes/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newNote)
			});
			if (res.ok) {
				let data = await res.json();
				if (data) {
					dispatch('create', data);
				}
			} else {
				let data = await res.json();
				console.error('Failed to save note', data);
				console.error('Failed to save note');
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">Note Editor</h3>
		{#if initialName}
			<p class="font-semibold text-md mb-2">Editing note {initialName}</p>
		{/if}

		<form on:submit|preventDefault>
			<div class="form-control mb-2">
				<label for="name">Name</label>
				<input
					type="text"
					id="name"
					class="input input-bordered w-full max-w-xs"
					bind:value={newNote.name}
				/>
			</div>
			<div class="form-control mb-2">
				<label for="content">Date</label>
				<input
					type="date"
					id="date"
					name="date"
					min={collection.start_date || ''}
					max={collection.end_date || ''}
					bind:value={newNote.date}
					class="input input-bordered w-full max-w-xs mt-1"
				/>
			</div>
			<div class="form-control mb-2">
				<label for="content">Content</label>
				<textarea
					id="content"
					class="textarea textarea-bordered"
					bind:value={newNote.content}
					rows="5"
				></textarea>
			</div>
			{#if collection.is_public}
				<p class="text-warning mb-1">
					This note will be public because it is in a public collection.
				</p>
			{/if}
			<button class="btn btn-primary" on:click={save}>Save</button>
			<button class="btn btn-neutral" on:click={close}>Close</button>
		</form>
	</div>
</dialog>
