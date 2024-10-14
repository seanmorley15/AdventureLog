<script lang="ts">
	import { goto } from '$app/navigation';
	import CollectionCard from '$lib/components/CollectionCard.svelte';
	import type { Collection } from '$lib/types';
	import type { PageData } from './$types';

	export let data: PageData;
	console.log(data);
	let collections: Collection[] = data.props.collections;
</script>

{#if collections.length > 0}
	<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
		{#each collections as collection}
			<CollectionCard type="viewonly" {collection} />
		{/each}
	</div>
{:else}
	<p class="text-center font-semibold text-xl mt-6">
		No collections found that are shared with you.
		{#if data.user && !data.user?.public_profile}
			<p>In order to allow users to share with you, you need your profile set to public.</p>
			<button class="btn btn-neutral mt-4" on:click={() => goto('/settings')}>Go to Settings</button
			>
		{/if}
	</p>
{/if}

<svelte:head>
	<title>Shared Collections</title>
	<meta name="description" content="Collections shared with you by other users." />
</svelte:head>
