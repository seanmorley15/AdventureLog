<script lang="ts">
	import type { AdditionalLodging } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import { DefaultMarker, MapLibre, Popup } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	// @ts-ignore
	import { DateTime } from 'luxon';

	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import AttachmentCard from '$lib/components/cards/AttachmentCard.svelte';
	import { getBasemapUrl, isAllDay } from '$lib';
	import { getLodgingIcon } from '$lib/stores/entityTypes';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import CalendarRange from '~icons/mdi/calendar-range';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import CardAccountDetails from '~icons/mdi/card-account-details';
	import OpenInNew from '~icons/mdi/open-in-new';
	import { formatDateInTimezone, formatAllDayDate } from '$lib/dateUtils';
	import LodgingModal from '$lib/components/lodging/LodgingModal.svelte';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '$lib/money';
import { fetchExchangeRates, formatConvertedPrice, ratesLoaded } from '$lib/stores/exchangeRates';
import { PriceTierBadge } from '$lib/components/shared/cards';
	import HistoryPanel from '$lib/components/HistoryPanel.svelte';

	// Shared components
	import {
		EntityNotFound,
		EntityLoading,
		EntityHeroSection,
		EntityDescriptionCard,
		EntityVisitsTimeline,
		EntityEditFab,
		EntityAttachmentsCard,
		EntityImagesCard,
		sortImagesByPrimary,
		sortVisitsChronologically,
		getTotalActivities,
		getTotalDistance,
		getTotalElevationGain,
		renderStars
	} from '$lib/components/shared/detail';

	export let data: PageData;

	let lodging: AdditionalLodging;
	let notFound: boolean = false;
	let modalInitialIndex: number = 0;
	let isImageModalOpen: boolean = false;
	let isEditModalOpen: boolean = false;
	let ratingRefreshKey: number = 0;
	let history: any[] = [];

	// Note: is_visited is computed by the backend (VisitStatusMixin)
	// It checks: visit date is in the past AND (in collab mode) only current user's visits
	$: userHasVisited = lodging?.is_visited ?? false;

	$: lodgingPriceLabel = lodging
		? formatMoney(
				toMoneyValue(
					lodging.price,
					lodging.price_currency,
					data.user?.default_currency || DEFAULT_CURRENCY
				)
			)
		: null;

	$: canEdit = (data.user?.uuid && lodging?.user && data.user.uuid === lodging.user) ||
		(data.collaborativeMode && lodging?.is_public);

	// Build hero badges
	$: heroBadges = lodging ? buildHeroBadges(lodging) : [];

	function buildHeroBadges(l: Lodging) {
		const badges: { label: string; class: string; href?: string }[] = [];

		if (l.type) {
			badges.push({
				label: $t(`lodging.${l.type}`),
				class: 'badge-primary'
			});
		}
		if (l.location) {
			badges.push({
				label: `📍 ${l.location}`,
				class: 'badge-secondary'
			});
		}
		if (l.visits && l.visits.length > 0) {
			badges.push({
				label: `🎯 ${l.visits.length} ${l.visits.length === 1 ? $t('adventures.visit') : $t('adventures.visits')}`,
				class: 'badge-accent'
			});
		}
		if (userHasVisited) {
			badges.push({
				label: `✅ ${$t('adventures.visited')}`,
				class: 'badge-success'
			});
		} else {
			badges.push({
				label: `⏳ ${$t('adventures.not_visited')}`,
				class: 'badge-warning'
			});
		}
		if (l.is_public) {
			badges.push({
				label: `👁️ ${$t('adventures.public')}`,
				class: 'badge-info'
			});
		} else {
			badges.push({
				label: `🔒 ${$t('adventures.private')}`,
				class: 'badge-ghost'
			});
		}

		return badges;
	}

	const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';
	const getTimezoneLabel = (zone?: string | null) => zone ?? localTimeZone;
	const getTimezoneTip = (zone?: string | null) => {
		const label = getTimezoneLabel(zone);
		return label === localTimeZone
			? null
			: `${$t('adventures.trip_timezone') ?? 'Trip TZ'}: ${label}. ${$t('adventures.your_time') ?? 'Your time'}: ${localTimeZone}.`;
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
		localStayWindow && lodging?.timezone && lodging.timezone !== localTimeZone
	);

	onMount(async () => {
		// Fetch exchange rates for currency conversion
		fetchExchangeRates();

		if (data.props.lodging) {
			lodging = data.props.lodging;
			lodging.images = sortImagesByPrimary(lodging.images || []);
			if (lodging.visits) {
				lodging.visits = sortVisitsChronologically(lodging.visits);
			}

			// Fetch history in collaborative mode
			if (data.collaborativeMode) {
				try {
					const res = await fetch(`/api/lodging/${lodging.id}/history/`);
					if (res.ok) {
						history = await res.json();
					}
				} catch (e) {
					console.error('Failed to fetch history:', e);
				}
			}
		} else {
			notFound = true;
		}
	});

	function closeImageModal() {
		isImageModalOpen = false;
	}

	function openImageModal(index: number) {
		modalInitialIndex = index;
		isImageModalOpen = true;
	}

	async function handleEditModalClose() {
		try {
			const res = await fetch(`/api/lodging/${lodging.id}`);
			if (res.ok) {
				lodging = await res.json();
				ratingRefreshKey++;
			}
		} catch (e) {
			console.error('Failed to refresh lodging:', e);
		}
		// Refresh history after save in collaborative mode
		if (data.collaborativeMode && lodging.id) {
			try {
				const res = await fetch(`/api/lodging/${lodging.id}/history/`);
				if (res.ok) {
					history = await res.json();
				}
			} catch (e) {
				console.error('Failed to refresh history:', e);
			}
		}
		isEditModalOpen = false;
	}
</script>

{#if notFound}
	<EntityNotFound title={$t('adventures.lodging_not_found')} />
{/if}

{#if isEditModalOpen}
	<LodgingModal
		on:close={handleEditModalClose}
		user={data.user}
		lodgingToEdit={lodging}
		collaborativeMode={data.collaborativeMode}
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
	<EntityLoading />
{/if}

{#if lodging}
	<EntityEditFab show={canEdit} onClick={() => (isEditModalOpen = true)} />

	<!-- Hero Section -->
	<EntityHeroSection
		name={lodging.name}
		icon={getLodgingIcon(lodging.type)}
		images={lodging.images || []}
		averageRating={lodging.average_rating}
		rating={lodging.rating}
		ratingCount={lodging.rating_count}
		{ratingRefreshKey}
		badges={heroBadges}
		on:openImage={(e) => openImageModal(e.detail)}
	/>

	<!-- Main Content -->
	<div class="container mx-auto px-2 sm:px-4 py-6 sm:py-8 max-w-7xl">
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-8">
			<!-- Left Column - Main Content -->
			<div class="lg:col-span-2 space-y-6 sm:space-y-8">
				<EntityDescriptionCard description={lodging.description} />

				<EntityVisitsTimeline
					visits={lodging.visits || []}
					measurementSystem={data.user?.measurement_system || 'metric'}
					sunTimes={lodging.sun_times || []}
					countryCurrency={lodging.country?.currency_code || null}
				/>

				<!-- Map Section -->
				{#if lodging.latitude && lodging.longitude}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">🗺️ {$t('adventures.lodging')}</h2>
							<div class="rounded-lg overflow-hidden shadow-lg">
								<MapLibre
									style={getBasemapUrl()}
									class="w-full h-96"
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
													<div class="text-xs text-black">📍 {lodging.location}</div>
												{/if}
											</div>
										</Popup>
									</DefaultMarker>
								</MapLibre>
							</div>
							{#if lodging.location}
								<div class="rounded-lg p-3 mb-3 bg-gradient-to-br from-primary/10 to-secondary/10">
									<p class="flex items-center gap-2 text-sm mb-2">
										<MapMarker class="w-4 h-4" />
										{lodging.location}
									</p>
									<div class="grid grid-cols-3 gap-2">
										<a
											class="btn btn-sm btn-outline hover:btn-neutral"
											href={`https://maps.apple.com/?q=${encodeURIComponent(lodging.location)}`}
											target="_blank"
											rel="noopener noreferrer"
										>
											🍎 Apple
										</a>
										<a
											class="btn btn-sm btn-outline hover:btn-accent"
											href={`https://maps.google.com/?q=${encodeURIComponent(lodging.location)}`}
											target="_blank"
											rel="noopener noreferrer"
										>
											🌍 Google
										</a>
										<a
											class="btn btn-sm btn-outline hover:btn-primary"
											href={`https://www.openstreetmap.org/search?query=${encodeURIComponent(lodging.location)}`}
											target="_blank"
											rel="noopener noreferrer"
										>
											🗺️ OSM
										</a>
									</div>
								</div>
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
												{calculateNights(lodging.check_in, lodging.check_out)} {$t('adventures.nights')}
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

							<!-- Tags -->
							{#if lodging.tags && lodging.tags.length > 0}
								<div>
									<p class="font-semibold text-sm opacity-70 mb-2">🏷️ {$t('adventures.tags')}</p>
									<div class="flex flex-wrap gap-1">
										{#each lodging.tags as tag}
											<span class="badge badge-sm badge-outline">{tag}</span>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Price Information -->
				{#if lodging.average_price_per_user_per_night || lodging.price_tier}
					{@const avgPrice = lodging.average_price_per_user_per_night}
					{@const userCurrency = data.user?.default_currency || DEFAULT_CURRENCY}
					{@const countryCurrency = lodging.country?.currency_code}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-3">💰 {$t('adventures.avg_price')}</h3>
							<div class="space-y-3">
								<!-- Price Tier Badge -->
								{#if lodging.price_tier}
									<div class="flex items-center gap-3">
										<PriceTierBadge priceTier={lodging.price_tier} badgeClass="badge-success badge-lg text-lg" />
										<span class="text-sm opacity-70">
											{#if lodging.price_tier.tier === 1}
												{$t('adventures.price_tier_budget')}
											{:else if lodging.price_tier.tier === 2}
												{$t('adventures.price_tier_moderate')}
											{:else if lodging.price_tier.tier === 3}
												{$t('adventures.price_tier_expensive')}
											{:else}
												{$t('adventures.price_tier_premium')}
											{/if}
											<span class="text-xs">({lodging.country?.name})</span>
										</span>
									</div>
								{/if}

								{#if avgPrice}
									<!-- Main price in country's currency (or original if no country) -->
									{#if $ratesLoaded && countryCurrency && avgPrice.currency !== countryCurrency}
										{@const countryConverted = formatConvertedPrice(avgPrice.amount, avgPrice.currency, countryCurrency)}
										{#if countryConverted}
											<div class="text-2xl font-bold text-success">
												{countryConverted}
											</div>
										{:else}
											<div class="text-2xl font-bold text-success">
												{formatMoney({ amount: avgPrice.amount, currency: avgPrice.currency })}
											</div>
										{/if}
									{:else}
										<div class="text-2xl font-bold text-success">
											{formatMoney({ amount: avgPrice.amount, currency: avgPrice.currency })}
										</div>
									{/if}
									<div class="text-sm opacity-70">
										{$t('adventures.avg_per_user_per_night')}
									</div>

									<!-- Converted price in user's currency (if different from country currency) -->
									{#if $ratesLoaded && countryCurrency && userCurrency !== countryCurrency}
										{@const userConverted = formatConvertedPrice(avgPrice.amount, avgPrice.currency, userCurrency)}
										{#if userConverted}
											<div class="text-sm text-base-content/70">
												{userConverted}
											</div>
										{/if}
									{:else if $ratesLoaded && !countryCurrency && avgPrice.currency !== userCurrency}
										{@const userConverted = formatConvertedPrice(avgPrice.amount, avgPrice.currency, userCurrency)}
										{#if userConverted}
											<div class="text-sm text-base-content/70">
												{userConverted}
											</div>
										{/if}
									{/if}

									{#if avgPrice.visit_count > 0}
										<div class="text-xs opacity-50">
											{$t('adventures.based_on_visits', { values: { count: avgPrice.visit_count } })}
										</div>
									{/if}
								{/if}
							</div>
						</div>
					</div>
				{/if}

				<!-- Activity Summary -->
				{#if getTotalActivities(lodging) > 0}
					{@const ms = data.user?.measurement_system ?? 'metric'}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">🏃‍♂️ Activity Summary</h3>
							<div class="space-y-2">
								<div class="stat">
									<div class="stat-title">Total Activities</div>
									<div class="stat-value text-2xl">{getTotalActivities(lodging)}</div>
								</div>
								{#if getTotalDistance(lodging, ms) > 0}
									<div class="stat">
										<div class="stat-title">Total Distance</div>
										<div class="stat-value text-xl">
											{getTotalDistance(lodging, ms).toFixed(1)}
											{ms === 'imperial' ? 'mi' : 'km'}
										</div>
									</div>
								{/if}
								{#if getTotalElevationGain(lodging, ms) > 0}
									<div class="stat">
										<div class="stat-title">Total Elevation</div>
										<div class="stat-value text-xl">
											{getTotalElevationGain(lodging, ms).toFixed(0)}
											{ms === 'imperial' ? 'ft' : 'm'}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>
				{/if}

				<EntityImagesCard
					images={lodging.images || []}
					showPrimaryBadge={false}
					showUserBadge={false}
					on:openImage={(e) => openImageModal(e.detail)}
				/>

				<EntityAttachmentsCard attachments={lodging.attachments || []} />

				<!-- History Panel (Collaborative Mode) -->
				{#if data.collaborativeMode && history.length > 0}
					<HistoryPanel
						{history}
						itemId={lodging.id}
						apiEndpoint="lodging"
						canRevert={true}
						on:reverted={async () => {
							const historyRes = await fetch(`/api/lodging/${lodging.id}/history/`);
							if (historyRes.ok) {
								history = await historyRes.json();
							}
							window.location.reload();
						}}
					/>
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
