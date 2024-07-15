<!-- <script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import type { Adventure } from '$lib/types';

	export let data;
	console.log(data);
	let adventure: Adventure | null = data.props.adventure;
</script>

{#if !adventure}
	<p>Adventure not found</p>
{:else}
	<AdventureCard {adventure} type={adventure.type} />
{/if} -->

<script lang="ts">
	import type { Adventure } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';

	export let data: PageData;

	let adventure: Adventure;

	let notFound: boolean = false;

	onMount(() => {
		if (data.props.adventure) {
			adventure = data.props.adventure;
		} else {
			notFound = true;
		}
	});
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

{#if !adventure && !notFound}
	<div class="flex justify-center items-center w-full mt-16">
		<span class="loading loading-spinner w-24 h-24"></span>
	</div>
{/if}
{#if adventure}
	{#if adventure.name}
		<h1 class="text-center font-extrabold text-4xl mb-2">{adventure.name}</h1>
	{/if}
	{#if adventure.location}
		<p class="text-center text-2xl">
			<iconify-icon icon="mdi:map-marker" class="text-xl -mb-0.5"
			></iconify-icon>{adventure.location}
		</p>
	{/if}
	{#if adventure.date}
		<p class="text-center text-lg mt-4 pl-16 pr-16">
			Visited on: {adventure.date}
		</p>
	{/if}
	{#if adventure.rating !== undefined && adventure.rating !== null}
		<div class="flex justify-center items-center">
			<div class="rating" aria-readonly="true">
				{#each Array.from({ length: 5 }, (_, i) => i + 1) as star}
					<input
						type="radio"
						name="rating-1"
						class="mask mask-star"
						checked={star <= adventure.rating}
						disabled
					/>
				{/each}
			</div>
		</div>
	{/if}
	{#if adventure.description}
		<p class="text-center text-lg mt-4 pl-16 pr-16">{adventure.description}</p>
	{/if}
	{#if adventure.link}
		<div class="flex justify-center items-center mt-4">
			<a href={adventure.link} target="_blank" rel="noopener noreferrer" class="btn btn-primary">
				Visit Website
			</a>
		</div>
	{/if}
	{#if adventure.activity_types && adventure.activity_types.length > 0}
		<div class="flex justify-center items-center mt-4">
			<p class="text-center text-lg">Activities:&nbsp</p>
			<ul class="flex flex-wrap">
				{#each adventure.activity_types as activity}
					<div class="badge badge-primary mr-1 text-md font-semibold pb-2 pt-1 mb-1">
						{activity}
					</div>
				{/each}
			</ul>
		</div>
	{/if}
	{#if adventure.image}
		<div class="flex content-center justify-center">
			<!-- svelte-ignore a11y-img-redundant-alt -->
			<img
				src={adventure.image}
				alt="Adventure Image"
				class="w-1/2 mt-4 align-middle rounded-lg shadow-lg"
			/>
		</div>
	{/if}
{/if}
