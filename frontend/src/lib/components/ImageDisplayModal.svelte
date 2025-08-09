<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';
	import type { ContentImage } from '$lib/types';
	export let images: ContentImage[] = [];
	export let initialIndex: number = 0;
	export let name: string = '';
	export let location: string = '';

	let currentIndex = initialIndex;
	let currentImage = images[currentIndex]?.image || '';

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		// Set initial values
		updateCurrentSlide(initialIndex);
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
		} else if (event.key === 'ArrowLeft') {
			previousSlide();
		} else if (event.key === 'ArrowRight') {
			nextSlide();
		}
	}

	function handleClickOutside(event: MouseEvent) {
		if (event.target === modal) {
			close();
		}
	}

	function updateCurrentSlide(index: number) {
		currentIndex = index;
		currentImage = images[currentIndex]?.image || '';
	}

	function nextSlide() {
		if (images.length > 0) {
			const nextIndex = (currentIndex + 1) % images.length;
			updateCurrentSlide(nextIndex);
		}
	}

	function previousSlide() {
		if (images.length > 0) {
			const prevIndex = (currentIndex - 1 + images.length) % images.length;
			updateCurrentSlide(prevIndex);
		}
	}

	function goToSlide(index: number) {
		updateCurrentSlide(index);
	}

	// Reactive statement to handle prop changes
	$: if (images.length > 0 && currentIndex >= images.length) {
		updateCurrentSlide(0);
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<!-- svelte-ignore a11y-click-events-have-key-events -->
<dialog id="my_modal_1" class="modal backdrop-blur-sm" on:click={handleClickOutside}>
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		{#if images.length > 0 && currentImage}
			<!-- Header -->
			<div
				class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
			>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<div class="p-2 bg-primary/10 rounded-xl">
							<svg
								class="w-6 h-6 text-primary"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
								/>
							</svg>
						</div>
						<div>
							<h1 class="text-2xl font-bold text-primary">
								{name}
							</h1>
							{#if images.length > 1}
								<p class="text-sm text-base-content/60">
									{currentIndex + 1} of {images.length}
									{$t('adventures.images')}
								</p>
							{/if}
						</div>
					</div>

					<!-- Navigation indicators for multiple images -->
					{#if images.length > 1}
						<div class="hidden md:flex items-center gap-2">
							<div class="flex gap-1">
								{#each images as _, index}
									<button
										class="w-2 h-2 rounded-full transition-all {index === currentIndex
											? 'bg-primary'
											: 'bg-base-300 hover:bg-base-400'}"
										on:click={() => goToSlide(index)}
									/>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Close Button -->
					<button class="btn btn-ghost btn-square" on:click={close}>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>
			</div>

			<!-- Image Display Area -->
			<div class="relative h-[75vh] flex justify-center items-center max-w-full">
				<!-- Previous Button -->
				{#if images.length > 1}
					<button
						class="absolute left-4 top-1/2 -translate-y-1/2 z-20 btn btn-circle btn-primary/80 hover:btn-primary"
						on:click={previousSlide}
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15 19l-7-7 7-7"
							/>
						</svg>
					</button>
				{/if}

				<!-- Main Image -->
				<div class="flex justify-center items-center max-w-full">
					<img
						src={currentImage}
						alt={name}
						class="max-w-full max-h-[75vh] object-contain rounded-lg shadow-lg"
						style="max-width: 100%; max-height: 75vh; object-fit: contain;"
					/>
				</div>

				<!-- Next Button -->
				{#if images.length > 1}
					<button
						class="absolute right-4 top-1/2 -translate-y-1/2 z-20 btn btn-circle btn-primary/80 hover:btn-primary"
						on:click={nextSlide}
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 5l7 7-7 7"
							/>
						</svg>
					</button>
				{/if}
			</div>

			<!-- Thumbnail Navigation (for multiple images) -->
			{#if images.length > 1}
				<div class="mt-6 px-2">
					<div class="flex gap-2 overflow-x-auto pb-2">
						{#each images as imageData, index}
							<button
								class="flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all {index ===
								currentIndex
									? 'border-primary shadow-lg'
									: 'border-base-300 hover:border-base-400'}"
								on:click={() => goToSlide(index)}
							>
								<img src={imageData.image} alt={name} class="w-full h-full object-cover" />
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Footer -->
			<div
				class="bottom-0 bg-base-100/90 backdrop-blur-lg border-t border-base-300 -mx-6 -mb-6 px-6 py-4 mt-6 rounded-lg"
			>
				<div class="flex items-center justify-between">
					<div class="text-sm text-base-content/60">
						{#if location}
							<span class="flex items-center gap-1">
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
									/>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
									/>
								</svg>
								{location}
							</span>
						{/if}
					</div>
					<div class="flex items-center gap-3">
						{#if images.length > 1}
							<div class="text-sm text-base-content/60">
								{$t('adventures.image_modal_navigate')}
							</div>
						{/if}
						<button class="btn btn-primary gap-2" on:click={close}>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M6 18L18 6M6 6l12 12"
								/>
							</svg>
							{$t('about.close')}
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
</dialog>
