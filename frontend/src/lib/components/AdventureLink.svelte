<script lang="ts">
	import { deserialize } from '$app/forms';
	import type { Adventure, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import type { ActionResult } from '@sveltejs/kit';
	import { onMount } from 'svelte';
	import AdventureCard from './AdventureCard.svelte';
	let modal: HTMLDialogElement;

	let adventures: Adventure[] = [];

	export let user: User | null;

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		let formData = new FormData();
		formData.append('include_collections', 'false');
		let res = await fetch(`/adventures?/all`, {
			method: 'POST',
			body: formData
		});

		const result: ActionResult = deserialize(await res.text());
		console.log(result);

		if (result.type === 'success' && result.data) {
			adventures = result.data.adventures as Adventure[];
		}
	});

	function close() {
		dispatch('close');
	}

	function add(event: CustomEvent<Adventure>) {
		adventures = adventures.filter((a) => a.id !== event.detail.id);
		dispatch('add', event.detail);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box w-11/12 max-w-5xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h1 class="text-center font-bold text-4xl mb-6">My Adventures</h1>
		<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
			{#each adventures as adventure}
				<AdventureCard user={user ?? null} type="link" {adventure} on:link={add} />
			{/each}
			{#if adventures.length === 0}
				<p class="text-center text-lg">
					No adventures found that can be linked to this collection.
				</p>
			{/if}
		</div>
		<button class="btn btn-primary" on:click={close}>Close</button>
	</div>
</dialog>
