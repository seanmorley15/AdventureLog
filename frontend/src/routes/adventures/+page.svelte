<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure } from '$lib/types';
	import { onMount } from 'svelte';

	export let data: any;
	console.log(data);

	let adventures: Adventure[] = data.props.visited;

	let sidebarOpen = false;

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	// onMount(() => {
	// 	const mediaQuery = window.matchMedia('(min-width: 768px)');
	// 	sidebarOpen = mediaQuery.matches;
	// 	mediaQuery.addListener((e) => (sidebarOpen = e.matches));
	// });
</script>

<div class="drawer lg:drawer-open">
	<input id="my-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />
	<div class="drawer-content">
		<!-- Page content -->
		<h1 class="text-center font-bold text-4xl mb-6">My Adventures</h1>
		{#if adventures.length === 0}
			<NotFound />
		{/if}
		<div class="p-4">
			<button
				class="btn btn-primary drawer-button lg:hidden mb-4 fixed bottom-0 left-0 ml-2 z-[999]"
				on:click={toggleSidebar}
			>
				{sidebarOpen ? 'Close Filters' : 'Open Filters'}
			</button>
			<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
				{#each adventures as adventure}
					<AdventureCard type="visited" {adventure} />
				{/each}
			</div>
		</div>
	</div>
	<div class="drawer-side">
		<label for="my-drawer" class="drawer-overlay"></label>
		<ul class="menu p-4 w-80 h-full bg-base-200 text-base-content rounded-lg">
			<!-- Sidebar content here -->
			<h3 class="text-center font-semibold text-lg mb-4">Adventure Types</h3>
			<div class="form-control">
				<label class="label cursor-pointer">
					<span class="label-text">Completed</span>
					<input type="checkbox" class="checkbox checkbox-primary" />
				</label>
				<label class="label cursor-pointer">
					<span class="label-text">Planned</span>
					<input type="checkbox" class="checkbox checkbox-primary" />
				</label>
				<label class="label cursor-pointer">
					<span class="label-text">Featured</span>
					<input type="checkbox" class="checkbox checkbox-primary" />
				</label>
				<div class="divider"></div>
				<button type="button" class="btn btn-primary mt-4">Filter</button>
			</div>
		</ul>
	</div>
</div>
