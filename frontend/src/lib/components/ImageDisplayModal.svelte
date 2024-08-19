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
		if (modal) {
			modal.close();
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	function handleClickOutside(event: MouseEvent) {
		if (event.target === modal) {
			close();
		}
	}
</script>

<dialog id="my_modal_1" class="modal" on:click={handleClickOutside}>
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box w-11/12 max-w-5xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<div class="modal-header flex justify-between items-center mb-4">
			<h3 class="font-bold text-2xl">{adventure.name}</h3>
			<button class="close-btn" on:click={close} aria-label="Close" style="font-size: 3rem">&times;</button>
		</div>
		<div class="flex justify-center items-center" style="display: flex; justify-content: center; align-items: center;">
			<img src={image} alt={adventure.name} style="max-width: 100%; max-height: 75vh; object-fit: contain;" />
		</div>
	</div>
</dialog>
