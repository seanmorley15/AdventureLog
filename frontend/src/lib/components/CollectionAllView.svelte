<script lang="ts">
	import type {
		Location,
		Transportation,
		Lodging,
		Note,
		Checklist,
		User,
		Collection
	} from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';

	const dispatch = createEventDispatcher();

	// Icons
	import Adventures from '~icons/mdi/map-marker-path';
	import TransportationIcon from '~icons/mdi/car';
	import Hotel from '~icons/mdi/hotel';
	import NoteIcon from '~icons/mdi/note-text';
	import ChecklistIcon from '~icons/mdi/check-box-outline';
	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Filter from '~icons/mdi/filter-variant';

	// Component imports
	import LocationCard from './LocationCard.svelte';
	import TransportationCard from './TransportationCard.svelte';
	import LodgingCard from './LodgingCard.svelte';
	import NoteCard from './NoteCard.svelte';
	import ChecklistCard from './ChecklistCard.svelte';

	// Props
	export let adventures: Location[] = [];
	export let transportations: Transportation[] = [];
	export let lodging: Lodging[] = [];
	export let notes: Note[] = [];
	export let checklists: Checklist[] = [];
	export let user: User | null;
	export let collection: Collection;

	// State
	let searchQuery: string = '';
	let filterOption: string = 'all';
	let sortOption: string = 'name_asc';

	// Filtered arrays
	let filteredAdventures: Location[] = [];
	let filteredTransportations: Transportation[] = [];
	let filteredLodging: Lodging[] = [];
	let filteredNotes: Note[] = [];
	let filteredChecklists: Checklist[] = [];

	// Helper function to sort items
	function sortItems(items: any[], sortOption: string) {
		const sorted = [...items];

		switch (sortOption) {
			case 'name_asc':
				return sorted.sort((a, b) =>
					(a.name || a.title || '').localeCompare(b.name || b.title || '')
				);
			case 'name_desc':
				return sorted.sort((a, b) =>
					(b.name || b.title || '').localeCompare(a.name || a.title || '')
				);
			case 'date_newest':
				return sorted.sort(
					(a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
				);
			case 'date_oldest':
				return sorted.sort(
					(a, b) => new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime()
				);
			case 'visited_first':
				return sorted.sort((a, b) => {
					const aVisited = a.visits && a.visits.length > 0;
					const bVisited = b.visits && b.visits.length > 0;
					if (aVisited && !bVisited) return -1;
					if (!aVisited && bVisited) return 1;
					return 0;
				});
			case 'unvisited_first':
				return sorted.sort((a, b) => {
					const aVisited = a.visits && a.visits.length > 0;
					const bVisited = b.visits && b.visits.length > 0;
					if (!aVisited && bVisited) return -1;
					if (aVisited && !bVisited) return 1;
					return 0;
				});
			default:
				return sorted;
		}
	}

	// Clear all filters function
	function clearAllFilters() {
		searchQuery = '';
		filterOption = 'all';
		sortOption = 'name_asc';
	}

	// Reactive statements for filtering and sorting
	$: {
		// Filter adventures
		let filtered = adventures;
		if (searchQuery !== '') {
			filtered = filtered.filter((adventure) => {
				const nameMatch =
					adventure.name?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				const locationMatch =
					adventure.location?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				const descriptionMatch =
					adventure.description?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				return nameMatch || locationMatch || descriptionMatch;
			});
		}

		filteredAdventures = sortItems(filtered, sortOption);
	}

	$: {
		// Filter transportations
		let filtered = transportations;
		if (searchQuery !== '') {
			filtered = filtered.filter((transport) => {
				const nameMatch =
					transport.name?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				const fromMatch =
					transport.from_location?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				const toMatch =
					transport.to_location?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				return nameMatch || fromMatch || toMatch;
			});
		}

		filteredTransportations = sortItems(filtered, sortOption);
	}

	$: {
		// Filter lodging
		let filtered = lodging;
		if (searchQuery !== '') {
			filtered = filtered.filter((hotel) => {
				const nameMatch = hotel.name?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				const locationMatch =
					hotel.location?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				return nameMatch || locationMatch;
			});
		}

		filteredLodging = sortItems(filtered, sortOption);
	}

	$: {
		// Filter notes
		let filtered = notes;
		if (searchQuery !== '') {
			filtered = filtered.filter((note) => {
				const titleMatch = note.name?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				const contentMatch =
					note.content?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				return titleMatch || contentMatch;
			});
		}

		filteredNotes = sortItems(filtered, sortOption);
	}

	$: {
		// Filter checklists
		let filtered = checklists;
		if (searchQuery !== '') {
			filtered = filtered.filter((checklist) => {
				const titleMatch =
					checklist.name?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				return titleMatch;
			});
		}

		filteredChecklists = sortItems(filtered, sortOption);
	}

	// Calculate total items
	$: totalItems =
		filteredAdventures.length +
		filteredTransportations.length +
		filteredLodging.length +
		filteredNotes.length +
		filteredChecklists.length;

	// Event handlers
	function handleEditAdventure(event: { detail: any }) {
		dispatch('editAdventure', event.detail);
	}

	function handleDeleteAdventure(event: { detail: any }) {
		dispatch('deleteAdventure', event.detail);
	}

	function handleEditTransportation(event: { detail: any }) {
		dispatch('editTransportation', event.detail);
	}

	function handleDeleteTransportation(event: { detail: any }) {
		dispatch('deleteTransportation', event.detail);
	}

	function handleEditLodging(event: { detail: any }) {
		dispatch('editLodging', event.detail);
	}

	function handleDeleteLodging(event: { detail: any }) {
		dispatch('deleteLodging', event.detail);
	}

	function handleEditNote(event: { detail: any }) {
		dispatch('editNote', event.detail);
	}

	function handleDeleteNote(event: { detail: any }) {
		dispatch('deleteNote', event.detail);
	}

	function handleEditChecklist(event: { detail: any }) {
		dispatch('editChecklist', event.detail);
	}

	function handleDeleteChecklist(event: { detail: any }) {
		dispatch('deleteChecklist', event.detail);
	}
</script>

<!-- Search and Filter Controls -->
<div
	class="bg-base-100/90 backdrop-blur-lg border border-base-300/50 rounded-2xl p-6 mx-4 mb-6 shadow-lg mt-4"
>
	<!-- Header with Stats -->
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<div class="p-2 bg-primary/10 rounded-xl">
				<Adventures class="w-6 h-6 text-primary" />
			</div>
			<div>
				<h2 class="text-xl font-bold text-primary">
					{$t('adventures.collection_contents')}
				</h2>
				<p class="text-sm text-base-content/60">
					{totalItems}
					{$t('worldtravel.total_items')}
				</p>
			</div>
		</div>

		<!-- Quick Stats -->
		<div class="hidden md:flex items-center gap-2">
			<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
				<div class="stat py-2 px-3">
					<div class="stat-title text-xs">{$t('locations.locations')}</div>
					<div class="stat-value text-sm text-info">{adventures.length}</div>
				</div>
				<div class="stat py-2 px-3">
					<div class="stat-title text-xs">{$t('adventures.transportations')}</div>
					<div class="stat-value text-sm text-warning">{transportations.length}</div>
				</div>
				<div class="stat py-2 px-3">
					<div class="stat-title text-xs">{$t('adventures.lodging')}</div>
					<div class="stat-value text-sm text-success">{lodging.length}</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Search Bar -->
	<div class="flex flex-col lg:flex-row items-stretch lg:items-center gap-4 mb-4">
		<div class="relative flex-1 max-w-md">
			<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-base-content/40" />
			<input
				type="text"
				placeholder="{$t('navbar.search')} {$t('adventures.name_location')}..."
				class="input input-bordered w-full pl-10 pr-10 bg-base-100/80"
				bind:value={searchQuery}
			/>
			{#if searchQuery.length > 0}
				<button
					class="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content"
					on:click={() => (searchQuery = '')}
				>
					<Clear class="w-4 h-4" />
				</button>
			{/if}
		</div>

		{#if searchQuery || filterOption !== 'all' || sortOption !== 'name_asc'}
			<button class="btn btn-ghost btn-sm gap-1" on:click={clearAllFilters}>
				<Clear class="w-3 h-3" />
				{$t('worldtravel.clear_all')}
			</button>
		{/if}
	</div>

	<!-- Sort Labels (Mobile Friendly) -->
	<div class="flex flex-wrap gap-2 mb-4">
		<div class="badge badge-outline gap-1">
			<Filter class="w-3 h-3" />
			{$t('adventures.sort')}:
		</div>
		<div class="flex flex-wrap gap-1">
			<button
				class="badge {sortOption === 'name_asc'
					? 'badge-primary'
					: 'badge-ghost'} cursor-pointer hover:badge-primary"
				on:click={() => (sortOption = 'name_asc')}
			>
				A-Z
			</button>
			<button
				class="badge {sortOption === 'name_desc'
					? 'badge-primary'
					: 'badge-ghost'} cursor-pointer hover:badge-primary"
				on:click={() => (sortOption = 'name_desc')}
			>
				Z-A
			</button>
			<button
				class="badge {sortOption === 'date_newest'
					? 'badge-primary'
					: 'badge-ghost'} cursor-pointer hover:badge-primary"
				on:click={() => (sortOption = 'date_newest')}
			>
				{$t('worldtravel.newest_first')}
			</button>
			<button
				class="badge {sortOption === 'date_oldest'
					? 'badge-primary'
					: 'badge-ghost'} cursor-pointer hover:badge-primary"
				on:click={() => (sortOption = 'date_oldest')}
			>
				{$t('worldtravel.oldest_first')}
			</button>
			<button
				class="badge {sortOption === 'visited_first'
					? 'badge-primary'
					: 'badge-ghost'} cursor-pointer hover:badge-primary"
				on:click={() => (sortOption = 'visited_first')}
			>
				{$t('worldtravel.visited_first')}
			</button>
			<button
				class="badge {sortOption === 'unvisited_first'
					? 'badge-primary'
					: 'badge-ghost'} cursor-pointer hover:badge-primary"
				on:click={() => (sortOption = 'unvisited_first')}
			>
				{$t('worldtravel.unvisited_first')}
			</button>
		</div>
	</div>

	<!-- Filter Tabs -->
	<div class="flex flex-col sm:flex-row sm:items-center gap-2">
		<span class="text-sm font-medium text-base-content/60">
			{$t('adventures.show')}:
		</span>

		<!-- Scrollable container on mobile -->
		<div class="w-full overflow-x-auto">
			<div class="tabs tabs-boxed bg-base-200 flex-nowrap flex sm:flex-wrap w-max sm:w-auto">
				<button
					class="tab tab-sm gap-2 {filterOption === 'all' ? 'tab-active' : ''} whitespace-nowrap"
					on:click={() => (filterOption = 'all')}
				>
					<Adventures class="w-3 h-3" />
					{$t('adventures.all')}
				</button>
				<button
					class="tab tab-sm gap-2 {filterOption === 'adventures'
						? 'tab-active'
						: ''} whitespace-nowrap"
					on:click={() => (filterOption = 'adventures')}
				>
					<Adventures class="w-3 h-3" />
					{$t('locations.locations')}
				</button>
				<button
					class="tab tab-sm gap-2 {filterOption === 'transportation'
						? 'tab-active'
						: ''} whitespace-nowrap"
					on:click={() => (filterOption = 'transportation')}
				>
					<TransportationIcon class="w-3 h-3" />
					{$t('adventures.transportations')}
				</button>
				<button
					class="tab tab-sm gap-2 {filterOption === 'lodging'
						? 'tab-active'
						: ''} whitespace-nowrap"
					on:click={() => (filterOption = 'lodging')}
				>
					<Hotel class="w-3 h-3" />
					{$t('adventures.lodging')}
				</button>
				<button
					class="tab tab-sm gap-2 {filterOption === 'notes' ? 'tab-active' : ''} whitespace-nowrap"
					on:click={() => (filterOption = 'notes')}
				>
					<NoteIcon class="w-3 h-3" />
					{$t('adventures.notes')}
				</button>
				<button
					class="tab tab-sm gap-2 {filterOption === 'checklists'
						? 'tab-active'
						: ''} whitespace-nowrap"
					on:click={() => (filterOption = 'checklists')}
				>
					<ChecklistIcon class="w-3 h-3" />
					{$t('adventures.checklists')}
				</button>
			</div>
		</div>
	</div>
</div>

<!-- Adventures Section -->
{#if (filterOption === 'all' || filterOption === 'adventures') && filteredAdventures.length > 0}
	<div class="mb-8">
		<div class="flex items-center justify-between mx-4 mb-4">
			<h1 class="text-3xl font-bold text-primary">
				{$t('adventures.linked_locations')}
			</h1>
			<div class="badge badge-primary badge-lg">{filteredAdventures.length}</div>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mx-4">
			{#each filteredAdventures as adventure}
				<LocationCard
					{user}
					on:edit={handleEditAdventure}
					on:delete={handleDeleteAdventure}
					{adventure}
					{collection}
				/>
			{/each}
		</div>
	</div>
{/if}

<!-- Transportation Section -->
{#if (filterOption === 'all' || filterOption === 'transportation') && filteredTransportations.length > 0}
	<div class="mb-8">
		<div class="flex items-center justify-between mx-4 mb-4">
			<h1 class="text-3xl font-bold bg-clip-text text-primary">
				{$t('adventures.transportations')}
			</h1>
			<div class="badge badge-warning badge-lg">{filteredTransportations.length}</div>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mx-4">
			{#each filteredTransportations as transportation}
				<TransportationCard
					{transportation}
					{user}
					on:delete={handleDeleteTransportation}
					on:edit={handleEditTransportation}
					{collection}
				/>
			{/each}
		</div>
	</div>
{/if}

<!-- Lodging Section -->
{#if (filterOption === 'all' || filterOption === 'lodging') && filteredLodging.length > 0}
	<div class="mb-8">
		<div class="flex items-center justify-between mx-4 mb-4">
			<h1 class="text-3xl font-bold bg-clip-text text-primary">
				{$t('adventures.lodging')}
			</h1>
			<div class="badge badge-success badge-lg">{filteredLodging.length}</div>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mx-4">
			{#each filteredLodging as hotel}
				<LodgingCard
					lodging={hotel}
					{user}
					on:delete={handleDeleteLodging}
					on:edit={handleEditLodging}
					{collection}
				/>
			{/each}
		</div>
	</div>
{/if}

<!-- Notes Section -->
{#if (filterOption === 'all' || filterOption === 'notes') && filteredNotes.length > 0}
	<div class="mb-8">
		<div class="flex items-center justify-between mx-4 mb-4">
			<h1 class="text-3xl font-bold bg-clip-text text-primary">
				{$t('adventures.notes')}
			</h1>
			<div class="badge badge-info badge-lg">{filteredNotes.length}</div>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mx-4">
			{#each filteredNotes as note}
				<NoteCard
					{note}
					{user}
					on:edit={handleEditNote}
					on:delete={handleDeleteNote}
					{collection}
				/>
			{/each}
		</div>
	</div>
{/if}

<!-- Checklists Section -->
{#if (filterOption === 'all' || filterOption === 'checklists') && filteredChecklists.length > 0}
	<div class="mb-8">
		<div class="flex items-center justify-between mx-4 mb-4">
			<h1 class="text-3xl font-bold bg-clip-text text-primary">
				{$t('adventures.checklists')}
			</h1>
			<div class="badge badge-secondary badge-lg">{filteredChecklists.length}</div>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mx-4">
			{#each filteredChecklists as checklist}
				<ChecklistCard
					{checklist}
					{user}
					on:delete={handleDeleteChecklist}
					on:edit={handleEditChecklist}
					{collection}
				/>
			{/each}
		</div>
	</div>
{/if}

<!-- Empty State -->
{#if totalItems === 0}
	<div class="hero min-h-96">
		<div class="hero-content text-center">
			<div class="max-w-md">
				<Clear class="w-16 h-16 text-base-content/30 mb-4" />
				<h1 class="text-3xl font-bold text-base-content/70">
					{$t('immich.no_items_found')}
				</h1>
			</div>
		</div>
	</div>
{/if}
