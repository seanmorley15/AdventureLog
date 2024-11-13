<script lang="ts">
	import RegionCard from '$lib/components/RegionCard.svelte';
	import type { Region, VisitedRegion } from '$lib/types';
	import type { PageData } from './$types';
	export let data: PageData;

	let regions: Region[] = data.props?.regions || [];
	let visitedRegions: VisitedRegion[] = data.props?.visitedRegions || [];

	const country = data.props?.country || null;
	console.log(data);

	let numRegions: number = country?.num_regions || 0;
	let numVisitedRegions: number = country?.num_visits || 0;

	visitedRegions = visitedRegions.filter(
		(visitedRegion, index, self) =>
			index === self.findIndex((t) => t.region === visitedRegion.region)
	);
</script>

<h1 class="text-center font-bold text-4xl mb-4">Regions in {country?.name}</h1>
<div class="flex items-center justify-center mb-4">
	<div class="stats shadow bg-base-300">
		<div class="stat">
			<div class="stat-title">Region Stats</div>
			<div class="stat-value">{numVisitedRegions}/{numRegions} Visited</div>
			{#if numRegions === numVisitedRegions}
				<div class="stat-desc">You've visited all regions in {country?.name} 🎉!</div>
			{:else}
				<div class="stat-desc">Keep exploring!</div>
			{/if}
		</div>
	</div>
</div>

<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
	{#each regions as region}
		<RegionCard
			{region}
			visited={visitedRegions.some((visitedRegion) => visitedRegion.region === region.id)}
			on:visit={(e) => {
				visitedRegions = [...visitedRegions, e.detail];
				numVisitedRegions++;
			}}
			visit_id={visitedRegions.find((visitedRegion) => visitedRegion.region === region.id)?.id}
			on:remove={() => numVisitedRegions--}
		/>
	{/each}
</div>

<svelte:head>
	<title
		>{data.props && data.props.country ? `Regions in ${data.props.country.name}` : 'Regions'}</title
	>
	<meta
		name="description"
		content="View the regions in countries and mark them visited to track your world travel."
	/>
</svelte:head>
