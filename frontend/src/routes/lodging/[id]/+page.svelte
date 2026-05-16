<script lang="ts">
	import type { Lodging } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';
	import FullMap from '$lib/components/map/FullMap.svelte';
	import { DefaultMarker, Popup } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import { DateTime } from 'luxon';

	import ClipboardList from '~icons/mdi/clipboard-list';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import AttachmentCard from '$lib/components/cards/AttachmentCard.svelte';
	import { normalizeBasemapType, isAllDay, LODGING_TYPES_ICONS } from '$lib';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import CalendarRange from '~icons/mdi/calendar-range';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import OpenInNew from '~icons/mdi/open-in-new';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import CardAccountDetails from '~icons/mdi/card-account-details';
	import CardCarousel from '$lib/components/CardCarousel.svelte';
	import { formatDateInTimezone, formatAllDayDate } from '$lib/dateUtils';
	import LodgingModal from '$lib/components/lodging/LodgingModal.svelte';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '$lib/money';
	import ExternalMapLinks from '$lib/components/shared/ExternalMapLinks.svelte';

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	export let data: PageData;
	console.log(data);

	let lodging: Lodging;
	let currentSlide = 0;

	function goToSlide(index: number) {
		currentSlide = index;
	}

	let notFound: boolean = false;
	let lodging_images: { image: string; lodging: Lodging | null }[] = [];
	let modalInitialIndex: number = 0;
	let isImageModalOpen: boolean = false;
	let isEditModalOpen: boolean = false;
	let localStayWindow: string | null = null;
	let showLocalStayTime: boolean = false;

	$: lodgingPriceLabel = lodging
		? formatMoney(
				toMoneyValue(
					lodging.price,
					lodging.price_currency,
					data.user?.default_currency || DEFAULT_CURRENCY
				)
			)
		: null;

	function getLodgingIcon(type: string) {
		if (type in LODGING_TYPES_ICONS) {
			return LODGING_TYPES_ICONS[type as keyof typeof LODGING_TYPES_ICONS];
		} else {
			return '🏨';
		}
	}

	function renderStars(rating: number) {
		const stars = [];
		for (let i = 1; i <= 5; i++) {
			stars.push(i <= rating);
		}
		return stars;
	}

	const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';
	const getTimezoneLabel = (zone?: string | null) => zone ?? localTimeZone;
	const getTimezoneTip = (zone?: string | null) => {
		const label = getTimezoneLabel(zone);
		return label === localTimeZone
			? null
			: `${$t('adventures.trip_timezone') ?? 'Trip TZ'}: ${label}. ${
					$t('adventures.your_time') ?? 'Your time'
				}: ${localTimeZone}.`;
	};
	const shouldShowStayBadge = (zone?: string | null) =>
		!!zone && getTimezoneLabel(zone) !== localTimeZone;

	function formatLocalStayWindow(
		checkIn: string | null,
		checkOut: string | null,
		timezone: string | null
	): string | null {
		if (!checkIn && !checkOut) return null;

		const formatLocal = (dateStr: string | null) => {
			if (!dateStr || isAllDay(dateStr)) return null;
			const dt = DateTime.fromISO(dateStr, { zone: timezone ?? 'UTC' });
			if (!dt.isValid) return null;
			return dt.setZone(localTimeZone).toLocaleString(DateTime.DATETIME_MED);
		};

		const inLocal = formatLocal(checkIn);
		const outLocal = formatLocal(checkOut);

		if (!inLocal && !outLocal) return null;
		if (inLocal && outLocal) return `${inLocal} → ${outLocal}`;
		return inLocal ?? outLocal ?? null;
	}

	const primaryStayTimezone = (timezone: string | null) => timezone;

	onMount(async () => {
		if (data.props.lodging) {
			lodging = data.props.lodging;
			lodging.images.sort((a, b) => {
				if (a.is_primary && !b.is_primary) {
					return -1;
				} else if (!a.is_primary && b.is_primary) {
					return 1;
				} else {
					return 0;
				}
			});
		} else {
			notFound = true;
		}
	});

	function closeImageModal() {
		isImageModalOpen = false;
	}

	function openImageModal(imageIndex: number) {
		lodging_images = lodging.images.map((img) => ({
			image: img.image,
			lodging: lodging
		}));
		modalInitialIndex = imageIndex;
		isImageModalOpen = true;
	}

	function calculateNights(checkIn: string | null, checkOut: string | null): number | null {
		if (!checkIn || !checkOut) return null;

		const start = DateTime.fromISO(checkIn);
		const end = DateTime.fromISO(checkOut);

		if (!start.isValid || !end.isValid) return null;

		return Math.ceil(end.diff(start, 'days').days);
	}

	$: localStayWindow = lodging
		? formatLocalStayWindow(lodging.check_in, lodging.check_out, lodging.timezone)
		: null;

	$: showLocalStayTime = Boolean(
		localStayWindow && primaryStayTimezone(lodging?.timezone ?? null) !== localTimeZone
	);
</script>

{#if notFound}
	<div class="hero min-h-screen bg-gradient-to-br from-base-200 to-base-300 overflow-x-hidden">
		<div class="hero-content text-center">
			<div class="max-w-md">
				<img src={Lost} alt="Lost" class="w-64 mx-auto mb-8 opacity-80" />
				<h1 class="text-5xl font-bold text-primary mb-4">{$t('adventures.lodging_not_found')}</h1>
				<p class="text-lg opacity-70 mb-8">{$t('adventures.location_not_found_desc')}</p>
				<button class="btn btn-primary btn-lg" on:click={() => goto('/')}>
					{$t('adventures.homepage')}
				</button>
			</div>
		</div>
	</div>
{/if}

{#if isEditModalOpen}
	<LodgingModal
		on:close={() => (isEditModalOpen = false)}
		user={data.user}
		lodgingToEdit={lodging}
		bind:lodging
	/>
{/if}

{#if isImageModalOpen}
	<ImageDisplayModal
		images={lodging.images}
		initialIndex={modalInitialIndex}
		location={lodging.location ?? ''}
		on:close={closeImageModal}
	/>
{/if}

{#if !lodging && !notFound}
	<div class="hero min-h-screen overflow-x-hidden">
		<div class="hero-content">
			<span class="loading loading-spinner w-24 h-24 text-primary"></span>
		</div>
	</div>
{/if}

{#if lodging}
	{#if data.user?.uuid && lodging.user && data.user.uuid === lodging.user}
		<div class="fixed bottom-6 right-6 z-50">
			<button
				class="btn btn-primary btn-circle w-16 h-16 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-110"
				on:click={() => (isEditModalOpen = true)}
			>
				<ClipboardList class="w-8 h-8" />
			</button>
		</div>
	{/if}

	<!-- Hero Section -->
	<div class="relative">
		<div
			class="hero min-h-[60vh] relative overflow-hidden"
			class:min-h-[30vh]={!lodging.images || lodging.images.length === 0}
		>
			<!-- Background: Images or Gradient -->
			{#if lodging.images && lodging.images.length > 0}
				<div class="hero-overlay bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
				{#each lodging.images as image, i}
					<div
						class="absolute inset-0 transition-opacity duration-500"
						class:opacity-100={i === currentSlide}
						class:opacity-0={i !== currentSlide}
					>
						<button
							class="w-full h-full p-0 bg-transparent border-0"
							on:click={() => openImageModal(i)}
							aria-label={`View full image of ${lodging.name}`}
						>
							<img src={image.image} class="w-full h-full object-cover" alt={lodging.name} />
						</button>
					</div>
				{/each}
			{:else}
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 to-secondary/20"></div>
			{/if}

			<!-- Content -->
			<div
				class="hero-content relative z-10 text-center"
				class:text-white={lodging.images?.length > 0}
			>
				<div class="max-w-4xl">
					<div class="flex justify-center items-center gap-3 mb-4">
						<span class="text-5xl">{getLodgingIcon(lodging.type)}</span>
						<h1 class="text-6xl font-bold drop-shadow-lg">{lodging.name}</h1>
					</div>

					<!-- Rating -->
					{#if lodging.rating !== undefined && lodging.rating !== null}
						<div class="flex justify-center mb-6">
							<div class="rating rating-lg">
								{#each Array.from({ length: 5 }, (_, i) => i + 1) as star}
									<input
										type="radio"
										name="rating-hero"
										class="mask mask-star-2 bg-warning"
										checked={star <= lodging.rating}
										disabled
									/>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Quick Info Badges -->
					<div class="flex flex-wrap justify-center gap-4 mb-6">
						{#if lodging.type}
							<div class="badge badge-lg badge-primary font-semibold px-4 py-3">
								{$t(`lodging.${lodging.type}`)}
							</div>
						{/if}
						{#if lodging.location}
							<div class="badge badge-lg badge-secondary font-semibold px-4 py-3">
								📍 {lodging.location}
							</div>
						{/if}
						{#if lodging.is_public}
							<div class="badge badge-lg badge-accent font-semibold px-4 py-3">
								👁️ {$t('adventures.public')}
							</div>
						{:else}
							<div class="badge badge-lg badge-ghost font-semibold px-4 py-3">
								🔒 {$t('adventures.private')}
							</div>
						{/if}
					</div>

					<!-- Image Navigation (only shown when multiple images exist) -->
					{#if lodging.images && lodging.images.length > 1}
						<div class="w-full max-w-md mx-auto">
							<!-- Navigation arrows and current position -->
							<div class="flex items-center justify-center gap-4 mb-3">
								<button
									on:click={() =>
										goToSlide(currentSlide > 0 ? currentSlide - 1 : lodging.images.length - 1)}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.previous_image')}
								>
									❮
								</button>

								<div class="text-sm font-medium bg-black/50 px-3 py-1 rounded-full">
									{currentSlide + 1} / {lodging.images.length}
								</div>

								<button
									on:click={() =>
										goToSlide(currentSlide < lodging.images.length - 1 ? currentSlide + 1 : 0)}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.next_image')}
								>
									❯
								</button>
							</div>

							<!-- Dot navigation -->
							{#if lodging.images.length <= 12}
								<div class="flex justify-center gap-2 flex-wrap">
									{#each lodging.images as _, i}
										<button
											on:click={() => goToSlide(i)}
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
				<!-- Description Card -->
				{#if lodging.description}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">📝 {$t('adventures.description')}</h2>
							<article class="prose max-w-none">
								{@html DOMPurify.sanitize(renderMarkdown(lodging.description))}
							</article>
						</div>
					</div>
				{/if}

				<!-- Map Section -->
				{#if lodging.latitude && lodging.longitude}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">🗺️ {$t('adventures.lodging')}</h2>
							<div class="rounded-lg overflow-hidden shadow-lg">
								<FullMap
									basemapType={normalizeBasemapType(data.user?.map_style)}
									mapClass="w-full h-96"
									standardControls
									center={[lodging.longitude, lodging.latitude]}
									zoom={13}
								>
									<DefaultMarker lngLat={[lodging.longitude, lodging.latitude]}>
										<Popup openOn="click" offset={[0, -10]}>
											<div class="p-2">
												<div class="text-lg font-bold text-black mb-1">{lodging.name}</div>
												<p class="font-semibold text-black text-sm mb-2">
													{$t(`lodging.${lodging.type}`)}
													{getLodgingIcon(lodging.type)}
												</p>
												{#if lodging.rating}
													<div class="flex items-center gap-1 mb-2">
														{#each renderStars(lodging.rating) as filled}
															{#if filled}
																<Star class="w-4 h-4 text-warning fill-current" />
															{:else}
																<StarOutline class="w-4 h-4 text-gray-400" />
															{/if}
														{/each}
														<span class="text-xs text-black ml-1">({lodging.rating}/5)</span>
													</div>
												{/if}
												{#if lodging.location}
													<div class="text-xs text-black">
														📍 {lodging.location}
													</div>
												{/if}
											</div>
										</Popup>
									</DefaultMarker>
								</FullMap>
							</div>
							{#if lodging.location}
								<ExternalMapLinks
									className="mb-3"
									placeName={lodging.name}
									latitude={lodging.latitude}
									longitude={lodging.longitude}
								/>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<!-- Right Column - Sidebar -->
			<div class="space-y-4 sm:space-y-6">
				<!-- Quick Info Card -->
				<div class="card bg-base-200 shadow-xl">
					<div class="card-body">
						<h2 class="card-title text-xl mb-4">ℹ️ {$t('adventures.details')}</h2>
						<div class="space-y-4">
							<!-- Check-in/Check-out -->
							{#if lodging.check_in || lodging.check_out}
								<div class="flex items-start gap-3">
									<CalendarRange class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div class="w-full space-y-3">
										{#if lodging.check_in}
											<div class="flex items-start justify-between gap-3 text-sm">
												<div class="space-y-1">
													<p class="text-xs uppercase tracking-wide opacity-60">
														{$t('adventures.check_in') ?? 'Check-in'}
													</p>
													<p class="text-base font-semibold">
														{#if isAllDay(lodging.check_in)}
															{formatAllDayDate(lodging.check_in)}
														{:else}
															{formatDateInTimezone(lodging.check_in, lodging.timezone)}
														{/if}
													</p>
												</div>
												{#if lodging.check_in && !isAllDay(lodging.check_in)}
													<span
														class="badge badge-ghost badge-xs"
														class:tooltip={Boolean(getTimezoneTip(lodging.timezone))}
														data-tip={getTimezoneTip(lodging.timezone) ?? undefined}
													>
														{#if shouldShowStayBadge(lodging.timezone)}
															{getTimezoneLabel(lodging.timezone)}
														{:else}
															{$t('adventures.local') ?? 'Local'}
														{/if}
													</span>
												{/if}
											</div>
										{/if}

										{#if lodging.check_out}
											<div class="flex items-start justify-between gap-3 text-sm">
												<div class="space-y-1">
													<p class="text-xs uppercase tracking-wide opacity-60">
														{$t('adventures.check_out') ?? 'Check-out'}
													</p>
													<p class="text-base font-semibold">
														{#if isAllDay(lodging.check_out)}
															{formatAllDayDate(lodging.check_out)}
														{:else}
															{formatDateInTimezone(lodging.check_out, lodging.timezone)}
														{/if}
													</p>
												</div>
												{#if lodging.check_out && !isAllDay(lodging.check_out)}
													<span
														class="badge badge-ghost badge-xs"
														class:tooltip={Boolean(getTimezoneTip(lodging.timezone))}
														data-tip={getTimezoneTip(lodging.timezone) ?? undefined}
													>
														{#if shouldShowStayBadge(lodging.timezone)}
															{getTimezoneLabel(lodging.timezone)}
														{:else}
															{$t('adventures.local') ?? 'Local'}
														{/if}
													</span>
												{/if}
											</div>
										{/if}

										{#if showLocalStayTime}
											<p class="text-sm text-base-content/70">
												{$t('adventures.local_time') ?? 'Local time'}: {localStayWindow}
											</p>
										{/if}

										{#if calculateNights(lodging.check_in, lodging.check_out)}
											<p class="text-sm opacity-70">
												{calculateNights(lodging.check_in, lodging.check_out)}
												{$t('adventures.nights')}
											</p>
										{/if}
									</div>
								</div>
							{/if}

							<!-- Type -->
							<div class="flex items-start gap-3">
								<span class="text-xl mt-1 flex-shrink-0">{getLodgingIcon(lodging.type)}</span>
								<div>
									<p class="font-semibold text-sm opacity-70">{$t('transportation.type')}</p>
									<p class="text-base">{$t(`lodging.${lodging.type}`)}</p>
								</div>
							</div>

							<!-- Reservation Number -->
							{#if lodging.reservation_number}
								<div class="flex items-start gap-3">
									<CardAccountDetails class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div>
										<p class="font-semibold text-sm opacity-70">{$t('adventures.reservation')}</p>
										<p class="text-base font-mono">{lodging.reservation_number}</p>
									</div>
								</div>
							{/if}

							<!-- Price -->
							{#if lodgingPriceLabel}
								<div class="flex items-start gap-3">
									<CashMultiple class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div>
										<p class="font-semibold text-sm opacity-70">{$t('adventures.price')}</p>
										<p class="text-base font-semibold">{lodgingPriceLabel}</p>
									</div>
								</div>
							{/if}

							<!-- Link -->
							{#if lodging.link}
								<div class="flex items-start gap-3">
									<OpenInNew class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div class="flex-1">
										<p class="font-semibold text-sm opacity-70 mb-1">{$t('adventures.link')}</p>
										<a
											href={lodging.link}
											target="_blank"
											rel="noopener noreferrer"
											class="link link-primary text-base break-all"
										>
											{lodging.link}
										</a>
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Additional Images -->
				{#if lodging.images && lodging.images.length > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-xl mb-4">🖼️ {$t('adventures.images')}</h2>
							<div class="grid grid-cols-2 gap-2">
								{#each lodging.images as image, i}
									<button
										class="aspect-square rounded-lg overflow-hidden hover:opacity-80 transition-opacity"
										on:click={() => openImageModal(i)}
									>
										<img
											src={image.image}
											alt={`${lodging.name} - ${i + 1}`}
											class="w-full h-full object-cover"
										/>
									</button>
								{/each}
							</div>
						</div>
					</div>
				{/if}

				<!-- Attachments -->
				{#if lodging.attachments && lodging.attachments.length > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-xl mb-4">📎 {$t('adventures.attachments')}</h2>
							<div class="space-y-2">
								{#each lodging.attachments as attachment}
									<AttachmentCard {attachment} />
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
		{data.props.lodging && data.props.lodging.name ? `${data.props.lodging.name}` : 'Lodging'}
	</title>
	<meta name="description" content="View lodging details" />
</svelte:head>
