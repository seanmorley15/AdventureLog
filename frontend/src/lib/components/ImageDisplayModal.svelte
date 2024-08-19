<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { appVersion, copyrightYear, versionChangelog } from '$lib/config';
	import type { Adventure } from '$lib/types';

	export let image: string;
	export let adventure: Adventure;

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
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box w-11/12 max-w-5xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold mb-4 text-2xl">{adventure.name}</h3>

		<div class="flex flex-col items-center">
			<img src={image} alt={adventure.name} class="w-full h-full object-cover" />
		</div>

		<button class="btn mt-4 btn-primary" on:click={close}>Close</button>
	</div>
</dialog>
