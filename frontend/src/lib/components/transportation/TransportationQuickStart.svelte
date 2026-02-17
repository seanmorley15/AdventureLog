<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import LocationSearchMap, { type SearchMode } from '../shared/LocationSearchMap.svelte';

	const dispatch = createEventDispatcher();

	// Search mode (shared with parent)
	export let searchMode: SearchMode = 'location';

	let isReverseGeocoding = false;

	// Store selected locations
	let originData: {
		name: string;
		latitude: number;
		longitude: number;
		location: string;
		city: string | null;
		code: string | null;
	} | null = null;

	let destinationData: {
		name: string;
		latitude: number;
		longitude: number;
		location: string;
		city: string | null;
		code: string | null;
	} | null = null;

	function handleTransportationUpdate(
		event: CustomEvent<{
			start: { name: string; lat: number; lng: number; location: string; city?: string | null; code?: string | null } | null;
			end: { name: string; lat: number; lng: number; location: string; city?: string | null; code?: string | null } | null;
		}>
	) {
		const { start, end } = event.detail;

		if (start && start.lat && start.lng) {
			originData = {
				name: start.name,
				latitude: start.lat,
				longitude: start.lng,
				location: start.location,
				city: start.city || null,
				code: start.code || null
			};
		} else {
			originData = null;
		}

		if (end && end.lat && end.lng) {
			destinationData = {
				name: end.name,
				latitude: end.lat,
				longitude: end.lng,
				location: end.location,
				city: end.city || null,
				code: end.code || null
			};
		} else {
			destinationData = null;
		}
	}

	function handleClear() {
		originData = null;
		destinationData = null;
	}

	function continueWithLocations() {
		dispatch('locationsSelected', {
			origin: originData,
			destination: destinationData,
			searchMode
		});
	}
</script>

<div class="space-y-6">
	<!-- Location Search Map (same as Details) -->
	<LocationSearchMap
		bind:isReverseGeocoding
		transportationMode={true}
		unifiedSearch={true}
		bind:searchMode
		showDisplayNameInput={false}
		on:transportationUpdate={handleTransportationUpdate}
		on:clear={handleClear}
	/>

	<!-- Action Buttons -->
	<div class="flex gap-3 pt-4">
		<button type="button" class="btn btn-neutral-200 flex-1" on:click={() => dispatch('cancel')}>
			{$t('adventures.cancel') || 'Cancel'}
		</button>
		<button type="button" class="btn btn-primary flex-1" on:click={continueWithLocations}>
			{#if isReverseGeocoding}
				<span class="loading loading-spinner loading-xs"></span>
			{:else}
				{$t('adventures.continue')}
			{/if}
		</button>
	</div>
</div>
