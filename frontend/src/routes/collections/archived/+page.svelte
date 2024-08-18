<script lang="ts">
	import CollectionCard from '$lib/components/CollectionCard.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Collection } from '$lib/types';

	export let data: any;
	console.log(data);

	let collections: Collection[] = data.props.adventures || [];

	function deleteCollection(event: CustomEvent<string>) {
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
