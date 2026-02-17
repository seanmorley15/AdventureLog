<script lang="ts">
	import { t } from 'svelte-i18n';
	import { createEventDispatcher } from 'svelte';
	import StarRating from '$lib/components/StarRating.svelte';

	const dispatch = createEventDispatcher();

	// Required props
	export let name: string;
	export let images: { image: string; is_primary?: boolean }[] = [];

	// Optional props
	export let icon: string = '';
	export let averageRating: number | null = null;
	export let rating: number | null = null;
	export let ratingCount: number | null = null;
	export let ratingRefreshKey: number = 0;

	// Badges slot content via props
	export let badges: { label: string; class: string; href?: string }[] = [];

	let currentSlide = 0;

	function goToSlide(index: number) {
		currentSlide = index;
	}

	function openImageModal(index: number) {
		dispatch('openImage', index);
	}
</script>

<div class="relative">
	<div
		class="hero min-h-[60vh] relative overflow-hidden"
		class:min-h-[30vh]={!images || images.length === 0}
	>
		<!-- Background: Images or Gradient -->
		{#if images && images.length > 0}
			<div class="hero-overlay bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
			{#each images as image, i}
				<div
					class="absolute inset-0 transition-opacity duration-500"
					class:opacity-100={i === currentSlide}
					class:opacity-0={i !== currentSlide}
				>
					<button
						class="w-full h-full p-0 bg-transparent border-0"
						on:click={() => openImageModal(i)}
						aria-label={`View full image of ${name}`}
					>
						<img src={image.image} class="w-full h-full object-cover" alt={name} />
					</button>
				</div>
			{/each}
		{:else}
			<div class="absolute inset-0 bg-gradient-to-br from-primary/20 to-secondary/20"></div>
		{/if}

		<!-- Content -->
		<div
			class="hero-content relative z-10 text-center"
			class:text-white={images?.length > 0}
		>
			<div class="max-w-4xl">
				<!-- Title with optional icon -->
				<div class="flex justify-center items-center gap-3 mb-4">
					{#if icon}
						<span class="text-5xl">{icon}</span>
					{/if}
					<h1 class="text-6xl font-bold drop-shadow-lg">{name}</h1>
				</div>

				<!-- Rating -->
				{#key ratingRefreshKey}
					{#if averageRating !== undefined && averageRating !== null}
						<div class="flex flex-col items-center mb-6">
							<StarRating rating={averageRating} size="2xl" readonly showValue={false} />
							<span class="text-sm opacity-70 mt-1">{$t('adventures.average_rating')} ({ratingCount ?? 0} {ratingCount === 1 ? $t('adventures.rating') : $t('adventures.ratings')})</span>
						</div>
					{:else if rating !== undefined && rating !== null}
						<div class="flex flex-col items-center mb-6">
							<StarRating rating={rating} size="2xl" readonly showValue={false} />
							<span class="text-sm opacity-70 mt-1">(1 {$t('adventures.rating')})</span>
						</div>
					{/if}
				{/key}

				<!-- Quick Info Badges -->
				{#if badges.length > 0}
					<div class="flex flex-wrap justify-center gap-4 mb-6">
						{#each badges as badge}
							{#if badge.href}
								<a
									href={badge.href}
									class="badge badge-lg font-semibold px-4 py-3 cursor-pointer hover:brightness-110 transition-all {badge.class}"
								>
									{badge.label}
								</a>
							{:else}
								<div class="badge badge-lg font-semibold px-4 py-3 {badge.class}">
									{badge.label}
								</div>
							{/if}
						{/each}
					</div>
				{/if}

				<!-- Additional badges via slot -->
				<slot name="badges" />

				<!-- Image Navigation (only shown when multiple images exist) -->
				{#if images && images.length > 1}
					<div class="w-full max-w-md mx-auto">
						<!-- Navigation arrows and current position -->
						<div class="flex items-center justify-center gap-4 mb-3">
							<button
								on:click={() => goToSlide(currentSlide > 0 ? currentSlide - 1 : images.length - 1)}
								class="btn btn-circle btn-sm btn-primary"
								aria-label={$t('adventures.previous_image')}
							>
								❮
							</button>

							<div class="text-sm font-medium bg-black/50 px-3 py-1 rounded-full">
								{currentSlide + 1} / {images.length}
							</div>

							<button
								on:click={() => goToSlide(currentSlide < images.length - 1 ? currentSlide + 1 : 0)}
								class="btn btn-circle btn-sm btn-primary"
								aria-label={$t('adventures.next_image')}
							>
								❯
							</button>
						</div>

						<!-- Dot navigation -->
						{#if images.length <= 12}
							<div class="flex justify-center gap-2 flex-wrap">
								{#each images as _, i}
									<button
										on:click={() => goToSlide(i)}
										class="btn btn-circle btn-xs transition-all duration-200"
										class:btn-primary={i === currentSlide}
										class:btn-outline={i !== currentSlide}
										class:opacity-50={i !== currentSlide}
									>
										{i + 1}
									</button>
								{/each}
							</div>
						{:else}
							<div class="relative">
								<div
									class="absolute left-0 top-0 bottom-2 w-4 bg-gradient-to-r from-black/30 to-transparent pointer-events-none"
								></div>
								<div
									class="absolute right-0 top-0 bottom-2 w-4 bg-gradient-to-l from-black/30 to-transparent pointer-events-none"
								></div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
