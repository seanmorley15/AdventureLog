<script lang="ts">
	import type { Collection } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import LocationCard from '$lib/components/cards/LocationCard.svelte';
	import TransportationCard from '$lib/components/cards/TransportationCard.svelte';
	import LodgingCard from '$lib/components/cards/LodgingCard.svelte';
	import NoteCard from '$lib/components/cards/NoteCard.svelte';
	import ChecklistCard from '$lib/components/cards/ChecklistCard.svelte';
	import CollectionCatalogFilters from './CollectionCatalogFilters.svelte';
	import ClipboardList from '~icons/mdi/clipboard-list';
	import MapMarker from '~icons/mdi/map-marker';
	import Airplane from '~icons/mdi/airplane';
	import Bed from '~icons/mdi/bed';
	import NoteTextOutline from '~icons/mdi/note-text-outline';
	import { t } from 'svelte-i18n';
	import {
		CatalogFilters,
		checklistMatches,
		locationMatches,
		lodgingDateOf,
		lodgingMatches,
		noteMatches,
		sortByNameAndDate,
		sortLocations,
		transportationDateOf,
		transportationMatches
	} from '$lib/collections/catalog.svelte';

	const dispatch = createEventDispatcher();

	interface Props {
		collection: Collection;
		user: any;
		isFolderView?: boolean;
		filters?: CatalogFilters;
		showMapToggles?: boolean;
	}

	let {
		collection = $bindable(),
		user,
		isFolderView = false,
		filters = new CatalogFilters(),
		showMapToggles = false
	}: Props = $props();

	// Generic handlers for editing and deleting items in the collection.
	// `type` should match the collection property name: 'locations', 'transportations', 'lodging', 'notes', 'checklists'
	function handleItemDelete(type: string, detail: any) {
		const id = detail?.id ?? detail;
		if (!id) return;

		const arr = (collection as any)[type];
		if (!arr || !Array.isArray(arr)) return;

		// The server removes the item's itinerary placements with it, so drop them here too.
		// Otherwise the plan keeps a placement for something that no longer exists.
		const itinerary = (collection.itinerary ?? []).filter(
			(placement) => String(placement.object_id) !== String(id)
		);

		(collection as any) = {
			...(collection as any),
			[type]: arr.filter((item: any) => String(item.id) !== String(id)),
			itinerary
		};
	}

	function handleItemEdit(type: string, detail: any, initialStep: 'visits' | null = null) {
		const updated = detail;
		if (!updated || !updated.id) return;

		const arr = (collection as any)[type];
		if (!arr || !Array.isArray(arr)) return;

		(collection as any) = {
			...(collection as any),
			[type]: arr.map((item: any) => (String(item.id) === String(updated.id) ? updated : item))
		};

		// Bubble up so parent can open edit modals
		dispatch('openEdit', { type, item: updated, initialStep });
	}

	function handleLocationEditVisits(detail: any) {
		handleItemEdit('locations', detail, 'visits');
	}

	function handleLocationDuplicate(detail: any) {
		if (!detail || !detail.id) return;

		const collectionId = collection?.id ? String(collection.id) : null;
		const duplicated = { ...detail };

		if (collectionId) {
			const existingCollections = Array.isArray(duplicated.collections)
				? duplicated.collections.map((id: string) => String(id))
				: [];
			if (!existingCollections.includes(collectionId)) {
				duplicated.collections = [...existingCollections, collectionId];
			}
		}

		collection = {
			...collection,
			locations: [
				duplicated,
				...(collection.locations || []).filter((loc) => String(loc.id) !== String(duplicated.id))
			]
		};
	}
	let sortedLocations = $derived(
		sortLocations(
			(collection.locations ?? []).filter((loc) => locationMatches(loc, filters)),
			filters.sort
		)
	);
	let filteredTransportations = $derived(
		sortByNameAndDate(
			(collection.transportations ?? []).filter((item) => transportationMatches(item, filters)),
			filters.sort,
			transportationDateOf
		)
	);
	let filteredLodging = $derived(
		sortByNameAndDate(
			(collection.lodging ?? []).filter((item) => lodgingMatches(item, filters)),
			filters.sort,
			lodgingDateOf
		)
	);
	let filteredNotes = $derived(
		sortByNameAndDate(
			(collection.notes ?? []).filter((item) => noteMatches(item, filters)),
			filters.sort,
			(item) => item.date
		)
	);
	let filteredChecklists = $derived(
		sortByNameAndDate(
			(collection.checklists ?? []).filter((item) => checklistMatches(item, filters)),
			filters.sort,
			(item) => item.date
		)
	);

	const hasItems = $derived(
		(collection.locations?.length ?? 0) +
			(collection.transportations?.length ?? 0) +
			(collection.lodging?.length ?? 0) +
			(collection.notes?.length ?? 0) +
			(collection.checklists?.length ?? 0) >
			0
	);
	const matchedCount = $derived(
		sortedLocations.length +
			filteredTransportations.length +
			filteredLodging.length +
			filteredNotes.length +
			filteredChecklists.length
	);
	const totalCount = $derived(
		(collection.locations?.length ?? 0) +
			(collection.transportations?.length ?? 0) +
			(collection.lodging?.length ?? 0) +
			(collection.notes?.length ?? 0) +
			(collection.checklists?.length ?? 0)
	);
</script>

<div class="space-y-4 pb-24">
	<CollectionCatalogFilters
		{filters}
		{collection}
		{showMapToggles}
		showDayNumbers={showMapToggles}
		showCatalog
		{matchedCount}
		{totalCount}
	/>

	{#if !hasItems}
		<section class="card bg-base-200 shadow-xl">
			<div class="card-body p-4 sm:p-5">
				<p
					class="flex min-h-14 items-center justify-center rounded-xl border border-dashed border-base-300 bg-base-100/40 text-sm text-base-content/60"
				>
					{$t('collections.no_items')}
				</p>
			</div>
		</section>
	{/if}

	{#if filters.showLocations && collection.locations && collection.locations.length > 0}
		<section class="card bg-base-200 shadow-xl">
			<div class="card-body gap-3 p-4 sm:p-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex min-w-0 items-center gap-3">
						<MapMarker class="h-5 w-5 shrink-0 text-primary" />
						<div class="min-w-0 flex-1">
							<h3 class="text-lg font-bold">{$t('locations.locations') || 'Locations'}</h3>
						</div>
						<span class="badge badge-ghost badge-sm font-medium">
							{sortedLocations.length}/{collection.locations.length}
						</span>
					</div>
				</div>

				<div class="grid auto-rows-fr grid-cols-1 items-stretch gap-4 sm:grid-cols-2">
					{#each sortedLocations as location (location.id)}
						<div id={`catalog-location-${location.id}`} class="h-full">
							<LocationCard
								adventure={location}
								{user}
								{collection}
								on:delete={(e) => handleItemDelete('locations', e.detail)}
								on:edit={(e) => handleItemEdit('locations', e.detail)}
								on:editVisits={(e) => handleLocationEditVisits(e.detail)}
								on:duplicate={(e) => handleLocationDuplicate(e.detail)}
								on:unlink={(e) => handleItemDelete('locations', e.detail)}
							/>
						</div>
					{/each}
				</div>

				{#if sortedLocations.length === 0}
					<p
						class="flex min-h-14 items-center justify-center rounded-xl border border-dashed border-base-300 bg-base-100/40 text-sm text-base-content/60"
					>
						{$t('itinerary.no_matching_items')}
					</p>
				{/if}
			</div>
		</section>
	{/if}

	{#if !isFolderView && filters.showTransportation && collection.transportations && collection.transportations.length > 0}
		<section class="card bg-base-200 shadow-xl">
			<div class="card-body gap-3 p-4 sm:p-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex min-w-0 items-center gap-3">
						<Airplane class="h-5 w-5 shrink-0 text-secondary" />
						<div class="min-w-0 flex-1">
							<h3 class="text-lg font-bold">
								{$t('adventures.transportation') || 'Transportation'}
							</h3>
						</div>
						<span class="badge badge-ghost badge-sm font-medium">
							{filteredTransportations.length}/{collection.transportations.length}
						</span>
					</div>
				</div>

				<div class="grid auto-rows-fr grid-cols-1 items-stretch gap-4 sm:grid-cols-2">
					{#each filteredTransportations as transport (transport.id)}
						<div id={`catalog-transportation-${transport.id}`} class="h-full">
							<TransportationCard
								transportation={transport}
								{user}
								{collection}
								on:delete={(e) => handleItemDelete('transportations', e.detail)}
								on:edit={(e) => handleItemEdit('transportations', e.detail)}
							/>
						</div>
					{/each}
				</div>

				{#if filteredTransportations.length === 0}
					<p
						class="flex min-h-14 items-center justify-center rounded-xl border border-dashed border-base-300 bg-base-100/40 text-sm text-base-content/60"
					>
						{$t('itinerary.no_matching_items')}
					</p>
				{/if}
			</div>
		</section>
	{/if}

	{#if !isFolderView && filters.showLodging && collection.lodging && collection.lodging.length > 0}
		<section class="card bg-base-200 shadow-xl">
			<div class="card-body gap-3 p-4 sm:p-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex min-w-0 items-center gap-3">
						<Bed class="h-5 w-5 shrink-0 text-info" />
						<div class="min-w-0 flex-1">
							<h3 class="text-lg font-bold">{$t('adventures.lodging') || 'Lodging'}</h3>
						</div>
						<span class="badge badge-ghost badge-sm font-medium">
							{filteredLodging.length}/{collection.lodging.length}
						</span>
					</div>
				</div>

				<div class="grid auto-rows-fr grid-cols-1 items-stretch gap-4 sm:grid-cols-2">
					{#each filteredLodging as lodging (lodging.id)}
						<div id={`catalog-lodging-${lodging.id}`} class="h-full">
							<LodgingCard
								{lodging}
								{user}
								{collection}
								on:delete={(e) => handleItemDelete('lodging', e.detail)}
								on:edit={(e) => handleItemEdit('lodging', e.detail)}
							/>
						</div>
					{/each}
				</div>

				{#if filteredLodging.length === 0}
					<p
						class="flex min-h-14 items-center justify-center rounded-xl border border-dashed border-base-300 bg-base-100/40 text-sm text-base-content/60"
					>
						{$t('itinerary.no_matching_items')}
					</p>
				{/if}
			</div>
		</section>
	{/if}

	{#if filters.showNotes && collection.notes && collection.notes.length > 0}
		<section class="card bg-base-200 shadow-xl">
			<div class="card-body gap-3 p-4 sm:p-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex min-w-0 items-center gap-3">
						<NoteTextOutline class="h-5 w-5 shrink-0 text-base-content" />
						<div class="min-w-0 flex-1">
							<h3 class="text-lg font-bold">{$t('adventures.notes')}</h3>
						</div>
						<span class="badge badge-ghost badge-sm font-medium">
							{filteredNotes.length}/{collection.notes.length}
						</span>
					</div>
				</div>

				<div class="grid auto-rows-fr grid-cols-1 items-stretch gap-4 sm:grid-cols-2">
					{#each filteredNotes as note (note.id)}
						<div id={`catalog-note-${note.id}`} class="h-full">
							<NoteCard
								{note}
								{user}
								{collection}
								on:delete={(e) => handleItemDelete('notes', e.detail)}
								on:edit={(e) => handleItemEdit('notes', e.detail)}
							/>
						</div>
					{/each}
				</div>

				{#if filteredNotes.length === 0}
					<p
						class="flex min-h-14 items-center justify-center rounded-xl border border-dashed border-base-300 bg-base-100/40 text-sm text-base-content/60"
					>
						{$t('itinerary.no_matching_items')}
					</p>
				{/if}
			</div>
		</section>
	{/if}

	{#if filters.showChecklists && collection.checklists && collection.checklists.length > 0}
		<section class="card bg-base-200 shadow-xl">
			<div class="card-body gap-3 p-4 sm:p-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex min-w-0 items-center gap-3">
						<ClipboardList class="h-5 w-5 shrink-0 text-base-content" />
						<div class="min-w-0 flex-1">
							<h3 class="text-lg font-bold">{$t('adventures.checklists')}</h3>
						</div>
						<span class="badge badge-ghost badge-sm font-medium">
							{filteredChecklists.length}/{collection.checklists.length}
						</span>
					</div>
				</div>

				<div class="grid auto-rows-fr grid-cols-1 items-stretch gap-4 sm:grid-cols-2">
					{#each filteredChecklists as checklist (checklist.id)}
						<div id={`catalog-checklist-${checklist.id}`} class="h-full">
							<ChecklistCard
								{checklist}
								{user}
								{collection}
								on:delete={(e) => handleItemDelete('checklists', e.detail)}
								on:edit={(e) => handleItemEdit('checklists', e.detail)}
							/>
						</div>
					{/each}
				</div>

				{#if filteredChecklists.length === 0}
					<p
						class="flex min-h-14 items-center justify-center rounded-xl border border-dashed border-base-300 bg-base-100/40 text-sm text-base-content/60"
					>
						{$t('itinerary.no_matching_items')}
					</p>
				{/if}
			</div>
		</section>
	{/if}
</div>
