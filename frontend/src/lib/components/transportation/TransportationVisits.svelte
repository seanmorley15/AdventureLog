<script lang="ts">
	/**
	 * TransportationVisits - Thin wrapper around EntityVisitsBase for transportation entities
	 */
	import type { Collection, Visit, Trail } from '$lib/types';
	import { EntityVisitsBase } from '../shared/modal';

	// Props - matching the original interface
	export let collection: Collection | null = null;
	export let visits: Visit[] | null = null;
	export let transportationId: string;
	export let initialVisitDate: string | null = null;
	export let currentUserUsername: string | null = null;
	export let countryCurrency: string | null = null;
	export let userCurrency: string | null = null;
	// Optional activity props
	export let trails: Trail[] = [];
	export let measurementSystem: 'metric' | 'imperial' = 'metric';
</script>

<EntityVisitsBase
	{collection}
	bind:visits
	entityId={transportationId}
	entityType="transportation"
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
