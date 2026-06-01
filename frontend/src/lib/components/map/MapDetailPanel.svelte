<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import type { Location, PlaceSearchResult, Recommendation, ContentImage } from '$lib/types';
	import { formatProviderLabel } from '$lib/map/places';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';

	import ArrowLeft from '~icons/mdi/arrow-left';
	import OpenInNew from '~icons/mdi/open-in-new';
	import Phone from '~icons/mdi/phone';
	import Web from '~icons/mdi/web';
	import Star from '~icons/mdi/star';
	import StarHalfFull from '~icons/mdi/star-half-full';
	import StarOutline from '~icons/mdi/star-outline';
	import ClockOutline from '~icons/mdi/clock-outline';
	import LightningIcon from '~icons/mdi/lightning-bolt';
	import Plus from '~icons/mdi/plus';
	import MapMarker from '~icons/mdi/map-marker';
	import LinkIcon from '~icons/mdi/link-variant';

	export let selectionKind: 'pin' | 'place' | 'recommendation' | null = null;
	export let location: Location | null = null;
	export let place: PlaceSearchResult | null = null;
	export let recommendation: Recommendation | null = null;
	export let pinName = '';
	export let pinVisitStatus: 'visited' | 'planned' | null = null;
	export let pinCategoryIcon = '';
	export let loading = false;
	export let error: string | null = null;
	export let isQuickAdding = false;
	export let showLodgingAdd = false;
	export let isMetric = true;

	const dispatch = createEventDispatcher<{
		back: void;
		viewFull: { pinId: string };
		quickAdd: void;
		addDetails: void;
		addLodging: void;
	}>();

	let photoModalOpen = false;
	let selectedPhotos: ContentImage[] = [];
	let selectedPhotoIndex = 0;
	let photoTitle = '';
	let photoSubtitle = '';
	let descriptionExpanded = false;

	const DESCRIPTION_COLLAPSE_CHARS = 320;

	function renderMarkdown(markdown: string): string {
		return marked(markdown) as string;
	}

	function sanitizeMarkdown(html: string): string {
		return DOMPurify.sanitize(html);
	}

	function formatDate(value: string | null | undefined): string {
		if (!value) return '';
		return value.split('T')[0] ?? value;
	}

	function renderStars(rating: number | null | undefined) {
		if (rating === null || rating === undefined || Number.isNaN(rating)) return [];
		const stars = [];
		const fullStars = Math.floor(rating);
		const hasHalfStar = rating % 1 >= 0.5;
		for (let i = 0; i < 5; i++) {
			if (i < fullStars) stars.push({ type: 'full', key: i });
			else if (i === fullStars && hasHalfStar) stars.push({ type: 'half', key: i });
			else stars.push({ type: 'empty', key: i });
		}
		return stars;
	}

	function getPriceLevelDisplay(priceLevel: string | null | undefined) {
		if (!priceLevel) return '';
		const levels: Record<string, string> = {
			FREE: 'Free',
			INEXPENSIVE: '$',
			MODERATE: '$$',
			EXPENSIVE: '$$$',
			VERY_EXPENSIVE: '$$$$'
		};
		return levels[priceLevel] || '';
	}

	function formatDistance(km: number | null | undefined, metric: boolean) {
		if (km === null || km === undefined) return '';
		if (metric) {
			return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
		}
		const miles = km / 1.60934;
		return miles < 0.1 ? `${Math.round(miles * 5280)} ft` : `${miles.toFixed(1)} mi`;
	}

	function openPhotoUrls(urls: string[], title: string, subtitle = '', startIndex = 0) {
		selectedPhotos = urls.map((url, index) => ({
			id: `photo-${index}`,
			image: url,
			is_primary: index === 0,
			immich_id: null
		}));
		photoTitle = title;
		photoSubtitle = subtitle;
		selectedPhotoIndex = startIndex;
		photoModalOpen = true;
	}

	function openLocationImages(images: ContentImage[], title: string, subtitle = '', startIndex = 0) {
		selectedPhotos = images;
		photoTitle = title;
		photoSubtitle = subtitle;
		selectedPhotoIndex = startIndex;
		photoModalOpen = true;
	}

	$: title =
		selectionKind === 'pin'
			? location?.name || pinName
			: selectionKind === 'place'
				? place?.name
				: selectionKind === 'recommendation'
					? recommendation?.name
					: '';

	$: subtitle =
		selectionKind === 'pin'
			? location?.location
			: selectionKind === 'place'
				? place?.location
				: selectionKind === 'recommendation'
					? recommendation?.address
					: '';

	$: rating =
		selectionKind === 'pin'
			? location?.rating
			: selectionKind === 'place'
				? place?.rating
				: recommendation?.rating;

	$: displayRating = hasValidRating(rating) ? (rating as number) : null;

	$: externalPhotoUrls =
		selectionKind === 'place'
			? place?.photos || []
			: selectionKind === 'recommendation'
				? recommendation?.photos || []
				: [];

	$: locationImages = selectionKind === 'pin' && location?.images?.length ? location.images : [];

	$: descriptionText =
		selectionKind === 'pin'
			? location?.description
			: selectionKind === 'place'
				? place?.description
				: selectionKind === 'recommendation'
					? recommendation?.description
					: null;

	$: providerLabel =
		selectionKind === 'place'
			? formatProviderLabel(place?.provider || place?.powered_by)
			: selectionKind === 'recommendation' && recommendation
				? recommendation.source === 'google'
					? 'Google Maps'
					: 'OpenStreetMap'
				: null;

	function hasValidRating(value: number | null | undefined): boolean {
		return value !== null && value !== undefined && !Number.isNaN(value);
	}

	function plainTextFromMarkdown(markdown: string): string {
		return markdown
			.replace(/```[\s\S]*?```/g, ' ')
			.replace(/`[^`]*`/g, ' ')
			.replace(/!\[[^\]]*]\([^)]*\)/g, ' ')
			.replace(/\[[^\]]*]\([^)]*\)/g, '$1')
			.replace(/[#>*_~\-]/g, ' ')
			.replace(/\s+/g, ' ')
			.trim();
	}

	$: selectionKey =
		selectionKind === 'pin'
			? (location?.id ?? pinName)
			: selectionKind === 'place'
				? (place?.place_id ?? place?.name)
				: selectionKind === 'recommendation'
					? recommendation?.id
					: '';

	$: selectionKey, (descriptionExpanded = false);

	$: descriptionPlain = descriptionText?.trim() ? plainTextFromMarkdown(descriptionText) : '';
	$: descriptionIsLong = descriptionPlain.length > DESCRIPTION_COLLAPSE_CHARS;
	$: descriptionPreview = descriptionIsLong
		? `${descriptionPlain.slice(0, DESCRIPTION_COLLAPSE_CHARS).trim()}…`
		: descriptionPlain;
</script>

{#if photoModalOpen}
	<ImageDisplayModal
		images={selectedPhotos}
		initialIndex={selectedPhotoIndex}
		name={photoTitle}
		location={photoSubtitle}
		on:close={() => (photoModalOpen = false)}
	/>
{/if}

<div class="flex flex-col h-full min-h-0 max-h-full">
	<button
		type="button"
		class="btn btn-ghost btn-sm gap-2 justify-start shrink-0 mb-4"
		on:click={() => dispatch('back')}
	>
		<ArrowLeft class="w-4 h-4" />
		{$t('map.back_to_controls')}
	</button>

	{#if !selectionKind}
		<p class="text-sm text-base-content/60">{$t('map.select_on_map')}</p>
	{:else if loading && selectionKind === 'pin' && !location}
		<div class="space-y-3 flex-1">
			<div class="flex items-center gap-2">
				<span class="loading loading-spinner loading-sm"></span>
				<span class="text-sm text-base-content/60">{$t('map.loading_details')}</span>
			</div>
			<div class="skeleton h-6 w-3/4"></div>
			<div class="skeleton h-32 w-full"></div>
			<div class="skeleton h-24 w-full"></div>
		</div>
	{:else if error}
		<div role="alert" class="alert alert-error alert-soft">
			<span class="text-sm">{error}</span>
		</div>
	{:else}
		<div class="flex-1 overflow-y-auto min-h-0 space-y-4 pr-1">
			<div>
				<h2 class="text-lg font-bold leading-tight">{title}</h2>
				{#if subtitle}
					<p class="text-sm text-base-content/70 mt-1 leading-snug">{subtitle}</p>
				{/if}
			</div>

			{#if selectionKind === 'pin'}
				<div class="flex flex-wrap items-center gap-2">
					{#if pinVisitStatus}
						<div
							class="badge badge-sm {pinVisitStatus === 'visited'
								? 'badge-success'
								: 'badge-info'}"
						>
							{pinVisitStatus === 'visited'
								? $t('adventures.visited')
								: $t('adventures.planned')}
						</div>
					{/if}
					{#if pinCategoryIcon}
						<div class="badge badge-ghost badge-sm text-base">{pinCategoryIcon}</div>
					{/if}
					{#if location?.category?.display_name}
						<div class="badge badge-outline badge-sm">{location.category.display_name}</div>
					{/if}
				</div>
			{/if}

			{#if displayRating !== null}
				<div class="flex items-center gap-2">
					<div class="flex items-center text-warning">
						{#each renderStars(displayRating) as star (star.key)}
							{#if star.type === 'full'}
								<Star class="w-4 h-4" />
							{:else if star.type === 'half'}
								<StarHalfFull class="w-4 h-4" />
							{:else}
								<StarOutline class="w-4 h-4" />
							{/if}
						{/each}
					</div>
					<span class="text-sm font-medium">{displayRating}</span>
					{#if selectionKind === 'place' && place?.review_count}
						<span class="text-xs text-base-content/60"
							>({place.review_count.toLocaleString()})</span
						>
					{/if}
					{#if selectionKind === 'recommendation' && recommendation?.review_count}
						<span class="text-xs text-base-content/60"
							>({recommendation.review_count.toLocaleString()})</span
						>
					{/if}
				</div>
			{/if}

			{#if selectionKind === 'recommendation' && recommendation}
				<div class="flex flex-wrap gap-2">
					{#if recommendation.primary_type}
						<div class="badge badge-ghost badge-sm">{recommendation.primary_type}</div>
					{/if}
					{#if recommendation.distance_km != null}
						<div class="badge badge-ghost badge-sm">
							<MapMarker class="w-3 h-3" />
							{formatDistance(recommendation.distance_km, isMetric)}
						</div>
					{/if}
					{#if recommendation.price_level}
						<div class="badge badge-ghost badge-sm">
							{getPriceLevelDisplay(recommendation.price_level)}
						</div>
					{/if}
					{#if recommendation.is_open_now === true}
						<div class="badge badge-success badge-sm">{$t('map.open_now')}</div>
					{:else if recommendation.is_open_now === false}
						<div class="badge badge-ghost badge-sm">{$t('map.closed_now')}</div>
					{/if}
				</div>
			{/if}

			{#if selectionKind === 'pin' && locationImages.length > 0}
				<div>
					<h3 class="text-sm font-semibold mb-2">{$t('adventures.images')}</h3>
					<div class="grid grid-cols-2 gap-2">
						{#each locationImages as image, i}
							<button
								type="button"
								class="aspect-square rounded-lg overflow-hidden border border-base-300 hover:ring-2 ring-primary relative"
								on:click={() => openLocationImages(locationImages, title || '', subtitle || '', i)}
							>
								<img src={image.image} alt="" class="w-full h-full object-cover" />
								{#if image.is_primary}
									<span class="badge badge-primary badge-xs absolute top-1 right-1"
										>{$t('settings.primary')}</span
									>
								{/if}
							</button>
						{/each}
					</div>
				</div>
			{:else if externalPhotoUrls.length > 0}
				<div>
					<h3 class="text-sm font-semibold mb-2">{$t('adventures.images')}</h3>
					<div class="grid grid-cols-2 gap-2">
						{#each externalPhotoUrls.slice(0, 6) as photo, i}
							<button
								type="button"
								class="aspect-square rounded-lg overflow-hidden border border-base-300 hover:ring-2 ring-primary"
								on:click={() => openPhotoUrls(externalPhotoUrls, title || '', subtitle || '', i)}
							>
								<img src={photo} alt="" class="w-full h-full object-cover" />
							</button>
						{/each}
					</div>
				</div>
			{/if}

			{#if selectionKind === 'pin' && location}
				<div class="flex flex-wrap gap-2 text-xs">
					<div class="badge badge-ghost badge-sm">
						{$t('map.visits')}: {location.visits?.length ?? 0}
					</div>
					{#if location.trails?.length}
						<div class="badge badge-ghost badge-sm">
							{$t('adventures.trails')}: {location.trails.length}
						</div>
					{/if}
					{#if location.attachments?.length}
						<div class="badge badge-ghost badge-sm">
							{$t('adventures.attachments')}: {location.attachments.length}
						</div>
					{/if}
				</div>

				{#if location.visits?.length}
					<div>
						<h3 class="text-sm font-semibold mb-2">{$t('adventures.visits')}</h3>
						<ul class="space-y-2">
							{#each location.visits.slice(0, 5) as visit}
								<li class="text-xs text-base-content/80 bg-base-200/60 rounded-lg px-3 py-2">
									{#if visit.start_date}
										{formatDate(visit.start_date)}
										{#if visit.end_date && visit.end_date !== visit.start_date}
											– {formatDate(visit.end_date)}
										{/if}
									{:else}
										{$t('adventures.visit')}
									{/if}
								</li>
							{/each}
							{#if location.visits.length > 5}
								<li class="text-xs text-base-content/50">
									+{location.visits.length - 5} more
								</li>
							{/if}
						</ul>
					</div>
				{/if}

				{#if location.link}
					<a
						href={location.link}
						target="_blank"
						rel="noopener noreferrer"
						class="btn btn-ghost btn-sm gap-2 justify-start w-full"
					>
						<LinkIcon class="w-4 h-4" />
						<span class="truncate">{$t('map.visit_website')}</span>
						<OpenInNew class="w-3 h-3 shrink-0" />
					</a>
				{/if}
			{/if}

			{#if descriptionText?.trim()}
				<div>
					<h3 class="text-sm font-semibold mb-2">{$t('adventures.description')}</h3>
					{#if descriptionExpanded}
						<article class="prose prose-sm max-w-none text-base-content">
							{@html sanitizeMarkdown(renderMarkdown(descriptionText))}
						</article>
					{:else if descriptionIsLong}
						<p class="text-sm text-base-content/80 leading-relaxed whitespace-pre-wrap">
							{descriptionPreview}
						</p>
					{:else}
						<article class="prose prose-sm max-w-none text-base-content">
							{@html sanitizeMarkdown(renderMarkdown(descriptionText))}
						</article>
					{/if}
					{#if descriptionIsLong}
						<button
							type="button"
							class="btn btn-ghost btn-xs mt-2 px-0"
							on:click={() => (descriptionExpanded = !descriptionExpanded)}
						>
							{descriptionExpanded ? $t('map.show_less') : $t('map.show_more')}
						</button>
					{/if}
				</div>
			{/if}

			{#if selectionKind === 'pin' && location?.tags?.length}
				<div>
					<h3 class="text-sm font-semibold mb-2">{$t('adventures.tags')}</h3>
					<div class="flex flex-wrap gap-1">
						{#each location.tags as tag}
							<span class="badge badge-ghost badge-sm">{tag}</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if selectionKind === 'recommendation' && recommendation?.opening_hours?.length}
				<div class="text-xs space-y-1">
					<div class="font-semibold flex items-center gap-1">
						<ClockOutline class="w-4 h-4" />
						{$t('map.hours')}
					</div>
					{#each recommendation.opening_hours as hour}
						<p class="text-base-content/70">{hour}</p>
					{/each}
				</div>
			{/if}

			{#if selectionKind === 'place' && place}
				{#if place.phone_number}
					<a href="tel:{place.phone_number}" class="btn btn-ghost btn-sm gap-2 justify-start">
						<Phone class="w-4 h-4" />
						{place.phone_number}
					</a>
				{/if}
				{#if place.website || place.google_maps_url}
					<a
						href={place.website || place.google_maps_url}
						target="_blank"
						rel="noopener noreferrer"
						class="btn btn-ghost btn-sm gap-2 justify-start"
					>
						<Web class="w-4 h-4" />
						{$t('map.visit_website')}
						<OpenInNew class="w-3 h-3" />
					</a>
				{/if}
			{/if}

			{#if selectionKind === 'recommendation' && recommendation}
				{#if recommendation.phone_number}
					<a
						href="tel:{recommendation.phone_number}"
						class="btn btn-ghost btn-sm gap-2 justify-start"
					>
						<Phone class="w-4 h-4" />
						{recommendation.phone_number}
					</a>
				{/if}
				{#if recommendation.website || recommendation.google_maps_url}
					<a
						href={recommendation.website || recommendation.google_maps_url}
						target="_blank"
						rel="noopener noreferrer"
						class="btn btn-ghost btn-sm gap-2 justify-start"
					>
						<Web class="w-4 h-4" />
						{$t('map.visit_website')}
						<OpenInNew class="w-3 h-3" />
					</a>
				{/if}
			{/if}

			{#if providerLabel}
				<p class="text-xs text-base-content/50">
					{$t('map.powered_by', { values: { provider: providerLabel } })}
				</p>
			{/if}
		</div>

		<div class="shrink-0 pt-4 space-y-2 border-t border-base-300 mt-4">
			{#if selectionKind === 'pin' && location?.id}
				<button
					type="button"
					class="btn btn-primary w-full"
					on:click={() => dispatch('viewFull', { pinId: location.id })}
				>
					{$t('map.view_details')}
				</button>
			{/if}

			{#if selectionKind === 'place' || selectionKind === 'recommendation'}
				<button
					type="button"
					class="btn btn-primary w-full gap-2"
					class:loading={isQuickAdding}
					disabled={isQuickAdding}
					on:click={() => dispatch('quickAdd')}
				>
					<LightningIcon class="w-4 h-4" />
					{$t('map.quick_add')}
				</button>
				<button
					type="button"
					class="btn btn-outline w-full gap-2"
					disabled={isQuickAdding}
					on:click={() => dispatch('addDetails')}
				>
					<Plus class="w-4 h-4" />
					{$t('map.add_with_details')}
				</button>
				{#if showLodgingAdd && selectionKind === 'recommendation'}
					<button
						type="button"
						class="btn btn-ghost w-full gap-2"
						on:click={() => dispatch('addLodging')}
					>
						{$t('map.add_as_lodging')}
					</button>
				{/if}
			{/if}
		</div>
	{/if}
</div>
