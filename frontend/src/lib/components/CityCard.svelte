<script lang="ts">
	import { goto } from '$app/navigation';
	import { continentCodeToString, getFlag } from '$lib';
	import type { City, Country } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import MapMarkerStar from '~icons/mdi/map-marker-star';

	export let city: City;
</script>

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-neutral text-neutral-content shadow-xl overflow-hidden"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{city.name}</h2>
		<div class="flex flex-wrap gap-2">
			<div class="badge badge-primary">{city.region}</div>
			<!-- 
			{#if country.num_visits > 0 && country.num_visits != country.num_regions}
				<div class="badge badge-accent">
					Visited {country.num_visits} Region{country.num_visits > 1 ? 's' : ''}
				</div>
			{:else if country.num_visits > 0 && country.num_visits === country.num_regions}
				<div class="badge badge-success">Completed</div>
			{:else}
				<div class="badge badge-error">Not Visited</div>
			{/if} -->
		</div>

		<div class="card-actions justify-end">
			<!-- <button class="btn btn-info" on:click={moreInfo}>More Info</button> -->
		</div>
	</div>
</div>
