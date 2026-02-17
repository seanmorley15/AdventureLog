<script lang="ts">
	/**
	 * RatingFilter - Star rating filter with interactive selector (collapsible)
	 */
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import Star from '~icons/mdi/star';

	export let minRating: string = 'all';
	export let collapsed: boolean = false;

	const dispatch = createEventDispatcher<{ change: string }>();

	let ratingHover: number | null = null;

	function handleRatingChange(rating: number) {
		if (minRating === rating.toString()) {
			minRating = 'all';
		} else {
			minRating = rating.toString();
		}
		dispatch('change', minRating);
	}

	function clearRating() {
		minRating = 'all';
		dispatch('change', minRating);
	}

	$: isFiltered = minRating !== 'all';
</script>

<div class="collapse collapse-arrow bg-base-200/50 rounded-box">
	<input type="checkbox" checked={!collapsed} />
	<div class="collapse-title font-medium flex items-center gap-2 py-2 min-h-0">
		<Star class="w-5 h-5" />
		{$t('adventures.min_rating')}
		{#if isFiltered}
			<span class="badge badge-warning badge-sm">{minRating}+</span>
		{/if}
	</div>
	<div class="collapse-content !pb-2">
		<div class="flex flex-col gap-1">
			<!-- Interactive star selector -->
			<div
				class="flex items-center justify-center gap-0"
				on:mouseleave={() => (ratingHover = null)}
				role="group"
				aria-label="Rating filter"
			>
				{#each [1, 2, 3, 4, 5] as rating}
					{@const isActive = minRating !== 'all' && rating <= parseInt(minRating)}
					{@const isHovered = ratingHover !== null && rating <= ratingHover}
					<button
						type="button"
						class="btn btn-ghost btn-sm p-0.5 min-h-0 h-auto transition-transform hover:scale-110"
						on:click={() => handleRatingChange(rating)}
						on:mouseenter={() => (ratingHover = rating)}
						aria-label="Filter by {rating}+ stars"
					>
						<Star
							class="w-7 h-7 transition-all duration-150"
							style="color: {isActive || isHovered ? '#FBBD23' : 'oklch(var(--bc) / 0.2)'};"
						/>
					</button>
				{/each}
			</div>
			<!-- Current filter display -->
			<div class="text-center text-sm text-base-content/70">
				{#if minRating !== 'all'}
					<span class="font-medium">{minRating}+ {$t('adventures.stars')}</span>
					<button class="btn btn-ghost btn-xs ml-1" on:click={clearRating}>
						{$t('adventures.clear')}
					</button>
				{:else}
					<span>{$t('adventures.all')}</span>
				{/if}
			</div>
		</div>
	</div>
</div>
