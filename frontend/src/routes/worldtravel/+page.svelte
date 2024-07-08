<script lang="ts">
	import CountryCard from '$lib/components/CountryCard.svelte';
	import type { Country } from '$lib/types';
	import type { PageData } from './$types';

	export let data: PageData;
	console.log(data);

	const countries: Country[] = data.props?.countries || [];
</script>

<h1 class="text-center font-bold text-4xl mb-4">Country List</h1>

<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
	{#each countries as country}
		<CountryCard countryCode={country.country_code} countryName={country.name} />
		<!-- <p>Name: {item.name}, Continent: {item.continent}</p> -->
	{/each}
</div>

<svelte:head>
	<title>WorldTravel | AdventureLog</title>
	<meta name="description" content="Explore the world and add countries to your visited list!" />
</svelte:head>
