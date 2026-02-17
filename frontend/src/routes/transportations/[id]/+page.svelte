<script lang="ts">
	import type { AdditionalTransportation } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import { DefaultMarker, MapLibre, Popup, GeoJSON, LineLayer } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	// @ts-ignore
	import { DateTime } from 'luxon';

	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import AttachmentCard from '$lib/components/cards/AttachmentCard.svelte';
	import { getBasemapUrl, isAllDay } from '$lib';
	import { getTransportationIcon } from '$lib/stores/entityTypes';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import CalendarRange from '~icons/mdi/calendar-range';
	import OpenInNew from '~icons/mdi/open-in-new';
	import MapMarkerDistanceIcon from '~icons/mdi/map-marker-distance';
	import CardAccountDetails from '~icons/mdi/card-account-details';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import { formatDateInTimezone, formatAllDayDate } from '$lib/dateUtils';
	import TransportationModal from '$lib/components/transportation/TransportationModal.svelte';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '$lib/money';
import { fetchExchangeRates, formatConvertedPrice, ratesLoaded } from '$lib/stores/exchangeRates';
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

	let transportation: AdditionalTransportation;
	let notFound: boolean = false;
	let mapCenter: [number, number] | null = null;
	let attachmentGeojson: any = null;
	let modalInitialIndex: number = 0;
	let isImageModalOpen: boolean = false;
	let isEditModalOpen: boolean = false;
	let localTravelWindow: string | null = null;
	let showLocalTripTime: boolean = false;
	let history: any[] = [];
	let ratingRefreshKey: number = 0;

	// Note: is_visited is computed by the backend (VisitStatusMixin)
	// It checks: visit date is in the past AND (in collab mode) only current user's visits
	$: userHasVisited = transportation?.is_visited ?? false;

	$: transportationPriceLabel = transportation
		? formatMoney(
				toMoneyValue(
					transportation.price,
					transportation.price_currency,
					data.user?.default_currency || DEFAULT_CURRENCY
				)
			)
		: null;

	$: canEdit = (data.user?.uuid && transportation?.user && data.user.uuid === transportation.user) ||
		(data.collaborativeMode && transportation?.is_public);

	// Build hero badges
	$: heroBadges = transportation ? buildHeroBadges(transportation) : [];

	function buildHeroBadges(t: Transportation) {
		const badges: { label: string; class: string; href?: string }[] = [];

		if (t.type) {
			badges.push({
				label: $t(`transportation.modes.${t.type}`),
				class: 'badge-primary'
			});
		}
		if (t.from_location) {
			badges.push({
				label: `🚩 ${t.from_location}`,
				class: 'badge-secondary'
			});
		}
		if (t.to_location) {
			badges.push({
				label: `🏁 ${t.to_location}`,
				class: 'badge-secondary'
			});
		}
		if (getRouteCodes(t)) {
			badges.push({
				label: `${getTransportationIcon(t.type)} ${getRouteCodes(t)}`,
				class: 'badge-outline'
			});
		}
		if (t.visits && t.visits.length > 0) {
			badges.push({
				label: `🎯 ${t.visits.length} ${t.visits.length === 1 ? $t('adventures.visit') : $t('adventures.visits')}`,
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
		if (t.is_public) {
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
	const shouldShowTzBadge = (zone?: string | null) =>
		!!zone && getTimezoneLabel(zone) !== localTimeZone;

	function getRouteLabel() {
		if (!transportation) return '';
		if (transportation.from_location && transportation.to_location) {
			return `${transportation.from_location} → ${transportation.to_location}`;
		}
		return transportation.from_location ?? transportation.to_location ?? '';
	}

	function calculateDuration(
		start: string | null,
		end: string | null,
		startTimezone: string | null,
		endTimezone: string | null
	): string | null {
		if (!start || !end) return null;
		const startDT = DateTime.fromISO(start, { zone: startTimezone ?? 'UTC' });
		const endDT = DateTime.fromISO(end, { zone: endTimezone ?? startTimezone ?? 'UTC' });
		if (!startDT.isValid || !endDT.isValid) return null;
		const totalMinutes = Math.round(endDT.diff(startDT, 'minutes').minutes ?? 0);
		if (totalMinutes <= 0) return null;
		const days = Math.floor(totalMinutes / (60 * 24));
		const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
		const minutes = totalMinutes % 60;
		const parts: string[] = [];
		if (days) parts.push(`${days}d`);
		if (hours) parts.push(`${hours}h`);
		if (minutes) parts.push(`${minutes}m`);
		return parts.join(' ');
	}

	function hasOriginCoordinates(item: Transportation) {
		return item.origin_latitude !== null && item.origin_longitude !== null;
	}

	function hasDestinationCoordinates(item: Transportation) {
		return item.destination_latitude !== null && item.destination_longitude !== null;
	}

	function getMapCenter(item: Transportation): [number, number] | null {
		if (hasOriginCoordinates(item)) {
			return [item.origin_longitude as number, item.origin_latitude as number];
		}
		if (hasDestinationCoordinates(item)) {
			return [item.destination_longitude as number, item.destination_latitude as number];
		}
		return null;
	}

	function getRouteCodes(item: Transportation): string | null {
		if (item.start_code && item.end_code) return `${item.start_code} → ${item.end_code}`;
		if (item.start_code) return item.start_code;
		if (item.end_code) return item.end_code;
		return null;
	}

	function formatDistance(distanceKm: number | null): string | null {
		if (distanceKm === null || distanceKm === undefined) return null;
		const ms = data.user?.measurement_system ?? 'metric';
		if (ms === 'imperial') {
			const miles = distanceKm * 0.621371;
			if (miles >= 0.1) return `${miles.toFixed(1)} mi`;
			return `${Math.round(miles * 5280)} ft`;
		} else {
			if (distanceKm >= 1) return `${distanceKm.toFixed(1)} km`;
			return `${Math.round(distanceKm * 1000)} m`;
		}
	}

	function collectAttachmentGeojson(item: Transportation) {
		if (!item.attachments || item.attachments.length === 0) return null;
		const features: any[] = [];
		for (const a of item.attachments) {
			if (a && a.geojson && a.geojson.features) {
				if (a.geojson.type === 'FeatureCollection' && Array.isArray(a.geojson.features)) {
					features.push(...a.geojson.features);
				} else if (a.geojson.type === 'Feature') {
					features.push(a.geojson);
				}
			}
		}
		if (features.length === 0) return null;
		return { type: 'FeatureCollection', features };
	}

	function formatLocalTravelWindow(
		start: string | null,
		end: string | null,
		startTimezone: string | null,
		endTimezone: string | null
	): string | null {
		if (!start && !end) return null;
		const formatLocal = (dateStr: string | null, zone: string | null) => {
			if (!dateStr || isAllDay(dateStr)) return null;
			const dt = DateTime.fromISO(dateStr, { zone: zone ?? 'UTC' });
			if (!dt.isValid) return null;
			return dt.setZone(localTimeZone).toLocaleString(DateTime.DATETIME_MED);
		};
		const startLocal = formatLocal(start, startTimezone);
		const endLocal = formatLocal(end, endTimezone ?? startTimezone);
		if (!startLocal && !endLocal) return null;
		if (startLocal && endLocal) return `${startLocal} → ${endLocal}`;
		return startLocal ?? endLocal ?? null;
	}

	const primaryTripTimezone = (startTimezone: string | null, endTimezone: string | null) =>
		startTimezone ?? endTimezone ?? null;

	$: localTravelWindow = transportation
		? formatLocalTravelWindow(
				transportation.date,
				transportation.end_date,
				transportation.start_timezone,
				transportation.end_timezone
			)
		: null;

	$: showLocalTripTime = Boolean(
		localTravelWindow &&
			primaryTripTimezone(
				transportation?.start_timezone ?? null,
				transportation?.end_timezone ?? null
			) !== localTimeZone
	);

	$: mapCenter = transportation ? getMapCenter(transportation) : null;
	$: attachmentGeojson = transportation ? collectAttachmentGeojson(transportation) : null;

	onMount(async () => {
		// Fetch exchange rates for currency conversion
		fetchExchangeRates();

		if (data.props.transportation) {
			transportation = data.props.transportation;
			transportation.images = sortImagesByPrimary(transportation.images || []);
			if (transportation.visits) {
				transportation.visits = sortVisitsChronologically(transportation.visits);
			}

			// Fetch history in collaborative mode
			if (data.collaborativeMode) {
				try {
					const res = await fetch(`/api/transportations/${transportation.id}/history/`);
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
			const res = await fetch(`/api/transportations/${transportation.id}`);
			if (res.ok) {
				transportation = await res.json();
				ratingRefreshKey++;
			}
		} catch (e) {
			console.error('Failed to refresh transportation:', e);
		}
		// Refresh history after save in collaborative mode
		if (data.collaborativeMode && transportation.id) {
			try {
				const res = await fetch(`/api/transportations/${transportation.id}/history/`);
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
	<EntityNotFound title="Transportation not found" />
{/if}

{#if isEditModalOpen}
	<TransportationModal
		on:close={handleEditModalClose}
		user={data.user}
		transportationToEdit={transportation}
		collaborativeMode={data.collaborativeMode}
	/>
{/if}

{#if isImageModalOpen}
	<ImageDisplayModal
		images={transportation.images}
		initialIndex={modalInitialIndex}
		location={getRouteLabel()}
		on:close={closeImageModal}
	/>
{/if}

{#if !transportation && !notFound}
	<EntityLoading />
{/if}

{#if transportation}
	<EntityEditFab show={canEdit} onClick={() => (isEditModalOpen = true)} />

	<!-- Hero Section -->
	<EntityHeroSection
		name={transportation.name}
		icon={getTransportationIcon(transportation.type)}
		images={transportation.images || []}
		averageRating={transportation.average_rating}
		rating={transportation.rating}
		ratingCount={transportation.rating_count}
		{ratingRefreshKey}
		badges={heroBadges}
		on:openImage={(e) => openImageModal(e.detail)}
	/>

	<!-- Main Content -->
	<div class="container mx-auto px-2 sm:px-4 py-6 sm:py-8 max-w-7xl">
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-8">
			<!-- Left Column - Main Content -->
			<div class="lg:col-span-2 space-y-6 sm:space-y-8">
				<EntityDescriptionCard description={transportation.description} />

				<EntityVisitsTimeline
					visits={transportation.visits || []}
					measurementSystem={data.user?.measurement_system || 'metric'}
					sunTimes={transportation.sun_times || []}
					countryCurrency={transportation.origin_country?.currency_code || null}
				/>

				<!-- Map Section -->
				{#if mapCenter}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">🗺️ {$t('adventures.transportation')}</h2>
							<div class="rounded-lg overflow-hidden shadow-lg">
								<MapLibre
									style={getBasemapUrl()}
									class="w-full h-96"
									standardControls
									center={mapCenter}
									zoom={13}
								>
									{#if hasOriginCoordinates(transportation)}
										<DefaultMarker
											lngLat={[
												Number(transportation.origin_longitude),
												Number(transportation.origin_latitude)
											]}
										>
											<Popup openOn="click" offset={[0, -10]}>
												<div class="p-2">
													<div class="text-lg font-bold text-black mb-1">{transportation.name}</div>
													<p class="font-semibold text-black text-sm mb-2">
														{$t('transportation.from_location')}
														{getTransportationIcon(transportation.type)}
													</p>
													{#if transportation.rating}
														<div class="flex items-center gap-1 mb-2">
															{#each renderStars(transportation.rating) as filled}
																{#if filled}
																	<Star class="w-4 h-4 text-warning fill-current" />
																{:else}
																	<StarOutline class="w-4 h-4 text-gray-400" />
																{/if}
															{/each}
															<span class="text-xs text-black ml-1">({transportation.rating}/5)</span>
														</div>
													{/if}
													{#if transportation.from_location}
														<div class="text-xs text-black">📍 {transportation.from_location}</div>
													{/if}
												</div>
											</Popup>
										</DefaultMarker>
									{/if}

									{#if hasDestinationCoordinates(transportation)}
										<DefaultMarker
											lngLat={[
												Number(transportation.destination_longitude),
												Number(transportation.destination_latitude)
											]}
										>
											<Popup openOn="click" offset={[0, -10]}>
												<div class="p-2">
													<div class="text-lg font-bold text-black mb-1">{transportation.name}</div>
													<p class="font-semibold text-black text-sm mb-2">
														{$t('transportation.to_location')}
														{getTransportationIcon(transportation.type)}
													</p>
													{#if transportation.rating}
														<div class="flex items-center gap-1 mb-2">
															{#each renderStars(transportation.rating) as filled}
																{#if filled}
																	<Star class="w-4 h-4 text-warning fill-current" />
																{:else}
																	<StarOutline class="w-4 h-4 text-gray-400" />
																{/if}
															{/each}
															<span class="text-xs text-black ml-1">({transportation.rating}/5)</span>
														</div>
													{/if}
													{#if transportation.to_location}
														<div class="text-xs text-black">📍 {transportation.to_location}</div>
													{/if}
												</div>
											</Popup>
										</DefaultMarker>
									{/if}

									{#if attachmentGeojson}
										<GeoJSON data={attachmentGeojson}>
											<LineLayer
												id="transportation-route"
												paint={{ 'line-color': '#60a5fa', 'line-width': 4, 'line-opacity': 0.9 }}
											/>
										</GeoJSON>
									{/if}
								</MapLibre>
							</div>
							{#if transportation.from_location || transportation.to_location}
								<p class="mt-4 text-base-content/70 flex items-center gap-2">
									<MapMarker class="w-5 h-5" />
									{getRouteLabel()}
								</p>

								<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
									{#if transportation.from_location}
										<div class="rounded-lg p-3 bg-gradient-to-br from-primary/10 to-secondary/10">
											<p class="flex items-center gap-2 text-sm mb-2">
												<MapMarker class="w-4 h-4" />
												{transportation.from_location}
											</p>
											<div class="grid grid-cols-3 gap-2">
												<a
													class="btn btn-sm btn-outline hover:btn-neutral"
													href={`https://maps.apple.com/?q=${encodeURIComponent(transportation.from_location)}`}
													target="_blank"
													rel="noopener noreferrer"
												>
													🍎 Apple
												</a>
												<a
													class="btn btn-sm btn-outline hover:btn-accent"
													href={`https://maps.google.com/?q=${encodeURIComponent(transportation.from_location)}`}
													target="_blank"
													rel="noopener noreferrer"
												>
													🌍 Google
												</a>
												<a
													class="btn btn-sm btn-outline hover:btn-primary"
													href={`https://www.openstreetmap.org/search?query=${encodeURIComponent(transportation.from_location)}`}
													target="_blank"
													rel="noopener noreferrer"
												>
													🗺️ OSM
												</a>
											</div>
										</div>
									{/if}

									{#if transportation.to_location}
										<div class="rounded-lg p-3 bg-gradient-to-br from-primary/10 to-secondary/10">
											<p class="flex items-center gap-2 text-sm mb-2">
												<MapMarker class="w-4 h-4" />
												{transportation.to_location}
											</p>
											<div class="grid grid-cols-3 gap-2">
												<a
													class="btn btn-sm btn-outline hover:btn-neutral"
													href={`https://maps.apple.com/?q=${encodeURIComponent(transportation.to_location)}`}
													target="_blank"
													rel="noopener noreferrer"
												>
													🍎 Apple
												</a>
												<a
													class="btn btn-sm btn-outline hover:btn-accent"
													href={`https://maps.google.com/?q=${encodeURIComponent(transportation.to_location)}`}
													target="_blank"
													rel="noopener noreferrer"
												>
													🌍 Google
												</a>
												<a
													class="btn btn-sm btn-outline hover:btn-primary"
													href={`https://www.openstreetmap.org/search?query=${encodeURIComponent(transportation.to_location)}`}
													target="_blank"
													rel="noopener noreferrer"
												>
													🗺️ OSM
												</a>
											</div>
										</div>
									{/if}
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
							<!-- Departure/Arrival -->
							{#if transportation.date || transportation.end_date}
								<div class="flex items-start gap-3">
									<CalendarRange class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div class="w-full space-y-2">
										<p class="font-semibold text-sm opacity-70">{$t('adventures.dates')}</p>
										<div class="space-y-2">
											{#if transportation.date}
												<div class="flex items-start justify-between gap-3 text-sm">
													<div class="space-y-1">
														<p class="text-xs uppercase tracking-wide opacity-60">
															{$t('adventures.start') ?? 'Start'}
														</p>
														<p class="text-base font-semibold">
															{#if isAllDay(transportation.date)}
																{formatAllDayDate(transportation.date)}
															{:else}
																{formatDateInTimezone(transportation.date, transportation.start_timezone)}
															{/if}
														</p>
													</div>
													{#if transportation.date && !isAllDay(transportation.date)}
														<span
															class="badge badge-ghost badge-xs"
															class:tooltip={Boolean(getTimezoneTip(transportation.start_timezone))}
															data-tip={getTimezoneTip(transportation.start_timezone) ?? undefined}
														>
															{#if shouldShowTzBadge(transportation.start_timezone)}
																{getTimezoneLabel(transportation.start_timezone)}
															{:else}
																{$t('adventures.local') ?? 'Local'}
															{/if}
														</span>
													{/if}
												</div>
											{/if}

											{#if transportation.end_date}
												<div class="flex items-start justify-between gap-3 text-sm">
													<div class="space-y-1">
														<p class="text-xs uppercase tracking-wide opacity-60">
															{$t('adventures.end') ?? 'End'}
														</p>
														<p class="text-base font-semibold">
															{#if isAllDay(transportation.end_date)}
																{formatAllDayDate(transportation.end_date)}
															{:else}
																{formatDateInTimezone(
																	transportation.end_date,
																	transportation.end_timezone ?? transportation.start_timezone
																)}
															{/if}
														</p>
													</div>
													{#if transportation.end_date && !isAllDay(transportation.end_date)}
														<span
															class="badge badge-ghost badge-xs"
															class:tooltip={Boolean(
																getTimezoneTip(transportation.end_timezone ?? transportation.start_timezone)
															)}
															data-tip={getTimezoneTip(transportation.end_timezone ?? transportation.start_timezone) ?? undefined}
														>
															{#if shouldShowTzBadge(transportation.end_timezone ?? transportation.start_timezone)}
																{getTimezoneLabel(transportation.end_timezone ?? transportation.start_timezone)}
															{:else}
																{$t('adventures.local') ?? 'Local'}
															{/if}
														</span>
													{/if}
												</div>
											{/if}

											{#if showLocalTripTime}
												<p class="text-sm text-base-content/70">
													{$t('adventures.local_time') ?? 'Local time'}: {localTravelWindow}
												</p>
											{/if}
										</div>
										{#if calculateDuration(transportation.date, transportation.end_date, transportation.start_timezone, transportation.end_timezone)}
											<p class="text-sm opacity-70">
												{calculateDuration(
													transportation.date,
													transportation.end_date,
													transportation.start_timezone,
													transportation.end_timezone
												)}
											</p>
										{/if}
									</div>
								</div>
							{/if}

							<!-- Type -->
							<div class="flex items-start gap-3">
								<span class="text-xl mt-1 flex-shrink-0">{getTransportationIcon(transportation.type)}</span>
								<div>
									<p class="font-semibold text-sm opacity-70">{$t('transportation.type')}</p>
									<p class="text-base">{$t(`transportation.modes.${transportation.type}`)}</p>
								</div>
							</div>

							<!-- Flight Number -->
							{#if transportation.flight_number}
								<div class="flex items-start gap-3">
									<CardAccountDetails class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div>
										<p class="font-semibold text-sm opacity-70">{$t('transportation.flight_number')}</p>
										<p class="text-base font-mono">{transportation.flight_number}</p>
									</div>
								</div>
							{/if}

							<!-- Route Codes -->
							{#if getRouteCodes(transportation)}
								<div class="flex items-start gap-3">
									<MapMarker class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div>
										<p class="font-semibold text-sm opacity-70">{$t('transportation.codes') ?? 'Codes'}</p>
										<p class="text-base font-mono">{getRouteCodes(transportation)}</p>
									</div>
								</div>
							{/if}

							<!-- Distance -->
							{#if transportation.distance}
								<div class="flex items-start gap-3">
									<MapMarkerDistanceIcon class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div>
										<p class="font-semibold text-sm opacity-70">{$t('adventures.distance') ?? 'Distance'}</p>
										<p class="text-base">{formatDistance(transportation.distance)}</p>
									</div>
								</div>
							{/if}

							<!-- Price -->
							{#if transportationPriceLabel}
								<div class="flex items-start gap-3">
									<CashMultiple class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div>
										<p class="font-semibold text-sm opacity-70">{$t('adventures.price')}</p>
										<p class="text-base font-semibold">{transportationPriceLabel}</p>
									</div>
								</div>
							{/if}

							<!-- Link -->
							{#if transportation.link}
								<div class="flex items-start gap-3">
									<OpenInNew class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div class="flex-1">
										<p class="font-semibold text-sm opacity-70 mb-1">{$t('adventures.link')}</p>
										<a
											href={transportation.link}
											target="_blank"
											rel="noopener noreferrer"
											class="link link-primary text-base break-all"
										>
											{transportation.link}
										</a>
									</div>
								</div>
							{/if}

							<!-- Tags -->
							{#if transportation.tags && transportation.tags.length > 0}
								<div>
									<p class="font-semibold text-sm opacity-70 mb-2">🏷️ {$t('adventures.tags')}</p>
									<div class="flex flex-wrap gap-1">
										{#each transportation.tags as tag}
											<span class="badge badge-sm badge-outline">{tag}</span>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Average Price -->
				{#if transportation.average_price_per_user}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-3">💰 {$t('adventures.price')}</h3>
							<div class="space-y-4">
								{#if transportation.average_price_per_user}
									{@const avgPrice = transportation.average_price_per_user}
									{@const userCurrency = data.user?.default_currency || DEFAULT_CURRENCY}
									{@const countryCurrency = transportation.origin_country?.currency_code}
									<div class="border-t border-base-300 pt-3">
										<div class="text-sm opacity-70 mb-1">{$t('adventures.avg_price')}</div>
										<!-- Main price in country's currency (or original if no country) -->
										{#if $ratesLoaded && countryCurrency && avgPrice.currency !== countryCurrency}
											{@const countryConverted = formatConvertedPrice(avgPrice.amount, avgPrice.currency, countryCurrency)}
											{#if countryConverted}
												<div class="text-xl font-bold text-success">
													{countryConverted}
												</div>
											{:else}
												<div class="text-xl font-bold text-success">
													{formatMoney({ amount: avgPrice.amount, currency: avgPrice.currency })}
												</div>
											{/if}
										{:else}
											<div class="text-xl font-bold text-success">
												{formatMoney({ amount: avgPrice.amount, currency: avgPrice.currency })}
											</div>
										{/if}
										<div class="text-xs opacity-70">
											{$t('adventures.avg_per_user')}
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
											<div class="text-xs opacity-50 mt-1">
												{$t('adventures.based_on_visits', { values: { count: avgPrice.visit_count } })}
											</div>
										{/if}
									</div>
								{/if}
							</div>
						</div>
					</div>
				{/if}

				<!-- Activity Summary -->
				{#if getTotalActivities(transportation) > 0}
					{@const ms = data.user?.measurement_system ?? 'metric'}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">🏃‍♂️ Activity Summary</h3>
							<div class="space-y-2">
								<div class="stat">
									<div class="stat-title">Total Activities</div>
									<div class="stat-value text-2xl">{getTotalActivities(transportation)}</div>
								</div>
								{#if getTotalDistance(transportation, ms) > 0}
									<div class="stat">
										<div class="stat-title">Total Distance</div>
										<div class="stat-value text-xl">
											{getTotalDistance(transportation, ms).toFixed(1)}
											{ms === 'imperial' ? 'mi' : 'km'}
										</div>
									</div>
								{/if}
								{#if getTotalElevationGain(transportation, ms) > 0}
									<div class="stat">
										<div class="stat-title">Total Elevation</div>
										<div class="stat-value text-xl">
											{getTotalElevationGain(transportation, ms).toFixed(0)}
											{ms === 'imperial' ? 'ft' : 'm'}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>
				{/if}

				<EntityImagesCard
					images={transportation.images || []}
					showPrimaryBadge={false}
					showUserBadge={false}
					on:openImage={(e) => openImageModal(e.detail)}
				/>

				<EntityAttachmentsCard attachments={transportation.attachments || []} />

				<!-- History Panel (Collaborative Mode) -->
				{#if data.collaborativeMode && history.length > 0}
					<HistoryPanel
						{history}
						itemId={transportation.id}
						apiEndpoint="transportations"
						canRevert={true}
						on:reverted={async () => {
							const historyRes = await fetch(`/api/transportations/${transportation.id}/history/`);
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
		{data.props.transportation && data.props.transportation.name
			? `${data.props.transportation.name}`
			: 'Transportation'}
	</title>
	<meta name="description" content="View transportation details" />
</svelte:head>
