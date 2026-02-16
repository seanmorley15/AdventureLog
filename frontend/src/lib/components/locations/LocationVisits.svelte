<script lang="ts">
	/**
	 * LocationVisits - Thin wrapper around EntityVisitsBase for location entities
	 * Includes activity/Strava support (not available in Transportation/Lodging)
	 */
	import type { Collection, Visit, Trail } from '$lib/types';
	import { EntityVisitsBase } from '../shared/modal';

	// Props - matching the original interface
	export let collection: Collection | null = null;
	export let visits: Visit[] | null = null;
	export let objectId: string;
	export let trails: Trail[] = [];
	export let measurementSystem: 'metric' | 'imperial' = 'metric';
	export let initialVisitDate: string | null = null;
	export let currentUserUsername: string | null = null;
	export let countryCurrency: string | null = null;
	export let userCurrency: string | null = null;
</script>

<EntityVisitsBase
	{collection}
	bind:visits
	entityId={objectId}
	entityType="location"
	{trails}
	{measurementSystem}
	{initialVisitDate}
	{currentUserUsername}
	{countryCurrency}
	{userCurrency}
	on:back
	on:close
	on:visitAdded
	on:visitDeleted
/>
