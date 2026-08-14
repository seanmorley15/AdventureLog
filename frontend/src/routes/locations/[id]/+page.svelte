<script lang="ts">
	import { run } from 'svelte/legacy';

	import type { Location } from '$lib/types';
	import { fetchSunriseSunset, visitDateKey, type SunriseSunset } from '$lib/sunriseSunset';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';
	import FullMap from '$lib/components/map/FullMap.svelte';
	import { DefaultMarker, Popup, GeoJSON, LineLayer } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import { DateTime } from 'luxon';

	import LightbulbOn from '~icons/mdi/lightbulb-on';
	import WeatherSunset from '~icons/mdi/weather-sunset';
	import ClipboardList from '~icons/mdi/clipboard-list';
	import ContentCopy from '~icons/mdi/content-copy';
	import DotsVertical from '~icons/mdi/dots-vertical';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import ImageFrame from '$lib/components/ImageFrame.svelte';
	import { googleContentImage } from '$lib/images';
	import AttachmentCard from '$lib/components/cards/AttachmentCard.svelte';
	import { addToast } from '$lib/toasts';
	import { getActivityColor, normalizeBasemapType, isVisitAllDay, copyToClipboard } from '$lib';
	import ActivityCard from '$lib/components/cards/ActivityCard.svelte';
	import TrailCard from '$lib/components/cards/TrailCard.svelte';
	import NewLocationModal from '$lib/components/locations/LocationModal.svelte';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '$lib/money';
	import ExternalMapLinks from '$lib/components/shared/ExternalMapLinks.svelte';
	import MapFloatingControls from '$lib/components/map/MapFloatingControls.svelte';
	import MapTrackLayerControls from '$lib/components/map/MapTrackLayerControls.svelte';
	import MapImagePinLayer from '$lib/components/map/MapImagePinLayer.svelte';
	import { contentImagesToGeoJson, EMPTY_IMAGE_PIN_GEOJSON } from '$lib/map/imagePins';
	import ImageOutline from '~icons/mdi/image-outline';
	import SocialShareModal from '$lib/components/SocialShareModal.svelte';
	import UserAvatar from '$lib/components/UserAvatar.svelte';

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	let measurementSystem = $derived(data.user?.measurement_system || 'metric');

	let adventure: Location | undefined = $state();
	let visitSunriseSunset: Record<string, SunriseSunset> = $state({});
	let sunriseSunsetLoading: Record<string, boolean> = $state({});
	let currentSlide = $state(0);

	let adventurePriceLabel = $derived(adventure
		? formatMoney(
				toMoneyValue(
					adventure.price,
					adventure.price_currency,
					data.user?.default_currency || DEFAULT_CURRENCY
				)
			)
		: null);

	function goToSlide(index: number) {
		currentSlide = index;
	}

	let notFound: boolean = $state(false);
	let isEditModalOpen: boolean = $state(false);
	let isSocialShareModalOpen: boolean = $state(false);
	let adventure_images: { image: string; adventure: Location | null }[] = [];
	let modalInitialIndex: number = $state(0);
	let isImageModalOpen: boolean = $state(false);
	let mapBasemapType = $state(normalizeBasemapType(undefined));
	$effect.pre(() => {
		mapBasemapType = normalizeBasemapType(data.user?.map_style);
	});
	let showActivityTracks = $state(true);
	let showTrailTracks = $state(true);
	let showImagePins = $state(true);

	async function loadSunriseSunsetForDate(date: string) {
		if (!adventure?.id || sunriseSunsetLoading[date] || visitSunriseSunset[date]) {
			return;
		}

		sunriseSunsetLoading = { ...sunriseSunsetLoading, [date]: true };

		try {
			const sunriseSunset = await fetchSunriseSunset(adventure.id, date);
			if (sunriseSunset) {
				visitSunriseSunset = { ...visitSunriseSunset, [date]: sunriseSunset };
			} else {
				addToast('error', $t('adventures.sunrise_sunset_load_error'));
			}
		} finally {
			const { [date]: _removed, ...rest } = sunriseSunsetLoading;
			sunriseSunsetLoading = rest;
		}
	}

	function applyLocationPageData(adventureData: Location | null | undefined) {
		if (!adventureData) {
			notFound = true;
			adventure = undefined;
			visitSunriseSunset = {};
			sunriseSunsetLoading = {};
			currentSlide = 0;
			return;
		}

		notFound = false;
		adventure = adventureData;
		adventure.images.sort((a, b) => {
			if (a.is_primary && !b.is_primary) {
				return -1;
			} else if (!a.is_primary && b.is_primary) {
				return 1;
			} else {
				return 0;
			}
		});

		if (adventure.visits && adventure.visits.length > 1) {
			adventure.visits.sort((a, b) => {
				const aTs = DateTime.fromISO(a.start_date || a.created_at || '').toMillis() || 0;
				const bTs = DateTime.fromISO(b.start_date || b.created_at || '').toMillis() || 0;
				return aTs - bTs;
			});
		}

		visitSunriseSunset = {};
		sunriseSunsetLoading = {};
		currentSlide = 0;
		isImageModalOpen = false;
		isEditModalOpen = false;
		isSocialShareModalOpen = false;
	}

	run(() => {
		applyLocationPageData(data.props.adventure);
	});

	let imagePinGeoJson = $derived(adventure
		? contentImagesToGeoJson(adventure.images, {
				parentType: 'location',
				parentId: adventure.id,
				parentName: adventure.name
			})
		: EMPTY_IMAGE_PIN_GEOJSON);
	let hasImagePins = $derived(imagePinGeoJson.features.length > 0);

	function hasActivityGeojson(adventure: Location) {
		return adventure.visits.some((visit) => visit.activities.some((activity) => activity.geojson));
	}

	function hasAttachmentGeojson(adventure: Location) {
		return adventure.attachments.some((attachment) => attachment.geojson);
	}

	function hasTrailGeojson(adventure: Location) {
		return adventure.trails?.some((trail) => trail.geojson) ?? false;
	}

	function getTotalActivities(adventure: Location) {
		return adventure.visits.reduce(
			(total, visit) => total + (visit.activities ? visit.activities.length : 0),
			0
		);
	}

	function getTotalDistance(adventure: Location) {
		const totalMeters = adventure.visits.reduce(
			(total, visit) =>
				total +
				(visit.activities
					? visit.activities.reduce((sum, activity) => sum + (activity.distance || 0), 0)
					: 0),
			0
		);

		// Convert meters to km, then to miles if using imperial system
		const totalKm = totalMeters / 1000;
		return measurementSystem === 'imperial' ? totalKm * 0.621371 : totalKm;
	}

	function getTotalElevationGain(adventure: Location) {
		const totalMeters = adventure.visits.reduce(
			(total, visit) =>
				total +
				(visit.activities
					? visit.activities.reduce((sum, activity) => sum + (activity.elevation_gain || 0), 0)
					: 0),
			0
		);

		// Convert to feet if using imperial system
		return measurementSystem === 'imperial' ? totalMeters * 3.28084 : totalMeters;
	}

	let isDuplicating = $state(false);
	let isFabMenuOpen = $state(false);

	async function duplicateAdventure() {
		if (isDuplicating || !adventure) return;
		isDuplicating = true;
		isFabMenuOpen = false;
		try {
			const res = await fetch(`/api/locations/${adventure.id}/duplicate/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});
			if (res.ok) {
				const newLocation = await res.json();
				addToast('success', $t('adventures.location_duplicate_success'));
				goto(`/locations/${newLocation.id}`);
			} else {
				addToast('error', $t('adventures.location_duplicate_error'));
			}
		} catch (e) {
			addToast('error', $t('adventures.location_duplicate_error'));
		} finally {
			isDuplicating = false;
		}
	}

	function closeImageModal() {
		isImageModalOpen = false;
	}

	function openImageModal(imageIndex: number) {
		const current = adventure;
		if (!current) return;
		adventure_images = current.images.map((img) => ({
			image: img.image,
			adventure: current
		}));
		modalInitialIndex = imageIndex;
		isImageModalOpen = true;
	}

	function goToPreviousImage() {
		if (!adventure?.images?.length) return;
		goToSlide(currentSlide > 0 ? currentSlide - 1 : adventure.images.length - 1);
	}

	function goToNextImage() {
		if (!adventure?.images?.length) return;
		goToSlide(currentSlide < adventure.images.length - 1 ? currentSlide + 1 : 0);
	}

	function navigateToWorldTravelRegion() {
		if (!adventure?.country) return;
		if (adventure.region) {
			goto(`/worldtravel/${adventure.country.country_code}/${adventure.region.id}`);
		} else {
			goto(`/worldtravel/${adventure.country.country_code}`);
		}
	}

	function navigateToWorldTravelCountry() {
		if (!adventure?.country?.country_code) return;
		goto(`/worldtravel/${adventure.country.country_code}`);
	}

	async function copyAdventureCoordinates() {
		if (!adventure) return;
		try {
			await copyToClipboard(`${adventure.latitude}, ${adventure.longitude}`);
		} catch {
			addToast('error', $t('adventures.copy_failed'));
		}
	}

	async function copyAdventureGoogleMapsLink() {
		if (!adventure) return;
		try {
			await copyToClipboard(
				`https://www.google.com/maps/@${adventure.latitude},${adventure.longitude},15z`
			);
		} catch {
			addToast('error', $t('adventures.copy_failed'));
		}
	}
</script>

{#if notFound}
	<div class="hero min-h-screen bg-gradient-to-br from-base-200 to-base-300 overflow-x-hidden">
		<div class="hero-content text-center">
			<div class="max-w-md">
				<img src={Lost} alt="Lost" class="w-64 mx-auto mb-8 opacity-80" />
				<h1 class="text-5xl font-bold text-primary mb-4">{$t('adventures.location_not_found')}</h1>
				<p class="text-lg opacity-70 mb-8">{$t('adventures.location_not_found_desc')}</p>
				<button class="btn btn-primary btn-lg" onclick={() => goto('/')}>
					{$t('adventures.homepage')}
				</button>
			</div>
		</div>
	</div>
{/if}

{#if isEditModalOpen}
	<NewLocationModal
		on:close={() => (isEditModalOpen = false)}
		user={data.user}
		locationToEdit={adventure}
		bind:location={adventure}
	/>
{/if}

{#if isImageModalOpen && adventure}
	<ImageDisplayModal
		images={adventure.images}
		initialIndex={modalInitialIndex}
		on:close={closeImageModal}
	/>
{/if}

{#if isSocialShareModalOpen && adventure}
	<SocialShareModal
		type="location"
		id={adventure.id}
		name={adventure.name}
		isPublic={!!adventure.is_public}
		on:close={() => (isSocialShareModalOpen = false)}
	/>
{/if}

{#if !adventure && !notFound}
	<div class="hero min-h-screen overflow-x-hidden">
		<div class="hero-content">
			<span class="loading loading-spinner w-24 h-24 text-primary"></span>
		</div>
	</div>
{/if}

{#if adventure}
	{#if data.user?.uuid && adventure.user?.uuid && data.user.uuid === adventure.user.uuid}
		<div class="fixed bottom-6 right-6 z-50">
			<div class="dropdown dropdown-top dropdown-end" class:dropdown-open={isFabMenuOpen}>
				<button
					class="btn btn-primary btn-circle w-16 h-16 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-110"
					onclick={() => (isFabMenuOpen = !isFabMenuOpen)}
				>
					<DotsVertical class="w-8 h-8" />
				</button>
				<ul
					tabindex="-1"
					class="dropdown-content menu bg-base-100 rounded-box w-52 p-2 shadow-lg border border-base-300 mb-2"
				>
					<li>
						<button
							onclick={() => {
								isFabMenuOpen = false;
								isEditModalOpen = true;
							}}
							class="flex items-center gap-2"
						>
							<ClipboardList class="w-5 h-5" />
							{$t('adventures.edit_location')}
						</button>
					</li>
					<li>
						<button
							onclick={() => {
								isFabMenuOpen = false;
								isSocialShareModalOpen = true;
							}}
							class="flex items-center gap-2"
						>
							<ImageOutline class="w-5 h-5" />
							{$t('social_share.share_externally')}
						</button>
					</li>
					<li>
						<button
							onclick={duplicateAdventure}
							class="flex items-center gap-2"
							disabled={isDuplicating}
						>
							<ContentCopy class="w-5 h-5" />
							{isDuplicating ? '...' : $t('adventures.duplicate_location')}
						</button>
					</li>
				</ul>
			</div>
		</div>
	{/if}

	<!-- Hero Section -->
	<div class="relative">
		<div
			class="hero min-h-[60vh] relative overflow-hidden"
			class:min-h-[30vh]={!adventure.images || adventure.images.length === 0}
		>
			<!-- Background: Images or Gradient -->
			{#if adventure.images && adventure.images.length > 0}
				<div class="hero-overlay bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
				{#each adventure.images as image, i}
					<div
						class="absolute inset-0 transition-opacity duration-500"
						class:opacity-100={i === currentSlide}
						class:opacity-0={i !== currentSlide}
					>
						<button
							class="w-full h-full p-0 bg-transparent border-0"
							onclick={() => openImageModal(i)}
							aria-label={`View full image of ${adventure.name}`}
						>
							<ImageFrame source={image.source} showSourceBadge className="w-full h-full">
								<img src={image.image} class="w-full h-full object-cover" alt={adventure.name} />
							</ImageFrame>
						</button>
					</div>
				{/each}
			{:else}
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 to-secondary/20"></div>
			{/if}

			<!-- Content -->
			<div
				class="hero-content relative z-10 text-center"
				class:text-white={adventure.images?.length > 0}
			>
				<div class="max-w-4xl">
					<h1 class="text-6xl font-bold mb-4 drop-shadow-lg">{adventure.name}</h1>

					<!-- Rating -->
					{#if adventure.rating !== undefined && adventure.rating !== null}
						<div class="flex justify-center mb-6">
							<div class="rating rating-lg">
								{#each Array.from({ length: 5 }, (_, i) => i + 1) as star}
									<input
										type="radio"
										name="rating-hero"
										class="mask mask-star-2 bg-warning"
										checked={star <= adventure.rating}
										disabled
									/>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Quick Info Badges -->
					<div class="flex flex-wrap justify-center gap-4 mb-6">
						<a
							href="/locations?types={adventure.category?.name}"
							class="badge badge-lg badge-primary font-semibold px-4 py-3 cursor-pointer hover:brightness-110 transition-all"
						>
							{adventure.category?.display_name}
							{adventure.category?.icon}
						</a>
						{#if adventure.location}
							<div class="badge badge-lg badge-secondary font-semibold px-4 py-3">
								📍 {adventure.location}
							</div>
						{/if}
						{#if adventure.visits.length > 0}
							<div class="badge badge-lg badge-accent font-semibold px-4 py-3">
								🎯 {adventure.visits.length}
								{adventure.visits.length === 1 ? $t('adventures.visit') : $t('adventures.visits')}
							</div>
						{/if}
						{#if adventure.is_visited}
							<div class="badge badge-lg badge-success font-semibold px-4 py-3">
								✅ {$t('adventures.visited')}
							</div>
						{:else}
							<div class="badge badge-lg badge-warning font-semibold px-4 py-3">
								⏳ {$t('adventures.not_visited')}
							</div>
						{/if}
						{#if adventure.trails && adventure.trails.length > 0}
							<div class="badge badge-lg badge-info font-semibold px-4 py-3">
								🥾 {adventure.trails.length} Trail{adventure.trails.length === 1 ? '' : 's'}
							</div>
						{/if}
					</div>

					<!-- Image Navigation (only shown when multiple images exist) -->
					{#if adventure.images && adventure.images.length > 1}
						<div class="w-full max-w-md mx-auto">
							<!-- Navigation arrows and current position -->
							<div class="flex items-center justify-center gap-4 mb-3">
								<button
									onclick={goToPreviousImage}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.previous_image')}
								>
									❮
								</button>

								<div class="text-sm font-medium bg-black/50 px-3 py-1 rounded-full">
									{currentSlide + 1} / {adventure.images.length}
								</div>

								<button
									onclick={goToNextImage}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.next_image')}
								>
									❯
								</button>
							</div>

							<!-- Dot navigation -->
							{#if adventure.images.length <= 12}
								<div class="flex justify-center gap-2 flex-wrap">
									{#each adventure.images as _, i}
										<button
											onclick={() => goToSlide(i)}
											class="btn btn-circle btn-xs transition-all duration-200"
											class:btn-primary={i === currentSlide}
											class:btn-outline={i !== currentSlide}
											class:opacity-50={i !== currentSlide}
										>
											{i + 1}
										</button>
									{/each}
								</div>
							{:else}
								<div class="relative">
									<div
										class="absolute left-0 top-0 bottom-2 w-4 bg-gradient-to-r from-black/30 to-transparent pointer-events-none"
									></div>
									<div
										class="absolute right-0 top-0 bottom-2 w-4 bg-gradient-to-l from-black/30 to-transparent pointer-events-none"
									></div>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Main Content -->
	<div class="container mx-auto px-2 sm:px-4 py-6 sm:py-8 max-w-7xl">
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-8">
			<!-- Left Column - Main Content -->
			<div class="lg:col-span-2 space-y-6 sm:space-y-8">
				<!-- Author Info Card -->
				{#if adventure.user}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<div class="flex items-center gap-4">
								<div class="avatar shrink-0">
									<div
										class="w-16 overflow-hidden rounded-full ring-3 ring-neutral ring-offset-base-100 ring-offset-2"
									>
										<UserAvatar
											user={adventure.user}
											alt={adventure.user.first_name && adventure.user.last_name
												? `${adventure.user.first_name} ${adventure.user.last_name}`
												: adventure.user.username}
											className="w-16 h-16 rounded-full"
											textClass="text-xl"
										/>
									</div>
								</div>
								<div class="flex-1">
									<div class="text-lg font-bold">
										{#if adventure.user.public_profile}
											<a href={`/profile/${adventure.user.username}`} class="link link-hover">
												{adventure.user.first_name || adventure.user.username}
												{adventure.user.last_name || ''}
											</a>
										{:else}
											{adventure.user.first_name || adventure.user.username}
											{adventure.user.last_name || ''}
										{/if}
									</div>
									<div class="flex items-center gap-2 text-sm opacity-70 mt-1">
										<div class="badge badge-sm">
											{adventure.is_public
												? `🌍 ${$t('adventures.public')}`
												: `🔒 ${$t('adventures.private')}`}
										</div>
										{#if adventure.collections && adventure.collections.length > 0}
											<div class="badge badge-sm badge-outline">
												📚
												<p>{adventure.collections.length} {$t('navbar.collections')}</p>
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Description Card -->
				{#if adventure.description}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">📝 {$t('adventures.description')}</h2>
							<article class="prose max-w-none">
								{@html DOMPurify.sanitize(renderMarkdown(adventure.description))}
							</article>
						</div>
					</div>
				{/if}

				<!-- Trails Section -->
				{#if adventure.trails && adventure.trails.length > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-6">🥾 {$t('adventures.trails')}</h2>
							<div class="grid gap-4">
								{#each adventure.trails as trail}
									<TrailCard
										{trail}
										measurementSystem={data.user?.measurement_system || 'metric'}
									/>
								{/each}
							</div>
						</div>
					</div>
				{/if}

				<!-- Visits Timeline -->
				{#if adventure.visits.length > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-6">🎯 {$t('adventures.visits')}</h2>
							<div class="space-y-4">
								{#each adventure.visits as visit, index}
									{@const visitDate = visitDateKey(visit.start_date)}
									<div class="flex gap-4">
										<div class="flex flex-col items-center">
											<div class="w-4 h-4 bg-primary rounded-full"></div>
											{#if index < adventure.visits.length - 1}
												<div class="w-0.5 bg-primary/30 h-full min-h-12"></div>
											{/if}
										</div>
										<div class="flex-1 pb-4">
											<div class="card bg-base-100 shadow-sm">
												<div class="card-body p-4">
													<div class="flex gap-2">
														<div class="flex-1 min-w-0">
															{#if isVisitAllDay(visit.start_date, visit.end_date)}
																<div class="flex items-center gap-2 mb-2">
																	<span class="badge badge-primary">All Day</span>
																	<span class="font-semibold">
																		{visit.start_date ? visit.start_date.split('T')[0] : ''} – {visit.end_date
																			? visit.end_date.split('T')[0]
																			: ''}
																	</span>
																</div>
															{:else}
																<div class="space-y-2">
																	<div class="flex items-center gap-2">
																		<span class="badge badge-primary"
																			>🕓 {$t('adventures.timed')}</span
																		>
																		{#if visit.timezone}
																			<span class="badge badge-outline">{visit.timezone}</span>
																		{/if}
																	</div>
																	<div class="text-sm">
																		{#if visit.timezone}
																			<strong>{$t('adventures.start')}:</strong>
																			{DateTime.fromISO(visit.start_date, { zone: 'utc' })
																				.setZone(visit.timezone)
																				.toLocaleString(DateTime.DATETIME_MED)}<br />
																			<strong>{$t('adventures.end')}:</strong>
																			{DateTime.fromISO(visit.end_date, { zone: 'utc' })
																				.setZone(visit.timezone)
																				.toLocaleString(DateTime.DATETIME_MED)}
																		{:else}
																			<strong>Start:</strong>
																			{DateTime.fromISO(visit.start_date).toLocaleString(
																				DateTime.DATETIME_MED
																			)}<br />
																			<strong>End:</strong>
																			{DateTime.fromISO(visit.end_date).toLocaleString(
																				DateTime.DATETIME_MED
																			)}
																		{/if}
																	</div>
																</div>
															{/if}
															{#if visit.notes}
																<div class="mt-3 p-3 bg-base-200 rounded-lg">
																	<p class="text-sm italic">"{visit.notes}"</p>
																</div>
															{/if}

															<!-- Activities Section -->
															{#if visit.activities && visit.activities.length > 0}
																<div class="mt-4">
																	<h4 class="font-semibold mb-3 flex items-center gap-2">
																		🏃‍♂️ Activities ({visit.activities.length})
																	</h4>
																	<div class="space-y-3">
																		{#each visit.activities as activity}
																			<ActivityCard
																				{activity}
																				readOnly={true}
																				trails={adventure.trails}
																				{visit}
																				measurementSystem={data.user?.measurement_system ||
																					'metric'}
																			/>
																		{/each}
																	</div>
																</div>
															{/if}
														</div>

														{#if visitDate && adventure.latitude && adventure.longitude}
															<div class="shrink-0 self-start pt-0.5">
																{#if visitSunriseSunset[visitDate]}
																	{@const sunriseSunset = visitSunriseSunset[visitDate]}
																	<div
																		class="tooltip tooltip-left"
																		data-tip="{$t(
																			'adventures.sunrise'
																		)}: {sunriseSunset.sunrise} • {$t(
																			'adventures.sunset'
																		)}: {sunriseSunset.sunset}"
																	>
																		<button
																			class="btn btn-circle btn-ghost btn-sm text-warning"
																			type="button"
																			aria-label="{$t(
																				'adventures.sunrise'
																			)}: {sunriseSunset.sunrise}, {$t(
																				'adventures.sunset'
																			)}: {sunriseSunset.sunset}"
																		>
																			<WeatherSunset class="w-5 h-5" />
																		</button>
																	</div>
																{:else if sunriseSunsetLoading[visitDate]}
																	<button
																		class="btn btn-circle btn-ghost btn-sm"
																		type="button"
																		disabled
																		aria-label={$t('adventures.loading_sunrise_sunset')}
																	>
																		<span class="loading loading-spinner loading-xs"></span>
																	</button>
																{:else}
																	<div
																		class="tooltip tooltip-left"
																		data-tip={$t('adventures.show_sunrise_sunset')}
																	>
																		<button
																			class="btn btn-circle btn-ghost btn-sm opacity-60 hover:opacity-100"
																			type="button"
																			aria-label={$t('adventures.show_sunrise_sunset')}
																			onclick={() => loadSunriseSunsetForDate(visitDate)}
																		>
																			<WeatherSunset class="w-5 h-5" />
																		</button>
																	</div>
																{/if}
															</div>
														{/if}
													</div>
												</div>
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					</div>
				{/if}

				<!-- Map Section -->
				{#if (adventure.longitude && adventure.latitude) || hasAttachmentGeojson(adventure) || hasActivityGeojson(adventure)}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">🗺️ {$t('adventures.location')}</h2>

							{#if adventure.longitude && adventure.latitude}
								<!-- Compact Coordinates Card -->
								<div
									class="card bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg mb-4 border border-primary/10"
								>
									<div class="card-body p-4">
										<div class="flex items-center justify-between mb-3">
											<h3 class="text-lg font-bold flex items-center gap-2">
												🎯 {$t('adventures.coordinates')}
											</h3>
										</div>

										<div class="grid grid-cols-2 gap-3 mb-4">
											<div class="text-center p-2 bg-base-200/70 rounded-sm border border-primary/10">
												<div class="text-xs text-primary/70 uppercase tracking-wide">
													{$t('adventures.latitude')}
												</div>
												<div class="text-lg font-bold text-primary">{adventure.latitude}°</div>
											</div>
											<div
												class="text-center p-2 bg-base-200/70 rounded-sm border border-secondary/10"
											>
												<div class="text-xs text-secondary/70 uppercase tracking-wide">
													{$t('adventures.longitude')}
												</div>
												<div class="text-lg font-bold text-secondary">{adventure.longitude}°</div>
											</div>
										</div>

										<!-- Location Info (individual clickable items) -->
										{#if adventure.city || adventure.region || adventure.country}
											<div class="flex flex-wrap justify-center gap-2 mb-4">
												{#if adventure.city}
													<button
														class="btn btn-xs btn-outline hover:btn-info"
														onclick={navigateToWorldTravelRegion}
													>
														🏙️ {adventure.city.name}
													</button>
												{/if}
												{#if adventure.region}
													<button
														class="btn btn-xs btn-outline hover:btn-warning"
														onclick={navigateToWorldTravelRegion}
													>
														🗺️ {adventure.region.name}
													</button>
												{/if}
												{#if adventure.country}
													<button
														class="btn btn-xs btn-outline hover:btn-success"
														onclick={navigateToWorldTravelCountry}
													>
														{#if adventure.country.flag_url}
															<img
																src={adventure.country.flag_url}
																alt={adventure.country.name}
																class="w-4 h-3 rounded-sm"
															/>
														{:else}
															🌎
														{/if}
														{adventure.country.name}
													</button>
												{/if}
											</div>
										{/if}

										<!-- External Maps Links -->
										<ExternalMapLinks
											className="mb-3"
											placeName={adventure.name}
											latitude={adventure.latitude}
											longitude={adventure.longitude}
										/>

										<!-- Quick Copy Actions -->
										<div class="flex gap-2">
											<button
												class="btn btn-xs btn-ghost flex-1 text-xs"
												onclick={copyAdventureCoordinates}
											>
												📋 {$t('adventures.copy_coordinates')}
											</button>
											<button
												class="btn btn-xs btn-ghost flex-1 text-xs"
												onclick={copyAdventureGoogleMapsLink}
											>
												🔗 {$t('adventures.copy_link')}
											</button>
										</div>
									</div>
								</div>
							{/if}

							<div class="rounded-lg overflow-hidden shadow-lg">
								<FullMap
									bind:basemapType={mapBasemapType}
									mapClass="w-full h-96"
									center={[adventure.longitude || 0, adventure.latitude || 0]}
									zoom={adventure.longitude ? 12 : 1}
								>
									{#snippet overlayControls({ map, fullscreenTarget })}
																		<div
											
											
											
											class="pointer-events-none absolute inset-0 z-20"
										>
											<MapTrackLayerControls
												bind:showActivities={showActivityTracks}
												bind:showTrails={showTrailTracks}
												bind:showImagePins
												hasActivities={adventure ? hasActivityGeojson(adventure) : false}
												hasTrails={adventure ? hasTrailGeojson(adventure) : false}
												{hasImagePins}
											/>
											<MapFloatingControls
												{map}
												{fullscreenTarget}
												bind:basemapType={mapBasemapType}
											/>
										</div>
																	{/snippet}

									<!-- Activity GPS tracks -->
									{#if showActivityTracks}
										{#each adventure.visits as visit}
											{#each visit.activities as activity}
												{#if activity.geojson}
													<GeoJSON data={activity.geojson}>
														<LineLayer
															paint={{
																'line-color': getActivityColor(activity.sport_type),
																'line-width': 3,
																'line-opacity': 0.8
															}}
														/>
													</GeoJSON>
												{/if}
											{/each}
										{/each}
									{/if}

									{#each adventure.attachments as attachment}
										{#if attachment.geojson}
											<GeoJSON data={attachment.geojson}>
												<LineLayer
													paint={{
														'line-color': '#00FF00',
														'line-width': 2,
														'line-opacity': 0.6
													}}
												/>
											</GeoJSON>
										{/if}
									{/each}

									{#if showTrailTracks}
										{#each adventure.trails as trail}
											{#if trail.geojson}
												<GeoJSON data={trail.geojson}>
													<LineLayer
														paint={{
															'line-color': '#a855f7',
															'line-width': 3,
															'line-opacity': 0.85
														}}
													/>
												</GeoJSON>
											{/if}
										{/each}
									{/if}

									{#if adventure.longitude && adventure.latitude}
										<DefaultMarker lngLat={{ lng: adventure.longitude, lat: adventure.latitude }}>
											<Popup openOn="click" offset={[0, -10]}>
												<div class="p-2">
													<div class="text-lg font-bold text-black mb-1">{adventure.name}</div>
													<p class="font-semibold text-black text-sm mb-2">
														{adventure.category?.display_name + ' ' + adventure.category?.icon}
													</p>
													{#if adventure.visits.length > 0}
														<div class="text-xs text-black">
															{adventure.visits.length}
															{$t('adventures.visit')}{adventure.visits.length !== 1 ? 's' : ''}
														</div>
													{/if}
												</div>
											</Popup>
										</DefaultMarker>
									{/if}

									<MapImagePinLayer geoJson={imagePinGeoJson} visible={showImagePins} />
								</FullMap>
							</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- Right Column - Sidebar -->
			<div class="space-y-4 sm:space-y-6">
				<!-- Quick Info Card -->
				<div class="card bg-base-200 shadow-xl">
					<div class="card-body">
						<h3 class="card-title text-lg mb-4">ℹ️ {$t('adventures.basic_information')}</h3>
						<div class="space-y-3">
							{#if adventurePriceLabel}
								<div class="flex items-start gap-3">
									<CashMultiple class="w-5 h-5 text-primary mt-1 shrink-0" />
									<div>
										<div class="text-sm opacity-70 mb-0.5">{$t('adventures.price')}</div>
										<div class="text-base font-semibold">{adventurePriceLabel}</div>
									</div>
								</div>
							{/if}
							{#if adventure.tags && adventure.tags?.length > 0}
								<div>
									<div class="text-sm opacity-70 mb-1">{$t('adventures.tags')}</div>
									<div class="flex flex-wrap gap-1">
										{#each adventure.tags as activity}
											<span class="badge badge-sm badge-outline">{activity}</span>
										{/each}
									</div>
								</div>
							{/if}
							{#if adventure.link}
								<div>
									<div class="text-sm opacity-70 mb-1">{$t('adventures.link')}</div>
									<a
										href={adventure.link}
										class="link link-primary text-sm break-all"
										target="_blank"
									>
										{adventure.link.length > 30
											? `${adventure.link.slice(0, 30)}...`
											: adventure.link}
									</a>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Activity Summary -->
				{#if getTotalActivities(adventure) > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">🏃‍♂️ Activity Summary</h3>
							<div class="space-y-2">
								<div class="stat">
									<div class="stat-title">Total Activities</div>
									<div class="stat-value text-2xl">{getTotalActivities(adventure)}</div>
								</div>
								{#if getTotalDistance(adventure) > 0}
									<div class="stat">
										<div class="stat-title">Total Distance</div>
										<div class="stat-value text-xl">
											{getTotalDistance(adventure).toFixed(1)}
											{#if measurementSystem === 'imperial'}mi
											{:else}km{/if}
										</div>
									</div>
								{/if}
								{#if getTotalElevationGain(adventure) > 0}
									<div class="stat">
										<div class="stat-title">Total Elevation</div>
										<div class="stat-value text-xl">
											{getTotalElevationGain(adventure).toFixed(0)}
											{#if measurementSystem === 'imperial'}ft
											{:else}m{/if}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>
				{/if}

				<!-- Attachments -->
				{#if adventure.attachments && adventure.attachments.length > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">
								📎 {$t('adventures.attachments')}
								<div class="tooltip" data-tip={$t('adventures.gpx_tip')}>
									<LightbulbOn class="w-4 h-4 opacity-60" />
								</div>
							</h3>
							<div class="space-y-2">
								{#each adventure.attachments as attachment}
									<AttachmentCard {attachment} />
								{/each}
							</div>
						</div>
					</div>
				{/if}

				<!-- Additional Images -->
				{#if adventure.images}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">🖼️ {$t('adventures.images')}</h3>
							<div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
								{#each adventure.images as image, index}
									<ImageFrame source={image.source} showSourceBadge className="relative group">
										<div
											class="aspect-square bg-cover bg-center rounded-lg cursor-pointer transition-transform duration-200 group-hover:scale-105"
											style="background-image: url({image.image})"
											onclick={() => openImageModal(index)}
											onkeydown={(e) => e.key === 'Enter' && openImageModal(index)}
											role="button"
											tabindex="0"
										></div>
										{#snippet overlays()}
																				<div >
												{#if image.is_primary}
													<div class="absolute top-1 right-1">
														<span class="badge badge-primary badge-xs">{$t('settings.primary')}</span>
													</div>
												{/if}
											</div>
																			{/snippet}
									</ImageFrame>
								{/each}
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<svelte:head>
	<title>
		{data.props.adventure && data.props.adventure.name
			? `${data.props.adventure.name}`
			: 'Adventure'}
	</title>
	{#if data.shareMeta}
		<meta name="description" content={data.shareMeta.description} />
		<meta property="og:title" content={data.shareMeta.title} />
		<meta property="og:description" content={data.shareMeta.description} />
		<meta property="og:image" content={data.shareMeta.imageUrl} />
		<meta property="og:url" content={data.shareMeta.pageUrl} />
		<meta property="og:type" content="website" />
		<meta name="twitter:card" content="summary_large_image" />
		<meta name="twitter:title" content={data.shareMeta.title} />
		<meta name="twitter:description" content={data.shareMeta.description} />
		<meta name="twitter:image" content={data.shareMeta.imageUrl} />
	{:else}
		<meta name="description" content="Explore the world and add countries to your visited list!" />
	{/if}
</svelte:head>
