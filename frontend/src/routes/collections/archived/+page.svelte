<script lang="ts">
	import { enhance, deserialize } from '$app/forms';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import CollectionCard from '$lib/components/CollectionCard.svelte';
	import EditAdventure from '$lib/components/EditAdventure.svelte';
	import EditCollection from '$lib/components/EditCollection.svelte';
	import NewAdventure from '$lib/components/NewAdventure.svelte';
	import NewCollection from '$lib/components/NewCollection.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure, Collection } from '$lib/types';

	import Plus from '~icons/mdi/plus';

	export let data: any;
	console.log(data);

	let collections: Collection[] = data.props.adventures || [];

	function deleteCollection(event: CustomEvent<number>) {
		collections = collections.filter((collection) => collection.id !== event.detail);
	}
</script>

<div class="drawer lg:drawer-open">
	<div class="drawer-content">
		<!-- Page content -->
		<h1 class="text-center font-bold text-4xl mb-6">Archived Collections</h1>
		{#if collections.length === 0}
			<NotFound error={undefined} />
		{/if}
		<div class="p-4">
			<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
				{#each collections as collection}
					<CollectionCard type="" {collection} on:delete={deleteCollection} />
				{/each}
			</div>
		</div>
	</div>
</div>

<svelte:head>
	<title>Collections</title>
	<meta name="description" content="View your adventure collections." />
</svelte:head>
