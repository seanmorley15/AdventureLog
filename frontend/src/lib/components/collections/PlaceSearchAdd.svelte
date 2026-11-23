<script lang="ts">
	import { onDestroy } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { Collection, Location, PlaceSearchResult, User } from '#lib/types.js';
	import CategoryDropdown from '#lib/components/CategoryDropdown.svelte';
	import { placeCategory } from '#lib/collections/place-category.svelte.js';
	import {
		enrichPlace,
		placeToLocationPrefill,
		placeToQuickAddPayload,
		quickAddLocation,
		resolveQuickAddPayload,
		searchPlaces
	} from '#lib/map/places.js';
	import { findCollectionMatch } from '#lib/recommendations/match.js';
	import { addToast } from '#lib/toasts.js';

	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Plus from '~icons/mdi/plus';
	import MapMarker from '~icons/mdi/map-marker';
	import Compass from '~icons/mdi/compass-outline';
	import Check from '~icons/mdi/check';
	import TextBoxEdit from '~icons/mdi/text-box-edit-outline';

	interface Props {
		collection: Collection;
		user?: User | null;
		/** A place was picked (or the pick was cleared with `null`), so the parent can show it on its map. */
		onSelect?: (place: PlaceSearchResult | null) => void;
		/** The place was quick-added to the collection. */
		onAdded?: (location: Location) => void;
		/** The user wants the full form; receives a prefilled location to edit. Hidden when not provided. */
		onDetails?: (prefill: Location) => void;
		/** Recenter a nearby search on the place. Hidden when not provided. */
		onSearchNearby?: (place: PlaceSearchResult) => void;
		class?: string;
	}

	let {
		collection,
		user = null,
		onSelect,
		onAdded,
		onDetails,
		onSearchNearby,
		class: className = ''
	}: Props = $props();

	const MIN_QUERY = 3;

	let root: HTMLElement | undefined = $state();
	let query = $state('');
	let results: PlaceSearchResult[] = $state([]);
	let searching = $state(false);
	let searchError = $state<string | null>(null);
	let hasSearched = $state(false);
	let open = $state(false);
	let picked = $state<PlaceSearchResult | null>(null);
	let adding = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;
	let requestId = 0;

	const alreadyAdded = $derived(
		picked
			? findCollectionMatch(
					{ name: picked.name, latitude: picked.lat, longitude: picked.lng } as never,
					collection
				)
			: null
	);
	const showDropdown = $derived(open && (searching || searchError || hasSearched));

	function onInput() {
		clearTimeout(timer);
		const q = query.trim();
		if (q.length < MIN_QUERY) {
			requestId++;
			results = [];
			searching = false;
			searchError = null;
			hasSearched = false;
			return;
		}
		searching = true;
		open = true;
		timer = setTimeout(() => void run(q), 300);
	}

	async function run(q: string) {
		const id = ++requestId;
		searchError = null;
		try {
			const response = await searchPlaces(q);
			if (id !== requestId) return;
			results = response.results;
		} catch (err) {
			if (id !== requestId) return;
			results = [];
			searchError = err instanceof Error ? err.message : $t('map.search_error');
		} finally {
			if (id === requestId) {
				searching = false;
				hasSearched = true;
			}
		}
	}

	async function pick(place: PlaceSearchResult) {
		picked = place;
		query = place.name;
		open = false;
		onSelect?.(place);
		// Details (photos, website, rating) arrive after the card is already usable.
		const enriched = await enrichPlace(place).catch(() => place);
		if (picked === place && enriched !== place) picked = enriched;
	}

	/** Resets the search box and drops the picked place. */
	export function clear() {
		clearTimeout(timer);
		requestId++;
		query = '';
		results = [];
		searching = false;
		searchError = null;
		hasSearched = false;
		open = false;
		picked = null;
		onSelect?.(null);
	}

	async function add() {
		if (!picked || adding) return;
		adding = true;
		try {
			const payload = await resolveQuickAddPayload({
				...placeToQuickAddPayload(picked),
				category: placeCategory.current
			});
			const created = await quickAddLocation(payload, { collectionId: String(collection.id) });
			addToast('success', $t('collection.place_added', { values: { name: created.name } }));
			onAdded?.(created);
			clear();
		} catch (err) {
			addToast('error', err instanceof Error ? err.message : $t('collection.add_failed'));
		} finally {
			adding = false;
		}
	}

	function details() {
		if (!picked) return;
		onDetails?.({
			...placeToLocationPrefill(picked),
			visits: [],
			collections: [collection.id],
			user,
			category: placeCategory.current,
			attachments: [],
			trails: [],
			is_public: false,
			is_visited: false
		} as unknown as Location);
	}

	function onWindowPointerDown(event: PointerEvent) {
		if (open && root && !root.contains(event.target as Node)) open = false;
	}

	function onWindowKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && open) open = false;
	}

	onDestroy(() => clearTimeout(timer));
</script>

<svelte:window onpointerdown={onWindowPointerDown} onkeydown={onWindowKeydown} />

<div bind:this={root} class={['relative w-full', className]} role="search">
	<label class="input input-sm flex w-full items-center gap-2 bg-base-100 shadow-md">
		<Search class="h-4 w-4 shrink-0 opacity-60" />
		<input
			type="text"
			class="grow"
			placeholder={$t('collection.find_place_placeholder')}
			aria-label={$t('collection.find_place')}
			bind:value={query}
			oninput={onInput}
			onfocus={() => {
				if (hasSearched || searching) open = true;
			}}
		/>
		{#if searching}
			<span class="loading loading-spinner loading-xs"></span>
		{/if}
		{#if query}
			<button
				type="button"
				class="btn btn-ghost btn-xs btn-circle"
				aria-label={$t('adventures.clear')}
				onclick={clear}
			>
				<Clear class="h-4 w-4" />
			</button>
		{/if}
	</label>

	{#if showDropdown}
		<ul
			class="menu absolute left-0 right-0 top-full z-[1100] mt-1 max-h-72 w-full flex-nowrap overflow-y-auto rounded-box bg-base-100 p-1 shadow-xl"
		>
			{#if searching && results.length === 0}
				<li class="menu-disabled px-3 py-2 text-sm opacity-70">
					{$t('collection.searching_places')}
				</li>
			{:else if searchError}
				<li class="px-3 py-2 text-sm text-error">{searchError}</li>
			{:else if results.length === 0}
				<li class="menu-disabled px-3 py-2 text-sm opacity-70">
					{$t('collection.no_places_found')}
				</li>
			{:else}
				{#each results as place (place.id)}
					<li>
						<button type="button" class="items-start gap-2 text-left" onclick={() => pick(place)}>
							<MapMarker class="mt-0.5 h-4 w-4 shrink-0 text-primary" />
							<span class="min-w-0">
								<span class="block truncate font-medium">{place.name}</span>
								{#if place.location}
									<span class="block truncate text-xs opacity-60">{place.location}</span>
								{/if}
							</span>
						</button>
					</li>
				{/each}
			{/if}
		</ul>
	{/if}

	{#if picked}
		<div class="card mt-2 border border-base-300 bg-base-100 shadow-xl">
			<div class="card-body gap-3 p-3">
				<div class="flex items-start gap-2">
					<MapMarker class="mt-0.5 h-5 w-5 shrink-0 text-primary" />
					<div class="min-w-0 flex-1">
						<p class="truncate font-semibold leading-tight">{picked.name}</p>
						{#if picked.location}
							<p class="truncate text-xs opacity-60">{picked.location}</p>
						{/if}
					</div>
				</div>

				{#if alreadyAdded}
					<p class="flex items-center gap-1.5 text-xs text-warning">
						<Check class="h-4 w-4" />
						{$t('collection.already_in_collection_hint')}
					</p>
				{/if}

				<div>
					<span class="field-label">{$t('collection.save_to_category')}</span>
					<CategoryDropdown bind:selected_category={placeCategory.current} />
				</div>

				<div class="flex flex-wrap items-center gap-2">
					<button
						type="button"
						class="btn btn-primary btn-sm gap-1"
						disabled={adding}
						onclick={add}
					>
						{#if adding}
							<span class="loading loading-spinner loading-xs"></span>
						{:else}
							<Plus class="h-4 w-4" />
						{/if}
						{$t('adventures.add_to_collection')}
					</button>
					{#if onDetails}
						<button type="button" class="btn btn-ghost btn-sm gap-1" onclick={details}>
							<TextBoxEdit class="h-4 w-4" />
							{$t('collection.add_with_details')}
						</button>
					{/if}
					{#if onSearchNearby}
						<button
							type="button"
							class="btn btn-ghost btn-sm gap-1"
							onclick={() => picked && onSearchNearby(picked)}
						>
							<Compass class="h-4 w-4" />
							{$t('collection.search_nearby_here')}
						</button>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
