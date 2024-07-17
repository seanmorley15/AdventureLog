<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure } from '$lib/types';
	import type { PageData } from './$types';

	export let data: PageData;

	console.log(data);
	let adventures: Adventure[] = [];
	if (data.props) {
		adventures = data.props.adventures;
	}
</script>

{#if adventures.length === 0}
	<NotFound />
{:else}
	<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
		{#each adventures as adventure}
			<AdventureCard type={adventure.type} {adventure} />
		{/each}
	</div>
{/if}
