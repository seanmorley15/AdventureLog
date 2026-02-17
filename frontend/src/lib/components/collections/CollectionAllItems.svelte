<script lang="ts">
	import type { Collection } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import LocationCard from '$lib/components/cards/LocationCard.svelte';
	import TransportationCard from '$lib/components/cards/TransportationCard.svelte';
	import LodgingCard from '$lib/components/cards/LodgingCard.svelte';
	import NoteCard from '$lib/components/cards/NoteCard.svelte';
	import ChecklistCard from '$lib/components/cards/ChecklistCard.svelte';
	import Magnify from '~icons/mdi/magnify';
	import ClipboardList from '~icons/mdi/clipboard-list';
	import { t } from 'svelte-i18n';

	const dispatch = createEventDispatcher();

	export let collection: Collection;
	export let user: any;
	export let isFolderView: boolean = false;

	// Whether the current user can modify this collection (owner or shared user)

	// Exported so a parent can bind to them if desired
	export let locationSearch: string = '';
	export let locationSort:
		| 'alphabetical-asc'
		| 'alphabetical-desc'
		| 'visited'
		| 'date-asc'
		| 'date-desc' = 'alphabetical-asc';

	$: sortedLocations = (() => {
		if (!collection?.locations) return [];

		let filtered = collection.locations.filter(
			(loc) =>
				loc.name.toLowerCase().includes(locationSearch.toLowerCase()) ||
				loc.location?.toLowerCase().includes(locationSearch.toLowerCase())
		);

		switch (locationSort) {
			case 'alphabetical-asc':
				return filtered.sort((a, b) => a.name.localeCompare(b.name));
			case 'alphabetical-desc':
				return filtered.sort((a, b) => b.name.localeCompare(a.name));
			case 'visited':
				return filtered.sort((a, b) => {
					const aVisited = a.visits && a.visits.length > 0 ? 1 : 0;
					const bVisited = b.visits && b.visits.length > 0 ? 1 : 0;
					return bVisited - aVisited;
				});
			case 'date-asc':
				return filtered.sort((a, b) => {
					const aDate = a.visits?.[0]?.start_date || '';
					const bDate = b.visits?.[0]?.start_date || '';
					return aDate.localeCompare(bDate);
				});
			case 'date-desc':
				return filtered.sort((a, b) => {
					const aDate = a.visits?.[0]?.start_date || '';
					const bDate = b.visits?.[0]?.start_date || '';
					return bDate.localeCompare(aDate);
				});
			default:
				return filtered;
		}
	})();

	// Transportations
	export let transportationSearch: string = '';
	$: filteredTransportations = (() => {
		if (!collection?.transportations) return [];
		return collection.transportations.filter((t) =>
			t.name.toLowerCase().includes(transportationSearch.toLowerCase())
		);
	})();

	// Lodging
	export let lodgingSearch: string = '';
	$: filteredLodging = (() => {
		if (!collection?.lodging) return [];
		return collection.lodging.filter((l) =>
			l.name.toLowerCase().includes(lodgingSearch.toLowerCase())
		);
	})();

	// Notes
	export let noteSearch: string = '';
	$: filteredNotes = (() => {
		if (!collection?.notes) return [];
		return collection.notes.filter((n) => n.name.toLowerCase().includes(noteSearch.toLowerCase()));
	})();

	// Checklists
	export let checklistSearch: string = '';
	$: filteredChecklists = (() => {
		if (!collection?.checklists) return [];
		return collection.checklists.filter((c) =>
			c.name.toLowerCase().includes(checklistSearch.toLowerCase())
		);
	})();

	// Generic handlers for editing and deleting items in the collection.
	// `type` should match the collection property name: 'locations', 'transportations', 'lodging', 'notes', 'checklists'
	function handleItemDelete(type: string, detail: any) {
		const id = detail?.id ?? detail;
		if (!id) return;

		const arr = (collection as any)[type];
		if (!arr || !Array.isArray(arr)) return;

		(collection as any) = {
			...(collection as any),
			[type]: arr.filter((item: any) => String(item.id) !== String(id))
		};
	}

	function handleItemEdit(type: string, detail: any) {
		const updated = detail;
		if (!updated || !updated.id) return;

		const arr = (collection as any)[type];
		if (!arr || !Array.isArray(arr)) return;

		(collection as any) = {
			...(collection as any),
			[type]: arr.map((item: any) => (String(item.id) === String(updated.id) ? updated : item))
		};

		// Bubble up so parent can open edit modals
		dispatch('openEdit', { type, item: updated });
	}
</script>

<!-- Show each section as its own card so transportations and others
	 render even when there are no locations. Use vertical spacing
	 between cards via a wrapper. -->
<div class="space-y-6">
	{#if collection.locations && collection.locations.length > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
					<h2 class="card-title text-2xl">
						📍 {$t('locations.locations') || 'Locations'} ({sortedLocations.length}/{collection
							.locations.length})
					</h2>

					{#if isFolderView}
						<div class="flex flex-wrap gap-2">
							<!-- Search -->
							<div class="join">
								<input
									type="text"
									placeholder="Search locations..."
									class="input input-sm input-bordered join-item w-48"
									bind:value={locationSearch}
								/>
							</div>

							<!-- Sort dropdown -->
							<select class="select select-sm select-bordered" bind:value={locationSort}>
								<option value="alphabetical-asc">A → Z</option>
								<option value="alphabetical-desc">Z → A</option>
								<option value="visited">Visited First</option>
								<option value="date-asc">Oldest First</option>
								<option value="date-desc">Newest First</option>
							</select>
						</div>
					{/if}
				</div>

				<div
					class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch"
				>
					{#each sortedLocations as location}
						<LocationCard
							adventure={location}
							{user}
							{collection}
							on:delete={(e) => handleItemDelete('locations', e.detail)}
							on:edit={(e) => handleItemEdit('locations', e.detail)}
						/>
					{/each}
				</div>

				{#if sortedLocations.length === 0}
					<div class="text-center py-8 opacity-70">
						<p>No locations match your search</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Transportations Section -->
	{#if collection.transportations && collection.transportations.length > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
					<h2 class="card-title text-2xl">
						✈️ {$t('adventures.transportation') || 'Transportation'} ({filteredTransportations.length}/{collection
							.transportations.length})
					</h2>

					{#if isFolderView}
						<div class="join">
							<input
								type="text"
								placeholder="Search transportation..."
								class="input input-sm input-bordered join-item w-48"
								bind:value={transportationSearch}
							/>
							<button class="btn btn-sm btn-square join-item">
								<Magnify class="w-4 h-4" />
							</button>
						</div>
					{/if}
				</div>

				<div
					class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch"
				>
					{#each filteredTransportations as transport}
						<TransportationCard
							transportation={transport}
							{user}
							{collection}
							on:delete={(e) => handleItemDelete('transportations', e.detail)}
							on:edit={(e) => handleItemEdit('transportations', e.detail)}
						/>
					{/each}
				</div>

				{#if filteredTransportations.length === 0}
					<div class="text-center py-8 opacity-70">
						<p>No transportation matches your search</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Lodging Section -->
	{#if collection.lodging && collection.lodging.length > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
					<h2 class="card-title text-2xl">
						🏨 {$t('adventures.lodging') || 'Lodging'} ({filteredLodging.length}/{collection.lodging
							.length})
					</h2>

					{#if isFolderView}
						<div class="join">
							<input
								type="text"
								placeholder="Search lodging..."
								class="input input-sm input-bordered join-item w-48"
								bind:value={lodgingSearch}
							/>
							<button class="btn btn-sm btn-square join-item">
								<Magnify class="w-4 h-4" />
							</button>
						</div>
					{/if}
				</div>

				<div
					class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch"
				>
					{#each filteredLodging as lodging}
						<LodgingCard
							{lodging}
							{user}
							{collection}
							on:delete={(e) => handleItemDelete('lodging', e.detail)}
							on:edit={(e) => handleItemEdit('lodging', e.detail)}
						/>
					{/each}
				</div>

				{#if filteredLodging.length === 0}
					<div class="text-center py-8 opacity-70">
						<p>No lodging matches your search</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Notes Section -->
	{#if collection.notes && collection.notes.length > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
					<h2 class="card-title text-2xl">
						📝 Notes ({filteredNotes.length}/{collection.notes.length})
					</h2>

					{#if isFolderView}
						<div class="join">
							<input
								type="text"
								placeholder="Search notes..."
								class="input input-sm input-bordered join-item w-48"
								bind:value={noteSearch}
							/>
							<button class="btn btn-sm btn-square join-item">
								<Magnify class="w-4 h-4" />
							</button>
						</div>
					{/if}
				</div>

				<div
					class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch"
				>
					{#each filteredNotes as note}
						<NoteCard
							{note}
							{user}
							{collection}
							on:delete={(e) => handleItemDelete('notes', e.detail)}
							on:edit={(e) => handleItemEdit('notes', e.detail)}
						/>
					{/each}
				</div>

				{#if filteredNotes.length === 0}
					<div class="text-center py-8 opacity-70">
						<p>No notes match your search</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Checklists Section -->
	{#if collection.checklists && collection.checklists.length > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
					<h2 class="card-title text-2xl">
						<ClipboardList class="w-6 h-6" />
						Checklists ({filteredChecklists.length}/{collection.checklists.length})
					</h2>

					{#if isFolderView}
						<div class="join">
							<input
								type="text"
								placeholder="Search checklists..."
								class="input input-sm input-bordered join-item w-48"
								bind:value={checklistSearch}
							/>
							<button class="btn btn-sm btn-square join-item">
								<Magnify class="w-4 h-4" />
							</button>
						</div>
					{/if}
				</div>

				<div
					class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch"
				>
					{#each filteredChecklists as checklist}
						<ChecklistCard
							{checklist}
							{user}
							{collection}
							on:delete={(e) => handleItemDelete('checklists', e.detail)}
							on:edit={(e) => handleItemEdit('checklists', e.detail)}
						/>
					{/each}
				</div>

				{#if filteredChecklists.length === 0}
					<div class="text-center py-8 opacity-70">
						<p>No checklists match your search</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
