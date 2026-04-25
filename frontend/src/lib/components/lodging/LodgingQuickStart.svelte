<script lang="ts">
	import PlaceQuickStart from '../shared/PlaceQuickStart.svelte';

	export let googleEnabled = false;
	export let collectionId: string | null = null;
</script>

<PlaceQuickStart
	mode="lodging"
	{googleEnabled}
	{collectionId}
	on:addDetails
	on:manual
	on:quickAdded
	on:quickAddedEdit
	on:quickAddedDone
	on:cancel
/>
