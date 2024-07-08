<script lang="ts">
	import RegionCard from '$lib/components/RegionCard.svelte';
	import type { Region, VisitedRegion } from '$lib/types';
	import type { PageData } from './$types';
	export let data: PageData;
	let regions: Region[] = data.props?.regions || [];
	let visitedRegions: VisitedRegion[] = data.props?.visitedRegions || [];

	console.log(data);
</script>

<h1 class="text-center font-bold text-4xl mb-4">Regions</h1>

<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
	{#each regions as region}
		<RegionCard
			{region}
			visited={visitedRegions.some((visitedRegion) => visitedRegion.region === region.id)}
			on:visit={(e) => {
				visitedRegions = [...visitedRegions, e.detail];
			}}
			visit_id={visitedRegions.find((visitedRegion) => visitedRegion.region === region.id)?.id}
		/>
	{/each}
</div>
