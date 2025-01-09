<script lang="ts">
	import { goto } from '$app/navigation';
	import CityCard from '$lib/components/CityCard.svelte';
	import CountryCard from '$lib/components/CountryCard.svelte';
	import type { City, Country } from '$lib/types';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import { MapLibre, Marker } from 'svelte-maplibre';

	export let data: PageData;
	console.log(data);

	let searchQuery: string = '';

	let filteredCities: City[] = [];
	const allCities: City[] = data.props?.cities || [];
	let showMap: boolean = false;

	let filterOption: string = 'all';
	let subRegionOption: string = '';

	$: {
		if (searchQuery === '') {
			filteredCities = allCities;
		} else {
			// otherwise, filter countries by name
			filteredCities = filteredCities.filter((country) =>
				country.name.toLowerCase().includes(searchQuery.toLowerCase())
			);
		}
	}
</script>

<h1 class="text-center font-bold text-4xl">{$t('worldtravel.country_list')}</h1>
<!-- result count -->
<p class="text-center mb-4">
	{allCities.length}
	Cities Found
</p>

<!-- <div class="flex items-center justify-center mb-4">
	<div class="join">
		<input
			class="join-item btn"
			type="radio"
			name="filter"
			aria-label={$t('worldtravel.all')}
			checked
			on:click={() => (filterOption = 'all')}
		/>
		<input
			class="join-item btn"
			type="radio"
			name="filter"
			aria-label={$t('worldtravel.partially_visited')}
			on:click={() => (filterOption = 'partial')}
		/>
		<input
			class="join-item btn"
			type="radio"
			name="filter"
			aria-label={$t('worldtravel.completely_visited')}
			on:click={() => (filterOption = 'complete')}
		/>
		<input
			class="join-item btn"
			type="radio"
			name="filter"
			aria-label={$t('worldtravel.not_visited')}
			on:click={() => (filterOption = 'not')}
		/>
	</div>
	<select class="select select-bordered w-full max-w-xs ml-4" bind:value={subRegionOption}>
		<option value="">{$t('worldtravel.all_subregions')}</option>
		{#each worldSubregions as subregion}
			<option value={subregion}>{subregion}</option>
		{/each}
	</select>

	<div class="flex items-center justify-center ml-4">
		<input
			type="checkbox"
			class="checkbox checkbox-bordered"
			bind:checked={showMap}
			aria-label={$t('adventures.show_map')}
		/>
		<span class="ml-2">{$t('adventures.show_map')}</span>
	</div>
</div> -->

<div class="flex items-center justify-center mb-4">
	<input
		type="text"
		placeholder={$t('navbar.search')}
		class="input input-bordered w-full max-w-xs"
		bind:value={searchQuery}
	/>
	{#if searchQuery.length > 0}
		<!-- clear button -->
		<div class="flex items-center justify-center ml-4">
			<button class="btn btn-neutral" on:click={() => (searchQuery = '')}>
				{$t('worldtravel.clear_search')}
			</button>
		</div>
	{/if}
</div>

<div class="mt-4 mb-4 flex justify-center">
	<!-- checkbox to toggle marker -->

	<MapLibre
		style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
		class="aspect-[9/16] max-h-[70vh] sm:aspect-video sm:max-h-full w-10/12 rounded-lg"
		standardControls
		center={allCities[0] && allCities[0].longitude !== null && allCities[0].latitude !== null
			? [allCities[0].longitude, allCities[0].latitude]
			: [0, 0]}
		zoom={8}
	>
		{#each filteredCities as city}
			{#if city.latitude && city.longitude}
				<Marker
					lngLat={[city.longitude, city.latitude]}
					class="grid px-2 py-1 place-items-center rounded-full border border-gray-200 bg-green-200 text-black focus:outline-6 focus:outline-black"
				>
					<span class="text-xs">
						{city.name}
					</span>
				</Marker>
			{/if}
		{/each}
	</MapLibre>
</div>

<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
	{#each filteredCities as city}
		<CityCard {city} />
	{/each}
</div>

{#if filteredCities.length === 0}
	<p class="text-center font-bold text-2xl mt-12">{$t('worldtravel.no_countries_found')}</p>
{/if}

<svelte:head>
	<title>Countries | World Travel</title>
	<meta name="description" content="Explore the world and add countries to your visited list!" />
</svelte:head>
