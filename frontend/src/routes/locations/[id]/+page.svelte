<script lang="ts">
	import { tick, untrack } from 'svelte';

	import { createEmptyLocation } from '#lib/location-draft.js';
	import type { Location } from '#lib/types.js';
	import { fetchSunriseSunset, visitDateKey, type SunriseSunset } from '#lib/sunriseSunset.js';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { openLocationDrawer } from '#lib/location-drawer.svelte.js';
	import { GeoJSON, LineLayer } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import { formatAllDayDate, formatDateInTimezone } from '#lib/dateUtils.js';
	import { dateFormatFromUser } from '#lib/dateFormat.js';

	import WeatherSunset from '~icons/mdi/weather-sunset';
	import ImageDisplayModal from '#lib/components/ImageDisplayModal.svelte';
	import { googleContentImage } from '#lib/images.js';
	import AttachmentCard from '#lib/components/cards/AttachmentCard.svelte';
	import { addToast } from '#lib/toasts.js';
	import { getActivityColor, normalizeBasemapType, isVisitAllDay, copyToClipboard } from '#lib';
	import ActivityCard from '#lib/components/cards/ActivityCard.svelte';
	import TrailCard from '#lib/components/cards/TrailCard.svelte';
	import NewLocationModal from '#lib/components/locations/LocationModal.svelte';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '#lib/money.js';
	import ExternalMapLinks from '#lib/components/shared/ExternalMapLinks.svelte';
	import { contentImagesToGeoJson, EMPTY_IMAGE_PIN_GEOJSON } from '#lib/map/imagePins.js';
	import ImageOutline from '~icons/mdi/image-outline';
	import SocialShareModal from '#lib/components/SocialShareModal.svelte';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import ContentCopy from '~icons/mdi/content-copy';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import TextBoxOutline from '~icons/mdi/text-box-outline';
	import Hiking from '~icons/mdi/hiking';
	import CalendarCheck from '~icons/mdi/calendar-check-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import MapOutline from '~icons/mdi/map-outline';
	import ImageMultiple from '~icons/mdi/image-multiple-outline';
	import Paperclip from '~icons/mdi/paperclip';
	import AccountOutline from '~icons/mdi/account-outline';
	import Run from '~icons/mdi/run';
	import Tag from '~icons/mdi/tag-outline';
	import LinkVariant from '~icons/mdi/link-variant';
	import InformationOutline from '~icons/mdi/information-outline';
	import CheckCircle from '~icons/mdi/check-circle';
	import ClockOutline from '~icons/mdi/clock-outline';
	import ClockTimeFour from '~icons/mdi/clock-time-four-outline';
	import CityVariant from '~icons/mdi/city-variant-outline';
	import Folder from '~icons/mdi/folder-outline';
	import Speedometer from '~icons/mdi/map-marker-distance';
	import TrendingUp from '~icons/mdi/trending-up';
	import DetailHeader from '#lib/components/detail/DetailHeader.svelte';
	import DetailCard from '#lib/components/detail/DetailCard.svelte';
	import DetailFact from '#lib/components/detail/DetailFact.svelte';
	import LocationCollectionChips from '#lib/components/collections/LocationCollectionChips.svelte';
	import DetailStat from '#lib/components/detail/DetailStat.svelte';
	import DetailTabs, { type DetailTab } from '#lib/components/detail/DetailTabs.svelte';
	import DetailPhotos from '#lib/components/detail/DetailPhotos.svelte';
	import DetailMapPanel from '#lib/components/detail/DetailMapPanel.svelte';
	import CountryFlag from '#lib/components/shared/CountryFlag.svelte';
	import DetailMapPin from '#lib/components/detail/DetailMapPin.svelte';
	import DetailMapPopup from '#lib/components/detail/DetailMapPopup.svelte';
	import DetailVisibilityBadge from '#lib/components/detail/DetailVisibilityBadge.svelte';
	import DetailNotFound from '#lib/components/detail/DetailNotFound.svelte';
	import DetailLoading from '#lib/components/detail/DetailLoading.svelte';
	import LocationPageHead from '#lib/components/locations/LocationPageHead.svelte';

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	interface Props {
		data: PageData;
		embedded?: boolean;
		scrollHash?: string;
	}

	let { data, embedded = false, scrollHash = '' }: Props = $props();

	const dateFormat = $derived(dateFormatFromUser(data.user));
	let measurementSystem = $derived(data.user?.measurement_system || 'metric');

	let adventure: Location | undefined = $state();

	// A link to one visit opens the Visits tab, then scrolls to it.
	$effect(() => {
		const hash = embedded ? scrollHash : page.url.hash;
		if (!hash.startsWith('#visit-') || !adventure) return;
		tab = 'visits';
		void tick().then(() =>
			document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'center' })
		);
	});
	let visitSunriseSunset: Record<string, SunriseSunset> = $state({});
	let sunriseSunsetLoading: Record<string, boolean> = $state({});
	let tab = $state('overview');

	let adventurePriceLabel = $derived(
		adventure
			? formatMoney(
					toMoneyValue(
						adventure.price,
						adventure.price_currency,
						data.user?.default_currency || DEFAULT_CURRENCY
					)
				)
			: null
	);

	let notFound: boolean = $state(false);
	let isEditModalOpen: boolean = $state(false);
	let locationDraft = $state(createEmptyLocation());
	let isSocialShareModalOpen: boolean = $state(false);
	let modalInitialIndex: number = $state(0);
	let isImageModalOpen: boolean = $state(false);
	let mapBasemapType = $state(normalizeBasemapType(undefined));
	$effect.pre(() => {
		mapBasemapType = normalizeBasemapType(data.user?.map_style);
	});
	let showActivityTracks = $state(true);
	let showTrailTracks = $state(true);

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
		const previousId = adventure?.id ?? null;
		const nextId = adventureData?.id ?? null;
		const locationChanged = previousId !== nextId;

		if (!adventureData) {
			notFound = true;
			adventure = undefined;
			visitSunriseSunset = {};
			sunriseSunsetLoading = {};
			tab = 'overview';
			isImageModalOpen = false;
			isEditModalOpen = false;
			isSocialShareModalOpen = false;
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

		if (!locationChanged) {
			return;
		}

		visitSunriseSunset = {};
		sunriseSunsetLoading = {};
		tab = 'overview';
		isImageModalOpen = false;
		isEditModalOpen = false;
		isSocialShareModalOpen = false;
	}

	$effect.pre(() => {
		const adventureData = data.props.adventure;
		untrack(() => {
			applyLocationPageData(adventureData);
		});
	});

	let imagePinGeoJson = $derived(
		adventure
			? contentImagesToGeoJson(adventure.images, {
					parentType: 'location',
					parentId: adventure.id,
					parentName: adventure.name
				})
			: EMPTY_IMAGE_PIN_GEOJSON
	);

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
				if (embedded) {
					openLocationDrawer(newLocation.id);
				} else {
					goto(`/locations/${newLocation.id}`);
				}
			} else {
				addToast('error', $t('adventures.location_duplicate_error'));
			}
		} catch (e) {
			addToast('error', $t('adventures.location_duplicate_error'));
		} finally {
			isDuplicating = false;
		}
	}

	function closeEditModal() {
		if (adventure && locationDraft?.id === adventure.id) {
			adventure = {
				...adventure,
				...locationDraft,
				city: adventure.city,
				region: adventure.region,
				country: adventure.country,
				created_at: adventure.created_at,
				updated_at: adventure.updated_at,
				rating:
					typeof locationDraft.rating === 'number' && Number.isFinite(locationDraft.rating)
						? locationDraft.rating
						: adventure.rating,
				latitude: Number.isFinite(locationDraft.latitude)
					? locationDraft.latitude
					: adventure.latitude,
				longitude: Number.isFinite(locationDraft.longitude)
					? locationDraft.longitude
					: adventure.longitude
			};
		}
		isEditModalOpen = false;
	}

	function closeImageModal() {
		isImageModalOpen = false;
	}

	function openImageModal(imageIndex: number) {
		if (!adventure) return;
		modalInitialIndex = imageIndex;
		isImageModalOpen = true;
	}

	// A city or region links to its region page; with no region, to the country.
	function regionHref(place: Location) {
		const code = place.country?.country_code;
		if (!code) return '#';
		return place.region ? `/worldtravel/${code}/${place.region.id}` : `/worldtravel/${code}`;
	}

	async function copyAdventureCoordinates() {
		if (!adventure) return;
		try {
			await copyToClipboard(`${adventure.latitude}, ${adventure.longitude}`);
			addToast('success', $t('detail.coordinates_copied'));
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
			addToast('success', $t('adventures.link_copied'));
		} catch {
			addToast('error', $t('adventures.copy_failed'));
		}
	}

	let isOwner = $derived(
		Boolean(
			!embedded &&
			data.user?.uuid &&
			adventure?.user?.uuid &&
			data.user.uuid === adventure.user.uuid
		)
	);
	let hasMapContent = $derived(
		adventure
			? Boolean(
					(adventure.longitude && adventure.latitude) ||
					hasAttachmentGeojson(adventure) ||
					hasActivityGeojson(adventure)
				)
			: false
	);
	let tabs = $derived.by((): DetailTab[] => {
		if (!adventure) return [];
		const list: DetailTab[] = [
			{ id: 'overview', label: $t('detail.overview'), icon: InformationOutline }
		];
		if (adventure.visits.length > 0) {
			list.push({
				id: 'visits',
				label: $t('adventures.visits'),
				icon: CalendarCheck,
				count: adventure.visits.length
			});
		}
		if (hasMapContent) list.push({ id: 'map', label: $t('navbar.map'), icon: MapOutline });
		const media = adventure.images.length + adventure.attachments.length;
		if (media > 0) {
			list.push({
				id: 'media',
				label: $t('detail.photos_and_files'),
				icon: ImageMultiple,
				count: media
			});
		}
		return list;
	});
	// A tab that has gone away (e.g. the last visit was deleted) falls back to Overview.
	let activeTab = $derived(tabs.some((item) => item.id === tab) ? tab : 'overview');
	let measurementUnits = $derived(
		measurementSystem === 'imperial'
			? { distance: 'mi', elevation: 'ft' }
			: { distance: 'km', elevation: 'm' }
	);
</script>

{#if notFound}
	<DetailNotFound
		title={$t('adventures.location_not_found')}
		description={$t('adventures.location_not_found_desc')}
	/>
{/if}

{#if isEditModalOpen}
	<NewLocationModal
		on:close={closeEditModal}
		user={data.user}
		locationToEdit={adventure}
		bind:location={locationDraft}
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
	<DetailLoading />
{/if}

{#if adventure}
	<DetailHeader
		title={adventure.name}
		emoji={adventure.category?.icon}
		rating={adventure.rating}
		images={adventure.images ?? []}
		onOpenImage={openImageModal}
	>
		{#snippet chips()}
			{#if adventure?.category}
				<a
					href="/locations?types={adventure.category.name}"
					class="badge badge-primary transition-all hover:brightness-110"
				>
					{adventure.category.display_name}
				</a>
			{/if}
			{#if adventure?.location}
				<span class="badge badge-neutral gap-1">
					<MapMarker class="h-3.5 w-3.5" />
					{adventure.location}
				</span>
			{/if}
			{#if adventure?.is_visited}
				<span class="badge badge-success gap-1">
					<CheckCircle class="h-3.5 w-3.5" />
					{$t('adventures.visited')}
				</span>
			{:else}
				<span class="badge badge-warning gap-1">
					<ClockOutline class="h-3.5 w-3.5" />
					{$t('adventures.not_visited')}
				</span>
			{/if}
			{#if adventure && adventure.visits.length > 0}
				<span class="badge badge-accent gap-1">
					<CalendarCheck class="h-3.5 w-3.5" />
					{adventure.visits.length}
					{adventure.visits.length === 1 ? $t('adventures.visit') : $t('adventures.visits')}
				</span>
			{/if}
			{#if adventure?.trails && adventure.trails.length > 0}
				<span class="badge badge-info gap-1">
					<Hiking class="h-3.5 w-3.5" />
					{adventure.trails.length}
					{adventure.trails.length === 1 ? $t('adventures.trail') : $t('adventures.trails')}
				</span>
			{/if}
			<DetailVisibilityBadge isPublic={Boolean(adventure?.is_public)} />
		{/snippet}
		{#snippet actions()}
			{#if isOwner}
				<button class="btn btn-primary btn-sm gap-2" onclick={() => (isEditModalOpen = true)}>
					<FileDocumentEdit class="h-4 w-4" />
					{$t('detail.edit')}
				</button>
				<button
					class="btn btn-outline btn-primary btn-sm gap-2"
					onclick={() => (isSocialShareModalOpen = true)}
				>
					<ImageOutline class="h-4 w-4" />
					<span class="hidden sm:inline">{$t('social_share.share_externally')}</span>
				</button>
				<div class="dropdown dropdown-end">
					<button
						type="button"
						tabindex="0"
						class="btn btn-ghost btn-sm btn-square"
						aria-label={$t('detail.more')}
					>
						<DotsHorizontal class="h-5 w-5" />
					</button>
					<ul
						tabindex="-1"
						class="dropdown-content menu z-10 mt-1 w-56 rounded-box border border-base-300 bg-base-100 p-2 shadow-lg"
					>
						<li>
							<button
								onclick={duplicateAdventure}
								class="flex items-center gap-2"
								disabled={isDuplicating}
							>
								<ContentCopy class="h-4 w-4" />
								{isDuplicating ? '...' : $t('adventures.duplicate_location')}
							</button>
						</li>
					</ul>
				</div>
			{/if}
		{/snippet}
	</DetailHeader>

	<div class="container mx-auto max-w-7xl px-3 py-5 sm:px-6 sm:py-6">
		<div class="mb-4 sm:mb-6">
			<DetailTabs {tabs} value={activeTab} onChange={(id) => (tab = id)} label={adventure.name} />
		</div>

		<div class={['grid grid-cols-1 items-start gap-4 sm:gap-6', !embedded && 'lg:grid-cols-3']}>
			<!-- Tab content -->
			<div class={['min-w-0 space-y-4 sm:space-y-6', !embedded && 'lg:col-span-2']}>
				{#if activeTab === 'overview'}
					{#if adventure.description}
						<DetailCard title={$t('adventures.description')} icon={TextBoxOutline}>
							<article class="prose max-w-none">
								{@html DOMPurify.sanitize(renderMarkdown(adventure.description))}
							</article>
						</DetailCard>
					{/if}

					{#if adventure.trails && adventure.trails.length > 0}
						<DetailCard title={$t('adventures.trails')} icon={Hiking}>
							<div class="grid gap-4">
								{#each adventure.trails as trail}
									<TrailCard
										{trail}
										measurementSystem={data.user?.measurement_system || 'metric'}
									/>
								{/each}
							</div>
						</DetailCard>
					{/if}

					{#if !adventure.description && !(adventure.trails && adventure.trails.length > 0)}
						<DetailCard title={$t('detail.overview')} icon={InformationOutline}>
							<p class="text-sm text-base-content/60">{$t('detail.nothing_here_yet')}</p>
						</DetailCard>
					{/if}
				{/if}

				{#if activeTab === 'visits'}
					<DetailCard title={$t('adventures.visits')} icon={CalendarCheck}>
						{#snippet actions()}
							<span class="badge badge-ghost">{adventure?.visits.length}</span>
						{/snippet}
						<div class="space-y-4">
							{#each adventure.visits as visit, index}
								{@const visitDate = visitDateKey(visit.start_date)}
								<div class="flex gap-3 sm:gap-4" id="visit-{visit.id}">
									<div class="flex flex-col items-center pt-1.5">
										<div class="h-3.5 w-3.5 shrink-0 rounded-full bg-primary"></div>
										{#if index < adventure.visits.length - 1}
											<div class="min-h-12 w-0.5 flex-1 bg-primary/30"></div>
										{/if}
									</div>
									<div class="min-w-0 flex-1 pb-2">
										<div class="rounded-xl border border-base-300 bg-base-100 p-4">
											<div class="flex gap-2">
												<div class="min-w-0 flex-1">
													{#if isVisitAllDay(visit.start_date, visit.end_date)}
														<div class="flex flex-wrap items-center gap-2">
															<span class="badge badge-primary gap-1">
																<CalendarCheck class="h-3.5 w-3.5" />
																{$t('adventures.all_day')}
															</span>
															<span class="font-semibold">
																{formatAllDayDate(visit.start_date, dateFormat)} – {formatAllDayDate(
																	visit.end_date,
																	dateFormat
																)}
															</span>
														</div>
													{:else}
														<div class="space-y-2">
															<div class="flex flex-wrap items-center gap-2">
																<span class="badge badge-primary gap-1">
																	<ClockTimeFour class="h-3.5 w-3.5" />
																	{$t('adventures.timed')}
																</span>
																{#if visit.timezone}
																	<span class="badge badge-outline">{visit.timezone}</span>
																{/if}
															</div>
															<div class="space-y-0.5 text-sm">
																<p>
																	<span class="text-base-content/60">{$t('adventures.start')}:</span
																	>
																	<span class="font-medium">
																		{formatDateInTimezone(
																			visit.start_date,
																			visit.timezone,
																			dateFormat
																		)}
																	</span>
																</p>
																<p>
																	<span class="text-base-content/60">{$t('adventures.end')}:</span>
																	<span class="font-medium">
																		{formatDateInTimezone(
																			visit.end_date,
																			visit.timezone,
																			dateFormat
																		)}
																	</span>
																</p>
															</div>
														</div>
													{/if}
													{#if visit.notes}
														<div class="mt-3 rounded-lg bg-base-200 p-3">
															<p class="text-sm italic">"{visit.notes}"</p>
														</div>
													{/if}

													{#if visit.activities && visit.activities.length > 0}
														<div class="mt-4">
															<h4 class="mb-3 flex items-center gap-2 font-semibold">
																<Run class="h-4 w-4 text-primary" />
																{$t('detail.activities')}
																<span class="badge badge-ghost badge-sm"
																	>{visit.activities.length}</span
																>
															</h4>
															<div class="space-y-3">
																{#each visit.activities as activity}
																	<ActivityCard
																		{activity}
																		readOnly={true}
																		trails={adventure.trails}
																		{visit}
																		measurementSystem={data.user?.measurement_system || 'metric'}
																	/>
																{/each}
															</div>
														</div>
													{/if}
												</div>

												{#if visitDate && adventure.latitude && adventure.longitude}
													<div class="shrink-0 self-start">
														{#if visitSunriseSunset[visitDate]}
															{@const sunriseSunset = visitSunriseSunset[visitDate]}
															<div
																class="tooltip tooltip-left"
																data-tip="{$t('adventures.sunrise')}: {sunriseSunset.sunrise} • {$t(
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
																	<WeatherSunset class="h-5 w-5" />
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
																	<WeatherSunset class="h-5 w-5" />
																</button>
															</div>
														{/if}
													</div>
												{/if}
											</div>
										</div>
									</div>
								</div>
							{/each}
						</div>
					</DetailCard>
				{/if}

				{#if activeTab === 'map'}
					<DetailMapPanel
						title={$t('navbar.map')}
						hint={adventure.location ?? ''}
						bind:basemapType={mapBasemapType}
						bind:showActivities={showActivityTracks}
						bind:showTrails={showTrailTracks}
						center={[adventure.longitude || 0, adventure.latitude || 0]}
						zoom={adventure.longitude ? 12 : 1}
						{imagePinGeoJson}
						hasActivities={hasActivityGeojson(adventure)}
						hasTrails={hasTrailGeojson(adventure)}
					>
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
										paint={{ 'line-color': '#00FF00', 'line-width': 2, 'line-opacity': 0.6 }}
									/>
								</GeoJSON>
							{/if}
						{/each}

						{#if showTrailTracks}
							{#each adventure.trails as trail}
								{#if trail.geojson}
									<GeoJSON data={trail.geojson}>
										<LineLayer
											paint={{ 'line-color': '#a855f7', 'line-width': 3, 'line-opacity': 0.85 }}
										/>
									</GeoJSON>
								{/if}
							{/each}
						{/if}

						{#if adventure.longitude && adventure.latitude}
							<DetailMapPin
								lngLat={[adventure.longitude, adventure.latitude]}
								icon={adventure.category?.icon || '📍'}
								tone={adventure.is_visited ? 'visited' : 'planned'}
							>
								<DetailMapPopup
									title={adventure.name}
									subtitle={adventure.category
										? `${adventure.category.display_name} ${adventure.category.icon}`
										: ''}
									address={adventure.visits.length > 0
										? `${adventure.visits.length} ${adventure.visits.length === 1 ? $t('adventures.visit') : $t('adventures.visits')}`
										: null}
								/>
							</DetailMapPin>
						{/if}

						{#snippet footer()}
							{#if adventure && (adventure.city || adventure.region || adventure.country)}
								<!-- Where it is: each part links to its World Travel page -->
								<div class="flex flex-wrap items-center gap-2">
									{#if adventure.city}
										{#if adventure.country}
											<a href={regionHref(adventure)} class="btn btn-sm btn-soft btn-primary gap-2">
												<CityVariant class="h-4 w-4" />
												{adventure.city.name}
											</a>
										{:else}
											<span class="badge badge-lg gap-2"
												><CityVariant class="h-4 w-4" />{adventure.city.name}</span
											>
										{/if}
									{/if}
									{#if adventure.region && adventure.country}
										<a href={regionHref(adventure)} class="btn btn-sm btn-soft btn-primary gap-2">
											<MapOutline class="h-4 w-4" />
											{adventure.region.name}
										</a>
									{/if}
									{#if adventure.country}
										<a
											href={`/worldtravel/${adventure.country.country_code}`}
											class="btn btn-sm btn-soft btn-primary gap-2"
										>
											<CountryFlag
												src={adventure.country.flag_url}
												code={adventure.country.country_code}
												name={adventure.country.name}
											/>
											{adventure.country.name}
										</a>
									{/if}
								</div>
							{/if}

							<div class="flex flex-wrap items-center justify-between gap-3">
								{#if adventure && adventure.longitude && adventure.latitude}
									<div class="flex items-center gap-1">
										<span class="font-mono text-sm text-base-content/80">
											{adventure.latitude}, {adventure.longitude}
										</span>
										<div class="tooltip" data-tip={$t('detail.copy_coordinates')}>
											<button
												class="btn btn-ghost btn-xs btn-square"
												aria-label={$t('detail.copy_coordinates')}
												onclick={copyAdventureCoordinates}
											>
												<ContentCopy class="h-4 w-4" />
											</button>
										</div>
										<div class="tooltip" data-tip={$t('detail.copy_map_link')}>
											<button
												class="btn btn-ghost btn-xs btn-square"
												aria-label={$t('detail.copy_map_link')}
												onclick={copyAdventureGoogleMapsLink}
											>
												<LinkVariant class="h-4 w-4" />
											</button>
										</div>
									</div>
									<ExternalMapLinks
										placeName={adventure.name}
										latitude={adventure.latitude}
										longitude={adventure.longitude}
									/>
								{/if}
							</div>
						{/snippet}
					</DetailMapPanel>
				{/if}

				{#if activeTab === 'media'}
					{#if adventure.images.length > 0}
						<DetailCard
							title={$t('adventures.images')}
							hint={$t('detail.photos_hint')}
							icon={ImageMultiple}
						>
							{#snippet actions()}
								<span class="badge badge-ghost">{adventure?.images.length}</span>
							{/snippet}
							<DetailPhotos
								images={adventure.images}
								name={adventure.name}
								onOpen={openImageModal}
								columns={4}
							/>
						</DetailCard>
					{/if}
					{#if adventure.attachments.length > 0}
						<DetailCard
							title={$t('adventures.attachments')}
							hint={$t('adventures.gpx_tip')}
							icon={Paperclip}
						>
							<div class="space-y-2">
								{#each adventure.attachments as attachment}
									<AttachmentCard {attachment} />
								{/each}
							</div>
						</DetailCard>
					{/if}
				{/if}
			</div>

			<!-- Sidebar -->
			<div class="space-y-4 sm:space-y-6">
				<DetailCard title={$t('adventures.basic_information')} icon={InformationOutline}>
					<div class="space-y-4">
						{#if adventure.user}
							<DetailFact label={$t('detail.added_by')} icon={AccountOutline}>
								<span class="flex items-center gap-2">
									<!-- A fixed-size circle: UserAvatar fills its parent. -->
									<span class="h-6 w-6 shrink-0 overflow-hidden rounded-full">
										<UserAvatar
											user={adventure.user}
											alt={adventure.user.username}
											className="h-full w-full rounded-full"
											textClass="text-[10px]"
										/>
									</span>
									{#if adventure.user.public_profile}
										<a href={`/profile/${adventure.user.username}`} class="link link-hover">
											{adventure.user.first_name || adventure.user.username}
											{adventure.user.last_name || ''}
										</a>
									{:else}
										{adventure.user.first_name || adventure.user.username}
										{adventure.user.last_name || ''}
									{/if}
								</span>
							</DetailFact>
						{/if}
						{#if isOwner || (adventure.collections && adventure.collections.length > 0)}
							<DetailFact label={$t('navbar.collections')} icon={Folder}>
								<LocationCollectionChips
									locationId={adventure.id}
									locationName={adventure.name}
									canManage={isOwner}
								/>
							</DetailFact>
						{/if}
						{#if adventurePriceLabel}
							<DetailFact label={$t('adventures.price')} icon={CashMultiple}>
								<span class="font-semibold">{adventurePriceLabel}</span>
							</DetailFact>
						{/if}
						{#if adventure.tags && adventure.tags.length > 0}
							<DetailFact label={$t('adventures.tags')} icon={Tag}>
								<span class="mt-1 flex flex-wrap gap-1">
									{#each adventure.tags as tag}
										<span class="badge badge-outline badge-sm">{tag}</span>
									{/each}
								</span>
							</DetailFact>
						{/if}
						{#if adventure.link}
							<DetailFact label={$t('adventures.link')} icon={LinkVariant}>
								<a
									href={adventure.link}
									class="link link-primary break-all"
									target="_blank"
									rel="noopener noreferrer"
								>
									{adventure.link.length > 40
										? `${adventure.link.slice(0, 40)}...`
										: adventure.link}
								</a>
							</DetailFact>
						{/if}
					</div>
				</DetailCard>

				{#if getTotalActivities(adventure) > 0}
					<DetailCard title={$t('detail.activity_summary')} icon={Run}>
						<div class="grid grid-cols-2 gap-3">
							<DetailStat
								label={$t('adventures.total_activities')}
								value={getTotalActivities(adventure)}
								icon={Run}
							/>
							{#if getTotalDistance(adventure) > 0}
								<DetailStat
									label={$t('adventures.total_distance')}
									value={getTotalDistance(adventure).toFixed(1)}
									unit={measurementUnits.distance}
									icon={Speedometer}
								/>
							{/if}
							{#if getTotalElevationGain(adventure) > 0}
								<DetailStat
									label={$t('detail.total_elevation')}
									value={getTotalElevationGain(adventure).toFixed(0)}
									unit={measurementUnits.elevation}
									icon={TrendingUp}
								/>
							{/if}
						</div>
					</DetailCard>
				{/if}
			</div>
		</div>
	</div>
{/if}

{#if !embedded}
	<LocationPageHead name={data.props.adventure?.name} shareMeta={data.shareMeta} />
{/if}
