<script lang="ts">
	import { run } from 'svelte/legacy';

	import type { Location, User, Pin } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import LocationCard from './cards/LocationCard.svelte';
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
	import Loading from '~icons/mdi/loading';

	let pins: Pin[] = $state([]);
	let locationCache: Map<string, Location> = $state(new Map());
	let loadingLocationIds: Set<string> = new Set();
	let locationRequests: Map<string, Promise<Location | null>> = new Map();

	let filteredPins: Pin[] = $state([]);
	let filteredLocations: Map<string, Location | null> = new Map();
	let searchQuery: string = $state('');
	let filterOption: string = $state('all');
	let isLoading: boolean = $state(true);

	interface Props {
		user: User | null;
		collectionId: string;
	}

	let { user, collectionId }: Props = $props();

	// Search and filter functionality - works with pins and cached locations
	run(() => {
		let filtered = pins;

		// Apply search filter - include name and location (using pin data + cached location data)
		if (searchQuery !== '') {
			filtered = filtered.filter((pin) => {
				const nameMatch = pin.name.toLowerCase().includes(searchQuery.toLowerCase());
				const cachedLocation = locationCache.get(pin.id);
				const locationMatch =
					cachedLocation?.location?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				const descriptionMatch =
					cachedLocation?.description?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
				return nameMatch || locationMatch || descriptionMatch;
			});
		}

		// Apply status filter (using pin data + cached location data)
		if (filterOption === 'public') {
			filtered = filtered.filter((pin) => {
				const cachedLocation = locationCache.get(pin.id);
				return cachedLocation?.is_public ?? false;
			});
		} else if (filterOption === 'private') {
			filtered = filtered.filter((pin) => {
				const cachedLocation = locationCache.get(pin.id);
				return !(cachedLocation?.is_public ?? true);
			});
		} else if (filterOption === 'visited') {
			filtered = filtered.filter((pin) => pin.is_visited === true);
		} else if (filterOption === 'not_visited') {
			filtered = filtered.filter((pin) => pin.is_visited !== true);
		}

		filteredPins = filtered;
	});

	// Statistics following worldtravel pattern
	let totalAdventures = $derived(pins.length);
	let visitedAdventures = $derived(pins.filter((p) => p.is_visited === true).length);
	let plannedAdventures = $derived(pins.filter((p) => p.is_visited !== true).length);

	// Fetch location details lazily (like the map page)
	async function fetchLocationDetails(locationId: string): Promise<Location | null> {
		// Check cache first
		if (locationCache.has(locationId)) {
			return locationCache.get(locationId)!;
		}

		// Reuse in-flight requests
		const existing = locationRequests.get(locationId);
		if (existing) return existing;

		const request = (async () => {
			try {
				loadingLocationIds.add(locationId);
				const res = await fetch(`/api/locations/${locationId}/?include_collections=true`);
				if (!res.ok) {
					console.error(`Failed to fetch location ${locationId}`);
					return null;
				}
				const location = (await res.json()) as Location;
				locationCache.set(locationId, location);
				// Trigger reactivity
				locationCache = locationCache;
				return location;
			} catch (error) {
				console.error('Error fetching location details:', error);
				return null;
			} finally {
				loadingLocationIds.delete(locationId);
				locationRequests.delete(locationId);
			}
		})();

		locationRequests.set(locationId, request);
		loadingLocationIds.add(locationId);
		return request;
	}

	// Intersection Observer for lazy loading
	let observer: IntersectionObserver | null = $state(null);

	function setupLazyLoading(element: HTMLElement) {
		observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						const pinId = entry.target.getAttribute('data-pin-id');
						if (pinId && !locationCache.has(pinId) && !loadingLocationIds.has(pinId)) {
							console.log('Lazy loading location:', pinId);
							fetchLocationDetails(pinId);
						}
					}
				});
			},
			{ rootMargin: '200px' } // Start loading 200px before it comes into view
		);

		return {
			destroy: () => {
				if (observer) {
					observer.disconnect();
				}
			}
		};
	}

	// Re-observe elements when pins change
	run(() => {
		if (observer && filteredPins.length > 0) {
			// Disconnect and reconnect to observe all pin cards
			observer.disconnect();
			setTimeout(() => {
				const pinCards = document.querySelectorAll('[data-pin-id]');
				console.log('Observing pin cards:', pinCards.length);
				pinCards.forEach((el) => observer?.observe(el));
			}, 0);
		}
	});

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}

		try {
			// Fetch minimal pin data first
			const res = await fetch(`/api/locations/pins/`, {
				method: 'GET'
			});

			if (!res.ok) {
				console.error('Failed to fetch pins:', res.status, res.statusText);
				isLoading = false;
				return;
			}

			const newPins = (await res.json()) as Pin[];
			console.log('Fetched pins:', newPins);

			// Filter out pins that are already linked to the collection
			if (collectionId) {
				// For now, show all pins - we'll check collections when fetching full data
				pins = newPins;
			} else {
				pins = newPins;
			}

			console.log('Set pins to:', pins);
			isLoading = false;
		} catch (error) {
			console.error('Error fetching pins:', error);
			isLoading = false;
		}
	});

	function close() {
		dispatch('close');
	}

	function add(event: CustomEvent<Location>) {
		pins = pins.filter((p) => p.id !== event.detail.id);
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

<dialog id="my_modal_1" class="modal backdrop-blur-xs">
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		onkeydown={handleKeydown}
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
							{$t('adventures.my_locations')}
						</h1>
						<p class="text-sm text-base-content/60">
							{filteredPins.length}
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
				<button class="btn btn-ghost btn-square" onclick={close}>
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
						class="input w-full pl-10 pr-10 bg-base-100/80"
						bind:value={searchQuery}
					/>
					{#if searchQuery.length > 0}
						<button
							class="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content"
							onclick={() => (searchQuery = '')}
						>
							<Clear class="w-4 h-4" />
						</button>
					{/if}
				</div>

				{#if searchQuery || filterOption !== 'all'}
					<button class="btn btn-ghost btn-xs gap-1" onclick={clearFilters}>
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
				<div class="tabs tabs-box bg-base-200">
					<button
						class="tab tab-sm gap-2 {filterOption === 'all' ? 'tab-active' : ''}"
						onclick={() => (filterOption = 'all')}
					>
						<Adventures class="w-3 h-3" />
						{$t('adventures.all')}
					</button>
					<button
						class="tab tab-sm gap-2 {filterOption === 'visited' ? 'tab-active' : ''}"
						onclick={() => (filterOption = 'visited')}
					>
						<Check class="w-3 h-3" />
						{$t('adventures.visited')}
					</button>
					<button
						class="tab tab-sm gap-2 {filterOption === 'not_visited' ? 'tab-active' : ''}"
						onclick={() => (filterOption = 'not_visited')}
					>
						<Cancel class="w-3 h-3" />
						{$t('adventures.not_visited')}
					</button>
					<button
						class="tab tab-sm gap-2 {filterOption === 'public' ? 'tab-active' : ''}"
						onclick={() => (filterOption = 'public')}
					>
						<Public class="w-3 h-3" />
						{$t('adventures.public')}
					</button>
					<button
						class="tab tab-sm gap-2 {filterOption === 'private' ? 'tab-active' : ''}"
						onclick={() => (filterOption = 'private')}
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
				<!-- <h3 class="text-xl font-semibold text-base-content/70 mb-2">
					{$t('immich.loading')}
				</h3> -->
			</div>
		{:else}
			<!-- Main Content -->
			<div class="px-2" use:setupLazyLoading>
				{#if filteredPins.length === 0}
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
							<button class="btn btn-primary gap-2" onclick={clearFilters}>
								<Clear class="w-4 h-4" />
								{$t('worldtravel.clear_filters')}
							</button>
						{:else}
							<h3 class="text-xl font-semibold text-base-content/70 mb-2">
								{$t('adventures.no_linkable_locations')}
							</h3>
							<p class="text-base-content/50 text-center max-w-md">
								{$t('adventures.all_locations_already_linked')}
							</p>
						{/if}
					</div>
				{:else}
					<!-- Locations Grid with Lazy Loading -->
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6 p-4">
						{#each filteredPins as pin (pin.id)}
							<div data-pin-id={pin.id} class="h-full">
								{#if locationCache.has(pin.id)}
									{@const location = locationCache.get(pin.id)}
									{#if location}
										<LocationCard {user} type="link" adventure={location} on:link={add} />
									{/if}
								{:else}
									<!-- Skeleton Loading Card -->
									<div class="card w-full bg-base-300 shadow-sm animate-pulse">
										<div class="h-48 bg-base-200"></div>
										<div class="card-body gap-3">
											<div class="h-6 bg-base-200 rounded-sm w-3/4"></div>
											<div class="h-4 bg-base-200 rounded-sm w-full"></div>
											<div class="h-4 bg-base-200 rounded-sm w-2/3"></div>
										</div>
									</div>
								{/if}
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
					{filteredPins.length}
					{$t('locations.locations')}
				</div>
				<button class="btn btn-primary gap-2" onclick={close}>
					<Link class="w-4 h-4" />
					{$t('adventures.done')}
				</button>
			</div>
		</div>
	</div>
</dialog>
