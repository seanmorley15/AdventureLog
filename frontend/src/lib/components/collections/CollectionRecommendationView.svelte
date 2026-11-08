<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import { untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import { Marker } from 'svelte-maplibre';
	import type { Collection, Location, Lodging, Recommendation, User } from '#lib/types.js';
	import FullMap from '#lib/components/map/FullMap.svelte';
	import MapNearbyRadiusLayer from '#lib/components/map/MapNearbyRadiusLayer.svelte';
	import MapRecommendationsLayer from '#lib/components/map/MapRecommendationsLayer.svelte';
	import MapDetailPanel from '#lib/components/map/MapDetailPanel.svelte';
	import RecommendationControls, {
		type Anchor,
		type AnchorOption,
		type SortMode
	} from '#lib/components/recommendations/RecommendationControls.svelte';
	import RecommendationListItem from '#lib/components/recommendations/RecommendationListItem.svelte';
	import type { DayOption } from '#lib/components/recommendations/RecommendationAddButton.svelte';
	import LocationModal from '#lib/components/locations/LocationModal.svelte';
	import LodgingModal from '#lib/components/lodging/LodgingModal.svelte';
	import { normalizeBasemapType } from '#lib';
	import { addToast } from '#lib/toasts.js';
	import { getMapViewportCenter } from '#lib/map/viewportCenter.js';
	import { LocationDuplicateChecker } from '#lib/location-duplicate-checker.svelte.js';
	import { indexedDays, showsDayPlanner } from '#lib/collections/plan.js';
	import {
		fetchRecommendations,
		nearbyRadiusOptions,
		quickAddLocation,
		quickAddLodging,
		recommendationToLocationPrefill,
		recommendationToLodgingPrefill,
		recommendationToQuickAddPayload,
		resolveQuickAddPayload
	} from '#lib/map/places.js';
	import {
		categoryMeta,
		isLodgingRecommendation,
		type RecommendationCategory
	} from '#lib/recommendations/categories.js';
	import { findCollectionMatch } from '#lib/recommendations/match.js';
	import Compass from '~icons/mdi/compass';
	import Lightbulb from '~icons/mdi/lightbulb-outline';
	import ChevronLeft from '~icons/mdi/chevron-left';

	interface Props {
		collection: Collection;
		user: User | null;
	}

	let { collection = $bindable(), user }: Props = $props();

	let category = $state<RecommendationCategory>('attractions');
	let radius = $state<number>(0);
	let sort = $state<SortMode>('best');
	let hideAdded = $state(false);
	let anchor = $state<Anchor>({ kind: 'map' });
	let recommendations = $state<Recommendation[]>([]);
	let warnings = $state<string[]>([]);
	let hasSearched = $state(false);
	let selected = $state<Recommendation | null>(null);
	let highlightedId = $state<string | null>(null);
	let loading = $state(false);
	let busyIds = $state<Set<string>>(new Set());
	let error = $state<string | null>(null);
	let showSearch = $state(false);
	let basemapType = $state('default');
	let map = $state<any>(undefined);
	let mapRoot = $state<HTMLElement | null>(null);
	const captureMapRoot: Attachment = (node) => {
		mapRoot = node;
		return () => {
			if (mapRoot === node) mapRoot = null;
		};
	};
	let locationToEdit = $state<Location | null>(null);
	let lodgingToEdit = $state<Lodging | null>(null);
	let listScroller = $state<HTMLElement | null>(null);
	let savedScroll = 0;
	let requestId = 0;
	const duplicates = new LocationDuplicateChecker();

	const isMetric = $derived(user?.measurement_system !== 'imperial');
	const radiusOptions = $derived(nearbyRadiusOptions(isMetric));
	const radiusMeters = $derived(
		radius ||
			(radiusOptions.find((option) => option.label.startsWith('5'))?.value ??
				radiusOptions[0].value)
	);

	$effect(() => {
		const style = user?.map_style;
		if (!style) return;
		if (untrack(() => basemapType) !== 'default') return;
		basemapType = normalizeBasemapType(style);
	});

	function finitePoint(lat: unknown, lng: unknown): [number, number] | null {
		const latitude = typeof lat === 'number' ? lat : Number(lat);
		const longitude = typeof lng === 'number' ? lng : Number(lng);
		if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
		return [longitude, latitude];
	}

	const collectionPoints = $derived.by(() => {
		const points: { id: string; lngLat: [number, number]; icon: string }[] = [];
		for (const loc of collection.locations ?? []) {
			const lngLat = finitePoint(loc.latitude, loc.longitude);
			if (lngLat)
				points.push({ id: `location-${loc.id}`, lngLat, icon: loc.category?.icon || '📍' });
		}
		for (const stay of collection.lodging ?? []) {
			const lngLat = finitePoint(stay.latitude, stay.longitude);
			if (lngLat) points.push({ id: `lodging-${stay.id}`, lngLat, icon: '🏨' });
		}
		return points;
	});

	const startCenter = $derived.by(() => {
		if (!collectionPoints.length) return { lng: 0, lat: 20 };
		const n = collectionPoints.length;
		return {
			lng: collectionPoints.reduce((sum, point) => sum + point.lngLat[0], 0) / n,
			lat: collectionPoints.reduce((sum, point) => sum + point.lngLat[1], 0) / n
		};
	});

	/** Places in the trip that a search can be centered on. */
	const anchorOptions = $derived.by<AnchorOption[]>(() => {
		const options: AnchorOption[] = [];
		for (const stay of collection.lodging ?? []) {
			const p = finitePoint(stay.latitude, stay.longitude);
			if (p)
				options.push({
					id: `lodging-${stay.id}`,
					label: stay.name,
					group: $t('adventures.lodging'),
					lng: p[0],
					lat: p[1]
				});
		}
		for (const loc of collection.locations ?? []) {
			const p = finitePoint(loc.latitude, loc.longitude);
			if (p)
				options.push({
					id: `location-${loc.id}`,
					label: loc.name,
					group: $t('locations.locations'),
					lng: p[0],
					lat: p[1]
				});
		}
		return options;
	});

	const days = $derived.by<DayOption[]>(() => {
		if (!showsDayPlanner(collection)) return [];
		return indexedDays(collection)
			.filter((day) => day.date)
			.map((day) => ({
				date: day.date as string,
				label: `${day.index} · ${new Date(`${day.date}T00:00:00`).toLocaleDateString(undefined, {
					month: 'short',
					day: 'numeric'
				})}`
			}));
	});

	let viewportCenter = $state<{ lng: number; lat: number } | null>(null);
	let focusCenter = $state<[number, number] | null>(null);
	let focusZoom = $state<number | undefined>(undefined);
	let lastSearchCenter = $state<{ lng: number; lat: number } | null>(null);
	const circleCenter = $derived(
		anchor.kind === 'point' ? { lng: anchor.lng, lat: anchor.lat } : (viewportCenter ?? startCenter)
	);
	const mapCenter = $derived<[number, number]>(focusCenter ?? [startCenter.lng, startCenter.lat]);
	const mapZoom = $derived(focusZoom ?? (collectionPoints.length ? 11 : 2));

	const matches = $derived.by(() => {
		const out = new Map<string, { kind: 'location' | 'lodging'; id: string }>();
		for (const rec of recommendations) {
			const match = findCollectionMatch(rec, collection);
			if (match) out.set(rec.id, match);
		}
		return out;
	});
	const addedIds = $derived(new Set(matches.keys()));

	const visible = $derived.by(() => {
		let list = hideAdded
			? recommendations.filter((rec) => !matches.has(rec.id))
			: [...recommendations];
		if (sort === 'nearest')
			list.sort((a, b) => (a.distance_km ?? Infinity) - (b.distance_km ?? Infinity));
		else if (sort === 'rating')
			list.sort(
				(a, b) =>
					(b.rating ?? -1) - (a.rating ?? -1) || (b.review_count ?? 0) - (a.review_count ?? 0)
			);
		return list;
	});

	function currentSearchCenter(): { lng: number; lat: number } {
		if (anchor.kind === 'point') return { lng: anchor.lng, lat: anchor.lat };
		if (map) return getMapViewportCenter(map, mapRoot);
		return circleCenter;
	}

	async function search() {
		const center = currentSearchCenter();
		if (!Number.isFinite(center.lat) || !Number.isFinite(center.lng)) return;
		const id = ++requestId;
		loading = true;
		error = null;
		showSearch = false;
		lastSearchCenter = center;
		try {
			const data = await fetchRecommendations({
				lat: center.lat,
				lon: center.lng,
				radius: radiusMeters,
				category
			});
			if (id !== requestId) return;
			recommendations = data.results ?? [];
			warnings = data.warnings ?? [];
			if (selected && !recommendations.some((rec) => rec.id === selected?.id)) selected = null;
		} catch (err) {
			if (id !== requestId) return;
			recommendations = [];
			warnings = [];
			selected = null;
			error = err instanceof Error ? err.message : $t('map.recommendations_error');
		} finally {
			if (id === requestId) {
				loading = false;
				hasSearched = true;
			}
		}
	}

	function setAnchor(next: Anchor) {
		anchor = next;
		if (next.kind === 'point') {
			focusCenter = [next.lng, next.lat];
			focusZoom = radiusMeters > 20000 ? 9 : radiusMeters > 5000 ? 11 : 12;
		}
		void search();
	}

	// Changing the category or radius searches again around the current anchor.
	let firstRun = true;
	$effect(() => {
		void category;
		void radiusMeters;
		if (firstRun) {
			firstRun = false;
			return;
		}
		untrack(() => {
			if (hasSearched || anchor.kind === 'point') void search();
		});
	});

	// On open, search around the trip's first stay, or around where the map starts.
	$effect(() => {
		untrack(() => {
			if (hasSearched || loading || !collectionPoints.length) return;
			const stay = (collection.lodging ?? [])
				.map((s) => ({ s, p: finitePoint(s.latitude, s.longitude) }))
				.find((entry) => entry.p);
			if (stay?.p) {
				setAnchor({
					kind: 'point',
					id: `lodging-${stay.s.id}`,
					label: stay.s.name,
					lng: stay.p[0],
					lat: stay.p[1]
				});
			} else {
				void search();
			}
		});
	});

	function rememberMove(event: CustomEvent<{ center: { lng: number; lat: number } }>) {
		const center = map ? getMapViewportCenter(map, mapRoot) : event.detail.center;
		viewportCenter = center;
		if (anchor.kind !== 'map') {
			showSearch = false;
			return;
		}
		const from = lastSearchCenter;
		showSearch =
			!from || Math.abs(from.lng - center.lng) > 0.002 || Math.abs(from.lat - center.lat) > 0.002;
	}

	function selectRecommendation(item: Recommendation) {
		if (!selected) savedScroll = listScroller?.scrollTop ?? 0;
		selected = item;
		focusCenter = [item.longitude, item.latitude];
		focusZoom = 14;
		if (anchor.kind === 'map') lastSearchCenter = { lng: item.longitude, lat: item.latitude };
	}

	function backToList() {
		selected = null;
		queueMicrotask(() => listScroller?.scrollTo({ top: savedScroll }));
	}

	$effect(() => {
		if (!selected) {
			duplicates.reset();
			return;
		}
		duplicates.schedule(
			{
				name: selected.name,
				latitude: selected.latitude,
				longitude: selected.longitude,
				location: selected.address || selected.description || null
			},
			80
		);
	});

	function setBusy(id: string, value: boolean) {
		const next = new Set(busyIds);
		if (value) next.add(id);
		else next.delete(id);
		busyIds = next;
	}

	function upsertLocation(created: Location) {
		if (!(collection.locations ?? []).some((item) => item.id === created.id)) {
			collection.locations = [...(collection.locations ?? []), created];
		}
	}

	function upsertLodging(created: Lodging) {
		if (!(collection.lodging ?? []).some((item) => item.id === created.id)) {
			collection.lodging = [...(collection.lodging ?? []), created];
		}
	}

	async function add(item: Recommendation, opts: { date?: string; lodging?: boolean } = {}) {
		if (busyIds.has(item.id)) return;
		setBusy(item.id, true);
		try {
			const payload = await resolveQuickAddPayload(recommendationToQuickAddPayload(item));
			const options = { collectionId: collection.id, itineraryDate: opts.date ?? null };
			const created = opts.lodging
				? await quickAddLodging(payload, options)
				: await quickAddLocation(payload, options);
			if (opts.lodging) upsertLodging(created as Lodging);
			else upsertLocation(created as Location);
			const placed = created.quick_add_itinerary_item as any;
			if (placed && !(collection.itinerary ?? []).some((entry) => entry.id === placed.id)) {
				collection.itinerary = [...(collection.itinerary ?? []), placed];
			}
			const day = opts.date ? days.find((d) => d.date === opts.date) : null;
			addToast(
				'success',
				day
					? $t('recomendations.added_to_day', { values: { name: item.name, day: day.label } })
					: $t('recomendations.added_to_ideas', { values: { name: item.name } })
			);
		} catch (err) {
			addToast('error', err instanceof Error ? err.message : $t('map.search_error'));
		} finally {
			setBusy(item.id, false);
		}
	}

	function openDetails(item: Recommendation) {
		locationToEdit = {
			...recommendationToLocationPrefill(item),
			visits: [],
			collections: [collection.id],
			user: user ?? null,
			category: null,
			attachments: [],
			trails: [],
			is_public: false,
			is_visited: false
		} as Location;
	}

	function openLodging(item: Recommendation) {
		lodgingToEdit = recommendationToLodgingPrefill(item, user?.uuid, collection.id);
	}

	function keepLocation(event: CustomEvent<Location>) {
		if (!event.detail?.id) return;
		upsertLocation(event.detail);
		locationToEdit = null;
	}

	function keepLodging(event: CustomEvent<Lodging>) {
		if (!event.detail?.id) return;
		upsertLodging(event.detail);
		lodgingToEdit = null;
	}

	const lodgingFirst = $derived(categoryMeta(category).isLodging);
</script>

<div class="relative h-full min-h-0 lg:grid lg:grid-cols-2 lg:gap-4">
	<div
		class="relative h-[42%] overflow-hidden rounded-box lg:col-start-2 lg:row-start-1 lg:h-full lg:min-h-0"
		{@attach captureMapRoot}
	>
		<FullMap
			bind:map
			bind:basemapType
			center={mapCenter}
			zoom={mapZoom}
			mapClass="h-full w-full"
			clusterEnabled={false}
			on:mapMove={rememberMove}
		>
			{#snippet overlays()}
				<MapNearbyRadiusLayer visible center={circleCenter} {radiusMeters} />
				<MapRecommendationsLayer
					recommendations={visible}
					selectedId={selected?.id ?? null}
					{highlightedId}
					{addedIds}
					on:select={(event) => selectRecommendation(event.detail.item)}
				/>
				{#each collectionPoints as point (point.id)}
					<Marker lngLat={point.lngLat}>
						<div
							class="grid h-7 w-7 place-items-center rounded-full border-2 border-white bg-primary text-sm text-primary-content shadow"
						>
							{point.icon}
						</div>
					</Marker>
				{/each}
			{/snippet}
		</FullMap>

		<div class="pointer-events-none absolute bottom-10 left-1/2 z-20 -translate-x-1/2">
			{#if loading}
				<div
					class="flex items-center gap-2 rounded-full border border-base-300/80 bg-base-100/95 px-4 py-2 shadow-lg backdrop-blur-md"
				>
					<span class="loading loading-spinner loading-sm text-primary"></span>
					<span class="text-sm font-medium">{$t('map.searching_nearby')}</span>
				</div>
			{:else if showSearch}
				<button
					type="button"
					class="btn btn-primary btn-sm pointer-events-auto gap-2 shadow-lg"
					onclick={search}
				>
					<Compass class="h-4 w-4" />
					{$t('map.search_this_area')}
				</button>
			{/if}
		</div>
	</div>

	<div
		bind:this={listScroller}
		class="planner-pane absolute inset-x-0 bottom-0 top-[34%] z-10 overflow-x-hidden overflow-y-auto overscroll-contain rounded-t-3xl bg-base-100 px-2 pb-8 shadow-2xl lg:static lg:z-auto lg:col-start-1 lg:row-start-1 lg:h-full lg:min-h-0 lg:overflow-y-auto lg:rounded-none lg:bg-transparent lg:px-0 lg:pb-2 lg:shadow-none"
	>
		<div class="mx-auto mb-3 mt-2 h-1.5 w-12 rounded-full bg-base-300 lg:hidden"></div>

		{#if selected}
			<section class="card bg-base-200 shadow-xl">
				<div class="card-body gap-3 p-4 sm:p-5">
					<button type="button" class="btn btn-ghost btn-sm w-fit gap-1 px-2" onclick={backToList}>
						<ChevronLeft class="h-4 w-4" />
						{$t('recomendations.back_to_results')}
					</button>
					<MapDetailPanel
						embedded
						selectionKind="recommendation"
						recommendation={selected}
						{isMetric}
						isQuickAdding={busyIds.has(selected.id)}
						showLodgingAdd={isLodgingRecommendation(selected)}
						duplicateMatches={duplicates.matches}
						isCheckingDuplicates={duplicates.checking}
						showDuplicatePrompt={duplicates.visible}
						on:quickAdd={() => selected && add(selected, { lodging: lodgingFirst })}
						on:addDetails={() => selected && openDetails(selected)}
						on:addLodging={() => selected && openLodging(selected)}
					/>
				</div>
			</section>
		{:else}
			<div class="space-y-4">
				<section class="card bg-base-200 shadow-xl">
					<div class="card-body gap-3 p-4 sm:p-5">
						<RecommendationControls
							bind:category
							bind:radius={() => radiusMeters, (value) => (radius = value)}
							bind:sort
							bind:hideAdded
							{radiusOptions}
							{anchor}
							{anchorOptions}
							onAnchor={setAnchor}
						/>
					</div>
				</section>

				<section class="card bg-base-200 shadow-xl">
					<div class="card-body gap-3 p-4 sm:p-5">
						<div class="flex items-center gap-3">
							<Lightbulb class="h-5 w-5 shrink-0 text-warning" />
							<h3 class="min-w-0 flex-1 text-lg font-bold">
								{$t('map.recommendations_count', { values: { count: visible.length } })}
							</h3>
							{#if hasSearched}
								<span class="badge badge-ghost badge-sm font-medium">{recommendations.length}</span>
							{/if}
						</div>

						{#if error}
							<div class="alert alert-warning alert-soft py-2 text-sm">{error}</div>
						{/if}
						{#each warnings as warning (warning)}
							<div class="alert alert-info alert-soft py-2 text-sm">{warning}</div>
						{/each}

						{#if loading && !recommendations.length}
							{#each [0, 1, 2, 3] as n (n)}
								<div class="skeleton h-[4.5rem] w-full rounded-xl"></div>
							{/each}
						{:else if visible.length}
							<div class="space-y-2 {loading ? 'opacity-60' : ''}">
								{#each visible as item (item.id)}
									<RecommendationListItem
										{item}
										{isMetric}
										{days}
										selected={false}
										inTrip={matches.has(item.id)}
										busy={busyIds.has(item.id)}
										canAddLodging={isLodgingRecommendation(item)}
										lodgingDefault={lodgingFirst && isLodgingRecommendation(item)}
										onSelect={() => selectRecommendation(item)}
										onHover={(hovering) => (highlightedId = hovering ? item.id : null)}
										onAdd={() =>
											add(item, { lodging: lodgingFirst && isLodgingRecommendation(item) })}
										onAddToDay={(date) =>
											add(item, { date, lodging: lodgingFirst && isLodgingRecommendation(item) })}
										onAddDetails={() => openDetails(item)}
										onAddLodging={() => openLodging(item)}
									/>
								{/each}
							</div>
						{:else if !error}
							<div
								class="flex min-h-14 items-center justify-center rounded-xl border border-dashed border-base-300 bg-base-100/40 px-3 py-6 text-center text-sm text-base-content/60"
							>
								{hasSearched
									? $t('map.recommendations_empty')
									: $t('recomendations.pick_anchor_hint')}
							</div>
						{/if}
					</div>
				</section>
			</div>
		{/if}
	</div>
</div>

{#if locationToEdit}
	<LocationModal
		{user}
		{collection}
		{locationToEdit}
		skipQuickStart
		on:create={keepLocation}
		on:save={keepLocation}
		on:close={() => (locationToEdit = null)}
	/>
{/if}

{#if lodgingToEdit}
	<LodgingModal
		{user}
		{collection}
		{lodgingToEdit}
		on:create={keepLodging}
		on:save={keepLodging}
		on:close={() => (lodgingToEdit = null)}
	/>
{/if}

<style>
	.planner-pane {
		scrollbar-width: none;
	}
	.planner-pane::-webkit-scrollbar {
		display: none;
	}
</style>
