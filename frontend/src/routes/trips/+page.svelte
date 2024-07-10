<script lang="ts">
	import type { Trip } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import Lost from '$lib/assets/undraw_lost.svg';
	import { goto } from '$app/navigation';
	import TripCard from '$lib/components/TripCard.svelte';

	export let data: PageData;

	let trips: Trip[];
	let notFound: boolean = false;

	onMount(() => {
		if (data.props && data.props.trips) {
			trips = data.props.trips;
		} else {
			notFound = true;
		}
	});

	console.log(data);
</script>

{#if notFound}
	<div
		class="flex min-h-[100dvh] flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8 -mt-20"
	>
		<div class="mx-auto max-w-md text-center">
			<div class="flex items-center justify-center">
				<img src={Lost} alt="Lost" class="w-1/2" />
			</div>
			<h1 class="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
				Adventure not Found
			</h1>
			<p class="mt-4 text-muted-foreground">
				The adventure you were looking for could not be found. Please try a different adventure or
				check back later.
			</p>
			<div class="mt-6">
				<button class="btn btn-primary" on:click={() => goto('/')}>Homepage</button>
			</div>
		</div>
	</div>
{/if}

{#if trips && !notFound}
	<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
		{#each trips as trip (trip.id)}
			<TripCard {trip} />
		{/each}
	</div>
{/if}
