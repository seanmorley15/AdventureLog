<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	// Props
	export let rating: number | null = null;
	export let maxStars: number = 5;
	export let size: 'sm' | 'md' | 'lg' | 'xl' | '2xl' = 'md';
	export let readonly: boolean = true;
	export let showValue: boolean = false;

	const dispatch = createEventDispatcher<{ change: number | null }>();

	// Size classes
	const sizeClasses = {
		sm: 'w-4 h-4',
		md: 'w-5 h-5',
		lg: 'w-6 h-6',
		xl: 'w-8 h-8',
		'2xl': 'w-10 h-10'
	};

	// Calculate the fill percentage for each star
	function getStarFill(starIndex: number, currentRating: number | null): number {
		if (currentRating === null || currentRating === undefined) return 0;

		const starNumber = starIndex + 1;
		if (currentRating >= starNumber) {
			return 100; // Full star
		} else if (currentRating > starIndex) {
			// Partial star - calculate percentage
			return Math.round((currentRating - starIndex) * 100);
		}
		return 0; // Empty star
	}

	// Hover state for interactive mode
	let hoverRating: number | null = null;

	function handleClick(starIndex: number) {
		if (readonly) return;
		const newRating = starIndex + 1;
		// Toggle off if clicking same star
		if (rating === newRating) {
			rating = null;
			dispatch('change', null);
		} else {
			rating = newRating;
			dispatch('change', newRating);
		}
	}

	function handleMouseEnter(starIndex: number) {
		if (readonly) return;
		hoverRating = starIndex + 1;
	}

	function handleMouseLeave() {
		if (readonly) return;
		hoverRating = null;
	}

	// Use hover rating for display when hovering, otherwise use actual rating
	$: displayRating = hoverRating !== null ? hoverRating : rating;
</script>

<div class="inline-flex items-center gap-1">
	<div
		class="flex items-center gap-0.5"
		class:cursor-pointer={!readonly}
		role={readonly ? 'img' : 'group'}
		aria-label={rating !== null ? `Rating: ${rating} out of ${maxStars} stars` : 'No rating'}
	>
		{#each Array(maxStars) as _, i}
			{@const fillPercent = getStarFill(i, displayRating)}
			<button
				type="button"
				class="relative {sizeClasses[size]} transition-transform {!readonly ? 'hover:scale-110' : ''}"
				class:cursor-default={readonly}
				disabled={readonly}
				on:click={() => handleClick(i)}
				on:mouseenter={() => handleMouseEnter(i)}
				on:mouseleave={handleMouseLeave}
				aria-label="Star {i + 1}"
			>
				<!-- Background (empty) star -->
				<svg
					class="absolute inset-0 {sizeClasses[size]} text-base-content/20"
					viewBox="0 0 24 24"
					fill="currentColor"
				>
					<path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
				</svg>

				<!-- Filled star with clip for partial fill -->
				<svg
					class="absolute inset-0 {sizeClasses[size]} text-warning"
					viewBox="0 0 24 24"
					fill="currentColor"
					style="clip-path: inset(0 {100 - fillPercent}% 0 0);"
				>
					<path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
				</svg>
			</button>
		{/each}
	</div>

	{#if showValue && rating !== null}
		<span class="text-sm text-base-content/60 ml-1">({rating})</span>
	{/if}
</div>
