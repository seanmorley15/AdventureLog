<script lang="ts">
	import ImageDisplayModal from './ImageDisplayModal.svelte';
	import { t } from 'svelte-i18n';
	import type { ContentImage } from '$lib/types';
	export let images: ContentImage[] = [];
	export let name: string = '';
	export let icon: string = '';

	let currentSlide = 0;
	let showImageModal = false;
	let modalInitialIndex = 0;

	$: sortedImages = [...images].sort((a, b) => {
		if (a.is_primary && !b.is_primary) {
			return -1;
		} else if (!a.is_primary && b.is_primary) {
			return 1;
		} else {
			return 0;
		}
	});

	$: {
		if (sortedImages.length > 0) {
			currentSlide = 0;
		}
	}

	function changeSlide(direction: string) {
		if (direction === 'next' && currentSlide < sortedImages.length - 1) {
			currentSlide = currentSlide + 1;
		} else if (direction === 'prev' && currentSlide > 0) {
			currentSlide = currentSlide - 1;
		}
	}

	function openImageModal(initialIndex: number = currentSlide) {
		modalInitialIndex = initialIndex;
		showImageModal = true;
	}

	function closeImageModal() {
		showImageModal = false;
	}
</script>

{#if showImageModal && sortedImages.length > 0}
	<ImageDisplayModal
		images={sortedImages}
		initialIndex={modalInitialIndex}
		on:close={closeImageModal}
		{name}
	/>
{/if}

<figure>
	{#if sortedImages && sortedImages.length > 0}
		<div class="carousel w-full relative">
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<div class="carousel-item w-full block">
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<!-- svelte-ignore a11y-missing-attribute -->
				<a
					on:click|stopPropagation={() => openImageModal(currentSlide)}
					class="cursor-pointer relative group"
				>
					<img
						src={sortedImages[currentSlide].image}
						class="w-full h-48 object-cover transition-all group-hover:brightness-110"
						alt={name || 'Image'}
					/>

					<!-- Overlay indicator for multiple images -->
					<!-- {#if sortedImages.length > 1}
						<div
							class="absolute top-3 right-3 bg-black/60 text-white px-2 py-1 rounded-lg text-xs font-medium"
						>
							{currentSlide + 1} / {sortedImages.length}
						</div>
					{/if} -->

					<!-- Click to expand hint -->
					<!-- <div
						class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-all flex items-center justify-center"
					>
						<div
							class="opacity-0 group-hover:opacity-100 transition-all bg-white/90 rounded-full p-2"
						>
							<svg
								class="w-6 h-6 text-gray-800"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"
								/>
							</svg>
						</div>
					</div> -->
				</a>

				{#if sortedImages.length > 1}
					<div class="absolute inset-0 flex items-center justify-between pointer-events-none">
						{#if currentSlide > 0}
							<button
								on:click|stopPropagation={() => changeSlide('prev')}
								class="btn btn-circle btn-sm mr-2 pointer-events-auto bg-neutral border-none text-neutral-content shadow-lg"
								aria-label="Previous image"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M15 19l-7-7 7-7"
									/>
								</svg>
							</button>
						{:else}
							<div class="w-12"></div>
						{/if}

						{#if currentSlide < sortedImages.length - 1}
							<button
								on:click|stopPropagation={() => changeSlide('next')}
								class="btn btn-circle btn-sm mr-2 pointer-events-auto bg-neutral border-none text-neutral-content shadow-lg"
								aria-label="Next image"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 5l7 7-7 7"
									/>
								</svg>
							</button>
						{:else}
							<div class="w-12"></div>
						{/if}
					</div>

					<!-- Dot indicators at bottom -->
					<!-- {#if sortedImages.length > 1}
						<div class="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2">
							{#each sortedImages as _, index}
								<button
									on:click|stopPropagation={() => (currentSlide = index)}
									class="w-2 h-2 rounded-full transition-all pointer-events-auto {index ===
									currentSlide
										? 'bg-white shadow-lg'
										: 'bg-white/50 hover:bg-white/80'}"
									aria-label="Go to image {index + 1}"
								/>
							{/each}
						</div>
					{/if} -->
				{/if}
			</div>
		</div>
	{:else}
		<!-- Fallback with emoji icon as main image -->
		<div class="w-full h-48 relative flex items-center justify-center">
			{#if icon}
				<!-- Clean background with emoji as the focal point -->
				<div
					class="w-full h-full bg-gradient-to-r from-success via-base to-primary flex items-center justify-center"
				>
					<div class="text-8xl select-none">
						{icon}
					</div>
				</div>
			{:else}
				<!-- Original gradient fallback when no icon -->
				<div class="w-full h-full bg-gradient-to-r from-success via-base to-primary"></div>
			{/if}
		</div>
	{/if}
</figure>
