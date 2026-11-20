<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Recommendation } from '#lib/types.js';
	import { categoryMeta, type RecommendationCategory } from '#lib/recommendations/categories.js';
	import { placePhotoThumbnail } from '#lib/map/places.js';
	import RecommendationAddButton, { type DayOption } from './RecommendationAddButton.svelte';
	import Star from '~icons/mdi/star';
	import Check from '~icons/mdi/check-circle';

	interface Props {
		item: Recommendation;
		selected?: boolean;
		inTrip?: boolean;
		busy?: boolean;
		isMetric?: boolean;
		days?: DayOption[];
		canAddLodging?: boolean;
		lodgingDefault?: boolean;
		onSelect: () => void;
		onHover?: (hovering: boolean) => void;
		onAdd: () => void;
		onAddToDay: (date: string) => void;
		onAddDetails: () => void;
		onAddLodging: () => void;
	}

	let {
		item,
		selected = false,
		inTrip = false,
		busy = false,
		isMetric = true,
		days = [],
		canAddLodging = false,
		lodgingDefault = false,
		onSelect,
		onHover,
		onAdd,
		onAddToDay,
		onAddDetails,
		onAddLodging
	}: Props = $props();

	const emoji = $derived(categoryMeta(item.category as RecommendationCategory).emoji);

	function distance(km: number): string {
		if (isMetric)
			return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(km < 10 ? 1 : 0)} km`;
		const mi = km * 0.621371;
		return mi < 0.1 ? `${Math.round(km * 3280.84)} ft` : `${mi.toFixed(mi < 10 ? 1 : 0)} mi`;
	}

	function typeLabel(type: string | null): string {
		return (type ?? '').replace(/_/g, ' ');
	}
</script>

<div
	id={`rec-${item.id}`}
	role="presentation"
	class={[
		'rounded-xl border bg-base-100 px-3 py-2.5 shadow-sm transition-colors',
		selected ? 'border-primary ring-1 ring-primary' : 'border-base-300/80',
		inTrip && 'opacity-80'
	]}
	onmouseenter={() => onHover?.(true)}
	onmouseleave={() => onHover?.(false)}
>
	<button type="button" class="flex w-full items-start gap-3 text-left" onclick={onSelect}>
		{#if item.photos?.[0]}
			<img
				src={placePhotoThumbnail(item.photos[0])}
				alt=""
				loading="lazy"
				class="h-14 w-14 shrink-0 rounded-lg object-cover"
			/>
		{:else}
			<div class="grid h-14 w-14 shrink-0 place-items-center rounded-lg bg-base-200 text-2xl">
				{emoji}
			</div>
		{/if}
		<div class="min-w-0 flex-1">
			<div class="flex items-start gap-2">
				<p class="min-w-0 flex-1 truncate font-semibold">{item.name}</p>
				{#if inTrip}
					<span class="badge badge-success badge-soft badge-sm shrink-0 gap-1">
						<Check class="h-3 w-3" />
						{$t('recomendations.in_trip')}
					</span>
				{/if}
			</div>
			<p class="truncate text-sm opacity-70">
				{item.primary_type ? typeLabel(item.primary_type) : ''}{item.primary_type && item.address
					? ' · '
					: ''}{item.address ?? ''}
			</p>
			<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-base-content/70">
				{#if item.rating != null}
					<span class="inline-flex items-center gap-0.5 font-medium text-warning">
						<Star class="h-3.5 w-3.5" />{item.rating.toFixed(1)}
						{#if item.review_count}
							<span class="font-normal text-base-content/60">({item.review_count})</span>
						{/if}
					</span>
				{/if}
				{#if item.distance_km != null}<span>{distance(item.distance_km)}</span>{/if}
				{#if item.price_level}<span>{'$'.repeat(item.price_level)}</span>{/if}
				{#if item.is_open_now != null}
					<span class={item.is_open_now ? 'text-success' : 'text-error'}>
						{item.is_open_now ? $t('map.open_now') : $t('map.closed_now')}
					</span>
				{/if}
			</div>
		</div>
	</button>

	{#if !inTrip}
		<div class="mt-2 flex justify-end">
			<RecommendationAddButton
				{busy}
				{days}
				{canAddLodging}
				lodging={lodgingDefault}
				{onAdd}
				{onAddToDay}
				{onAddDetails}
				{onAddLodging}
			/>
		</div>
	{/if}
</div>
