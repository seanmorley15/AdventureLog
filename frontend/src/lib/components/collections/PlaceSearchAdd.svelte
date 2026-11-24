<script lang="ts">
	import { onDestroy } from 'svelte';
	import { t } from 'svelte-i18n';
	import type {
		Collection,
		CollectionItineraryItem,
		Location,
		PlaceSearchResult,
		User
	} from '#lib/types.js';
	import CategoryDropdown from '#lib/components/CategoryDropdown.svelte';
	import { placeCategory } from '#lib/collections/place-category.svelte.js';
	import {
		enrichPlace,
		placeToLocationPrefill,
		placeToQuickAddPayload,
		quickAddLocation,
		resolveQuickAddPayload,
		placePhotoThumbnail,
		searchPlaces
	} from '#lib/map/places.js';
	import { renderMarkdown } from '#lib/markdown.js';
	import { errorMessage, indexedDays, planRequest } from '#lib/collections/plan.js';
	import { findCollectionMatch } from '#lib/recommendations/match.js';
	import { addToast } from '#lib/toasts.js';

	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Plus from '~icons/mdi/plus';
	import MapMarker from '~icons/mdi/map-marker';
	import Compass from '~icons/mdi/compass-outline';
	import Check from '~icons/mdi/check';
	import Star from '~icons/mdi/star';
	import OpenInNew from '~icons/mdi/open-in-new';
	import TextBoxEdit from '~icons/mdi/text-box-edit-outline';

	interface Props {
		collection: Collection;
		user?: User | null;
		/** A place was picked (or the pick was cleared with `null`), so the parent can show it on its map. */
		onSelect?: (place: PlaceSearchResult | null) => void;
		/** The place was quick-added to the collection. */
		onAdded?: (location: Location, item?: CollectionItineraryItem) => void;
		/** Offer a day picker so the place lands on a day of the plan. */
		dayPicker?: boolean;
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
		dayPicker = false,
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
	let descExpanded = $state(false);
	const DESC_LIMIT = 220;
	let dayIndex = $state<number | ''>('');
	const days = $derived(indexedDays(collection));
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
		descExpanded = false;
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
			let item: CollectionItineraryItem | undefined;
			if (dayPicker && dayIndex !== '') {
				const res = await planRequest<CollectionItineraryItem>(
					`/api/collections/${collection.id}/itinerary-items/`,
					'POST',
					{
						content_type: 'location',
						object_id: created.id,
						day_index: dayIndex,
						is_global: false
					}
				);
				if (res.ok) item = res.data;
				else addToast('error', errorMessage(res.data, $t('itinerary.save_failed')));
			}
			addToast('success', $t('collection.place_added', { values: { name: created.name } }));
			onAdded?.(created, item);
			dayIndex = '';
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

<div
	bind:this={root}
	class={['relative flex max-h-full min-h-0 w-full flex-col', className]}
	role="search"
>
	<label class="input input-sm flex w-full shrink-0 items-center gap-2 bg-base-100 shadow-md">
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
		<div
			class="card mt-2 min-h-0 flex-1 overflow-y-auto overscroll-contain border border-base-300 bg-base-100 shadow-xl"
		>
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

				{#if picked.photos?.length}
					<div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1">
						{#each picked.photos.slice(0, 6) as photo (photo)}
							<img
								src={placePhotoThumbnail(photo, 320)}
								alt=""
								loading="lazy"
								class="h-24 w-32 shrink-0 rounded-lg object-cover"
							/>
						{/each}
					</div>
				{/if}

				{#if picked.rating != null || picked.website}
					<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
						{#if picked.rating != null}
							<span class="inline-flex items-center gap-0.5 font-medium text-warning">
								<Star class="h-3.5 w-3.5" />{picked.rating.toFixed(1)}
								{#if picked.review_count}
									<span class="font-normal opacity-60">({picked.review_count})</span>
								{/if}
							</span>
						{/if}
						{#if picked.website}
							<a
								href={picked.website}
								target="_blank"
								rel="noopener noreferrer"
								class="link inline-flex items-center gap-1"
							>
								<OpenInNew class="h-3.5 w-3.5" />
								{$t('map.visit_website')}
							</a>
						{/if}
					</div>
				{/if}

				{#if picked.description}
					{@const long = picked.description.length > DESC_LIMIT}
					<div class="text-xs">
						<div
							class="prose prose-sm max-w-none text-xs opacity-80 [&_h1]:text-sm [&_h2]:text-sm [&_h3]:text-xs [&_h3]:font-semibold {long &&
							!descExpanded
								? 'max-h-20 overflow-hidden [mask-image:linear-gradient(to_bottom,black_55%,transparent)]'
								: ''}"
						>
							{@html renderMarkdown(picked.description)}
						</div>
						{#if long}
							<button
								type="button"
								class="link link-primary mt-1"
								onclick={() => (descExpanded = !descExpanded)}
							>
								{descExpanded ? $t('map.show_less') : $t('map.show_more')}
							</button>
						{/if}
					</div>
				{/if}

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

				{#if dayPicker && days.length > 0}
					<div>
						<span class="field-label">{$t('itinerary.add_to_day_label')}</span>
						<select class="select select-sm select-bordered w-full" bind:value={dayIndex}>
							<option value="">{$t('itinerary.ideas')}</option>
							{#each days as day (day.id)}
								<option value={day.index}>
									{$t('itinerary.day_n', { values: { n: day.index } })}
								</option>
							{/each}
						</select>
					</div>
				{/if}

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
