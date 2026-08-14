<script lang="ts">
	import { run } from 'svelte/legacy';

	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { MapSearchMode, Pin, PlaceSearchResult } from '$lib/types';
	import { searchPlaces } from '$lib/map/places';
	import SearchIcon from '~icons/mdi/magnify';
	import ClearIcon from '~icons/mdi/close';
	import MapMarkerIcon from '~icons/mdi/map-marker';
	import PlaceIcon from '~icons/mdi/map-search';
	import NearbyIcon from '~icons/mdi/compass-outline';
	import DiceIcon from '~icons/mdi/dice-5';

	interface Props {
		mode?: MapSearchMode;
		query?: string;
		filteredPins?: Pin[];
		isSearching?: boolean;
		searchError?: string | null;
		randomDisabled?: boolean;
	}

	let {
		mode = 'my',
		query = $bindable(''),
		filteredPins = [],
		isSearching = $bindable(false),
		searchError = $bindable(null),
		randomDisabled = false
	}: Props = $props();

	const dispatch = createEventDispatcher<{
		modeChange: MapSearchMode;
		queryChange: string;
		selectPin: { pinId: string };
		selectPlace: { place: PlaceSearchResult };
		random: void;
	}>();

	let placeResults: PlaceSearchResult[] = $state([]);
	let showDropdown = $state(false);
	let searchTimeout: ReturnType<typeof setTimeout>;
	let placeProvider: string | null = null;

	const modes: {
		id: MapSearchMode;
		labelKey: string;
		icon: typeof MapMarkerIcon;
	}[] = [
		{ id: 'my', labelKey: 'map.search_mode_my', icon: MapMarkerIcon },
		{ id: 'places', labelKey: 'map.search_mode_places', icon: PlaceIcon },
		{ id: 'nearby', labelKey: 'map.search_mode_nearby', icon: NearbyIcon }
	];

	let myResults =
		$derived(mode === 'my' && query.trim()
			? filteredPins
					.filter((pin) => {
						const q = query.toLowerCase().trim();
						return (
							pin.name?.toLowerCase().includes(q) ||
							pin.category?.display_name?.toLowerCase().includes(q)
						);
					})
					.slice(0, 8)
			: []);

	run(() => {
		showDropdown = Boolean(
			(mode === 'my' && myResults.length > 0 && query.trim().length > 0) ||
			(mode === 'places' && (placeResults.length > 0 || isSearching || searchError))
		);
	});

	function handleModeChange(newMode: MapSearchMode) {
		if (newMode === mode) return;
		placeResults = [];
		searchError = null;
		showDropdown = false;
		dispatch('modeChange', newMode);
	}

	function handleInput() {
		dispatch('queryChange', query);
		if (mode !== 'places') {
			placeResults = [];
			searchError = null;
			return;
		}
		clearTimeout(searchTimeout);
		if (query.trim().length < 3) {
			placeResults = [];
			searchError = null;
			isSearching = false;
			return;
		}
		searchTimeout = setTimeout(runPlaceSearch, 300);
	}

	async function runPlaceSearch() {
		const q = query.trim();
		if (q.length < 3) return;
		isSearching = true;
		searchError = null;
		try {
			const meta = await searchPlaces(q);
			placeResults = meta.results;
			placeProvider = meta.provider_used || null;
		} catch (err) {
			placeResults = [];
			searchError = err instanceof Error ? err.message : $t('map.search_error');
		} finally {
			isSearching = false;
		}
	}

	function clearQuery() {
		query = '';
		placeResults = [];
		searchError = null;
		dispatch('queryChange', '');
	}

	function selectPin(pin: Pin) {
		showDropdown = false;
		dispatch('selectPin', { pinId: pin.id });
	}

	function selectPlace(place: PlaceSearchResult) {
		showDropdown = false;
		query = place.name;
		dispatch('selectPlace', { place });
	}

	function handleRandomClick() {
		dispatch('random');
	}

	onMount(() => () => clearTimeout(searchTimeout));
</script>

<div class="flex flex-col gap-1.5 sm:gap-2 w-full min-w-0">
	<div
		class="grid grid-cols-3 gap-0.5 sm:gap-1 w-full min-w-0 rounded-lg bg-base-200/60 p-0.5 sm:p-1"
		role="tablist"
		aria-label={$t('map.search_locations')}
	>
		{#each modes as m}
			<button
				type="button"
				role="tab"
				aria-selected={mode === m.id}
				class="btn btn-xs sm:btn-sm min-w-0 h-8 sm:h-9 px-1.5 sm:px-2 gap-0.5 sm:gap-1 {mode ===
 m.id
 ? 'btn-primary'
 : 'btn-ghost bg-base-100/80'}"
				onclick={() => handleModeChange(m.id)}
			>
				<m.icon class="w-3.5 h-3.5 sm:w-4 sm:h-4 shrink-0" />
				<span
					class="truncate text-[10px] min-[380px]:text-[11px] sm:text-sm leading-none max-[379px]:sr-only"
				>
					{$t(m.labelKey)}
				</span>
			</button>
		{/each}
	</div>

	{#if mode === 'nearby'}
		<p class="px-1 text-xs text-base-content/60 leading-snug">
			{$t('map.nearby_search_hint')}
		</p>
	{:else}
		<div class="relative w-full flex items-center gap-1.5">
			<div class="relative flex-1 min-w-0">
				<label
					class="input input-sm flex items-center gap-2 w-full min-w-0 bg-base-100/95 shadow-xs"
				>
					<SearchIcon class="h-4 w-4 opacity-70 shrink-0" />
					<input
						type="text"
						class="grow min-w-0"
						placeholder={mode === 'my'
							? $t('map.search_locations')
							: $t('map.search_places_placeholder')}
						bind:value={query}
						oninput={handleInput}
						onfocus={() => {
							if (mode === 'places' && placeResults.length) showDropdown = true;
						}}
					/>
					{#if query}
						<button
							type="button"
							class="btn btn-ghost btn-xs btn-circle shrink-0"
							onclick={clearQuery}
							aria-label={$t('map.clear_search')}
						>
							<ClearIcon class="w-4 h-4" />
						</button>
					{/if}
				</label>

				{#if showDropdown}
					<ul
						class="absolute top-full left-0 right-0 z-50 mt-1 menu bg-base-100 rounded-box shadow-xl border border-base-300 max-h-64 overflow-y-auto p-1"
						role="listbox"
					>
						{#if mode === 'my'}
							{#each myResults as pin (pin.id)}
								<li>
									<button type="button" onclick={() => selectPin(pin)}>
										<span class="truncate">{pin.name}</span>
										{#if pin.category?.icon}
											<span class="badge badge-ghost badge-xs">{pin.category.icon}</span>
										{/if}
									</button>
								</li>
							{/each}
						{:else if mode === 'places'}
							{#if isSearching}
								<li class="px-3 py-2 text-sm text-base-content/60">
									<span class="loading loading-spinner loading-xs"></span>
									{$t('map.searching')}
								</li>
							{:else if searchError}
								<li class="px-3 py-2 text-sm text-error">{searchError}</li>
							{:else if placeResults.length === 0 && query.trim().length >= 3}
								<li class="px-3 py-2 text-sm text-base-content/60">{$t('map.no_results')}</li>
							{:else}
								{#each placeResults as place (place.id)}
									<li>
										<button type="button" onclick={() => selectPlace(place)}>
											<div class="flex flex-col items-start min-w-0">
												<span class="font-medium truncate w-full">{place.name}</span>
												<span class="text-xs text-base-content/60 truncate w-full"
													>{place.location}</span
												>
											</div>
										</button>
									</li>
								{/each}
							{/if}
						{/if}
					</ul>
				{/if}
			</div>
			{#if mode === 'my'}
				<button
					type="button"
					class="btn btn-ghost btn-square btn-sm shrink-0 bg-base-100/95 border border-base-300 shadow-xs"
					disabled={randomDisabled}
					onclick={handleRandomClick}
					aria-label={$t('map.random_location')}
					title={$t('map.random_location')}
				>
					<DiceIcon class="w-4 h-4" />
				</button>
			{/if}
		</div>
	{/if}
</div>
