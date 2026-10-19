<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { ContentImage } from '$lib/types';
	import ImageFrame from '$lib/components/ImageFrame.svelte';
	import ChevronLeft from '~icons/mdi/chevron-left';
	import ChevronRight from '~icons/mdi/chevron-right';
	import ImageMultiple from '~icons/mdi/image-multiple-outline';

	interface Props {
		images: ContentImage[];
		/** Alt text for the photos. */
		name?: string;
		/** Clicking a photo opens it full screen. */
		onOpen?: (index: number) => void;
	}

	let { images, name = '', onOpen }: Props = $props();

	let current = $state(0);
	let index = $derived(Math.min(current, Math.max(images.length - 1, 0)));

	function step(direction: -1 | 1) {
		current = (index + direction + images.length) % images.length;
	}
</script>

<!-- A slim photo strip, not a full-screen hero: the page content starts immediately. -->
{#if images.length > 0}
	<div class="relative h-[30vh] max-h-80 min-h-44 overflow-hidden bg-neutral">
		{#each images as image, i (image.id ?? image.image)}
			<div
				class="absolute inset-0 transition-opacity duration-500 {i === index
					? 'opacity-100'
					: 'pointer-events-none opacity-0'}"
				aria-hidden={i !== index}
			>
				<button
					type="button"
					class="h-full w-full border-0 bg-transparent p-0"
					aria-label={$t('detail.open_photo', { values: { name } })}
					tabindex={i === index ? 0 : -1}
					onclick={() => onOpen?.(i)}
				>
					<ImageFrame source={image.source} className="h-full w-full">
						<img
							src={image.image}
							alt={name}
							loading={i === 0 ? 'eager' : 'lazy'}
							class="h-full w-full object-cover"
						/>
					</ImageFrame>
				</button>
			</div>
		{/each}
		<div
			class="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-transparent"
		></div>

		{#if images.length > 1}
			<button
				type="button"
				class="btn btn-circle btn-sm absolute left-3 top-1/2 -translate-y-1/2 border-0 bg-base-100/80 hover:bg-base-100"
				aria-label={$t('adventures.previous_image')}
				onclick={() => step(-1)}
			>
				<ChevronLeft class="h-5 w-5" />
			</button>
			<button
				type="button"
				class="btn btn-circle btn-sm absolute right-3 top-1/2 -translate-y-1/2 border-0 bg-base-100/80 hover:bg-base-100"
				aria-label={$t('adventures.next_image')}
				onclick={() => step(1)}
			>
				<ChevronRight class="h-5 w-5" />
			</button>
		{/if}
		<span class="badge absolute bottom-3 right-3 gap-1 border-0 bg-base-100/85 font-medium">
			<ImageMultiple class="h-3.5 w-3.5" />
			{index + 1} / {images.length}
		</span>
	</div>
{/if}
