<script lang="ts">
	import { run } from 'svelte/legacy';

	import { createEventDispatcher, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { CircleLayer, GeoJSON, Marker, MarkerLayer } from 'svelte-maplibre';
	import type { ClusterOptions, LayerClickInfo } from 'svelte-maplibre';
	import { resolveThemeColor, withAlpha } from '$lib/utils/resolveThemeColor';
	import ImageMapPinPopup from './ImageMapPinPopup.svelte';
	import type { ImagePinFeatureCollection, ImagePinProperties } from '$lib/map/imagePins';
	import { getImagePinNavigationUrl } from '$lib/map/imagePins';

	
	interface Props {
		geoJson?: ImagePinFeatureCollection;
		visible?: boolean;
		clusterEnabled?: boolean;
		clusterOptions?: ClusterOptions;
		sourceId?: string;
		/** When true (default), tap navigates to the parent entity. When false, dispatches `select` instead. */
		navigateOnSelect?: boolean;
		selectedId?: string | null;
	}

	let {
		geoJson = { type: 'FeatureCollection', features: [] },
		visible = true,
		clusterEnabled = true,
		clusterOptions = { radius: 280, maxZoom: 10, minPoints: 2 },
		sourceId = 'image-pins',
		navigateOnSelect = true,
		selectedId = null
	}: Props = $props();

	const dispatch = createEventDispatcher<{
		select: { props: ImagePinProperties };
	}>();

	let hoveredMarkerId: string | null = null;

	let rose400 = $state('#fb7185');
	let rose500 = $state('#f43f5e');
	let rose600 = $state('#e11d48');
	let baseContent = $state('#111827');

	onMount(() => {
		rose400 = resolveThemeColor('--color-error', rose400);
		rose500 = resolveThemeColor('--color-error', rose500);
		rose600 = resolveThemeColor('--color-error', rose600);
		baseContent = resolveThemeColor('--color-base-content', baseContent);
	});

	let clusterCirclePaint: Record<string, unknown> = $state({});

	run(() => {
		clusterCirclePaint = {
			'circle-color': [
				'step',
				['get', 'point_count'],
				withAlpha(rose400, 0.78),
				25,
				withAlpha(rose500, 0.84),
				80,
				withAlpha(rose600, 0.9)
			],
			'circle-radius': ['step', ['get', 'point_count'], 22, 20, 32, 60, 44],
			'circle-opacity': 1,
			'circle-stroke-color': withAlpha(baseContent, 0.22),
			'circle-stroke-width': 2,
			'circle-blur': 0
		};
	});

	function getPointCoordinates(feature: unknown): [number, number] | null {
		if (!feature || typeof feature !== 'object') return null;
		const geometry = (feature as { geometry?: { type?: string; coordinates?: unknown[] } })
			.geometry;
		if (!geometry || geometry.type !== 'Point' || !Array.isArray(geometry.coordinates)) return null;
		const lon = Number(geometry.coordinates[0]);
		const lat = Number(geometry.coordinates[1]);
		if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
		return [lon, lat];
	}

	function getMarkerProps(feature: unknown): ImagePinProperties | null {
		if (!feature || typeof feature !== 'object' || !('properties' in feature)) return null;
		return (feature as { properties: ImagePinProperties }).properties ?? null;
	}

	function getMarkerId(props: ImagePinProperties | null): string | null {
		return props?.imageId ?? null;
	}

	function setMarkerHovered(props: ImagePinProperties | null, hovered: boolean) {
		const markerId = getMarkerId(props);
		if (!markerId) return;
		hoveredMarkerId = hovered ? markerId : hoveredMarkerId === markerId ? null : hoveredMarkerId;
	}

	function isMarkerRaised(markerId: string | null): boolean {
		if (!markerId) return false;
		return selectedId === markerId || hoveredMarkerId === markerId;
	}

	function canNavigate(props: ImagePinProperties | null): boolean {
		return Boolean(props && getImagePinNavigationUrl(props));
	}

	function openImagePin(props: ImagePinProperties | null) {
		if (!props) return;
		const href = getImagePinNavigationUrl(props);
		if (href) goto(href);
	}

	function handleMarkerClick(event: MouseEvent, props: ImagePinProperties | null) {
		event.stopPropagation();
		if (!props) return;
		if (navigateOnSelect) {
			openImagePin(props);
			return;
		}
		dispatch('select', { props });
	}

	function handleMarkerKeydown(event: KeyboardEvent, props: ImagePinProperties | null) {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		if (!props) return;
		event.preventDefault();
		event.stopPropagation();
		if (navigateOnSelect) {
			if (!canNavigate(props)) return;
			openImagePin(props);
			return;
		}
		dispatch('select', { props });
	}

	function getClusterCount(feature: unknown): number | string | null | undefined {
		if (!feature || typeof feature !== 'object' || !('properties' in feature)) return null;
		const props = (feature as { properties?: Record<string, unknown> }).properties;
		if (!props) return null;
		const abbreviated = props['point_count_abbreviated'];
		const count = props['point_count'];
		return (abbreviated ?? count) as number | string | null | undefined;
	}

	type ClusterSource = {
		getClusterExpansionZoom: (
			clusterId: number,
			callback: (error: unknown, zoom: number) => void
		) => void;
	};

	function handleClusterClick(event: CustomEvent<LayerClickInfo>) {
		const { clusterId, features, map, source } = event.detail ?? ({} as LayerClickInfo);
		if (!clusterId || !features?.length || !map || !source) return;

		const center = getPointCoordinates(features[0]);
		if (!center) return;

		const geoJsonSource = map.getSource(source) as ClusterSource | undefined;
		if (!geoJsonSource?.getClusterExpansionZoom) return;

		geoJsonSource.getClusterExpansionZoom(Number(clusterId), (error, zoomLevel) => {
			if (error) {
				console.error('Failed to expand image pin cluster', error);
				return;
			}
			map.easeTo({ center, zoom: zoomLevel });
		});
	}
</script>

{#if visible && geoJson.features.length > 0}
	{#if clusterEnabled}
		<GeoJSON id={sourceId} data={geoJson} cluster={clusterOptions} generateId>
			<CircleLayer
				id={`${sourceId}-clusters`}
				applyToClusters
				hoverCursor="pointer"
				paint={clusterCirclePaint}
				on:click={handleClusterClick}
			/>
			<MarkerLayer applyToClusters >
				{#snippet children({ feature: clusterFeature }: { feature: unknown })}
								{@const count = getClusterCount(clusterFeature)}
					{#if count !== undefined && count !== null}
						<div
							class="pointer-events-none grid h-8 w-8 place-items-center select-none font-sans text-xs font-bold text-white drop-shadow-sm"
						>
							{count}
						</div>
					{/if}
											{/snippet}
						</MarkerLayer>
			<MarkerLayer applyToClusters={false} >
				{#snippet children({ feature: featureData }: { feature: unknown })}
								{@const markerProps = getMarkerProps(featureData)}
					{@const markerLngLat = getPointCoordinates(featureData)}
					{@const markerId = getMarkerId(markerProps)}
					{@const isRaised = isMarkerRaised(markerId)}
					{#if markerProps && markerLngLat}
						<Marker
							lngLat={markerLngLat}
							class={isRaised ? 'map-pin-active' : 'map-image-pin-marker'}
						>
							<div class="relative group z-[1000] group-hover:z-[10000] focus-within:z-[10000]">
								<div
									class="map-image-pin map-pin-hit grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-gradient-to-br from-rose-400 to-rose-600 text-sm shadow-lg transition-all duration-200 group-hover:scale-110"
									class:scale-110={isRaised}
									class:cursor-pointer={navigateOnSelect ? canNavigate(markerProps) : true}
									class:cursor-default={navigateOnSelect && !canNavigate(markerProps)}
									role="button"
									tabindex="0"
									aria-label={markerProps.parentName || markerProps.imageId}
									aria-pressed={selectedId === markerId}
									onmouseenter={() => setMarkerHovered(markerProps, true)}
									onmouseleave={() => setMarkerHovered(markerProps, false)}
									onfocus={() => setMarkerHovered(markerProps, true)}
									onblur={() => setMarkerHovered(markerProps, false)}
									onclick={(event) => handleMarkerClick(event, markerProps)}
									onkeydown={(event) => handleMarkerKeydown(event, markerProps)}
								>
									<span aria-hidden="true">📷</span>
								</div>

								<ImageMapPinPopup props={markerProps} visible={isRaised} />
							</div>
						</Marker>
					{/if}
											{/snippet}
						</MarkerLayer>
		</GeoJSON>
	{:else}
		<GeoJSON id={sourceId} data={geoJson} generateId>
			<MarkerLayer applyToClusters={false} >
				{#snippet children({ feature: featureData }: { feature: unknown })}
								{@const markerProps = getMarkerProps(featureData)}
					{@const markerLngLat = getPointCoordinates(featureData)}
					{@const markerId = getMarkerId(markerProps)}
					{@const isRaised = isMarkerRaised(markerId)}
					{#if markerProps && markerLngLat}
						<Marker
							lngLat={markerLngLat}
							class={isRaised ? 'map-pin-active' : 'map-image-pin-marker'}
						>
							<div class="relative group z-[1000] group-hover:z-[10000] focus-within:z-[10000]">
								<div
									class="map-image-pin map-pin-hit grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-gradient-to-br from-rose-400 to-rose-600 text-sm shadow-lg transition-all duration-200 group-hover:scale-110"
									class:scale-110={isRaised}
									class:cursor-pointer={navigateOnSelect ? canNavigate(markerProps) : true}
									class:cursor-default={navigateOnSelect && !canNavigate(markerProps)}
									role="button"
									tabindex="0"
									aria-label={markerProps.parentName || markerProps.imageId}
									aria-pressed={selectedId === markerId}
									onmouseenter={() => setMarkerHovered(markerProps, true)}
									onmouseleave={() => setMarkerHovered(markerProps, false)}
									onfocus={() => setMarkerHovered(markerProps, true)}
									onblur={() => setMarkerHovered(markerProps, false)}
									onclick={(event) => handleMarkerClick(event, markerProps)}
									onkeydown={(event) => handleMarkerKeydown(event, markerProps)}
								>
									<span aria-hidden="true">📷</span>
								</div>

								<ImageMapPinPopup props={markerProps} visible={isRaised} />
							</div>
						</Marker>
					{/if}
											{/snippet}
						</MarkerLayer>
		</GeoJSON>
	{/if}
{/if}

<style>
	:global(.map-image-pin-marker) {
		z-index: 4;
	}

	:global(.maplibregl-marker.map-pin-active.map-image-pin-marker) {
		z-index: 2147483000 !important;
	}
</style>
