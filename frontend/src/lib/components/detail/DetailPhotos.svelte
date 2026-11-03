<script lang="ts">
	import type { ContentImage } from '#lib/types.js';
	import ImageFrame from '#lib/components/ImageFrame.svelte';

	interface Props {
		images: ContentImage[];
		name?: string;
		onOpen?: (index: number) => void;
		/** Columns of the grid at the widest size. */
		columns?: 2 | 3 | 4;
	}

	let { images, name = '', onOpen, columns = 3 }: Props = $props();

	const COLUMNS = {
		2: 'grid-cols-2',
		3: 'grid-cols-2 sm:grid-cols-3',
		4: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4'
	} as const;
</script>

<div class="grid gap-2 {COLUMNS[columns]}">
	{#each images as image, i (image.id ?? image.image)}
		<button
			type="button"
			class="aspect-square w-full overflow-hidden rounded-xl bg-base-200"
			aria-label={`${name} ${i + 1}`}
			onclick={() => onOpen?.(i)}
		>
			<ImageFrame source={image.source} className="h-full w-full">
				<img
					src={image.image}
					alt={`${name} ${i + 1}`}
					loading="lazy"
					class="h-full w-full object-cover transition-transform duration-500 hover:scale-105"
				/>
			</ImageFrame>
		</button>
	{/each}
</div>
