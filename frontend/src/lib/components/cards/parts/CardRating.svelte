<script lang="ts">
	import Star from '~icons/mdi/star';

	interface Props {
		/** 0–5. Renders nothing when empty. */
		rating?: number | null;
	}

	let { rating = null }: Props = $props();
</script>

{#if rating}
	<span class="inline-flex items-center gap-1 text-sm" aria-label={`${rating}/5`}>
		<Star class="h-4 w-4 text-warning" />
		<span class="font-medium">{rating}</span><span class="-ml-0.5 text-base-content/50">/5</span>
	</span>
{/if}
