<script lang="ts">
	import type { Transportation } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { GeoJSON, LineLayer } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import { DateTime } from 'luxon';

	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import TextBoxOutline from '~icons/mdi/text-box-outline';
	import ImageMultiple from '~icons/mdi/image-multiple-outline';
	import Paperclip from '~icons/mdi/paperclip';
	import ClockOutline from '~icons/mdi/clock-outline';
	import RouteIcon from '~icons/mdi/routes';
	import TicketConfirmation from '~icons/mdi/ticket-confirmation-outline';
	import DetailHeader from '$lib/components/detail/DetailHeader.svelte';
	import DetailCard from '$lib/components/detail/DetailCard.svelte';
	import DetailFact from '$lib/components/detail/DetailFact.svelte';
	import DetailDateTime from '$lib/components/detail/DetailDateTime.svelte';
	import DetailPhotos from '$lib/components/detail/DetailPhotos.svelte';
	import DetailMapPanel from '$lib/components/detail/DetailMapPanel.svelte';
	import DetailMapPin from '$lib/components/detail/DetailMapPin.svelte';
	import DetailMapPopup from '$lib/components/detail/DetailMapPopup.svelte';
	import DetailVisibilityBadge from '$lib/components/detail/DetailVisibilityBadge.svelte';
	import DetailNotFound from '$lib/components/detail/DetailNotFound.svelte';
	import DetailLoading from '$lib/components/detail/DetailLoading.svelte';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import AttachmentCard from '$lib/components/cards/AttachmentCard.svelte';
	import { normalizeBasemapType, isAllDay, TRANSPORTATION_TYPES_ICONS } from '$lib';
	import MapMarker from '~icons/mdi/map-marker';
	import OpenInNew from '~icons/mdi/open-in-new';
	import MapMarkerDistanceIcon from '~icons/mdi/map-marker-distance';
	import CardAccountDetails from '~icons/mdi/card-account-details';
	import { dateFormatFromUser } from '$lib/dateFormat';
	import TransportationModal from '$lib/components/transportation/TransportationModal.svelte';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '$lib/money';
	import ExternalMapLinks from '$lib/components/shared/ExternalMapLinks.svelte';
	import { routeLine, type LngLat } from '$lib/map/routeArc';
	import { contentImagesToGeoJson, EMPTY_IMAGE_PIN_GEOJSON } from '$lib/map/imagePins';

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const dateFormat = $derived(dateFormatFromUser(data.user));
	let transportation = $state<Transportation | undefined>(undefined);

	let notFound: boolean = $state(false);
	let modalInitialIndex: number = $state(0);
	let isImageModalOpen: boolean = $state(false);
	let isEditModalOpen: boolean = $state(false);
	let mapBasemapType = $state(normalizeBasemapType(undefined));
	$effect.pre(() => {
		mapBasemapType = normalizeBasemapType(data.user?.map_style);
	});

	function getTransportationIcon(type: string) {
		if (type in TRANSPORTATION_TYPES_ICONS) {
			return TRANSPORTATION_TYPES_ICONS[type as keyof typeof TRANSPORTATION_TYPES_ICONS];
		}
		return '🚗';
	}

	onMount(async () => {
		if (data.props.transportation) {
			transportation = data.props.transportation;
			transportation.images.sort((a, b) => {
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
		modalInitialIndex = imageIndex;
		isImageModalOpen = true;
	}

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

	/**
	 * Format a distance given in kilometers according to the current user's
	 * measurement system (metric or imperial). For metric show meters for <1km,
	 * otherwise km; for imperial show feet for very small distances, otherwise miles.
	 */
	function formatDistance(distanceKm: number | null): string | null {
		if (distanceKm === null || distanceKm === undefined) return null;
		const ms = data.user?.measurement_system ?? 'metric';

		if (ms === 'imperial') {
			const miles = distanceKm * 0.621371;
			// show miles if at least 0.1 mi, otherwise show feet
			if (miles >= 0.1) {
				return `${miles.toFixed(1)} mi`;
			}
			const feet = Math.round(miles * 5280);
			return `${feet} ft`;
		} else {
			// metric
			if (distanceKm >= 1) {
				return `${distanceKm.toFixed(1)} km`;
			}
			const meters = Math.round(distanceKm * 1000);
			return `${meters} m`;
		}
	}

	function collectAttachmentGeojson(item: Transportation): any {
		if (!item.attachments || item.attachments.length === 0) return null;
		const features: any[] = [];
		for (const a of item.attachments) {
			if (a && a.geojson && a.geojson.features) {
				// If it's a FeatureCollection
				if (a.geojson.type === 'FeatureCollection' && Array.isArray(a.geojson.features)) {
					features.push(...a.geojson.features);
				} else if (a.geojson.type === 'Feature') {
					features.push(a.geojson);
				}
			}
		}
		if (features.length === 0) return null;
		return {
			type: 'FeatureCollection',
			features
		};
	}

	const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';
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

	let imagePinGeoJson = $derived(
		transportation
			? contentImagesToGeoJson(transportation.images, {
					parentType: 'transportation',
					parentId: transportation.id,
					parentName: transportation.name
				})
			: EMPTY_IMAGE_PIN_GEOJSON
	);
	let transportationPriceLabel = $derived(
		transportation
			? formatMoney(
					toMoneyValue(
						transportation.price,
						transportation.price_currency,
						data.user?.default_currency || DEFAULT_CURRENCY
					)
				)
			: null
	);
	// Both ends of the route, when known: drawn as a line and zoomed to so both are visible.
	let routeEnds = $derived.by((): [LngLat, LngLat] | null => {
		if (!transportation || !hasOriginCoordinates(transportation)) return null;
		if (!hasDestinationCoordinates(transportation)) return null;
		return [
			[Number(transportation.origin_longitude), Number(transportation.origin_latitude)],
			[Number(transportation.destination_longitude), Number(transportation.destination_latitude)]
		];
	});
	let routeFeature = $derived(
		routeEnds && transportation
			? routeLine(routeEnds[0], routeEnds[1], transportation.type === 'plane')
			: null
	);
	let mapCenter = $derived(transportation ? getMapCenter(transportation) : null);
	let attachmentGeojson = $derived(
		transportation ? collectAttachmentGeojson(transportation) : null
	);
	let localTravelWindow = $derived(
		transportation
			? formatLocalTravelWindow(
					transportation.date,
					transportation.end_date,
					transportation.start_timezone,
					transportation.end_timezone
				)
			: null
	);
	let showLocalTripTime = $derived(
		Boolean(
			localTravelWindow &&
			primaryTripTimezone(
				transportation?.start_timezone ?? null,
				transportation?.end_timezone ?? null
			) !== localTimeZone
		)
	);
	let duration = $derived(
		transportation
			? calculateDuration(
					transportation.date,
					transportation.end_date,
					transportation.start_timezone,
					transportation.end_timezone
				)
			: null
	);
	let isOwner = $derived(
		Boolean(data.user?.uuid && transportation?.user && data.user.uuid === transportation.user)
	);
</script>

{#if notFound}
	<DetailNotFound
		title={$t('adventures.transportation_not_found')}
		description={$t('adventures.location_not_found_desc')}
	/>
{/if}

{#if isEditModalOpen}
	<TransportationModal
		on:close={() => (isEditModalOpen = false)}
		user={data.user}
		transportationToEdit={transportation}
		bind:transportation
	/>
{/if}

{#if isImageModalOpen && transportation}
	<ImageDisplayModal
		images={transportation.images}
		initialIndex={modalInitialIndex}
		location={getRouteLabel()}
		on:close={closeImageModal}
	/>
{/if}

{#if !transportation && !notFound}
	<DetailLoading />
{/if}

<!-- One map marker per end of the route -->
{#snippet endpoint(kind: 'from' | 'to', lng: number, lat: number)}
	{#if transportation}
		<DetailMapPin
			lngLat={[lng, lat]}
			icon={getTransportationIcon(transportation.type)}
			tone="transportation"
			label={$t(kind === 'from' ? 'detail.route_from' : 'detail.route_to')}
		>
			<DetailMapPopup
				title={transportation.name}
				subtitle={`${$t(`transportation.${kind}_location`)} ${getTransportationIcon(transportation.type)}`}
				rating={transportation.rating}
				address={kind === 'from' ? transportation.from_location : transportation.to_location}
			/>
		</DetailMapPin>
	{/if}
{/snippet}

{#if transportation}
	<DetailHeader
		title={transportation.name}
		emoji={getTransportationIcon(transportation.type)}
		rating={transportation.rating}
		images={transportation.images ?? []}
		onOpenImage={openImageModal}
	>
		{#snippet chips()}
			{#if transportation?.type}
				<span class="badge badge-primary">{$t(`transportation.modes.${transportation.type}`)}</span>
			{/if}
			{#if transportation && (transportation.from_location || transportation.to_location)}
				<span class="badge badge-neutral gap-1">
					<MapMarker class="h-3.5 w-3.5" />
					{getRouteLabel()}
				</span>
			{/if}
			{#if transportation && getRouteCodes(transportation)}
				<span class="badge badge-outline font-mono">{getRouteCodes(transportation)}</span>
			{/if}
			<DetailVisibilityBadge isPublic={Boolean(transportation?.is_public)} />
		{/snippet}
		{#snippet actions()}
			{#if isOwner}
				<button class="btn btn-primary btn-sm gap-2" onclick={() => (isEditModalOpen = true)}>
					<FileDocumentEdit class="h-4 w-4" />
					{$t('detail.edit')}
				</button>
			{/if}
		{/snippet}
	</DetailHeader>

	<div class="container mx-auto max-w-7xl px-3 py-5 sm:px-6 sm:py-6">
		<div class="grid grid-cols-1 items-start gap-4 sm:gap-6 lg:grid-cols-3">
			<!-- Main column -->
			<div class="space-y-4 sm:space-y-6 lg:col-span-2">
				{#if transportation.description}
					<DetailCard title={$t('adventures.description')} icon={TextBoxOutline}>
						<article class="prose max-w-none">
							{@html DOMPurify.sanitize(renderMarkdown(transportation.description))}
						</article>
					</DetailCard>
				{/if}

				{#if mapCenter}
					<DetailMapPanel
						title={$t('detail.route')}
						hint={getRouteLabel() || $t('detail.map_hint')}
						bind:basemapType={mapBasemapType}
						center={mapCenter}
						fitPoints={routeFeature
							? (routeFeature.geometry.coordinates as [number, number][])
							: undefined}
						{imagePinGeoJson}
					>
						{#if routeFeature && !attachmentGeojson}
							<!-- A sketch of the route: a flight arcs, other modes run straight and dashed -->
							<GeoJSON data={routeFeature}>
								<LineLayer
									id="transportation-route-sketch"
									layout={{ 'line-cap': 'round', 'line-join': 'round' }}
									paint={{
										'line-color': '#f59e0b',
										'line-width': 3,
										'line-opacity': 0.9,
										...(transportation.type === 'plane' ? {} : { 'line-dasharray': [2, 2] })
									}}
								/>
							</GeoJSON>
						{/if}
						{#if hasOriginCoordinates(transportation)}
							{@render endpoint(
								'from',
								Number(transportation.origin_longitude),
								Number(transportation.origin_latitude)
							)}
						{/if}
						{#if hasDestinationCoordinates(transportation)}
							{@render endpoint(
								'to',
								Number(transportation.destination_longitude),
								Number(transportation.destination_latitude)
							)}
						{/if}
						{#if attachmentGeojson}
							<!-- Attachment GeoJSON, e.g. a GPX track -->
							<GeoJSON data={attachmentGeojson}>
								<LineLayer
									id="transportation-route"
									paint={{ 'line-color': '#60a5fa', 'line-width': 4, 'line-opacity': 0.9 }}
								/>
							</GeoJSON>
						{/if}
						{#snippet footer()}
							{#each [{ kind: 'from', place: transportation?.from_location }, { kind: 'to', place: transportation?.to_location }] as end}
								{#if end.place}
									<div class="flex flex-wrap items-center justify-between gap-2">
										<span class="flex min-w-0 items-center gap-2 text-sm">
											<MapMarker class="h-4 w-4 shrink-0 text-primary" />
											<span class="text-base-content/60"
												>{$t(`transportation.${end.kind}_location`)}</span
											>
											<span class="font-medium">{end.place}</span>
										</span>
										<ExternalMapLinks placeName={end.place} showLabel={false} />
									</div>
								{/if}
							{/each}
						{/snippet}
					</DetailMapPanel>
				{/if}

				{#if transportation.images && transportation.images.length > 1}
					<DetailCard
						title={$t('detail.photos')}
						hint={$t('detail.photos_hint')}
						icon={ImageMultiple}
					>
						{#snippet actions()}
							<span class="badge badge-ghost">{transportation?.images.length}</span>
						{/snippet}
						<DetailPhotos
							images={transportation.images}
							name={transportation.name}
							onOpen={openImageModal}
						/>
					</DetailCard>
				{/if}
			</div>

			<!-- Sidebar -->
			<div class="space-y-4 sm:space-y-6">
				<DetailCard title={$t('detail.details')} icon={ClockOutline}>
					<div class="space-y-4">
						{#if transportation.date}
							<DetailDateTime
								label={$t('adventures.start') ?? 'Start'}
								value={transportation.date}
								timezone={transportation.start_timezone}
								{dateFormat}
							/>
						{/if}
						{#if transportation.end_date}
							<DetailDateTime
								label={$t('adventures.end') ?? 'End'}
								value={transportation.end_date}
								timezone={transportation.end_timezone ?? transportation.start_timezone}
								{dateFormat}
							/>
						{/if}
						{#if duration || showLocalTripTime}
							<p class="-mt-1 pl-12 text-sm text-base-content/70">
								{duration ?? ''}
								{#if showLocalTripTime}
									{duration ? ' · ' : ''}{$t('adventures.local_time') ?? 'Local time'}: {localTravelWindow}
								{/if}
							</p>
						{/if}

						<DetailFact
							label={$t('transportation.type')}
							emoji={getTransportationIcon(transportation.type)}
						>
							{$t(`transportation.modes.${transportation.type}`)}
						</DetailFact>

						{#if transportation.flight_number}
							<DetailFact label={$t('transportation.flight_number')} icon={CardAccountDetails} mono>
								{transportation.flight_number}
							</DetailFact>
						{/if}

						{#if getRouteCodes(transportation)}
							<DetailFact
								label={$t('transportation.codes') ?? 'Codes'}
								icon={TicketConfirmation}
								mono
							>
								{getRouteCodes(transportation)}
							</DetailFact>
						{/if}

						{#if transportation.distance}
							<DetailFact
								label={$t('adventures.distance') ?? 'Distance'}
								icon={MapMarkerDistanceIcon}
							>
								{formatDistance(transportation.distance)}
							</DetailFact>
						{/if}

						{#if transportationPriceLabel}
							<DetailFact label={$t('adventures.price')} icon={CashMultiple}>
								<span class="font-semibold">{transportationPriceLabel}</span>
							</DetailFact>
						{/if}

						{#if transportation.link}
							<DetailFact label={$t('adventures.link')} icon={OpenInNew}>
								<a
									href={transportation.link}
									target="_blank"
									rel="noopener noreferrer"
									class="link link-primary break-all"
								>
									{transportation.link}
								</a>
							</DetailFact>
						{/if}
					</div>
				</DetailCard>

				{#if transportation.attachments && transportation.attachments.length > 0}
					<DetailCard
						title={$t('adventures.attachments')}
						hint={$t('detail.files_hint')}
						icon={Paperclip}
					>
						<div class="space-y-2">
							{#each transportation.attachments as attachment}
								<AttachmentCard {attachment} />
							{/each}
						</div>
					</DetailCard>
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
