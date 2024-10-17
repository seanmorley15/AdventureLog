<script lang="ts">
	import CountryCard from '$lib/components/CountryCard.svelte';
	import type { Country } from '$lib/types';
	import type { PageData } from './$types';

	export let data: PageData;
	console.log(data);

	let searchQuery: string = '';

	let filteredCountries: Country[] = [];
	const allCountries: Country[] = data.props?.countries || [];
	let worldSubregions: string[] = [];

	worldSubregions = [...new Set(allCountries.map((country) => country.subregion))];
	// remove blank subregions
	worldSubregions = worldSubregions.filter((subregion) => subregion !== '');
	console.log(worldSubregions);

	let filterOption: string = 'all';
	let subRegionOption: string = '';

	$: {
		if (searchQuery === '') {
			filteredCountries = allCountries;
		} else {
			// otherwise, filter countries by name
			filteredCountries = allCountries.filter((country) =>
				country.name.toLowerCase().includes(searchQuery.toLowerCase())
			);
		}
		if (filterOption === 'partial') {
			filteredCountries = filteredCountries.filter(
				(country) => country.num_visits > 0 && country.num_visits < country.num_regions
			);
		} else if (filterOption === 'complete') {
			filteredCountries = filteredCountries.filter(
				(country) => country.num_visits === country.num_regions
			);
		} else if (filterOption === 'not') {
			filteredCountries = filteredCountries.filter((country) => country.num_visits === 0);
		} else {
			filteredCountries = filteredCountries;
		}

		if (subRegionOption !== '') {
			filteredCountries = filteredCountries.filter(
				(country) => country.subregion === subRegionOption
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
	<div class="join">
		<input
			class="join-item btn"
			type="radio"
			name="filter"
			aria-label="All"
			checked
			on:click={() => (filterOption = 'all')}
		/>
		<input
			class="join-item btn"
			type="radio"
			name="filter"
			aria-label="Partially Visited"
			on:click={() => (filterOption = 'partial')}
		/>
		<input
			class="join-item btn"
			type="radio"
			name="filter"
			aria-label="Completely Visited"
			on:click={() => (filterOption = 'complete')}
		/>
		<input
			class="join-item btn"
			type="radio"
			name="filter"
			aria-label="Not Visited"
			on:click={() => (filterOption = 'not')}
		/>
	</div>
	<select class="select select-bordered w-full max-w-xs ml-4" bind:value={subRegionOption}>
		<option value="">All Subregions</option>
		{#each worldSubregions as subregion}
			<option value={subregion}>{subregion}</option>
		{/each}
	</select>
</div>

<div class="flex items-center justify-center mb-4">
	<input
		type="text"
		placeholder="Search"
		class="input input-bordered w-full max-w-xs"
		bind:value={searchQuery}
	/>
	{#if searchQuery.length > 0}
		<!-- clear button -->
		<div class="flex items-center justify-center ml-4">
			<button class="btn btn-neutral" on:click={() => (searchQuery = '')}> Clear Search </button>
		</div>
	{/if}
</div>

<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
	{#each filteredCountries as country}
		<CountryCard {country} />
		<!-- <p>Name: {item.name}, Continent: {item.continent}</p> -->
	{/each}
</div>

{#if filteredCountries.length === 0}
	<p class="text-center font-bold text-2xl mt-12">No countries found</p>
{/if}

<svelte:head>
	<title>Countries | World Travel</title>
	<meta name="description" content="Explore the world and add countries to your visited list!" />
</svelte:head>
