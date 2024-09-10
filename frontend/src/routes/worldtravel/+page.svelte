<script lang="ts">
	import CountryCard from '$lib/components/CountryCard.svelte';
	import type { Country } from '$lib/types';
	import type { PageData } from './$types';

	let searchQuery: string = '';

	let filteredCountries: Country[] = [];

	export let data: PageData;
	console.log(data);

	const countries: Country[] = data.props?.countries || [];

	$: {
		// if query is empty, show all countries
		if (searchQuery === '') {
			filteredCountries = countries;
		} else {
			// otherwise, filter countries by name
			filteredCountries = countries.filter((country) =>
				country.name.toLowerCase().includes(searchQuery.toLowerCase())
			);
		}
	}
</script>

<h1 class="text-center font-bold text-4xl">Country List</h1>
<!-- result count -->
<p class="text-center mb-4">
	{filteredCountries.length} countries found
</p>

<div class="flex items-center justify-center mb-4">
	<input
		type="text"
		placeholder="Search"
		class="input input-bordered w-full max-w-xs"
		bind:value={searchQuery}
	/>
</div>
<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
	{#each filteredCountries as country}
		<CountryCard {country} />
		<!-- <p>Name: {item.name}, Continent: {item.continent}</p> -->
	{/each}
</div>

<svelte:head>
	<title>Countries | World Travel</title>
	<meta name="description" content="Explore the world and add countries to your visited list!" />
</svelte:head>
