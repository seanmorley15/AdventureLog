<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import RegionCard from '$lib/components/RegionCard.svelte';
	import CityCard from '$lib/components/CityCard.svelte';
	import CountryCard from '$lib/components/CountryCard.svelte';
	import CollectionCard from '$lib/components/CollectionCard.svelte';
	import UserCard from '$lib/components/UserCard.svelte';

	export let data: PageData;

	let adventures = data.adventures;
	let collections = data.collections;
	let users = data.users;
	let countries = data.countries;
	let regions = data.regions;
	let cities = data.cities;

	let visited_regions: { region: any }[] = data.visited_regions;
	let visited_cities: { city: any }[] = data.visited_cities;

	let query: string | null = '';

	onMount(() => {
		const urlParams = new URLSearchParams(window.location.search);
		query = urlParams.get('query');
	});
</script>

<h1 class="text-4xl font-bold text-center m-4">Search{query ? `: ${query}` : ''}</h1>

{#if adventures.length > 0}
	<h2 class="text-3xl font-bold text-center m-4">Adventures</h2>
	<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
		{#each adventures as adventure}
			<AdventureCard {adventure} user={data.user} />
		{/each}
	</div>
{/if}

{#if collections.length > 0}
	<h2 class="text-3xl font-bold text-center m-4">Collections</h2>
	<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
		{#each collections as collection}
			<CollectionCard {collection} type={''} />
		{/each}
	</div>
{/if}

{#if countries.length > 0}
	<h2 class="text-3xl font-bold text-center m-4">Countries</h2>
	<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
		{#each countries as country}
			<CountryCard {country} />
		{/each}
	</div>
{/if}

{#if regions.length > 0}
	<h2 class="text-3xl font-bold text-center m-4">Regions</h2>
	<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
		{#each regions as region}
			<RegionCard
				{region}
				visited={visited_regions.some((visitedRegion) => visitedRegion.region === region.id)}
			/>
		{/each}
	</div>
{/if}

{#if cities.length > 0}
	<h2 class="text-3xl font-bold text-center m-4">Cities</h2>
	<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
		{#each cities as city}
			<CityCard
				{city}
				visited={visited_cities.some((visitedCity) => visitedCity.city === city.id)}
			/>
		{/each}
	</div>
{/if}

{#if users.length > 0}
	<h2 class="text-3xl font-bold text-center m-4">Users</h2>
	<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
		{#each users as user}
			<UserCard {user} />
		{/each}
	</div>
{/if}

{#if adventures.length === 0 && regions.length === 0 && cities.length === 0 && countries.length === 0 && collections.length === 0 && users.length === 0}
	<p class="text-center text-lg m-4">
		{$t('adventures.no_results')}
	</p>
{/if}

<svelte:head>
	<title>Search{query ? `: ${query}` : ''}</title>
	<meta name="description" content="Search your adventures." />
</svelte:head>
