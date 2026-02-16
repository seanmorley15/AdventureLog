<script lang="ts">
	import { processTags } from './visitUtils';

	export let tags: string[] | undefined | null = null;

	$: processedTags = processTags(tags);
</script>

{#if processedTags.displayTags.length > 0}
	<div class="flex flex-wrap gap-2">
		{#each processedTags.displayTags as tag}
			<span class="badge badge-ghost badge-sm">{tag}</span>
		{/each}
		{#if processedTags.remainingCount > 0}
			<span class="badge badge-ghost badge-sm">+{processedTags.remainingCount}</span>
		{/if}
	</div>
{/if}
