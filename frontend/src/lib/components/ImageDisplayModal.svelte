<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import type { Adventure } from '$lib/types';

	export let image: string;
	export let adventure: Adventure | null = null;

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

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-click-events-have-key-events -->
<dialog id="my_modal_1" class="modal" on:click={handleClickOutside}>
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box w-11/12 max-w-5xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		{#if adventure}
			<div class="modal-header flex justify-between items-center mb-4">
				<h3 class="font-bold text-2xl">{adventure.name}</h3>
				<button class="btn btn-circle btn-neutral" on:click={close}>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-6 w-6"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
			<div
				class="flex justify-center items-center"
				style="display: flex; justify-content: center; align-items: center;"
			>
				<img
					src={image}
					alt={adventure.name}
					style="max-width: 100%; max-height: 75vh; object-fit: contain;"
				/>
			</div>
		{/if}
	</div>
</dialog>
