<script lang="ts">
	import type { Location, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import LocationCard from './LocationCard.svelte';
	let modal: HTMLDialogElement;

	// Icons - following the worldtravel pattern
	import Adventures from '~icons/mdi/map-marker-path';
	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Link from '~icons/mdi/link-variant';
	import Check from '~icons/mdi/check-circle';
	import Cancel from '~icons/mdi/cancel';
	import Public from '~icons/mdi/earth';
	import Private from '~icons/mdi/lock';

	let adventures: Location[] = [];
	let filteredAdventures: Location[] = [];
	let searchQuery: string = '';
	let filterOption: string = 'all';
	let isLoading: boolean = true;

	export let user: User | null;
	export let collectionId: string;

	// Search and filter functionality following worldtravel pattern
	$: {
		let filtered = adventures;

		// Apply search filter - include name and location
		if (searchQuery !== '') {
			filtered = filtered.filter((adventure) => {
				const nameMatch = adventure.name.toLowerCase().includes(searchQuery.toLowerCase());
				const locationMatch =
					adventure.location?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				const descriptionMatch =
					adventure.description?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				return nameMatch || locationMatch || descriptionMatch;
			});
		}

		// Apply status filter
		if (filterOption === 'public') {
			filtered = filtered.filter((adventure) => adventure.is_public);
		} else if (filterOption === 'private') {
			filtered = filtered.filter((adventure) => !adventure.is_public);
		} else if (filterOption === 'visited') {
			filtered = filtered.filter((adventure) => adventure.visits && adventure.visits.length > 0);
		} else if (filterOption === 'not_visited') {
			filtered = filtered.filter((adventure) => !adventure.visits || adventure.visits.length === 0);
		}

		filteredAdventures = filtered;
	}

	// Statistics following worldtravel pattern
	$: totalAdventures = adventures.length;
	$: publicAdventures = adventures.filter((a) => a.is_public).length;
	$: privateAdventures = adventures.filter((a) => !a.is_public).length;
	$: visitedAdventures = adventures.filter((a) => a.visits && a.visits.length > 0).length;
	$: notVisitedAdventures = adventures.filter((a) => !a.visits || a.visits.length === 0).length;

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}

		let res = await fetch(`/api/locations/all/?include_collections=true`, {
			method: 'GET'
		});

		const newAdventures = await res.json();

		// Filter out adventures that are already linked to the collections
		if (collectionId) {
			adventures = newAdventures.filter((adventure: Location) => {
				return !(adventure.collections ?? []).includes(collectionId);
			});
		} else {
			adventures = newAdventures;
		}

		isLoading = false;
	});

	function close() {
		dispatch('close');
	}

	function add(event: CustomEvent<Location>) {
		adventures = adventures.filter((a) => a.id !== event.detail.id);
		dispatch('add', event.detail);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	function clearFilters() {
		searchQuery = '';
		filterOption = 'all';
	}
</script>

<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section - Following worldtravel pattern -->
		<div
			class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<Adventures class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{$t('adventures.my_adventures')}
						</h1>
						<p class="text-sm text-base-content/60">
							{filteredAdventures.length}
							{$t('worldtravel.of')}
							{totalAdventures}
							{$t('locations.locations')}
						</p>
					</div>
				</div>

				<!-- Quick Stats -->
				<div class="hidden md:flex items-center gap-2">
					<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
						<div class="stat py-2 px-4">
							<div class="stat-title text-xs">{$t('collection.available')}</div>
							<div class="stat-value text-lg text-info">{totalAdventures}</div>
						</div>
						<div class="stat py-2 px-4">
							<div class="stat-title text-xs">{$t('adventures.visited')}</div>
							<div class="stat-value text-lg text-success">{visitedAdventures}</div>
						</div>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={close}>
					<Clear class="w-5 h-5" />
				</button>
			</div>

			<!-- Search Bar -->
			<div class="mt-4 flex items-center gap-4">
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

				{#if searchQuery || filterOption !== 'all'}
					<button class="btn btn-ghost btn-xs gap-1" on:click={clearFilters}>
						<Clear class="w-3 h-3" />
						{$t('worldtravel.clear_all')}
					</button>
				{/if}
			</div>

			<!-- Filter Chips -->
			<div class="mt-4 flex flex-wrap items-center gap-2">
				<span class="text-sm font-medium text-base-content/60">
					{$t('worldtravel.filter_by')}:
				</span>
				<div class="tabs tabs-boxed bg-base-200">
					<button
						class="tab tab-sm gap-2 {filterOption === 'all' ? 'tab-active' : ''}"
						on:click={() => (filterOption = 'all')}
					>
						<Adventures class="w-3 h-3" />
						{$t('adventures.all')}
					</button>
					<button
						class="tab tab-sm gap-2 {filterOption === 'visited' ? 'tab-active' : ''}"
						on:click={() => (filterOption = 'visited')}
					>
						<Check class="w-3 h-3" />
						{$t('adventures.visited')}
					</button>
					<button
						class="tab tab-sm gap-2 {filterOption === 'not_visited' ? 'tab-active' : ''}"
						on:click={() => (filterOption = 'not_visited')}
					>
						<Cancel class="w-3 h-3" />
						{$t('adventures.not_visited')}
					</button>
					<button
						class="tab tab-sm gap-2 {filterOption === 'public' ? 'tab-active' : ''}"
						on:click={() => (filterOption = 'public')}
					>
						<Public class="w-3 h-3" />
						{$t('adventures.public')}
					</button>
					<button
						class="tab tab-sm gap-2 {filterOption === 'private' ? 'tab-active' : ''}"
						on:click={() => (filterOption = 'private')}
					>
						<Private class="w-3 h-3" />
						{$t('adventures.private')}
					</button>
				</div>
			</div>
		</div>

		<!-- Loading State -->
		{#if isLoading}
			<div class="flex flex-col items-center justify-center py-16">
				<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
					<span class="loading loading-spinner w-16 h-16 text-primary"></span>
				</div>
				<h3 class="text-xl font-semibold text-base-content/70 mb-2">
					{$t('adventures.loading_adventures')}
				</h3>
			</div>
		{:else}
			<!-- Main Content -->
			<div class="px-2">
				{#if filteredAdventures.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							<Adventures class="w-16 h-16 text-base-content/30" />
						</div>
						{#if searchQuery || filterOption !== 'all'}
							<h3 class="text-xl font-semibold text-base-content/70 mb-2">
								{$t('adventures.no_locations_found')}
							</h3>
							<p class="text-base-content/50 text-center max-w-md mb-6">
								{$t('collection.try_different_search')}
							</p>
							<button class="btn btn-primary gap-2" on:click={clearFilters}>
								<Clear class="w-4 h-4" />
								{$t('worldtravel.clear_filters')}
							</button>
						{:else}
							<h3 class="text-xl font-semibold text-base-content/70 mb-2">
								{$t('adventures.no_linkable_adventures')}
							</h3>
							<p class="text-base-content/50 text-center max-w-md">
								{$t('adventures.all_adventures_already_linked')}
							</p>
						{/if}
					</div>
				{:else}
					<!-- Adventures Grid -->
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6 p-4">
						{#each filteredAdventures as adventure}
							<LocationCard {user} type="link" {adventure} on:link={add} />
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Footer Actions -->
		<div
			class="sticky bottom-0 bg-base-100/90 backdrop-blur-lg border-t border-base-300 -mx-6 -mb-6 px-6 py-4 mt-6 rounded-lg"
		>
			<div class="flex items-center justify-between">
				<div class="text-sm text-base-content/60">
					{filteredAdventures.length}
					{$t('adventures.adventures_available')}
				</div>
				<button class="btn btn-primary gap-2" on:click={close}>
					<Link class="w-4 h-4" />
					{$t('adventures.done')}
				</button>
			</div>
		</div>
	</div>
</dialog>
