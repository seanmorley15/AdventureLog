<script lang="ts">
	import type { Adventure } from '$lib/types';
	import ImageDisplayModal from './ImageDisplayModal.svelte';
	import { t } from 'svelte-i18n';

	export let adventures: Adventure[] = [];

	let currentSlide = 0;
	let image_url: string | null = null;

	$: adventure_images = adventures.flatMap((adventure) =>
		adventure.images.map((image) => ({ image: image.image, adventure: adventure }))
	);

	$: {
		if (adventure_images.length > 0) {
			currentSlide = 0;
		}
	}

	function changeSlide(direction: string) {
		if (direction === 'next' && currentSlide < adventure_images.length - 1) {
			currentSlide = currentSlide + 1;
		} else if (direction === 'prev' && currentSlide > 0) {
			currentSlide = currentSlide - 1;
		}
	}
</script>

{#if image_url}
	<ImageDisplayModal
		adventure={adventure_images[currentSlide].adventure}
		image={image_url}
		on:close={() => (image_url = null)}
	/>
{/if}

<figure>
	{#if adventure_images && adventure_images.length > 0}
		<div class="carousel w-full relative">
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<div class="carousel-item w-full block">
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<!-- svelte-ignore a11y-missing-attribute -->
				<a
					on:click|stopPropagation={() => (image_url = adventure_images[currentSlide].image)}
					class="cursor-pointer"
				>
					<img
						src={adventure_images[currentSlide].image}
						class="w-full h-48 object-cover"
						alt={adventure_images[currentSlide].adventure.name}
					/>
				</a>

				{#if adventure_images.length > 1}
					<div class="absolute inset-0 flex items-center justify-between pointer-events-none">
						{#if currentSlide > 0}
							<button
								on:click|stopPropagation={() => changeSlide('prev')}
								class="btn btn-circle btn-sm ml-2 pointer-events-auto">❮</button
							>
						{:else}
							<div class="w-12"></div>
						{/if}

						{#if currentSlide < adventure_images.length - 1}
							<button
								on:click|stopPropagation={() => changeSlide('next')}
								class="btn btn-circle mr-2 btn-sm pointer-events-auto">❯</button
							>
						{:else}
							<div class="w-12"></div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{:else}
		<!-- svelte-ignore a11y-img-redundant-alt -->
		<img
			src={`https://placehold.co/300?text=${$t('adventures.no_image_found')}&font=roboto`}
			alt="No image available"
			class="w-full h-48 object-cover"
		/>
	{/if}
</figure>
