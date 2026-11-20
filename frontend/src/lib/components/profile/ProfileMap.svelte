<script lang="ts">
	import { goto } from '$app/navigation';
	import { untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import { Marker } from 'svelte-maplibre';
	import type { ClusterOptions } from 'svelte-maplibre';
	import FullMap from '#lib/components/map/FullMap.svelte';
	import { normalizeBasemapType } from '#lib';
	import type { ProfilePin } from './types.js';

	import MapOff from '~icons/mdi/map-outline';

	interface Props {
		pins: ProfilePin[];
		basemap?: string | null;
		isOwn?: boolean;
		/** Fill the parent (an embed) instead of sitting in a card with a caption. */
		embedded?: boolean;
	}

	let { pins, basemap = null, isOwn = false, embedded = false }: Props = $props();

	// The same clustering and pin look as the main map page.
	const clusterOptions: ClusterOptions = { radius: 300, maxZoom: 8, minPoints: 2 };
	const SOURCE_ID = 'profile-pins';

	// Seeded once from the viewer's preference; the map's own selector changes it after that.
	let basemapType = $state(untrack(() => normalizeBasemapType(basemap)));
	let map = $state<any>(undefined);

	function toFeature(item: unknown) {
		const pin = item as ProfilePin;
		return {
			type: 'Feature' as const,
			geometry: {
				type: 'Point' as const,
				coordinates: [pin.longitude, pin.latitude] as [number, number]
			},
			properties: {
				id: pin.id,
				name: pin.name,
				visitStatus: pin.is_visited ? 'visited' : 'planned',
				categoryIcon: pin.category,
				categoryName: pin.category_name
			}
		};
	}

	function getMarkerProps(feature: unknown) {
		return (feature as { properties?: Record<string, unknown> } | null)?.properties ?? null;
	}

	function getMarkerId(props: Record<string, unknown> | null): string | null {
		return props?.id == null ? null : String(props.id);
	}

	function fill(status: unknown): string {
		return status === 'visited'
			? 'bg-gradient-to-br from-emerald-400 to-emerald-600'
			: 'bg-gradient-to-br from-blue-400 to-blue-600';
	}

	function openLocation(props: Record<string, unknown>) {
		const path = `/locations/${props.id}`;
		// Inside another website the pin opens in a new tab, so the host page stays put.
		if (embedded) window.open(path, '_blank', 'noopener');
		else goto(path);
	}

	/** Fit the view around every pin once the map is ready (and again if the pins change). */
	let fittedKey = '';
	function fitToPins() {
		if (!map || pins.length === 0) return;
		const key = pins.map((p) => p.id).join(',');
		if (key === fittedKey) return;
		fittedKey = key;
		let minLon = 180,
			minLat = 90,
			maxLon = -180,
			maxLat = -90;
		for (const p of pins) {
			minLon = Math.min(minLon, p.longitude);
			maxLon = Math.max(maxLon, p.longitude);
			minLat = Math.min(minLat, p.latitude);
			maxLat = Math.max(maxLat, p.latitude);
		}
		if (maxLon - minLon < 1e-6 && maxLat - minLat < 1e-6) {
			map.jumpTo({ center: [minLon, minLat], zoom: 10 });
		} else {
			map.fitBounds(
				[
					[minLon, minLat],
					[maxLon, maxLat]
				],
				{ padding: 60, maxZoom: 10, duration: 0 }
			);
		}
	}

	$effect(() => {
		fitToPins();
	});
</script>

{#if pins.length === 0}
	<div
		class="flex flex-col items-center gap-3 rounded-box border border-base-300/60 bg-base-100 py-14 text-center"
	>
		<MapOff class="h-10 w-10 text-base-content/30" />
		<p class="max-w-md text-base-content/60">
			{isOwn ? $t('profile.map_empty_own') : $t('profile.map_empty')}
		</p>
	</div>
{:else}
	<div
		class="profile-map overflow-hidden bg-base-100 {embedded
			? 'h-full w-full'
			: 'rounded-box border border-base-300/60 shadow-sm'}"
	>
		<FullMap
			bind:map
			bind:basemapType
			sourceId={SOURCE_ID}
			items={pins}
			{toFeature}
			clusterEnabled={true}
			{clusterOptions}
			{getMarkerProps}
			{getMarkerId}
			mapClass={embedded ? 'h-full w-full' : 'h-[65vh] min-h-[360px] w-full'}
			on:load={fitToPins}
		>
			{#snippet marker({ markerProps, markerLngLat, isActive, setActive })}
				{#if markerProps && markerLngLat}
					<Marker lngLat={markerLngLat} class={isActive ? 'map-pin-active' : 'map-pin'}>
						<div class="group relative z-[1000] focus-within:z-[10000] group-hover:z-[10000]">
							<div
								class="map-pin-hit grid h-8 w-8 cursor-pointer place-items-center rounded-full border-2 border-white text-base text-white shadow-lg transition-all duration-200 group-hover:scale-110 {fill(
									markerProps.visitStatus
								)}"
								class:scale-110={isActive}
								role="button"
								tabindex="0"
								aria-label={String(markerProps.name ?? '')}
								onmouseenter={() => setActive(true)}
								onmouseleave={() => setActive(false)}
								onfocus={() => setActive(true)}
								onblur={() => setActive(false)}
								onclick={(e) => {
									e.stopPropagation();
									openLocation(markerProps);
								}}
								onkeydown={(e) => {
									if (e.key !== 'Enter') return;
									e.stopPropagation();
									openLocation(markerProps);
								}}
							>
								{markerProps.categoryIcon || '📍'}
							</div>

							<div
								class="pointer-events-none absolute bottom-full left-1/2 z-[9999] mb-2 -translate-x-1/2 opacity-0 transition-all duration-200 group-focus-within:opacity-100 group-hover:opacity-100"
								class:opacity-100={isActive}
							>
								<div
									class="card card-sm min-w-48 max-w-72 border border-base-300 bg-base-100 shadow-xl"
								>
									<div class="card-body gap-2 p-3">
										<h3 class="truncate text-sm font-semibold leading-tight">{markerProps.name}</h3>
										<div class="flex flex-wrap items-center gap-1.5">
											<span
												class="badge badge-sm {markerProps.visitStatus === 'visited'
													? 'badge-success'
													: 'badge-info'}"
											>
												{markerProps.visitStatus === 'visited'
													? $t('adventures.visited')
													: $t('adventures.planned')}
											</span>
											{#if markerProps.categoryName}
												<span class="badge badge-ghost badge-sm">{markerProps.categoryName}</span>
											{/if}
										</div>
										<p class="text-xs text-base-content/60">{$t('map.view_details')}</p>
									</div>
								</div>
							</div>
						</div>
					</Marker>
				{/if}
			{/snippet}
		</FullMap>
	</div>
	{#if !embedded}
		<p class="mt-2 text-sm text-base-content/60">
			{$t('profile.pins_count', { values: { count: pins.length } })}
		</p>
	{/if}
{/if}

<style>
	/* The marker wrapper ignores the pointer so the map stays draggable; only the pin itself takes it. */
	.profile-map :global(.maplibregl-marker.map-pin),
	.profile-map :global(.mapboxgl-marker.map-pin) {
		pointer-events: none;
	}

	.profile-map :global(.maplibregl-marker.map-pin .map-pin-hit),
	.profile-map :global(.mapboxgl-marker.map-pin .map-pin-hit) {
		pointer-events: auto;
	}
</style>
