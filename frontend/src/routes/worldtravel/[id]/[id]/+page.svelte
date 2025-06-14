<script lang="ts">
	import { getBasemapUrl } from '$lib';
	import CityCard from '$lib/components/CityCard.svelte';
	import { addToast } from '$lib/toasts';
	import type { City } from '$lib/types';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import { MapLibre, Marker } from 'svelte-maplibre';

	export let data: PageData;
	console.log(data);

	let searchQuery: string = '';

	let filteredCities: City[] = [];
	const allCities: City[] = data.props?.cities || [];
	let visitedCities = data.props?.visitedCities || [];

	$: {
		if (searchQuery === '') {
			filteredCities = allCities;
		} else {
			// otherwise, filter countries by name
			filteredCities = allCities.filter((country) =>
				country.name.toLowerCase().includes(searchQuery.toLowerCase())
			);
		}
	}

	function togleVisited(city: City) {
		return () => {
			const visitedCity = visitedCities.find((visitedCity) => visitedCity.city === city.id);
			if (visitedCity) {
				visitedCities = visitedCities.filter((visitedCity) => visitedCity.city !== city.id);
				removeVisit(city);
			} else {
				markVisited(city);
			}
		};
	}

	async function markVisited(city: City) {
		let res = await fetch(`/api/visitedcity/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ city: city.id })
		});
		if (!res.ok) {
			console.error('Failed to mark city as visited');
			addToast('error', `Failed to mark visit to ${city.name}`);
			return;
		} else {
			visitedCities = [...visitedCities, await res.json()];
			addToast('success', `Visit to ${city.name} marked`);
		}
	}
	async function removeVisit(region: City) {
		let res = await fetch(`/api/visitedcity/${region.id}`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'DELETE'
		});
		if (!res.ok) {
			console.error('Failed to remove visit');
			addToast('error', `Failed to remove visit to ${region.name}`);
			return;
		} else {
			visitedCities = visitedCities.filter((visitedCity) => visitedCity.city !== region.id);
			addToast('info', `Visit to ${region.name} removed`);
		}
	}

	let numCities: number = data.props?.cities?.length || 0;
	let numVisitedCities: number = visitedCities.length;

	$: {
		numVisitedCities = visitedCities.length;
	}
</script>

<h1 class="text-center font-bold text-4xl">Cities in {data.props?.region.name}</h1>
<!-- result count -->
<p class="text-center mb-4">
	{allCities.length}
	Cities Found
</p>

<div class="flex items-center justify-center mb-4">
	<div class="stats shadow bg-base-300">
		<div class="stat">
			<div class="stat-title">City Stats</div>
			<div class="stat-value">{numVisitedCities}/{numCities} Visited</div>
			{#if numCities === numVisitedCities}
				<div class="stat-desc">You've visited all cities in {data.props?.region.name} 🎉!</div>
			{:else}
				<div class="stat-desc">Keep exploring!</div>
			{/if}
		</div>
	</div>
</div>

{#if allCities.length > 0}
	<div class="mt-4 mb-4 flex justify-center">
		<!-- checkbox to toggle marker -->

		<MapLibre
			style={getBasemapUrl()}
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
						class="grid px-2 py-1 place-items-center rounded-full border border-gray-200 {visitedCities.some(
							(visitedCity) => visitedCity.city === city.id
						)
							? 'bg-green-200'
							: 'bg-red-200'} text-black focus:outline-6 focus:outline-black"
						on:click={togleVisited(city)}
					>
						<span class="text-xs">
							{city.name}
						</span>
					</Marker>
				{/if}
			{/each}
		</MapLibre>
	</div>
{/if}

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

<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
	{#each filteredCities as city}
		<CityCard
			{city}
			visited={visitedCities.some((visitedCity) => visitedCity.city === city.id)}
			on:visit={(e) => {
				visitedCities = [...visitedCities, e.detail];
			}}
			on:remove={() => {
				visitedCities = visitedCities.filter((visitedCity) => visitedCity.city !== city.id);
			}}
		/>
	{/each}
</div>

{#if filteredCities.length === 0}
	<p class="text-center font-bold text-2xl mt-12">{$t('worldtravel.no_cities_found')}</p>
{/if}

<svelte:head>
	<title>Cities in {data.props?.region.name} | World Travel</title>
	<meta name="description" content="Explore the world and add countries to your visited list!" />
</svelte:head>
