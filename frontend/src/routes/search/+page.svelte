<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure, OpenStreetMapPlace } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { page } from '$app/stores';

	export let data: PageData;

	function deleteAdventure(event: CustomEvent<number>) {
		adventures = adventures.filter((adventure) => adventure.id !== event.detail);
	}

	let osmResults: OpenStreetMapPlace[] = [];
	let adventures: Adventure[] = [];

	let query: string | null = '';

	onMount(() => {
		const urlParams = new URLSearchParams(window.location.search);
		query = urlParams.get('query');

		fetchData();
	});

	async function fetchData() {
		let res = await fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=jsonv2`);
		const data = await res.json();
		osmResults = data;
	}

	onMount(async () => {
		let res = await fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=jsonv2`);
		const data = await res.json();
		osmResults = data;
	});

	console.log(data);

	if (data.props) {
		adventures = data.props.adventures;
	}
</script>

{#if adventures.length === 0 && osmResults.length === 0}
	<NotFound error={data.error} />
{/if}

{#if adventures.length > 0}
	<h2 class="text-center font-bold text-2xl mb-4">AdventureLog Results</h2>
	<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
		{#each adventures as adventure}
			<AdventureCard
				user={data.user}
				type={adventure.type}
				{adventure}
				on:delete={deleteAdventure}
			/>
		{/each}
	</div>
{/if}
{#if adventures.length > 0 && osmResults.length > 0}
	<div class="divider"></div>
{/if}
{#if osmResults.length > 0}
	<h2 class="text-center font-bold text-2xl mb-4">Online Results</h2>
	<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
		{#each osmResults as result}
			<div class="bg-base-300 rounded-lg shadow-md p-4 w-96 mb-2">
				<h2 class="text-xl font-bold">{result.display_name}</h2>
				<p>{result.type}</p>
				<p>{result.lat}, {result.lon}</p>
			</div>
		{/each}
	</div>
{/if}
