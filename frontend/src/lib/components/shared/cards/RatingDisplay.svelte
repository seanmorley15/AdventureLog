<script lang="ts">
	import { t } from 'svelte-i18n';
	import StarRating from '../../StarRating.svelte';

	export let averageRating: number | null | undefined = null;
	export let fallbackRating: number | null | undefined = null;
	export let ratingCount: number | null | undefined = null;
	export let size: 'sm' | 'md' | 'lg' | 'xl' | '2xl' = 'sm';
	export let showValue: boolean = true;

	// For fallback display, count is always 1
	$: displayCount = ratingCount ?? (fallbackRating !== null && fallbackRating !== undefined ? 1 : 0);
</script>

{#if averageRating !== null && averageRating !== undefined}
	<div class="flex items-center gap-1">
		<StarRating rating={averageRating} {size} readonly />
		{#if showValue}
			<span class="text-xs text-base-content/60">({displayCount})</span>
		{/if}
	</div>
{:else if fallbackRating !== null && fallbackRating !== undefined}
	<div class="flex items-center gap-1">
		<StarRating rating={fallbackRating} {size} readonly />
		{#if showValue}
			<span class="text-xs text-base-content/60">({displayCount})</span>
		{/if}
	</div>
{/if}
