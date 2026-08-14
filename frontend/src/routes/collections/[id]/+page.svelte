<script lang="ts">
	import { run } from 'svelte/legacy';

	import type { Collection, ContentImage, Location, Collaborator, Lodging } from '$lib/types';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Lost from '$lib/assets/undraw_lost.svg';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import Calendar from '~icons/mdi/calendar';
	import CalendarComponent from '$lib/components/calendar/Calendar.svelte';
	import EventDetailsModal from '$lib/components/calendar/EventDetailsModal.svelte';
	import { buildCollectionCalendarEvents } from '$lib/calendar/events';
	import type { CalendarDisplayEvent, CalendarTimezoneMode } from '$lib/calendar/types';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import ImageFrame from '$lib/components/ImageFrame.svelte';
	import { normalizeContentImage } from '$lib/images';
	import CollectionAllItems from '$lib/components/collections/CollectionAllItems.svelte';
	import CollectionItineraryPlanner from '$lib/components/collections/CollectionItineraryPlanner.svelte';
	import CollectionRecommendationView from '$lib/components/CollectionRecommendationView.svelte';
	import CollectionMap from '$lib/components/collections/CollectionMap.svelte';
	import CollectionStats from '$lib/components/collections/CollectionStats.svelte';
	import LocationLink from '$lib/components/LocationLink.svelte';
	import { getBasemapUrl } from '$lib';
	import { formatMoney, toMoneyValue, DEFAULT_CURRENCY } from '$lib/money';
	import FolderMultiple from '~icons/mdi/folder-multiple';
	import FormatListBulleted from '~icons/mdi/format-list-bulleted';
	import Timeline from '~icons/mdi/timeline';
	import Map from '~icons/mdi/map';
	import Lightbulb from '~icons/mdi/lightbulb';
	import ChartBar from '~icons/mdi/chart-bar';
	import Plus from '~icons/mdi/plus';
	import FilePdfBox from '~icons/mdi/file-pdf-box';
	import ImageOutline from '~icons/mdi/image-outline';
	import SocialShareModal from '$lib/components/SocialShareModal.svelte';
	import { addToast } from '$lib/toasts';
	import NoteModal from '$lib/components/NoteModal.svelte';
	import ChecklistModal from '$lib/components/ChecklistModal.svelte';
	import LodgingModal from '$lib/components/lodging/LodgingModal.svelte';
	import TransportationModal from '$lib/components/transportation/TransportationModal.svelte';
	import LocationModal from '$lib/components/locations/LocationModal.svelte';
	import UserAvatar from '$lib/components/UserAvatar.svelte';

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	function getCollectionFromPageData(pageData: PageData): Collection | null | undefined {
		return (
			(pageData.props as { collection?: Collection; adventure?: Collection }).collection ??
			(pageData.props as { collection?: Collection; adventure?: Collection }).adventure
		);
	}

	let collection: Collection | undefined = $state();
	let currentSlide = $state(0);
	let notFound: boolean = $state(false);
	let isLocationModalOpen: boolean = $state(false);
	let isLodgingModalOpen: boolean = $state(false);
	let isTransportationModalOpen: boolean = $state(false);
	let isChecklistModalOpen: boolean = $state(false);
	let isNoteModalOpen: boolean = $state(false);
	// Edit placeholders used when creating new items from FAB dropdown
	let adventureToEdit: any = $state(null);
	let transportationToEdit: any = $state(null);
	let noteToEdit: any = $state(null);
	let checklistToEdit: any = $state(null);
	let lodgingToEdit: any = $state(null);
	let heroImages: ContentImage[] = $state([]);
	let modalInitialIndex: number = $state(0);
	let isImageModalOpen: boolean = $state(false);
	let isLocationLinkModalOpen: boolean = $state(false);
	let showCalendarModal = $state(false);

	// Shared helpers for keeping collection sub-items in sync after modal actions
	type CollectionArrayKey = 'locations' | 'transportations' | 'lodging' | 'notes' | 'checklists';

	function ensureCollectionArray(key: CollectionArrayKey) {
		if (!collection) return [] as any[];
		if (!(collection as any)[key]) {
			(collection as any)[key] = [];
		}
		return (collection as any)[key] as any[];
	}

	function upsertCollectionItem(key: CollectionArrayKey, item: any) {
		if (!item || item.id === undefined || item.id === null || !collection) return;
		const items = ensureCollectionArray(key);
		const exists = items.some((entry: any) => String(entry.id) === String(item.id));
		(collection as any)[key] = exists
			? items.map((entry: any) => (String(entry.id) === String(item.id) ? item : entry))
			: [...items, item];
		collection = { ...collection }; // trigger reactivity so cost summary & UI refresh immediately
	}

	// Helper to upload prefilled images (temp ids starting with 'rec-') sequentially
	async function importPrefilledImagesForItem(
		item: any,
		contentType: string,
		collectionKey: 'locations' | 'lodging'
	) {
		if (!item || !item.images || item.images.length === 0) return;
		const prefilled = item.images.filter((img: any) => img.id && String(img.id).startsWith('rec-'));
		if (prefilled.length === 0) return;

		// If we don't have a server id yet, retry a few times because the modal flow may set it asynchronously.
		let attempts = 0;
		const maxAttempts = 6;
		const attemptDelayMs = 2000;

		while ((!item.id || String(item.id).trim() === '') && attempts < maxAttempts) {
			attempts += 1;
			console.debug(`Waiting for server id for item (attempt ${attempts}/${maxAttempts})`);
			// Try to find an updated item in the collection by matching name and collection membership
			const candidates = (collection as any)[collectionKey] || [];
			const match = candidates.find(
				(c: any) =>
					c.name === item.name &&
					(c.collections || c.collection) &&
					collection &&
					String(c.collections || c.collection || '') === String(collection.id)
			);
			if (match && match.id) {
				item.id = match.id;
				break;
			}
			await new Promise((r) => setTimeout(r, attemptDelayMs));
		}

		if (!item.id || String(item.id).trim() === '') {
			console.warn('Unable to obtain server id for item; skipping image import for', item);
			return;
		}

		for (const img of prefilled) {
			try {
				const res = await fetch(img.image);
				if (!res.ok) throw new Error('Failed to fetch image');
				const blob = await res.blob();
				const file = new File([blob], 'image.jpg', { type: blob.type || 'image/jpeg' });
				const form = new FormData();
				form.append('image', file);
				form.append('object_id', item.id);
				form.append('content_type', contentType || 'location');
				form.append('source', img.source || 'google');

				const upload = await fetch('/locations?/image', {
					method: 'POST',
					body: form,
					credentials: 'same-origin'
				});
				if (!upload.ok) throw new Error('Upload failed');
				const newData = await upload.json();
				const newImage = newData && newData.data ? newData.data : newData;

				// Replace temporary image in the item and in the collection
				item.images = item.images.map((i: any) =>
					String(i.id) === String(img.id)
						? normalizeContentImage({
								...newImage,
								id: newImage.id,
								image: newImage.image,
								is_primary: newImage.is_primary || false
							})
						: i
				);

				// Upsert the updated item back into the collection to refresh UI bindings
				upsertCollectionItem(collectionKey, item);
				addToast('success', $t('adventures.image_upload_success'));
			} catch (err) {
				console.error('Error importing prefilled image for item:', err);
				addToast('error', $t('adventures.image_upload_error'));
			}
		}
	}

	// View state from URL params
	type ViewType = 'all' | 'itinerary' | 'map' | 'calendar' | 'recommendations' | 'stats';
	let currentView: ViewType = $state('itinerary');






	// Get default view based on available views
	let defaultView: ViewType = $state('itinerary');


	let isExportingPdf = $state(false);
	let isSocialShareModalOpen = $state(false);

	async function exportCollectionPdf() {
		if (!collection || isExportingPdf) return;
		isExportingPdf = true;
		try {
			const res = await fetch(`/api/collections/${collection.id}/export-pdf/`);
			if (!res.ok) {
				addToast('error', $t('adventures.export_pdf_failed'));
				return;
			}
			const blob = await res.blob();
			const safeName =
				String(collection.name)
					.replace(/[^\w\s-]/g, '')
					.replace(/\s+/g, '_') || 'collection';
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${safeName}_itinerary.pdf`;
			a.click();
			URL.revokeObjectURL(url);
			addToast('success', $t('adventures.export_pdf_success'));
		} catch {
			addToast('error', $t('adventures.export_pdf_failed'));
		} finally {
			isExportingPdf = false;
		}
	}

	// Calendar events from collection data
	let timezoneMode: CalendarTimezoneMode = $state('event');
	let calendarInitialDate: string | null = $state(null);
	let selectedCalendarEvent: CalendarDisplayEvent | null = $state(null);

	const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	const numberLocale = Intl.DateTimeFormat().resolvedOptions().locale;



	type CostCategory = 'lodging' | 'transportation' | 'location';

	type CostEntry = {
		currency: string;
		amount: number;
		category: CostCategory;
	};

	type CurrencyBreakdown = {
		currency: string;
		total: number;
		formattedTotal: string;
		categories: Array<{
			category: CostCategory;
			label: string;
			total: number;
			count: number;
			formattedTotal: string;
		}>;
	};


	let preferredCurrency: string = $state(DEFAULT_CURRENCY);
	let costEntries: CostEntry[] = $state([]);
	let costSummary: CurrencyBreakdown[] = $state([]);
	let pricedItemCount = $state(0);
	let currencyCount = $state(0);



	function buildCostEntries(current: Collection | null, fallbackCurrency: string): CostEntry[] {
		if (!current) return [];
		const entries: CostEntry[] = [];
		const fallback = fallbackCurrency || DEFAULT_CURRENCY;

		(current.locations || []).forEach((item) => {
			const moneyValue = toMoneyValue(item.price, item.price_currency, fallback);
			if (moneyValue.amount === null || moneyValue.amount === undefined) return;
			entries.push({
				currency: moneyValue.currency || fallback,
				amount: moneyValue.amount,
				category: 'location'
			});
		});

		(current.transportations || []).forEach((item) => {
			const moneyValue = toMoneyValue(item.price, item.price_currency, fallback);
			if (moneyValue.amount === null || moneyValue.amount === undefined) return;
			entries.push({
				currency: moneyValue.currency || fallback,
				amount: moneyValue.amount,
				category: 'transportation'
			});
		});

		(current.lodging || []).forEach((item) => {
			const moneyValue = toMoneyValue(item.price, item.price_currency, fallback);
			if (moneyValue.amount === null || moneyValue.amount === undefined) return;
			entries.push({
				currency: moneyValue.currency || fallback,
				amount: moneyValue.amount,
				category: 'lodging'
			});
		});

		return entries;
	}

	function summarizeCostEntries(
		entries: CostEntry[],
		locale: string,
		labels: Record<CostCategory, string>
	): CurrencyBreakdown[] {
		const currencyBuckets: Record<
			string,
			{ total: number; categories: Record<CostCategory, { total: number; count: number }> }
		> = {};

		entries.forEach(({ currency, amount, category }) => {
			if (amount === null || amount === undefined || Number.isNaN(amount)) return;
			const safeCurrency = currency || DEFAULT_CURRENCY;
			if (!currencyBuckets[safeCurrency]) {
				currencyBuckets[safeCurrency] = {
					total: 0,
					categories: {} as Record<CostCategory, { total: number; count: number }>
				};
			}

			const bucket = currencyBuckets[safeCurrency];
			bucket.total += amount;
			bucket.categories[category] = bucket.categories[category] || { total: 0, count: 0 };
			bucket.categories[category].total += amount;
			bucket.categories[category].count += 1;
		});

		const format = (value: number, currency: string) =>
			formatMoney({ amount: value, currency }, locale) || `${currency} ${value}`;

		return Object.entries(currencyBuckets)
			.map(([currency, data]) => {
				const categories = Object.entries(data.categories).map(([categoryKey, info]) => {
					const category = categoryKey as CostCategory;
					return {
						category,
						label: labels[category],
						total: info.total,
						count: info.count,
						formattedTotal: format(info.total, currency)
					};
				});

				return {
					currency,
					total: data.total,
					formattedTotal: format(data.total, currency),
					categories
				};
			})
			.sort((a, b) => a.currency.localeCompare(b.currency));
	}

	function handleCalendarEventClick(event: CalendarDisplayEvent) {
		selectedCalendarEvent = event;
		showCalendarModal = true;
	}

	function closeCalendarModal() {
		showCalendarModal = false;
		selectedCalendarEvent = null;
	}

	function resetCollectionPageUiState() {
		currentSlide = 0;
		isLocationModalOpen = false;
		isLodgingModalOpen = false;
		isTransportationModalOpen = false;
		isChecklistModalOpen = false;
		isNoteModalOpen = false;
		adventureToEdit = null;
		transportationToEdit = null;
		noteToEdit = null;
		checklistToEdit = null;
		lodgingToEdit = null;
		isImageModalOpen = false;
		isLocationLinkModalOpen = false;
		showCalendarModal = false;
		selectedCalendarEvent = null;
		isSocialShareModalOpen = false;
		calendarInitialDate = null;
	}

	function applyCollectionPageData(collectionData: Collection | null | undefined) {
		if (!collectionData) {
			notFound = true;
			collection = undefined;
			resetCollectionPageUiState();
			return;
		}

		notFound = false;
		collection = collectionData;
		resetCollectionPageUiState();
	}


	function goToSlide(index: number) {
		currentSlide = index;
	}

	function closeImageModal() {
		isImageModalOpen = false;
	}

	function openImageModal(imageIndex: number) {
		modalInitialIndex = imageIndex;
		isImageModalOpen = true;
	}

	function formatDate(dateString: string | null) {
		if (!dateString) return '';
		return DateTime.fromISO(dateString).toLocaleString(DateTime.DATE_MED);
	}

	function collaboratorDisplayName(person: Collaborator | null | undefined): string {
		if (!person) return '';
		const fullName = [person.first_name, person.last_name].filter(Boolean).join(' ').trim();
		return fullName || person.username;
	}

	function switchView(view: ViewType) {
		const url = new URL($page.url);
		url.searchParams.set('view', view);
		goto(url.toString(), { replaceState: true, noScroll: true });
	}

	function closeLocationLinkModal() {
		isLocationLinkModalOpen = false;
	}

	function handleOpenEdit(event: CustomEvent<{ type: CollectionArrayKey; item: any }>) {
		const { type, item } = event.detail;

		switch (type) {
			case 'locations':
				adventureToEdit = item;
				isLocationModalOpen = true;
				break;
			case 'transportations':
				transportationToEdit = item;
				isTransportationModalOpen = true;
				break;
			case 'lodging':
				lodgingToEdit = item;
				isLodgingModalOpen = true;
				break;
			case 'notes':
				noteToEdit = item;
				isNoteModalOpen = true;
				break;
			case 'checklists':
				checklistToEdit = item;
				isChecklistModalOpen = true;
				break;
			default:
				break;
		}
	}

	async function handleLocationAdded(event: CustomEvent<Location>) {
		// Link the location to this collection
		const location = event.detail;
		if (!collection) return;

		try {
			const response = await fetch(`/api/locations/${location.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					collections: [...(location.collections || []), collection.id]
				})
			});

			if (response.ok) {
				// Keep modal open so user can link more locations.
				// Update local collection state so UI reflects the new link immediately.
				try {
					if (!collection.locations) collection.locations = [];
					// Avoid duplicates
					const exists = collection.locations.some((l) => String(l.id) === String(location.id));
					if (!exists) {
						collection.locations = [...collection.locations, location];
					}
				} catch (e) {
					// if collection shape is unexpected, ignore and continue
					console.warn('Unable to update local collection.locations', e);
				}

				// Show success message but do NOT close the modal or reload the page
				addToast(
					'success',
					$t('adventures.collection_link_location_success') || 'Location added successfully'
				);
			} else {
				addToast(
					'error',
					$t('adventures.collection_link_location_error') || 'Failed to add location'
				);
			}
		} catch (error) {
			console.error('Error linking location:', error);
			addToast(
				'error',
				$t('adventures.collection_link_location_error') || 'Failed to add location'
			);
		}
	}
	// Determine if this is a folder view (no dates) or itinerary view (has dates)
	let isFolderView = $derived(!collection?.start_date && !collection?.end_date);
	// Gather hero images with collection primary image first when available
	run(() => {
		heroImages = (() => {
			const primary = collection?.primary_image ? [collection.primary_image] : [];
			const locationImages = collection?.locations?.flatMap((loc) => loc.images || []) || [];
			const seen = new Set<string>();

			return [...primary, ...locationImages].filter((img) => {
				if (!img || !img.image) return false;
				const key = String(img.id ?? img.image);
				if (seen.has(key)) return false;
				seen.add(key);
				return true;
			});
		})();
	});
	// Determine whether current user can modify the collection (owner or shared user)
	let canModifyCollection = $derived((() => {
		const u = data.user as any;
		if (!u || !collection) return false;

		const userUuid = u.uuid || null;
		const username = u.username || null;
		const pk = u.pk !== undefined && u.pk !== null ? String(u.pk) : null;
		const owner = collection.user;

		// Direct matches: UUID (primary), username, or numeric pk (stringified)
		if (userUuid && owner === userUuid) return true;
		if (username && owner === username) return true;
		if (pk && owner === pk) return true;

		// Shared with may contain UUIDs or other identifiers
		if (collection.shared_with && Array.isArray(collection.shared_with)) {
			if (userUuid && collection.shared_with.includes(userUuid)) return true;
			if (username && collection.shared_with.includes(username)) return true;
			if (pk && collection.shared_with.includes(pk)) return true;
		}

		return false;
	})());
	// Public collections: anyone can export/share; private: owner or shared users only
	let canExportCollection = $derived(!!collection?.is_public || canModifyCollection);
	// Define available views based on collection type
	let availableViews = $derived({
		all: true, // Always available
		itinerary: !isFolderView, // Only for collections with dates
		map:
			collection?.locations?.some((l) => l.latitude && l.longitude) ||
			collection?.lodging?.some((l) => l.latitude && l.longitude) ||
			collection?.transportations?.some(
				(t) =>
					(t.origin_latitude && t.origin_longitude) ||
					(t.destination_latitude && t.destination_longitude)
			) ||
			false,
		calendar: !isFolderView,
		recommendations: canModifyCollection,
		stats: true
	});
	run(() => {
		defaultView = (availableViews.itinerary ? 'itinerary' : 'all') as ViewType;
	});
	// Read view from URL params and validate it's available
	run(() => {
		const view = $page.url.searchParams.get('view') as ViewType;
		if (
			view &&
			['all', 'itinerary', 'map', 'calendar', 'recommendations', 'stats'].includes(view) &&
			availableViews[view]
		) {
			currentView = view;
		} else {
			currentView = defaultView;
		}
	});
	let calendarTimezoneLabels = $derived({
		eventTimezone: $t('collections.event_timezone'),
		localTimezone: $t('collections.local_timezone')
	});
	let collectionEvents = $derived(collection
		? buildCollectionCalendarEvents(
				collection,
				timezoneMode,
				userTimezone,
				calendarTimezoneLabels,
				(key) => $t(key)
			)
		: []);
	// Localized category labels - computed reactively from i18n
	let costCategoryLabels = $derived({
		lodging: $t('adventures.lodging') || 'Lodging',
		transportation: $t('adventures.transportation') || 'Transportation',
		location: $t('locations.locations') || 'Locations'
	});
	run(() => {
		preferredCurrency = (data.user as any)?.default_currency || DEFAULT_CURRENCY;
	});
	run(() => {
		costEntries = buildCostEntries(collection ?? null, preferredCurrency);
	});
	run(() => {
		costSummary = summarizeCostEntries(costEntries, numberLocale, costCategoryLabels);
	});
	run(() => {
		pricedItemCount = costEntries.length;
	});
	run(() => {
		currencyCount = costSummary.length;
	});
	run(() => {
		if (!calendarInitialDate && collectionEvents.length) {
			const collectionRangeStart = collection?.start_date
				? DateTime.fromISO(collection.start_date)
				: null;
			const collectionRangeEnd = collection?.end_date ? DateTime.fromISO(collection.end_date) : null;

			const validEvents = collectionEvents
				.map((ev) => ({ date: DateTime.fromISO(ev.start), event: ev }))
				.filter(({ date }) => date.isValid)
				.sort((a, b) => a.date.toMillis() - b.date.toMillis());

			const inCollectionRange = validEvents.filter(({ date }) => {
				if (collectionRangeStart?.isValid && date < collectionRangeStart.startOf('day')) return false;
				if (collectionRangeEnd?.isValid && date > collectionRangeEnd.endOf('day')) return false;
				return true;
			});

			const chosenDate = (inCollectionRange[0] || validEvents[0])?.date;

			calendarInitialDate = chosenDate?.toISODate() || calendarInitialDate;
		}
	});
	run(() => {
		applyCollectionPageData(getCollectionFromPageData(data));
	});
</script>

{#snippet collaboratorAvatar(person: Collaborator)}
	<div
		class="w-9 h-9 rounded-full ring-3 ring-base-200 ring-offset-base-100 ring-offset-2 overflow-hidden"
	>
		<UserAvatar
			user={person}
			alt={collaboratorDisplayName(person)}
			className="w-9 h-9 rounded-full"
			textClass="text-xs"
		/>
	</div>
{/snippet}

{#if notFound}
	<div class="hero min-h-screen bg-gradient-to-br from-base-200 to-base-300 overflow-x-hidden">
		<div class="hero-content text-center">
			<div class="max-w-md">
				<img src={Lost} alt="Lost" class="w-64 mx-auto mb-8 opacity-80" />
				<h1 class="text-5xl font-bold text-primary mb-4">{$t('collections.not_found')}</h1>
				<button class="btn btn-primary btn-lg" onclick={() => goto('/')}>
					{$t('adventures.homepage')}
				</button>
			</div>
		</div>
	</div>
{/if}

{#if isImageModalOpen && collection}
	<ImageDisplayModal
		images={heroImages}
		initialIndex={modalInitialIndex}
		name={collection.name}
		on:close={closeImageModal}
	/>
{/if}

{#if isSocialShareModalOpen && collection && canExportCollection}
	<SocialShareModal
		type="collection"
		id={collection.id}
		name={collection.name}
		isPublic={!!collection.is_public}
		on:close={() => (isSocialShareModalOpen = false)}
	/>
{/if}

{#if isLocationLinkModalOpen && collection}
	<LocationLink
		user={data.user}
		collectionId={collection.id}
		on:close={closeLocationLinkModal}
		on:add={handleLocationAdded}
	/>
{/if}

{#if isNoteModalOpen && collection}
	<NoteModal
		on:close={() => {
			noteToEdit = null;
			isNoteModalOpen = false;
		}}
		note={noteToEdit}
		{collection}
		user={data.user}
		on:save={(e) => {
			upsertCollectionItem('notes', e.detail);
			noteToEdit = null;
			isNoteModalOpen = false;
		}}
		on:create={(e) => {
			upsertCollectionItem('notes', e.detail);
			noteToEdit = null;
			isNoteModalOpen = false;
		}}
	/>
{/if}

{#if isLocationModalOpen && collection}
	<LocationModal
		on:close={() => {
			adventureToEdit = null;
			isLocationModalOpen = false;
		}}
		user={data.user}
		{collection}
		locationToEdit={adventureToEdit}
		on:save={(e) => {
			upsertCollectionItem('locations', e.detail);
			adventureToEdit = null;
			isLocationModalOpen = false;
		}}
		on:create={(e) => {
			upsertCollectionItem('locations', e.detail);
			adventureToEdit = null;
			isLocationModalOpen = false;
		}}
	/>
{/if}

{#if isTransportationModalOpen && collection}
	<TransportationModal
		on:close={() => {
			transportationToEdit = null;
			isTransportationModalOpen = false;
		}}
		user={data.user}
		{collection}
		{transportationToEdit}
		on:save={(e) => {
			upsertCollectionItem('transportations', e.detail);
			transportationToEdit = null;
			isTransportationModalOpen = false;
		}}
		on:create={(e) => {
			upsertCollectionItem('transportations', e.detail);
			transportationToEdit = null;
			isTransportationModalOpen = false;
		}}
	/>
{/if}

{#if isChecklistModalOpen && collection}
	<ChecklistModal
		on:close={() => {
			checklistToEdit = null;
			isChecklistModalOpen = false;
		}}
		{collection}
		user={data.user}
		checklist={checklistToEdit}
		on:save={(e) => {
			upsertCollectionItem('checklists', e.detail);
			checklistToEdit = null;
			isChecklistModalOpen = false;
		}}
		on:create={(e) => {
			upsertCollectionItem('checklists', e.detail);
			checklistToEdit = null;
			isChecklistModalOpen = false;
		}}
	/>
{/if}

{#if isLodgingModalOpen && collection}
	<LodgingModal
		on:close={() => {
			lodgingToEdit = null;
			isLodgingModalOpen = false;
		}}
		{collection}
		user={data.user}
		{lodgingToEdit}
		on:save={(e) => {
			upsertCollectionItem('lodging', e.detail);
			lodgingToEdit = null;
			isLodgingModalOpen = false;
		}}
		on:create={(e) => {
			upsertCollectionItem('lodging', e.detail);
			lodgingToEdit = null;
			isLodgingModalOpen = false;
		}}
	/>
{/if}

<EventDetailsModal
	show={showCalendarModal}
	event={selectedCalendarEvent}
	{timezoneMode}
	{userTimezone}
	onClose={closeCalendarModal}
/>

{#if !collection && !notFound}
	<div class="hero min-h-screen overflow-x-hidden">
		<div class="hero-content">
			<span class="loading loading-spinner w-24 h-24 text-primary"></span>
		</div>
	</div>
{/if}

{#if collection}
	<!-- Hero Section -->
	<div class="relative">
		<div
			class="hero min-h-[60vh] relative overflow-hidden"
			class:min-h-[30vh]={!heroImages || heroImages.length === 0}
		>
			<!-- Background: Images or Gradient -->
			{#if heroImages && heroImages.length > 0}
				<div class="hero-overlay bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
				{#each heroImages as image, i}
					<div
						class="absolute inset-0 transition-opacity duration-500"
						class:opacity-100={i === currentSlide}
						class:opacity-0={i !== currentSlide}
					>
						<button
							class="w-full h-full p-0 bg-transparent border-0"
							onclick={() => openImageModal(i)}
							aria-label={`View full image of ${collection.name}`}
						>
							<ImageFrame source={image.source} className="w-full h-full">
								<img src={image.image} class="w-full h-full object-cover" alt={collection.name} />
							</ImageFrame>
						</button>
					</div>
				{/each}
			{:else}
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 to-secondary/20"></div>
			{/if}

			<!-- Content -->
			<div class="hero-content relative z-10 text-center" class:text-white={heroImages?.length > 0}>
				<div class="max-w-4xl">
					<h1 class="text-6xl font-bold mb-4 drop-shadow-lg flex items-center justify-center gap-4">
						{#if isFolderView}
							<FolderMultiple class="w-16 h-16" />
						{/if}
						{collection.name}
					</h1>

					<!-- Quick Info Badges -->
					<div class="flex flex-wrap justify-center gap-4 mb-6">
						{#if collection.is_public}
							<div class="badge badge-lg badge-success font-semibold px-4 py-3">
								🌍 {$t('adventures.public')}
							</div>
						{:else}
							<div class="badge badge-lg badge-warning font-semibold px-4 py-3">
								🔒 {$t('adventures.private')}
							</div>
						{/if}
						{#if collection.locations && collection.locations.length > 0}
							<div class="badge badge-lg badge-primary font-semibold px-4 py-3">
								📍 {collection.locations.length}
								{collection.locations.length === 1
									? $t('locations.location')
									: $t('locations.locations')}
							</div>
						{/if}
						{#if collection.start_date || collection.end_date}
							<div class="badge badge-lg badge-accent font-semibold px-4 py-3">
								<Calendar class="w-5 h-5 mr-1" />
								{#if collection.start_date && collection.end_date}
									{formatDate(collection.start_date)} - {formatDate(collection.end_date)}
								{:else if collection.start_date}
									From {formatDate(collection.start_date)}
								{:else if collection.end_date}
									Until {formatDate(collection.end_date)}
								{/if}
							</div>
						{/if}
						{#if collection.is_archived}
							<div class="badge badge-lg badge-neutral font-semibold px-4 py-3">
								📦 {$t('adventures.archived')}
							</div>
						{/if}
					</div>

					<!-- Image Navigation (only shown when multiple images exist) -->
					{#if heroImages && heroImages.length > 1}
						<div class="w-full max-w-md mx-auto">
							<!-- Navigation arrows and current position -->
							<div class="flex items-center justify-center gap-4 mb-3">
								<button
									onclick={() =>
										goToSlide(currentSlide > 0 ? currentSlide - 1 : heroImages.length - 1)}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.previous_image')}
								>
									❮
								</button>

								<div class="text-sm font-medium bg-black/50 px-3 py-1 rounded-full">
									{currentSlide + 1} / {heroImages.length}
								</div>

								<button
									onclick={() =>
										goToSlide(currentSlide < heroImages.length - 1 ? currentSlide + 1 : 0)}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.next_image')}
								>
									❯
								</button>
							</div>

							<!-- Dot navigation -->
							{#if heroImages.length <= 12}
								<div class="flex justify-center gap-2 flex-wrap">
									{#each heroImages as _, i}
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
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Main Content -->
	<div class="container mx-auto px-2 sm:px-4 py-6 sm:py-8 max-w-7xl">
		<!-- View Switcher -->
		<div class="flex flex-col sm:flex-row items-center justify-center gap-3 mb-6">
			<div class="join">
				{#if availableViews.all}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'all'}
						onclick={() => switchView('all')}
					>
						<FormatListBulleted class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">{$t('collections.all_items')}</span>
					</button>
				{/if}
				{#if availableViews.itinerary}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'itinerary'}
						onclick={() => switchView('itinerary')}
					>
						<Timeline class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">{$t('adventures.itinerary')}</span>
					</button>
				{/if}
				{#if availableViews.map}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'map'}
						onclick={() => switchView('map')}
					>
						<Map class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">{$t('navbar.map')}</span>
					</button>
				{/if}
				{#if availableViews.calendar}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'calendar'}
						onclick={() => switchView('calendar')}
					>
						<Calendar class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">{$t('navbar.calendar')}</span>
					</button>
				{/if}
				{#if availableViews.recommendations}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'recommendations'}
						onclick={() => switchView('recommendations')}
					>
						<Lightbulb class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">{$t('recomendations.recommendations')}</span>
					</button>
				{/if}
				{#if availableViews.stats}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'stats'}
						onclick={() => switchView('stats')}
					>
						<ChartBar class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">{$t('collections.statistics')}</span>
					</button>
				{/if}
			</div>
			{#if canExportCollection}
				<div class="flex flex-wrap gap-2">
					<button
						class="btn btn-outline btn-primary gap-2"
						onclick={() => (isSocialShareModalOpen = true)}
					>
						<ImageOutline class="w-5 h-5" aria-hidden="true" />
						<span>{$t('social_share.share_externally')}</span>
					</button>
					<button
						class="btn btn-outline btn-primary gap-2"
						onclick={exportCollectionPdf}
						disabled={isExportingPdf}
						aria-busy={isExportingPdf}
					>
						<FilePdfBox class="w-5 h-5" aria-hidden="true" />
						<span>{isExportingPdf ? '...' : $t('adventures.export_pdf')}</span>
					</button>
				</div>
			{/if}
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-4 gap-6 sm:gap-10">
			<!-- Left Column - Main Content -->
			<div class="lg:col-span-3 space-y-8 sm:space-y-10">
				<!-- Description Card (always visible) -->
				{#if collection.description}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">📝 Description</h2>
							<article class="prose max-w-none">
								{@html DOMPurify.sanitize(renderMarkdown(collection.description))}
							</article>
						</div>
					</div>
				{/if}

				<!-- All Items View -->
				{#if currentView === 'all'}
					<CollectionAllItems
						bind:collection
						user={data.user}
						{isFolderView}
						on:openEdit={handleOpenEdit}
					/>
				{/if}

				<!-- Itinerary View -->
				{#if currentView === 'itinerary'}
					<CollectionItineraryPlanner
						bind:collection
						user={data.user}
						canModify={canModifyCollection}
					/>
				{/if}

				<!-- Stats View -->
				{#if currentView === 'stats'}
					<CollectionStats {collection} user={data.user} />
				{/if}

				<!-- Map View -->
				{#if currentView === 'map'}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">🗺️ {$t('navbar.map')}</h2>
							<div class="rounded-lg overflow-hidden shadow-lg">
								<CollectionMap bind:collection user={data.user} canModify={canModifyCollection} />
							</div>
						</div>
					</div>
				{/if}

				<!-- Calendar View -->
				{#if currentView === 'calendar'}
					{#if collectionEvents.length === 0}
						<div class="card bg-base-200 shadow-xl">
							<div class="card-body">
								<h2 class="card-title text-2xl mb-4">📆 {$t('navbar.calendar')}</h2>
								<p class="text-base-content/70">{$t('collections.no_calendar_events')}</p>
							</div>
						</div>
					{:else}
						<div class="card bg-base-200 shadow-xl">
							<div class="card-body space-y-4">
								<h2 class="card-title text-2xl flex items-center gap-2">
									📆 {$t('navbar.calendar')}
								</h2>
								<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
									<div class="flex items-center gap-2 text-sm text-base-content/80">
										<span class="badge badge-ghost"
											>{collectionEvents.length} {$t('collections.events')}</span
										>
									</div>
									<div class="flex items-center gap-2">
										<span class="text-xs opacity-70">{$t('collections.times_shown_in')}</span>
										<div class="join">
											<button
												class="btn btn-xs sm:btn-sm join-item"
												class:btn-active={timezoneMode === 'event'}
												onclick={() => (timezoneMode = 'event')}
											>
												{$t('collections.event_timezone')}
											</button>
											<button
												class="btn btn-xs sm:btn-sm join-item"
												class:btn-active={timezoneMode === 'local'}
												onclick={() => (timezoneMode = 'local')}
											>
												{$t('collections.local_timezone')}
											</button>
										</div>
									</div>
								</div>
								<p class="text-xs text-base-content/70">
									{$t('collections.event_timezone_desc')}
									{userTimezone}.
								</p>
								<CalendarComponent
									events={collectionEvents}
									initialDate={calendarInitialDate}
									bare={true}
									on:eventClick={(e) => handleCalendarEventClick(e.detail)}
								/>
							</div>
						</div>
					{/if}
				{/if}

				<!-- Recommendations View -->
				{#if currentView === 'recommendations' && canModifyCollection}
					<CollectionRecommendationView bind:collection user={data.user} />
				{/if}
			</div>

			<!-- Right Column - Sidebar -->
			<div class="lg:col-span-1 space-y-4 sm:space-y-6">
				<!-- Progress Tracker (only for folder views) -->
				{#if isFolderView && collection.locations && collection.locations.length > 0}
					{@const visitedCount = collection.locations.filter((l) => l.is_visited).length}
					{@const totalCount = collection.locations.length}
					{@const progressPercent = totalCount > 0 ? (visitedCount / totalCount) * 100 : 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">✅ {$t('worldtravel.progress')}</h3>
							<div class="space-y-4">
								<div class="flex justify-between text-sm">
									<span class="opacity-70">Visited</span>
									<span class="font-bold">{visitedCount} / {totalCount}</span>
								</div>
								<div class="w-full bg-base-300 rounded-full h-4 overflow-hidden">
									<div
										class="bg-success h-full transition-all duration-500 rounded-full flex items-center justify-center text-xs font-bold text-success-content"
										style="width: {progressPercent}%"
									>
										{#if progressPercent > 20}
											{Math.round(progressPercent)}%
										{/if}
									</div>
								</div>
								{#if progressPercent < 20 && progressPercent > 0}
									<div class="text-center text-xs opacity-70">{Math.round(progressPercent)}%</div>
								{/if}
								<div class="grid grid-cols-2 gap-2 pt-2">
									<div class="stat bg-base-300 rounded-lg p-3">
										<div class="stat-title text-xs">{$t('adventures.visited')}</div>
										<div class="stat-value text-lg text-success">{visitedCount}</div>
									</div>
									<div class="stat bg-base-300 rounded-lg p-3">
										<div class="stat-title text-xs">{$t('adventures.planned')}</div>
										<div class="stat-value text-lg text-warning">{totalCount - visitedCount}</div>
									</div>
								</div>
								{#if visitedCount === totalCount && totalCount > 0}
									<div class="alert alert-success text-sm py-2">
										<span>🎉 {$t('worldtravel.all_locations_visited')}</span>
									</div>
								{/if}
							</div>
						</div>
					</div>
				{/if}

				<!-- Quick Info Card -->
				<div class="card bg-base-200 shadow-xl">
					<div class="card-body">
						<h3 class="card-title text-lg mb-4">ℹ️ {$t('adventures.basic_information')}</h3>
						<div class="space-y-3">
							{#if collection.start_date || collection.end_date}
								<div>
									<div class="text-sm opacity-70 mb-1">{$t('adventures.dates')}</div>
									<div class="text-sm">
										{#if collection.start_date && collection.end_date}
											{formatDate(collection.start_date)} - {formatDate(collection.end_date)}
										{:else if collection.start_date}
											From {formatDate(collection.start_date)}
										{:else if collection.end_date}
											Until {formatDate(collection.end_date)}
										{/if}
									</div>
								</div>
							{/if}
							{#if collection.link}
								<div>
									<div class="text-sm opacity-70 mb-1">{$t('adventures.link')}</div>
									<a
										href={collection.link}
										class="link link-primary text-sm break-all"
										target="_blank"
									>
										{collection.link.length > 30
											? `${collection.link.slice(0, 30)}...`
											: collection.link}
									</a>
								</div>
							{/if}
							{#if collection.collaborators && collection.collaborators.length > 0}
								<div>
									<div class="text-sm opacity-70 mb-1">{$t('collection.collaborators')}</div>
									<div class="avatar-group -space-x-3">
										{#each collection.collaborators as person (person.uuid)}
											{#if person.public_profile}
												<a
													href={`/profile/${person.username}`}
													class="avatar tooltip"
													data-tip={collaboratorDisplayName(person)}
													title={collaboratorDisplayName(person)}
													tabindex="0"
												>
													{@render collaboratorAvatar(person)}
												</a>
											{:else}
												<div class="avatar tooltip" data-tip={collaboratorDisplayName(person)}>
													{@render collaboratorAvatar(person)}
												</div>
											{/if}
										{/each}
									</div>
								</div>
							{:else if collection.shared_with && collection.shared_with.length > 0}
								<div>
									<div class="text-sm opacity-70 mb-1">{$t('share.shared_with')}</div>
									<div class="flex flex-wrap gap-1">
										{#each collection.shared_with as username}
											<span class="badge badge-sm badge-outline">{username}</span>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Cost Summary Card -->
				<div class="card bg-base-200 shadow-xl">
					<div class="card-body space-y-4">
						<div class="flex items-center justify-between">
							<h3 class="card-title text-lg">💰 {$t('collections.trip_costs')}</h3>
							{#if currencyCount > 0}
								<span class="badge badge-primary badge-sm">
									{currencyCount}
									{currencyCount === 1 ? $t('collections.currency') : $t('collections.currencies')}
								</span>
							{/if}
						</div>

						{#if pricedItemCount === 0}
							<p class="text-sm opacity-70">
								{$t('collections.no_priced_items')}
							</p>
						{:else}
							<div class="space-y-3">
								{#each costSummary as summary}
									<div class="bg-base-300 rounded-lg p-3 space-y-2">
										<div class="flex items-center justify-between">
											<div class="flex items-center gap-2">
												<span class="badge badge-outline badge-sm">{summary.currency}</span>
												<span class="text-xs opacity-70">{$t('adventures.total')}</span>
											</div>
											<span class="text-lg font-bold">{summary.formattedTotal}</span>
										</div>
										<div class="grid grid-cols-1 gap-1 text-sm">
											{#each summary.categories as category}
												<div class="flex items-center justify-between">
													<span class="opacity-70">{category.label} ({category.count})</span>
													<span class="font-semibold">{category.formattedTotal}</span>
												</div>
											{/each}
										</div>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>

				<!-- Collection Stats Card -->
				<div class="card bg-base-200 shadow-xl">
					<div class="card-body">
						<h3 class="card-title text-lg mb-4">📊 {$t('collections.statistics')}</h3>
						<div class="stats stats-vertical bg-base-100 shadow-sm">
							{#if collection.locations}
								<div class="stat">
									<div class="stat-title">{$t('locations.locations')}</div>
									<div class="stat-value text-2xl">{collection.locations.length}</div>
								</div>
							{/if}
							{#if collection.transportations}
								<div class="stat">
									<div class="stat-title">{$t('adventures.transportations')}</div>
									<div class="stat-value text-2xl">{collection.transportations.length}</div>
								</div>
							{/if}
							{#if collection.lodging}
								<div class="stat">
									<div class="stat-title">{$t('adventures.lodging')}</div>
									<div class="stat-value text-2xl">{collection.lodging.length}</div>
								</div>
							{/if}
							{#if collection.notes}
								<div class="stat">
									<div class="stat-title">{$t('adventures.notes')}</div>
									<div class="stat-value text-2xl">{collection.notes.length}</div>
								</div>
							{/if}
							{#if collection.checklists}
								<div class="stat">
									<div class="stat-title">{$t('adventures.checklists')}</div>
									<div class="stat-value text-2xl">{collection.checklists.length}</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Additional Images (from locations) -->
				{#if heroImages && heroImages.length > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">🖼️ {$t('adventures.images')}</h3>
							<div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
								{#each heroImages.slice(0, 12) as image, index}
									<ImageFrame source={image.source} className="relative group">
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
							{#if heroImages.length > 12}
								<div class="text-center mt-2 text-sm opacity-70">
									+{heroImages.length - 12} more {heroImages.length - 12 === 1 ? 'image' : 'images'}
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Floating Action Button (FAB) - Only shown if user can modify collection -->
{#if collection && canModifyCollection && !collection.is_archived}
	<div class="fixed bottom-6 right-6 z-[999]">
		<div class="dropdown dropdown-top dropdown-end">
			<div
				tabindex="0"
				role="button"
				class="btn btn-primary btn-circle w-16 h-16 shadow-2xl hover:shadow-primary/25 transition-all duration-200"
			>
				<Plus class="w-8 h-8" />
			</div>
			<ul
				tabindex="-1"
				class="dropdown-content z-[1] menu p-4 shadow-sm bg-base-300 text-base-content rounded-box w-52 gap-4"
			>
				<p class="text-center font-bold text-lg">{$t('adventures.link_new')}</p>
				<!-- Link existing location to collection -->
				<button
					class="btn btn-primary"
					onclick={() => {
						isLocationLinkModalOpen = true;
					}}
				>
					{$t('locations.location')}
				</button>

				<p class="text-center font-bold text-lg">{$t('adventures.add_new')}</p>
				<button
					class="btn btn-primary"
					onclick={() => {
						isLocationModalOpen = true;
						adventureToEdit = null;
					}}
				>
					{$t('locations.location')}
				</button>

				<button
					class="btn btn-primary"
					onclick={() => {
						transportationToEdit = null;
						isTransportationModalOpen = true;
					}}
				>
					{$t('adventures.transportation')}
				</button>

				<button
					class="btn btn-primary"
					onclick={() => {
						isNoteModalOpen = true;
						noteToEdit = null;
					}}
				>
					{$t('adventures.note')}
				</button>

				<button
					class="btn btn-primary"
					onclick={() => {
						checklistToEdit = null;
						isChecklistModalOpen = true;
					}}
				>
					{$t('adventures.checklist')}
				</button>

				<button
					class="btn btn-primary"
					onclick={() => {
						lodgingToEdit = null;
						isLodgingModalOpen = true;
					}}
				>
					{$t('adventures.lodging')}
				</button>
			</ul>
		</div>
	</div>
{/if}

<svelte:head>
	<title>
		{collection && collection.name ? `${collection.name}` : 'Collection'}
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
		<meta name="description" content="View collection details and locations" />
	{/if}
</svelte:head>
