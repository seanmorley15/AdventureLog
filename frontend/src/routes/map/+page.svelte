<script lang="ts">
	import AdventureModal from '$lib/components/AdventureModal.svelte';
	import { DefaultMarker, MapEvents, MapLibre, Popup, Marker } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import type { Adventure, VisitedRegion } from '$lib/types.js';
	import { getAdventureTypeLabel } from '$lib';
	import CardCarousel from '$lib/components/CardCarousel.svelte';
	import { goto } from '$app/navigation';
	export let data;

	let createModalOpen: boolean = false;
	let showGeo: boolean = false;

	let visitedRegions: VisitedRegion[] = data.props.visitedRegions;
	let adventures: Adventure[] = data.props.adventures;

	let filteredAdventures = adventures;

	// Updates the filtered adventures based on the checkboxes
	$: {
		filteredAdventures = adventures.filter(
			(adventure) => (showVisited && adventure.is_visited) || (showPlanned && !adventure.is_visited)
		);
	}

	// Reset the longitude and latitude when the newMarker is set to null so new adventures are not created at the wrong location
	$: {
		if (!newMarker) {
			newLongitude = null;
			newLatitude = null;
		}
	}

	console.log(data);

	let showVisited: boolean = true;
	let showPlanned: boolean = true;

	let newMarker: { lngLat: any } | null = null;

	let newLongitude: number | null = null;
	let newLatitude: number | null = null;

	let openPopupId: string | null = null; // Store the ID of the currently open popup

	function addMarker(e: { detail: { lngLat: { lng: any; lat: any } } }) {
		newMarker = null;
		newMarker = { lngLat: e.detail.lngLat };
		newLongitude = e.detail.lngLat.lng;
		newLatitude = e.detail.lngLat.lat;
	}

	function createNewAdventure(event: CustomEvent) {
		adventures = [...adventures, event.detail];
		newMarker = null;
		createModalOpen = false;
	}

	let isPopupOpen = false;

	function togglePopup() {
		isPopupOpen = !isPopupOpen;
	}
</script>

<h1 class="text-center font-bold text-4xl">{$t('map.adventure_map')}</h1>

<div class="m-2 flex flex-col items-center justify-center">
	<div class="gap-4 border-solid border-2 rounded-lg p-2 mb-4 border-neutral max-w-4xl">
		<p class="font-semibold text-center text-xl mb-2">{$t('map.map_options')}</p>
		<div class="flex flex-wrap items-center justify-center gap-4">
			<label class="label cursor-pointer">
				<span class="label-text mr-1">{$t('adventures.visited')}</span>
				<input type="checkbox" bind:checked={showVisited} class="checkbox checkbox-primary" />
			</label>
			<label class="label cursor-pointer">
				<span class="label-text mr-1">{$t('adventures.planned')}</span>
				<input type="checkbox" bind:checked={showPlanned} class="checkbox checkbox-primary" />
			</label>
			<label for="show-geo">{$t('map.show_visited_regions')}</label>
			<input
				type="checkbox"
				id="show-geo"
				name="show-geo"
				class="checkbox"
				on:click={() => (showGeo = !showGeo)}
			/>
			<div class="divider divider-horizontal"></div>
			{#if newMarker}
				<button type="button" class="btn btn-primary mb-2" on:click={() => (createModalOpen = true)}
					>{$t('map.add_adventure_at_marker')}</button
				>
				<button type="button" class="btn btn-neutral mb-2" on:click={() => (newMarker = null)}
					>{$t('map.clear_marker')}</button
				>
			{:else}
				<button type="button" class="btn btn-primary mb-2" on:click={() => (createModalOpen = true)}
					>{$t('map.add_adventure')}</button
				>
			{/if}
		</div>
	</div>
</div>

{#if createModalOpen}
	<AdventureModal
		on:close={() => (createModalOpen = false)}
		on:save={createNewAdventure}
		latitude={newLatitude}
		longitude={newLongitude}
	/>
{/if}

<MapLibre
	style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
	class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full"
	standardControls
>
	{#each filteredAdventures as adventure}
		{#if adventure.latitude && adventure.longitude}
			<Marker
				lngLat={[adventure.longitude, adventure.latitude]}
				class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 {adventure.is_visited
					? 'bg-red-300'
					: 'bg-blue-300'} text-black focus:outline-6 focus:outline-black"
				on:click={togglePopup}
			>
				<span class="text-xl">
					{getAdventureTypeLabel(adventure.type)}
				</span>
				{#if isPopupOpen}
					<Popup openOn="click" offset={[0, -10]} on:close={() => (isPopupOpen = false)}>
						{#if adventure.images && adventure.images.length > 0}
							<CardCarousel adventures={[adventure]} />
						{/if}
						<div class="text-lg text-black font-bold">{adventure.name}</div>
						<p class="font-semibold text-black text-md">
							{adventure.is_visited ? $t('adventures.visited') : $t('adventures.planned')}
						</p>
						<p class="font-semibold text-black text-md">
							{$t(`adventures.activities.${adventure.type}`)}
						</p>
						{#if adventure.visits && adventure.visits.length > 0}
							<p class="text-black text-sm">
								{#each adventure.visits as visit}
									{visit.start_date
										? new Date(visit.start_date).toLocaleDateString(undefined, {
												timeZone: 'UTC'
											})
										: ''}
									{visit.end_date && visit.end_date !== '' && visit.end_date !== visit.start_date
										? ' - ' +
											new Date(visit.end_date).toLocaleDateString(undefined, {
												timeZone: 'UTC'
											})
										: ''}
									<br />
								{/each}
							</p>
						{/if}
						<button
							class="btn btn-neutral btn-wide btn-sm mt-4"
							on:click={() => goto(`/adventures/${adventure.id}`)}>{$t('map.view_details')}</button
						>
					</Popup>
				{/if}
			</Marker>
		{/if}
	{/each}

	<MapEvents on:click={addMarker} />
	{#if newMarker}
		<DefaultMarker lngLat={newMarker.lngLat} />
	{/if}

	{#each visitedRegions as region}
		{#if showGeo}
			<Marker
				lngLat={[region.longitude, region.latitude]}
				class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-green-300 text-black shadow-md"
			>
				<svg
					width="24"
					height="24"
					viewBox="0 0 24 24"
					fill="none"
					xmlns="http://www.w3.org/2000/svg"
				>
					<circle cx="12" cy="12" r="10" stroke="green" stroke-width="2" fill="green" />
				</svg>
				<Popup openOn="click" offset={[0, -10]}>
					<div class="text-lg text-black font-bold">{region.name}</div>
					<p class="font-semibold text-black text-md">{region.region}</p>
				</Popup>
			</Marker>
		{/if}
	{/each}
</MapLibre>

<svelte:head>
	<title>Travel Map</title>
	<meta name="description" content="View your travels on a map." />
</svelte:head>

<style>
	:global(.map) {
		height: 500px;
	}
</style>
