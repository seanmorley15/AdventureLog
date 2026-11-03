<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ContentImage } from '#lib/types.js';
	import DetailBanner from './DetailBanner.svelte';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';

	interface Props {
		title: string;
		/** Shown in a tile before the title, e.g. a category or type emoji. */
		emoji?: string | null;
		/** 0–5. Omit to hide. */
		rating?: number | null;
		images?: ContentImage[];
		onOpenImage?: (index: number) => void;
		/** Badges under the title. */
		chips?: Snippet;
		/** Buttons on the right (Edit, Share, …). */
		actions?: Snippet;
		/** Extra line under the chips, e.g. a short address. */
		meta?: Snippet;
	}

	let {
		title,
		emoji = null,
		rating = null,
		images = [],
		onOpenImage,
		chips,
		actions,
		meta
	}: Props = $props();
</script>

<header class="border-b border-base-300 bg-base-100">
	<DetailBanner {images} name={title} onOpen={onOpenImage} />
	<div class="mx-auto max-w-7xl px-4 py-4 sm:px-6">
		<!-- On a phone the buttons drop below the title; from sm up they sit on the right. -->
		<div class="flex flex-wrap items-start gap-3 sm:flex-nowrap sm:gap-4">
			{#if emoji}
				<div
					class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-2xl"
					aria-hidden="true"
				>
					{emoji}
				</div>
			{/if}
			<div class="min-w-0 flex-1 basis-[calc(100%-4rem)] sm:basis-0">
				<h1 class="break-words text-2xl font-bold leading-tight sm:text-3xl">{title}</h1>
				{#if rating !== null && rating !== undefined}
					<div class="mt-1 flex items-center gap-0.5 text-warning" aria-label={`${rating}/5`}>
						{#each [1, 2, 3, 4, 5] as star}
							{#if star <= Math.round(rating)}
								<Star class="h-4 w-4" />
							{:else}
								<StarOutline class="h-4 w-4 opacity-50" />
							{/if}
						{/each}
						<span class="ml-1 text-xs text-base-content/60">{rating}/5</span>
					</div>
				{/if}
				{#if chips}
					<!-- Long values (an address) wrap inside their badge instead of overflowing. -->
					<div
						class="mt-2 flex flex-wrap items-center gap-2 [&_.badge]:h-auto [&_.badge]:max-w-full [&_.badge]:whitespace-normal [&_.badge]:py-1 [&_.badge]:text-left"
					>
						{@render chips()}
					</div>
				{/if}
				{@render meta?.()}
			</div>
			{#if actions}
				<div class="flex w-full shrink-0 flex-wrap items-center gap-2 sm:w-auto">
					{@render actions()}
				</div>
			{/if}
		</div>
	</div>
</header>
