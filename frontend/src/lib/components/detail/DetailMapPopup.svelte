<script lang="ts">
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';

	interface Props {
		title: string;
		/** A second line, e.g. the type with its icon. */
		subtitle?: string;
		rating?: number | null;
		address?: string | null;
	}

	let { title, subtitle = '', rating = null, address = null }: Props = $props();
</script>

<!-- Map popups are light, whatever the theme, so the text is fixed dark. -->
<div class="p-2">
	<div class="mb-1 text-lg font-bold text-black">{title}</div>
	{#if subtitle}
		<p class="mb-2 text-sm font-semibold text-black">{subtitle}</p>
	{/if}
	{#if rating}
		<div class="mb-2 flex items-center gap-1">
			{#each [1, 2, 3, 4, 5] as star}
				{#if star <= rating}
					<Star class="h-4 w-4 fill-current text-warning" />
				{:else}
					<StarOutline class="h-4 w-4 text-gray-400" />
				{/if}
			{/each}
			<span class="ml-1 text-xs text-black">({rating}/5)</span>
		</div>
	{/if}
	{#if address}
		<div class="text-xs text-black">📍 {address}</div>
	{/if}
</div>
