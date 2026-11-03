<script lang="ts">
	import type { Lodging } from '#lib/types.js';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import { DateTime } from 'luxon';

	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import TextBoxOutline from '~icons/mdi/text-box-outline';
	import ImageMultiple from '~icons/mdi/image-multiple-outline';
	import Paperclip from '~icons/mdi/paperclip';
	import DetailHeader from '#lib/components/detail/DetailHeader.svelte';
	import DetailCard from '#lib/components/detail/DetailCard.svelte';
	import DetailFact from '#lib/components/detail/DetailFact.svelte';
	import DetailDateTime from '#lib/components/detail/DetailDateTime.svelte';
	import DetailVisibilityBadge from '#lib/components/detail/DetailVisibilityBadge.svelte';
	import DetailMapPanel from '#lib/components/detail/DetailMapPanel.svelte';
	import DetailMapPin from '#lib/components/detail/DetailMapPin.svelte';
	import DetailMapPopup from '#lib/components/detail/DetailMapPopup.svelte';
	import DetailPhotos from '#lib/components/detail/DetailPhotos.svelte';
	import DetailNotFound from '#lib/components/detail/DetailNotFound.svelte';
	import DetailLoading from '#lib/components/detail/DetailLoading.svelte';
	import ImageDisplayModal from '#lib/components/ImageDisplayModal.svelte';
	import AttachmentCard from '#lib/components/cards/AttachmentCard.svelte';
	import { normalizeBasemapType, isAllDay, LODGING_TYPES_ICONS } from '#lib';
	import MapMarker from '~icons/mdi/map-marker';
	import CalendarRange from '~icons/mdi/calendar-range';
	import BedOutline from '~icons/mdi/bed-outline';
	import OpenInNew from '~icons/mdi/open-in-new';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import CardAccountDetails from '~icons/mdi/card-account-details';
	import { dateFormatFromUser } from '#lib/dateFormat.js';
	import LodgingModal from '#lib/components/lodging/LodgingModal.svelte';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '#lib/money.js';
	import ExternalMapLinks from '#lib/components/shared/ExternalMapLinks.svelte';
	import { contentImagesToGeoJson, EMPTY_IMAGE_PIN_GEOJSON } from '#lib/map/imagePins.js';

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const dateFormat = $derived(dateFormatFromUser(data.user));
	let lodging = $state<Lodging | null>(null);

	let notFound: boolean = $state(false);
	let modalInitialIndex: number = $state(0);
	let isImageModalOpen: boolean = $state(false);
	let isEditModalOpen: boolean = $state(false);
	let mapBasemapType = $state(normalizeBasemapType(undefined));
	$effect.pre(() => {
		mapBasemapType = normalizeBasemapType(data.user?.map_style);
	});

	let imagePinGeoJson = $derived(
		lodging
			? contentImagesToGeoJson(lodging.images, {
					parentType: 'lodging',
					parentId: lodging.id,
					parentName: lodging.name
				})
			: EMPTY_IMAGE_PIN_GEOJSON
	);

	let lodgingPriceLabel = $derived(
		lodging
			? formatMoney(
					toMoneyValue(
						lodging.price,
						lodging.price_currency,
						data.user?.default_currency || DEFAULT_CURRENCY
					)
				)
			: null
	);

	function getLodgingIcon(type: string) {
		if (type in LODGING_TYPES_ICONS) {
			return LODGING_TYPES_ICONS[type as keyof typeof LODGING_TYPES_ICONS];
		} else {
			return '🏨';
		}
	}

	const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';
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
		if (!lodging) return;
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

	let localStayWindow = $derived(
		lodging ? formatLocalStayWindow(lodging.check_in, lodging.check_out, lodging.timezone) : null
	);
	let showLocalStayTime = $derived(
		Boolean(localStayWindow && primaryStayTimezone(lodging?.timezone ?? null) !== localTimeZone)
	);
	let nights = $derived(lodging ? calculateNights(lodging.check_in, lodging.check_out) : null);
	let isOwner = $derived(
		Boolean(data.user?.uuid && lodging?.user && data.user.uuid === lodging.user)
	);
</script>

{#if notFound}
	<DetailNotFound
		title={$t('adventures.lodging_not_found')}
		description={$t('adventures.location_not_found_desc')}
	/>
{/if}

{#if isEditModalOpen}
	<LodgingModal
		on:close={() => (isEditModalOpen = false)}
		user={data.user}
		lodgingToEdit={lodging}
		bind:lodging
	/>
{/if}

{#if isImageModalOpen && lodging}
	<ImageDisplayModal
		images={lodging.images}
		initialIndex={modalInitialIndex}
		location={lodging.location ?? ''}
		on:close={closeImageModal}
	/>
{/if}

{#if !lodging && !notFound}
	<DetailLoading />
{/if}

{#if lodging}
	<DetailHeader
		title={lodging.name}
		emoji={getLodgingIcon(lodging.type)}
		rating={lodging.rating}
		images={lodging.images ?? []}
		onOpenImage={openImageModal}
	>
		{#snippet chips()}
			{#if lodging?.type}
				<span class="badge badge-primary">{$t(`lodging.${lodging.type}`)}</span>
			{/if}
			{#if lodging?.location}
				<span class="badge badge-neutral gap-1">
					<MapMarker class="h-3.5 w-3.5" />
					{lodging.location}
				</span>
			{/if}
			<DetailVisibilityBadge isPublic={Boolean(lodging?.is_public)} />
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
				{#if lodging.description}
					<DetailCard title={$t('adventures.description')} icon={TextBoxOutline}>
						<article class="prose max-w-none">
							{@html DOMPurify.sanitize(renderMarkdown(lodging.description))}
						</article>
					</DetailCard>
				{/if}

				{#if lodging.latitude && lodging.longitude}
					<DetailMapPanel
						title={$t('detail.location')}
						hint={lodging.location ?? $t('detail.map_hint')}
						bind:basemapType={mapBasemapType}
						center={[lodging.longitude, lodging.latitude]}
						{imagePinGeoJson}
					>
						<DetailMapPin
							lngLat={[lodging.longitude, lodging.latitude]}
							icon={getLodgingIcon(lodging.type)}
							tone="lodging"
						>
							<DetailMapPopup
								title={lodging.name}
								subtitle={`${$t(`lodging.${lodging.type}`)} ${getLodgingIcon(lodging.type)}`}
								rating={lodging.rating}
								address={lodging.location}
							/>
						</DetailMapPin>
						{#snippet footer()}
							<div class="flex flex-wrap items-center justify-between gap-3">
								<span class="font-mono text-sm text-base-content/80">
									{lodging?.latitude}, {lodging?.longitude}
								</span>
								<ExternalMapLinks
									placeName={lodging?.name}
									latitude={lodging?.latitude}
									longitude={lodging?.longitude}
								/>
							</div>
						{/snippet}
					</DetailMapPanel>
				{/if}

				{#if lodging.images && lodging.images.length > 1}
					<DetailCard
						title={$t('detail.photos')}
						hint={$t('detail.photos_hint')}
						icon={ImageMultiple}
					>
						{#snippet actions()}
							<span class="badge badge-ghost">{lodging?.images.length}</span>
						{/snippet}
						<DetailPhotos images={lodging.images} name={lodging.name} onOpen={openImageModal} />
					</DetailCard>
				{/if}
			</div>

			<!-- Sidebar -->
			<div class="space-y-4 sm:space-y-6">
				<DetailCard title={$t('detail.details')} icon={BedOutline}>
					<div class="space-y-4">
						{#if lodging.check_in}
							<DetailDateTime
								label={$t('adventures.check_in') ?? 'Check-in'}
								value={lodging.check_in}
								timezone={lodging.timezone}
								{dateFormat}
							/>
						{/if}
						{#if lodging.check_out}
							<DetailDateTime
								label={$t('adventures.check_out') ?? 'Check-out'}
								value={lodging.check_out}
								timezone={lodging.timezone}
								{dateFormat}
							/>
						{/if}
						{#if showLocalStayTime || nights}
							<p class="-mt-1 pl-12 text-sm text-base-content/70">
								{#if nights}
									{$t('detail.nights', { values: { count: nights } })}
								{/if}
								{#if showLocalStayTime}
									{nights ? ' · ' : ''}{$t('adventures.local_time') ?? 'Local time'}: {localStayWindow}
								{/if}
							</p>
						{/if}

						<DetailFact label={$t('transportation.type')} emoji={getLodgingIcon(lodging.type)}>
							{$t(`lodging.${lodging.type}`)}
						</DetailFact>

						{#if lodging.reservation_number}
							<DetailFact label={$t('adventures.reservation')} icon={CardAccountDetails} mono>
								{lodging.reservation_number}
							</DetailFact>
						{/if}

						{#if lodgingPriceLabel}
							<DetailFact label={$t('adventures.price')} icon={CashMultiple}>
								<span class="font-semibold">{lodgingPriceLabel}</span>
							</DetailFact>
						{/if}

						{#if lodging.link}
							<DetailFact label={$t('adventures.link')} icon={OpenInNew}>
								<a
									href={lodging.link}
									target="_blank"
									rel="noopener noreferrer"
									class="link link-primary break-all"
								>
									{lodging.link}
								</a>
							</DetailFact>
						{/if}
					</div>
				</DetailCard>

				{#if lodging.attachments && lodging.attachments.length > 0}
					<DetailCard
						title={$t('adventures.attachments')}
						hint={$t('detail.files_hint')}
						icon={Paperclip}
					>
						<div class="space-y-2">
							{#each lodging.attachments as attachment}
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
		{data.props.lodging && data.props.lodging.name ? `${data.props.lodging.name}` : 'Lodging'}
	</title>
	<meta name="description" content="View lodging details" />
</svelte:head>
