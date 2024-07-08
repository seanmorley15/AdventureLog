<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import type { Adventure } from '$lib/types';
	import type { PageData } from './$types';

	export let data: PageData;
	console.log(data);

	let adventures: Adventure[] = data.props.featured;
</script>

<h1 class="text-center font-bold text-4xl mb-4">Featured Adventures</h1>
<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
	{#each adventures as adventure}
		<AdventureCard type="featured" {adventure} />
	{/each}
</div>

{#if adventures.length === 0}
	<div class="flex justify-center items-center h-96">
		<p class="text-2xl text-primary-content">No visited adventures yet!</p>
	</div>
{/if}
