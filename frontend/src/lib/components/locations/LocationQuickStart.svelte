<script lang="ts">
	import PlaceQuickStart from '../shared/PlaceQuickStart.svelte';

	interface Props {
		googleEnabled?: boolean;
		collectionId?: string | null;
		itineraryDate?: string | null;
		itineraryLabel?: string | null;
		basemapType?: string;
	}

	let {
		googleEnabled = false,
		collectionId = null,
		itineraryDate = null,
		itineraryLabel = null,
		basemapType = 'default'
	}: Props = $props();
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
