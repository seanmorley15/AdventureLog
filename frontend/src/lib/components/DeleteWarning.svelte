<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;

	export let title: string;
	export let button_text: string;
	export let description: string;
	export let is_warning: boolean;

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function close() {
		dispatch('close');
	}

	function confirm() {
		dispatch('close');
		dispatch('confirm');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}
</script>

<dialog id="my_modal_1" class="modal {is_warning ? 'bg-primary' : ''}">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">{title}</h3>
		<p class="py-1 mb-4">{description}</p>
		<button class="btn btn-{is_warning ? 'warning' : 'primary'} mr-2" on:click={confirm}
			>{button_text}</button
		>
		<button class="btn btn-neutral" on:click={close}>Cancel</button>
	</div>
</dialog>
