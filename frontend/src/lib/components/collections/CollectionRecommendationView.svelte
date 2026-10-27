<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import { untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import { Marker } from 'svelte-maplibre';
	import type { Collection, Location, Lodging, Recommendation, User } from '#lib/types.js';
	import FullMap from '#lib/components/map/FullMap.svelte';
	import MapNearbyRadiusLayer from '#lib/components/map/MapNearbyRadiusLayer.svelte';
	import MapRecommendationsLayer from '#lib/components/map/MapRecommendationsLayer.svelte';
	import RecommendationDetailsModal from '#lib/components/collections/RecommendationDetailsModal.svelte';
	import LocationModal from '#lib/components/locations/LocationModal.svelte';
	import LodgingModal from '#lib/components/lodging/LodgingModal.svelte';
	import { normalizeBasemapType } from '#lib';
	import { googleContentImage } from '#lib/images.js';
	import { addToast } from '#lib/toasts.js';
	import { getMapViewportCenter } from '#lib/map/viewportCenter.js';
	import {
		fetchRecommendations,
		nearbyRadiusOptions,
		quickAddLocation,
		recommendationToLocationPrefill,
		recommendationToQuickAddPayload,
		resolveQuickAddPayload
	} from '#lib/map/places.js';
	import Compass from '~icons/mdi/compass';
	import Lightbulb from '~icons/mdi/lightbulb-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import Bed from '~icons/mdi/bed';

	interface Props {
		collection: Collection;
		user: User | null;
	}

	let { collection = $bindable(), user }: Props = $props();

	type Category = 'tourism' | 'food' | 'lodging';

	let category = $state<Category>('tourism');
	let radius = $state<number | null>(null);
	let recommendations = $state<Recommendation[]>([]);
	let selected = $state<Recommendation | null>(null);
	let detailsOpen = $state(false);
	let loading = $state(false);
	let isQuickAdding = $state(false);
	let error = $state<string | null>(null);
	let showSearch = $state(true);
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

	const isMetric = $derived(user?.measurement_system !== 'imperial');
	const radiusOptions = $derived(nearbyRadiusOptions(isMetric));
	const radiusMeters = $derived(
		radius ??
			radiusOptions.find((option) => option.label.startsWith('5'))?.value ??
			radiusOptions[0].value
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
		const lng =
			collectionPoints.reduce((sum, point) => sum + point.lngLat[0], 0) / collectionPoints.length;
		const lat =
			collectionPoints.reduce((sum, point) => sum + point.lngLat[1], 0) / collectionPoints.length;
		return { lng, lat };
	});

	let viewportCenter = $state<{ lng: number; lat: number } | null>(null);
	let focusCenter = $state<[number, number] | null>(null);
	let focusZoom = $state<number | undefined>(undefined);
	const circleCenter = $derived(viewportCenter ?? startCenter);
	const mapCenter = $derived(focusCenter ?? [startCenter.lng, startCenter.lat]);
	const mapZoom = $derived(focusZoom ?? (collectionPoints.length ? 11 : 2));

	function currentSearchCenter() {
		if (map) return getMapViewportCenter(map, mapRoot);
		return circleCenter;
	}

	async function searchThisArea() {
		const center = currentSearchCenter();
		if (!Number.isFinite(center.lat) || !Number.isFinite(center.lng)) return;
		loading = true;
		error = null;
		showSearch = false;
		try {
			const data = await fetchRecommendations({
				lat: center.lat,
				lon: center.lng,
				radius: radiusMeters,
				category
			});
			recommendations = data.results ?? [];
			selected = null;
			detailsOpen = false;
			if (!recommendations.length) error = $t('map.recommendations_empty');
		} catch (err) {
			recommendations = [];
			selected = null;
			detailsOpen = false;
			error = err instanceof Error ? err.message : $t('map.recommendations_error');
		} finally {
			loading = false;
		}
	}

	function closeDetails() {
		detailsOpen = false;
	}

	function selectRecommendation(item: Recommendation) {
		selected = item;
		detailsOpen = true;
		focusCenter = [item.longitude, item.latitude];
		focusZoom = 14;
	}

	function rememberMove(event: CustomEvent<{ center: { lng: number; lat: number } }>) {
		const center = map ? getMapViewportCenter(map, mapRoot) : event.detail.center;
		viewportCenter = center;
		const anchor = focusCenter;
		if (!anchor) {
			showSearch = true;
			return;
		}
		showSearch =
			Math.abs(anchor[0] - center.lng) > 0.002 || Math.abs(anchor[1] - center.lat) > 0.002;
	}

	function openDetails(item: Recommendation | null = selected) {
		if (!item) return;
		selected = item;
		detailsOpen = false;
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

	function openLodging(item: Recommendation | null = selected) {
		if (!item) return;
		selected = item;
		detailsOpen = false;
		const rec = item;
		lodgingToEdit = {
			id: '',
			user: user?.uuid ?? '',
			name: rec.name,
			type: '',
			description: rec.description,
			rating: rec.rating,
			link: rec.website || rec.google_maps_url || null,
			check_in: null,
			check_out: null,
			timezone: null,
			reservation_number: null,
			price: null,
			price_currency: null,
			latitude: rec.latitude,
			longitude: rec.longitude,
			location: rec.address || rec.description || null,
			is_public: false,
			collection: collection.id,
			created_at: '',
			updated_at: '',
			images: (rec.photos || []).map((url, i) => googleContentImage(`rec-${i}`, url, i === 0)),
			attachments: []
		} as Lodging;
	}

	async function quickAdd(item: Recommendation | null = selected) {
		if (!item || isQuickAdding) return;
		selected = item;
		isQuickAdding = true;
		try {
			const payload = await resolveQuickAddPayload(recommendationToQuickAddPayload(item));
			const created = await quickAddLocation(payload, collection.id);
			const exists = (collection.locations ?? []).some((item) => item.id === created.id);
			if (!exists) {
				collection.locations = [...(collection.locations ?? []), created];
			}
			addToast('success', $t('map.quick_add'));
			detailsOpen = false;
		} catch (err) {
			addToast('error', err instanceof Error ? err.message : $t('map.search_error'));
		} finally {
			isQuickAdding = false;
		}
	}

	function keepLocation(event: CustomEvent<Location>) {
		const created = event.detail;
		if (!created?.id) return;
		const exists = (collection.locations ?? []).some((item) => item.id === created.id);
		if (!exists) collection.locations = [...(collection.locations ?? []), created];
		locationToEdit = null;
	}

	function chip(active: boolean) {
		return active
			? 'btn btn-xs h-7 min-h-7 btn-primary gap-1 px-2.5 font-normal'
			: 'btn btn-xs h-7 min-h-7 btn-ghost gap-1 border border-base-300/80 px-2.5 font-normal opacity-70';
	}

	function keepLodging(event: CustomEvent<Lodging>) {
		const created = event.detail;
		if (!created?.id) return;
		const exists = (collection.lodging ?? []).some((item) => item.id === created.id);
		if (!exists) collection.lodging = [...(collection.lodging ?? []), created];
		lodgingToEdit = null;
	}
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
					{recommendations}
					selectedId={selected?.id ?? null}
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
					onclick={searchThisArea}
				>
					<Compass class="h-4 w-4" />
					{$t('map.search_this_area')}
				</button>
			{/if}
		</div>
	</div>

	<div
		class="planner-pane absolute inset-x-0 bottom-0 top-[34%] z-10 overflow-x-hidden overflow-y-auto overscroll-contain rounded-t-3xl bg-base-100 px-2 pb-8 shadow-2xl lg:static lg:z-auto lg:col-start-1 lg:row-start-1 lg:h-full lg:min-h-0 lg:overflow-y-auto lg:rounded-none lg:bg-transparent lg:px-0 lg:pb-2 lg:shadow-none"
	>
		<div class="mx-auto mb-3 mt-2 h-1.5 w-12 rounded-full bg-base-300 lg:hidden"></div>
		<div class="space-y-4">
			<section class="card bg-base-200 shadow-xl">
				<div class="card-body gap-3 p-4 sm:p-5">
					<div class="flex items-center gap-3">
						<Compass class="h-5 w-5 shrink-0 text-primary" />
						<div class="min-w-0 flex-1">
							<h3 class="text-lg font-bold">{$t('recomendations.recommendations')}</h3>
							<p class="text-sm opacity-70">{$t('map.search_this_area')}</p>
						</div>
					</div>

					<div class="space-y-1.5">
						<p class="text-[11px] font-semibold uppercase tracking-wide text-base-content/50">
							{$t('map.recommendation_category')}
						</p>
						<div class="flex flex-wrap gap-1.5">
							<button
								type="button"
								class={chip(category === 'tourism')}
								onclick={() => (category = 'tourism')}
							>
								🏛️ {$t('recomendations.tourism')}
							</button>
							<button
								type="button"
								class={chip(category === 'food')}
								onclick={() => (category = 'food')}
							>
								🍴 {$t('recomendations.food')}
							</button>
							<button
								type="button"
								class={chip(category === 'lodging')}
								onclick={() => (category = 'lodging')}
							>
								🏨 {$t('recomendations.lodging')}
							</button>
						</div>
					</div>

					<div class="space-y-1.5">
						<p class="text-[11px] font-semibold uppercase tracking-wide text-base-content/50">
							{$t('map.recommendation_radius')}
						</p>
						<div class="flex flex-wrap gap-1.5">
							{#each radiusOptions as option (option.value)}
								<button
									type="button"
									class={chip(radiusMeters === option.value)}
									onclick={() => (radius = option.value)}
								>
									{option.label}
								</button>
							{/each}
						</div>
					</div>

					{#if error}
						<div class="alert alert-warning py-2 text-sm">{error}</div>
					{/if}
				</div>
			</section>

			{#if recommendations.length}
				<section class="card bg-base-200 shadow-xl">
					<div class="card-body gap-3 p-4 sm:p-5">
						<div class="flex items-center gap-3">
							<Lightbulb class="h-5 w-5 shrink-0 text-warning" />
							<div class="min-w-0 flex-1">
								<h3 class="text-lg font-bold">
									{$t('map.recommendations_count', { values: { count: recommendations.length } })}
								</h3>
							</div>
						</div>

						<div class="space-y-2">
							{#each recommendations as item (item.id)}
								<div
									id={`rec-${item.id}`}
									class={[
										'rounded-xl bg-base-100 p-3',
										selected?.id === item.id && 'ring-2 ring-primary'
									]}
								>
									<button
										type="button"
										class="flex w-full items-start gap-3 text-left"
										onclick={() => selectRecommendation(item)}
									>
										{#if item.photos?.[0]}
											<img
												src={item.photos[0]}
												alt=""
												class="h-16 w-16 shrink-0 rounded-lg object-cover"
											/>
										{:else}
											<div
												class="grid h-16 w-16 shrink-0 place-items-center rounded-lg bg-base-200 text-base-content/40"
											>
												<MapMarker class="h-6 w-6" />
											</div>
										{/if}
										<div class="min-w-0 flex-1">
											<p class="truncate font-semibold">{item.name}</p>
											{#if item.address || item.primary_type}
												<p class="truncate text-sm opacity-70">
													{item.address || item.primary_type}
												</p>
											{/if}
											<p class="mt-1 text-xs font-medium text-primary">{$t('map.view_details')}</p>
										</div>
										{#if item.rating != null}
											<span class="badge badge-warning badge-sm shrink-0"
												>{item.rating.toFixed(1)}</span
											>
										{/if}
									</button>
									<div class="mt-2 flex flex-wrap gap-1.5">
										<button
											type="button"
											class="btn btn-xs btn-primary gap-1"
											disabled={isQuickAdding}
											onclick={() => quickAdd(item)}
										>
											<MapMarker class="h-3.5 w-3.5" />
											{$t('recomendations.add_location')}
										</button>
										<button
											type="button"
											class="btn btn-xs btn-ghost gap-1 border border-base-300/80"
											onclick={() => openLodging(item)}
										>
											<Bed class="h-3.5 w-3.5" />
											{$t('recomendations.add_lodging')}
										</button>
									</div>
								</div>
							{/each}
						</div>
					</div>
				</section>
			{/if}
		</div>
	</div>
</div>

{#if detailsOpen && selected}
	{#key selected.id}
		<RecommendationDetailsModal
			recommendation={selected}
			{isMetric}
			{isQuickAdding}
			onClose={closeDetails}
			onQuickAdd={() => quickAdd()}
			onAddDetails={() => openDetails()}
			onAddLodging={() => openLodging()}
		/>
	{/key}
{/if}

{#if locationToEdit}
	<LocationModal
		{user}
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
