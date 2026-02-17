<script lang="ts">
	import type { Transportation, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import TransportationCard from './cards/TransportationCard.svelte';

	// Icons
	import Plane from '~icons/mdi/airplane';
	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Link from '~icons/mdi/link-variant';
	import Check from '~icons/mdi/check-circle';
	import Public from '~icons/mdi/earth';
	import Private from '~icons/mdi/lock';

	let modal: HTMLDialogElement;
	let transportations: Transportation[] = [];
	let filteredTransportations: Transportation[] = [];
	let searchQuery: string = '';
	let filterOption: string = 'all';
	let isLoading: boolean = true;
	let linkingId: string | null = null;

	export let user: User | null;
	export let collectionId: string;

	// Search and filter functionality
	$: {
		let filtered = transportations;

		// Apply search filter
		if (searchQuery !== '') {
			filtered = filtered.filter((t) => {
				const nameMatch = t.name.toLowerCase().includes(searchQuery.toLowerCase());
				const fromMatch = t.from_location?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				const toMatch = t.to_location?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				return nameMatch || fromMatch || toMatch;
			});
		}

		// Apply status filter
		if (filterOption === 'public') {
			filtered = filtered.filter((t) => t.is_public);
		} else if (filterOption === 'private') {
			filtered = filtered.filter((t) => !t.is_public);
		} else if (filterOption === 'unlinked') {
			filtered = filtered.filter((t) => !t.collections || t.collections.length === 0);
		}

		filteredTransportations = filtered;
	}

	// Statistics
	$: totalTransportations = transportations.length;
	$: unlinkedTransportations = transportations.filter((t) => !t.collections || t.collections.length === 0).length;

	onMount(async () => {
		modal = document.getElementById('transportation_link_modal') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}

		try {
			const res = await fetch(`/api/transportations/`, {
				method: 'GET'
			});

			if (!res.ok) {
				console.error('Failed to fetch transportations:', res.status, res.statusText);
				isLoading = false;
				return;
			}

			const allTransportations = (await res.json()) as Transportation[];
			// Filter out transportations that are already linked to this collection
			transportations = allTransportations.filter(
				(t) => !t.collections || !t.collections.includes(collectionId)
			);

			isLoading = false;
		} catch (error) {
			console.error('Error fetching transportations:', error);
			isLoading = false;
		}
	});

	function close() {
		dispatch('close');
	}

	async function linkTransportation(transportation: Transportation) {
		linkingId = transportation.id;

		// Transportation supports multiple collections, so just add the new one
		const existingCollections = transportation.collections || [];

		try {
			// Add the new collection to existing ones
			const newCollections = [...existingCollections, collectionId];
			const response = await fetch(`/api/transportations/${transportation.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					collections: newCollections
				})
			});

			if (response.ok) {
				const updated = await response.json();
				// Remove from list
				transportations = transportations.filter((t) => t.id !== transportation.id);
				dispatch('add', updated);
			} else {
				console.error('Failed to link transportation:', await response.text());
			}
		} catch (error) {
			console.error('Error linking transportation:', error);
		} finally {
			linkingId = null;
		}
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

<dialog id="transportation_link_modal" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section -->
		<div
			class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<Plane class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{$t('adventures.link_transportation')}
						</h1>
						<p class="text-sm text-base-content/60">
							{filteredTransportations.length}
							{$t('worldtravel.of')}
							{totalTransportations}
							{$t('adventures.transportations').toLowerCase()}
						</p>
					</div>
				</div>

				<!-- Quick Stats -->
				<div class="hidden md:flex items-center gap-2">
					<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
						<div class="stat py-2 px-4">
							<div class="stat-title text-xs">{$t('collection.available')}</div>
							<div class="stat-value text-lg text-info">{totalTransportations}</div>
						</div>
						<div class="stat py-2 px-4">
							<div class="stat-title text-xs">{$t('adventures.unlinked')}</div>
							<div class="stat-value text-lg text-success">{unlinkedTransportations}</div>
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
						placeholder="{$t('navbar.search')} {$t('adventures.name')}, {$t('adventures.from')}, {$t('adventures.to')}..."
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
						<Plane class="w-3 h-3" />
						{$t('adventures.all')}
					</button>
					<button
						class="tab tab-sm gap-2 {filterOption === 'unlinked' ? 'tab-active' : ''}"
						on:click={() => (filterOption = 'unlinked')}
					>
						<Check class="w-3 h-3" />
						{$t('adventures.unlinked')}
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
			</div>
		{:else}
			<!-- Main Content -->
			<div class="px-2">
				{#if filteredTransportations.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							<Plane class="w-16 h-16 text-base-content/30" />
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
								{$t('adventures.no_transportations_available')}
							</h3>
							<p class="text-base-content/50 text-center max-w-md">
								{$t('adventures.all_transportations_linked')}
							</p>
						{/if}
					</div>
				{:else}
					<!-- Transportation Grid -->
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6 p-4">
						{#each filteredTransportations as transportation (transportation.id)}
							<div class="relative">
								<TransportationCard {transportation} user={user} />
								<div class="absolute bottom-4 right-4">
									<button
										class="btn btn-primary btn-sm gap-2"
										disabled={linkingId === transportation.id}
										on:click={() => linkTransportation(transportation)}
									>
										{#if linkingId === transportation.id}
											<span class="loading loading-spinner loading-xs"></span>
										{:else}
											<Link class="w-4 h-4" />
										{/if}
										{$t('adventures.add_to_collection')}
									</button>
								</div>
							</div>
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
					{filteredTransportations.length}
					{$t('adventures.transportations').toLowerCase()}
				</div>
				<button class="btn btn-primary gap-2" on:click={close}>
					<Link class="w-4 h-4" />
					{$t('adventures.done')}
				</button>
			</div>
		</div>
	</div>
</dialog>
