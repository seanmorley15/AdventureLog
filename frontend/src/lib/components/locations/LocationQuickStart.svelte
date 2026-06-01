<script lang="ts">
	import PlaceQuickStart from '../shared/PlaceQuickStart.svelte';

	export let googleEnabled = false;
	export let collectionId: string | null = null;
	export let itineraryDate: string | null = null;
	export let itineraryLabel: string | null = null;
	export let basemapType: string = 'default';
</script>

<PlaceQuickStart
	mode="location"
	{googleEnabled}
	{collectionId}
	{itineraryDate}
	{itineraryLabel}
	{basemapType}
	on:addDetails
	on:manual
	on:quickAdded
	on:quickAddedEdit
	on:quickAddedDone
	on:cancel
/>
