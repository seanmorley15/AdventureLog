<script lang="ts">
	import { addToast } from '$lib/toasts';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;

	let url: string = '';

	export let name: string | null = null;

	let error = '';

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	async function fetchImage() {
		let res = await fetch(url);
		let data = await res.blob();
		if (!data) {
			error = 'No image found at that URL.';
			return;
		}
		let file = new File([data], 'image.jpg', { type: 'image/jpeg' });
		close();
		dispatch('image', { file });
	}

	async function fetchWikiImage() {
		let res = await fetch(`/api/generate/img/?name=${name}`);
		let data = await res.json();
		if (data.source) {
			let imageUrl = data.source;
			let res = await fetch(imageUrl);
			let blob = await res.blob();
			let file = new File([blob], `${name}.jpg`, { type: 'image/jpeg' });
			close();
			dispatch('image', { file });
		} else {
			error = 'No image found for that Wikipedia article.';
		}
	}

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
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">Image Fetcher with URL</h3>
		<form>
			<input
				type="text"
				class="input input-bordered w-full max-w-xs"
				bind:value={url}
				placeholder="Enter a URL"
			/>
			<button class="btn btn-primary" on:click={fetchImage}>Submit</button>
		</form>

		<h3 class="font-bold text-lg">Image Fetcher from Wikipedia</h3>
		<form>
			<input
				type="text"
				class="input input-bordered w-full max-w-xs"
				bind:value={name}
				placeholder="Enter a Wikipedia Article Name"
			/>
			<button class="btn btn-primary" on:click={fetchWikiImage}>Submit</button>
		</form>

		{#if error}
			<p class="text-red-500">{error}</p>
		{/if}

		<button class="btn btn-primary" on:click={close}>Close</button>
	</div>
</dialog>
