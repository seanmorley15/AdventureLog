<script lang="ts">
	import type { Component } from 'svelte';
	import ImageDisplayModal from './ImageDisplayModal.svelte';
	import ImageFrame from './ImageFrame.svelte';
	import ChevronLeft from '~icons/mdi/chevron-left';
	import ChevronRight from '~icons/mdi/chevron-right';
	import ImageMultipleOutline from '~icons/mdi/image-multiple-outline';
	import ImageOutline from '~icons/mdi/image-outline';
	import type { ContentImage } from '#lib/types.js';

	interface Props {
		images?: ContentImage[];
		name?: string;
		/** Shown when there is no photo: an mdi icon component, or an emoji string (e.g. a category). */
		icon?: string | Component<any> | null;
		/** Show the "2/5" counter when there are several photos. */
		showCount?: boolean;
	}

	let { images = [], name = '', icon = null, showCount = true }: Props = $props();

	let currentSlide = $state(0);
	let showImageModal = $state(false);
	let modalInitialIndex = $state(0);

	let sortedImages = $derived(
		[...images].sort((a, b) => Number(!!b.is_primary) - Number(!!a.is_primary))
	);

	// A new set of photos starts again at the first one.
	$effect(() => {
		if (sortedImages.length > 0) currentSlide = 0;
	});

	function changeSlide(direction: 'next' | 'prev') {
		if (direction === 'next' && currentSlide < sortedImages.length - 1) currentSlide += 1;
		else if (direction === 'prev' && currentSlide > 0) currentSlide -= 1;
	}

	function openImageModal(initialIndex: number = currentSlide) {
		modalInitialIndex = initialIndex;
		showImageModal = true;
	}

	const Icon = $derived(typeof icon === 'string' || !icon ? null : icon);
	const emoji = $derived(typeof icon === 'string' && icon ? icon : null);
</script>

{#if showImageModal && sortedImages.length > 0}
	<ImageDisplayModal
		images={sortedImages}
		initialIndex={modalInitialIndex}
		on:close={() => (showImageModal = false)}
		{name}
	/>
{/if}

<figure class="relative aspect-[16/10] w-full overflow-hidden bg-base-200">
	{#if sortedImages.length > 0}
		<button
			type="button"
			onclick={(e) => {
				e.stopPropagation();
				openImageModal(currentSlide);
			}}
			class="group block h-full w-full cursor-zoom-in"
			aria-label={name || 'Image'}
		>
			<ImageFrame source={sortedImages[currentSlide].source} className="h-full w-full">
				<img
					src={sortedImages[currentSlide].image}
					class="h-full w-full object-cover transition-[filter] group-hover:brightness-105"
					alt={name || 'Image'}
					loading="lazy"
				/>
			</ImageFrame>
		</button>

		{#if sortedImages.length > 1}
			{#if currentSlide > 0}
				<button
					type="button"
					onclick={(e) => {
						e.stopPropagation();
						changeSlide('prev');
					}}
					class="btn btn-circle btn-xs absolute left-2 top-1/2 -translate-y-1/2 border-none bg-base-100/85 text-base-content shadow-sm backdrop-blur-sm"
					aria-label="Previous image"
				>
					<ChevronLeft class="h-4 w-4" />
				</button>
			{/if}
			{#if currentSlide < sortedImages.length - 1}
				<button
					type="button"
					onclick={(e) => {
						e.stopPropagation();
						changeSlide('next');
					}}
					class="btn btn-circle btn-xs absolute right-2 top-1/2 -translate-y-1/2 border-none bg-base-100/85 text-base-content shadow-sm backdrop-blur-sm"
					aria-label="Next image"
				>
					<ChevronRight class="h-4 w-4" />
				</button>
			{/if}
			{#if showCount}
				<span
					class="pointer-events-none absolute bottom-2 right-2 inline-flex items-center gap-1 rounded-full bg-base-100/85 px-2 py-0.5 text-xs font-medium text-base-content shadow-xs backdrop-blur-sm"
				>
					<ImageMultipleOutline class="h-3.5 w-3.5" />
					{currentSlide + 1}/{sortedImages.length}
				</span>
			{/if}
		{/if}
	{:else}
		<!-- No photo: a quiet field with the type in a tinted tile, like the detail page header. -->
		<div class="flex h-full w-full items-center justify-center" aria-hidden="true">
			<div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
				{#if Icon}
					<Icon class="h-8 w-8 text-primary" />
				{:else if emoji}
					<span class="select-none text-4xl leading-none">{emoji}</span>
				{:else}
					<ImageOutline class="h-8 w-8 text-primary/60" />
				{/if}
			</div>
		</div>
	{/if}
</figure>
