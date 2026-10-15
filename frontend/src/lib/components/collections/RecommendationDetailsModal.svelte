<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import { t } from 'svelte-i18n';
	import type { Recommendation } from '$lib/types';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import { googleContentImage } from '$lib/images';
	import Close from '~icons/mdi/close';
	import MapMarker from '~icons/mdi/map-marker';
	import InfoIcon from '~icons/mdi/information';
	import ImageIcon from '~icons/mdi/image-multiple';
	import ClockOutline from '~icons/mdi/clock-outline';
	import Phone from '~icons/mdi/phone';
	import Web from '~icons/mdi/web';
	import OpenInNew from '~icons/mdi/open-in-new';
	import LightningIcon from '~icons/mdi/lightning-bolt';
	import Plus from '~icons/mdi/plus';
	import Bed from '~icons/mdi/bed';

	interface Props {
		recommendation: Recommendation;
		isMetric?: boolean;
		isQuickAdding?: boolean;
		onClose: () => void;
		onQuickAdd: () => void;
		onAddDetails: () => void;
		onAddLodging: () => void;
	}

	let {
		recommendation,
		isMetric = true,
		isQuickAdding = false,
		onClose,
		onQuickAdd,
		onAddDetails,
		onAddLodging
	}: Props = $props();

	const DESCRIPTION_LIMIT = 320;

	let descriptionExpanded = $state(false);
	let photoIndex = $state(0);
	let photoModalOpen = $state(false);

	const openDialog: Attachment = (node) => {
		const dialog = node as HTMLDialogElement;
		dialog.showModal();
		return () => {
			if (dialog.open) dialog.close();
		};
	};

	const photos = $derived(recommendation.photos ?? []);
	const activePhoto = $derived(photos[photoIndex] ?? photos[0] ?? null);
	const rating = $derived(
		recommendation.rating != null && !Number.isNaN(recommendation.rating)
			? recommendation.rating
			: null
	);
	const roundedRating = $derived(rating == null ? 0 : Math.round(rating));
	const description = $derived(recommendation.description?.trim() ?? '');
	const descriptionIsLong = $derived(description.length > DESCRIPTION_LIMIT);
	const descriptionText = $derived(
		descriptionExpanded || !descriptionIsLong
			? description
			: `${description.slice(0, DESCRIPTION_LIMIT).trim()}…`
	);
	const priceLabel = $derived.by(() => {
		const levels: Record<string, string> = {
			FREE: 'Free',
			INEXPENSIVE: '$',
			MODERATE: '$$',
			EXPENSIVE: '$$$',
			VERY_EXPENSIVE: '$$$$'
		};
		return recommendation.price_level ? levels[recommendation.price_level] || '' : '';
	});
	const distanceLabel = $derived.by(() => {
		const km = recommendation.distance_km;
		if (km == null || Number.isNaN(km)) return '';
		if (isMetric) return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
		const miles = km / 1.60934;
		return miles < 0.1 ? `${Math.round(miles * 5280)} ft` : `${miles.toFixed(1)} mi`;
	});
	const providerLabel = $derived(
		recommendation.source === 'google' ? 'Google Maps' : 'OpenStreetMap'
	);
	const website = $derived(recommendation.website || recommendation.google_maps_url || '');
	const genericTypes = new Set(['establishment', 'point_of_interest', 'premise', 'geocode']);
	const typeLabels = $derived(
		[recommendation.primary_type, ...(recommendation.types ?? [])]
			.filter((type): type is string => Boolean(type) && !genericTypes.has(type))
			.filter((type, index, all) => all.indexOf(type) === index)
			.map((type) => type.replaceAll('_', ' '))
	);
	const photoImages = $derived(
		photos.map((url, index) => googleContentImage(`rec-photo-${index}`, url, index === 0))
	);

	function openPhoto(index: number) {
		photoIndex = index;
		photoModalOpen = true;
	}
</script>

<dialog
	class="modal modal-bottom backdrop-blur-xs md:modal-middle"
	{@attach openDialog}
	onclose={onClose}
>
	<div
		class="details-modal modal-box flex flex-col overflow-hidden rounded-none border border-base-300 bg-base-100 p-0 shadow-2xl md:rounded-2xl"
		role="dialog"
		aria-labelledby="recommendation-details-title"
	>
		<div class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-3 md:px-6 md:py-4">
			<div class="flex items-center justify-between gap-3">
				<div class="flex min-w-0 items-center gap-3">
					<div class="shrink-0 rounded-xl bg-primary/10 p-2 text-primary">
						<MapMarker class="h-8 w-8" />
					</div>
					<div class="min-w-0">
						<h1
							id="recommendation-details-title"
							class="truncate text-2xl font-bold text-primary md:text-3xl"
						>
							{recommendation.name}
						</h1>
						<p class="truncate text-sm text-base-content/80">
							{recommendation.address || recommendation.primary_type || $t('map.view_details')}
						</p>
					</div>
				</div>
				<button
					type="button"
					class="btn btn-ghost btn-square shrink-0"
					aria-label={$t('about.close')}
					onclick={onClose}
				>
					<Close class="h-5 w-5" />
				</button>
			</div>
		</div>

		<div class="min-h-0 flex-1 space-y-6 overflow-y-auto px-4 py-4 md:px-6 md:py-5">
			<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
				{#if activePhoto}
					<div class="card border border-base-300 bg-base-100">
						<div class="card-body p-6">
							<div class="mb-6 flex items-center gap-3">
								<div class="rounded-lg bg-primary/10 p-2 text-primary">
									<ImageIcon class="h-5 w-5" />
								</div>
								<h2 class="text-xl font-bold">{$t('adventures.images')}</h2>
							</div>
							<button
								type="button"
								class="w-full overflow-hidden rounded-lg border border-base-300"
								onclick={() => openPhoto(photoIndex)}
							>
								<img src={activePhoto} alt="" class="h-64 w-full object-cover sm:h-80" />
							</button>
							{#if photos.length > 1}
								<div class="mt-3 flex gap-2 overflow-x-auto">
									{#each photos as photo, index (photo)}
										<button
											type="button"
											class={[
												'h-16 w-16 shrink-0 overflow-hidden rounded-lg border',
												index === photoIndex
													? 'border-primary ring-2 ring-primary'
													: 'border-base-300'
											]}
											aria-label={$t('adventures.images')}
											onclick={() => (photoIndex = index)}
										>
											<img src={photo} alt="" class="h-full w-full object-cover" />
										</button>
									{/each}
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<div class="card border border-base-300 bg-base-100">
					<div class="card-body p-6">
						<div class="mb-6 flex items-center gap-3">
							<div class="rounded-lg bg-primary/10 p-2 text-primary">
								<InfoIcon class="h-5 w-5" />
							</div>
							<h2 class="text-xl font-bold">{$t('adventures.basic_information')}</h2>
						</div>

						<div
							class="place-stats grid w-full rounded-box bg-base-200 shadow-sm"
							style:grid-template-columns="repeat(auto-fit, minmax(min(100%, 7.5rem), 1fr))"
						>
							{#if rating != null}
								<div class="stat min-w-0">
									<div class="stat-title">{$t('adventures.rating')}</div>
									<div class="stat-value text-2xl">{rating.toFixed(1)}</div>
									<div class="stat-desc mt-1 flex flex-wrap items-center gap-2">
										<div class="rating rating-xs pointer-events-none">
											{#each [1, 2, 3, 4, 5] as star (star)}
												<input
													type="radio"
													class="mask mask-star-2 bg-warning"
													checked={roundedRating === star}
													tabindex="-1"
													aria-label={String(star)}
												/>
											{/each}
										</div>
										{#if recommendation.review_count}
											<span>({recommendation.review_count.toLocaleString()})</span>
										{/if}
									</div>
								</div>
							{/if}
							{#if distanceLabel}
								<div class="stat min-w-0">
									<div class="stat-title">{$t('adventures.distance')}</div>
									<div class="stat-value text-2xl">{distanceLabel}</div>
								</div>
							{/if}
							{#if recommendation.is_open_now != null || priceLabel}
								<div class="stat min-w-0">
									<div class="stat-title">
										{recommendation.is_open_now != null ? $t('map.hours') : $t('adventures.price')}
									</div>
									<div class="stat-value text-lg">
										{#if recommendation.is_open_now === true}
											<span class="badge badge-success">{$t('map.open_now')}</span>
										{:else if recommendation.is_open_now === false}
											<span class="badge badge-ghost">{$t('map.closed_now')}</span>
										{:else}
											{priceLabel}
										{/if}
									</div>
									{#if recommendation.is_open_now != null && priceLabel}
										<div class="stat-desc">{priceLabel}</div>
									{/if}
								</div>
							{/if}
						</div>

						{#if typeLabels.length}
							<div class="mt-4 flex flex-wrap gap-2">
								{#each typeLabels as type, index (type)}
									<span
										class={index === 0 ? 'badge badge-primary badge-outline' : 'badge badge-ghost'}
									>
										{type}
									</span>
								{/each}
							</div>
						{/if}

						{#if recommendation.address}
							<div
								class="mt-4 flex items-start gap-3 rounded-lg border border-base-300 bg-base-200/40 p-3"
							>
								<MapMarker class="mt-0.5 h-5 w-5 shrink-0 text-primary" />
								<p class="text-sm leading-relaxed">{recommendation.address}</p>
							</div>
						{/if}

						{#if recommendation.phone_number || website}
							<div class="mt-4 space-y-2">
								{#if recommendation.phone_number}
									<a
										href="tel:{recommendation.phone_number}"
										class="flex items-center gap-3 rounded-lg border border-base-300 bg-base-200/40 p-3 text-sm font-medium hover:border-primary"
									>
										<Phone class="h-5 w-5 shrink-0 text-primary" />
										{recommendation.phone_number}
									</a>
								{/if}
								{#if website}
									<a
										href={website}
										target="_blank"
										rel="noopener noreferrer"
										class="flex items-center gap-3 rounded-lg border border-base-300 bg-base-200/40 p-3 text-sm font-medium hover:border-primary"
									>
										<Web class="h-5 w-5 shrink-0 text-primary" />
										<span class="min-w-0 flex-1 truncate">{$t('map.visit_website')}</span>
										<OpenInNew class="h-4 w-4 shrink-0 opacity-60" />
									</a>
								{/if}
							</div>
						{/if}
					</div>
				</div>
			</div>

			{#if description}
				<div class="card border border-base-300 bg-base-100">
					<div class="card-body p-6">
						<div class="mb-4 flex items-center gap-3">
							<div class="rounded-lg bg-primary/10 p-2 text-primary">
								<InfoIcon class="h-5 w-5" />
							</div>
							<h2 class="text-xl font-bold">{$t('adventures.description')}</h2>
						</div>
						<p class="whitespace-pre-wrap text-sm leading-relaxed text-base-content/80">
							{descriptionText}
						</p>
						{#if descriptionIsLong}
							<button
								type="button"
								class="btn btn-ghost btn-sm mt-2 px-0"
								onclick={() => (descriptionExpanded = !descriptionExpanded)}
							>
								{descriptionExpanded ? $t('map.show_less') : $t('map.show_more')}
							</button>
						{/if}
					</div>
				</div>
			{/if}

			{#if recommendation.opening_hours?.length}
				<div class="card border border-base-300 bg-base-100">
					<div class="card-body p-6">
						<div class="mb-4 flex items-center gap-3">
							<div class="rounded-lg bg-primary/10 p-2 text-primary">
								<ClockOutline class="h-5 w-5" />
							</div>
							<h2 class="text-xl font-bold">{$t('map.hours')}</h2>
						</div>
						<ul class="divide-y divide-base-300 overflow-hidden rounded-lg border border-base-300">
							{#each recommendation.opening_hours as hour (hour)}
								<li class="bg-base-200/40 px-4 py-2.5 text-sm">{hour}</li>
							{/each}
						</ul>
					</div>
				</div>
			{/if}

			<p class="text-xs text-base-content/50">
				{$t('map.powered_by', { values: { provider: providerLabel } })}
			</p>
		</div>

		<div
			class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-base-300 bg-base-100 px-4 py-3 md:px-6"
		>
			<button type="button" class="btn btn-ghost gap-2" onclick={onAddLodging}>
				<Bed class="h-4 w-4" />
				{$t('map.add_as_lodging')}
			</button>
			<button
				type="button"
				class="btn btn-outline gap-2"
				disabled={isQuickAdding}
				onclick={onAddDetails}
			>
				<Plus class="h-4 w-4" />
				{$t('map.add_with_details')}
			</button>
			<button
				type="button"
				class="btn btn-primary gap-2"
				class:loading={isQuickAdding}
				disabled={isQuickAdding}
				onclick={onQuickAdd}
			>
				<LightningIcon class="h-4 w-4" />
				{$t('map.quick_add')}
			</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button type="button" onclick={onClose}>{$t('about.close')}</button>
	</form>
</dialog>

{#if photoModalOpen}
	<ImageDisplayModal
		images={photoImages}
		initialIndex={photoIndex}
		name={recommendation.name}
		location={recommendation.address || ''}
		on:close={() => (photoModalOpen = false)}
	/>
{/if}

<style>
	.place-stats :global(.stat) {
		width: auto;
		min-width: 0;
	}

	.details-modal {
		width: 100%;
		max-width: 100%;
		height: 100dvh;
		max-height: 100dvh;
	}

	@media (min-width: 768px) {
		.details-modal {
			width: min(96vw, 64rem);
			max-width: 64rem;
			height: min(90dvh, 52rem);
			max-height: 90dvh;
		}
	}
</style>
