<script lang="ts">
	import { run } from 'svelte/legacy';
	import { untrack } from 'svelte';
	import type { Component } from 'svelte';

	import type { Collection, ContentImage, Location, Collaborator, Lodging } from '$lib/types';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Lost from '$lib/assets/undraw_lost.svg';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import Calendar from '~icons/mdi/calendar';
	import { dateFormatFromUser, formatDisplayDate } from '$lib/dateFormat';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import ImageFrame from '$lib/components/ImageFrame.svelte';
	import { normalizeContentImage } from '$lib/images';
	import CollectionAllItems from '$lib/components/collections/CollectionAllItems.svelte';
	import TripWorkspace from '$lib/components/collections/TripWorkspace.svelte';
	import LinkItemsModal from '$lib/components/collections/LinkItemsModal.svelte';
	import type { LinkScope } from '$lib/components/collections/LinkItemsModal.svelte';
	import { placementType, showsDayPlanner, type PlanObjectType } from '$lib/collections/plan';
	import CollectionRecommendationView from '$lib/components/collections/CollectionRecommendationView.svelte';
	import CollectionMap from '$lib/components/collections/CollectionMap.svelte';
	import CollectionStats from '$lib/components/collections/CollectionStats.svelte';
	import CollectionCosts from '$lib/components/collections/CollectionCosts.svelte';
	import CollectionCalendar from '$lib/components/collections/CollectionCalendar.svelte';
	import { DEFAULT_CURRENCY } from '$lib/money';
	import FolderMultiple from '~icons/mdi/folder-multiple';
	import FormatListBulleted from '~icons/mdi/format-list-bulleted';
	import Timeline from '~icons/mdi/timeline';
	import BookOpenVariant from '~icons/mdi/book-open-variant';
	import Lightbulb from '~icons/mdi/lightbulb';
	import ChartBar from '~icons/mdi/chart-bar';
	import Plus from '~icons/mdi/plus';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import FilePdfBox from '~icons/mdi/file-pdf-box';
	import ImageOutline from '~icons/mdi/image-outline';
	import ChevronLeft from '~icons/mdi/chevron-left';
	import ChevronRight from '~icons/mdi/chevron-right';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import ImageMultiple from '~icons/mdi/image-multiple';
	import InformationOutline from '~icons/mdi/information-outline';
	import TextBoxOutline from '~icons/mdi/text-box-outline';
	import CheckCircleOutline from '~icons/mdi/check-circle-outline';
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

	const dateFormat = $derived(dateFormatFromUser(data.user));

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
	let locationModalInitialStep: 'visits' | null = $state(null);
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
	let linkScope = $state<LinkScope | null>(null);

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
	type ViewType =
		| 'all'
		| 'plan'
		| 'read'
		| 'map'
		| 'calendar'
		| 'recommendations'
		| 'stats'
		| 'budget';
	let currentView: ViewType = $state('plan');
	// How many view tabs fit in the row. The rest collapse into More.
	let visibleTabCount = $state(Number.POSITIVE_INFINITY);

	type ViewTab = {
		id: ViewType;
		label: string;
		icon: Component<Record<string, unknown>>;
	};

	const viewTabClass =
		'inline-flex h-8 shrink-0 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-full px-3 text-sm font-medium transition-colors';

	function tabButtonClass(active: boolean) {
		return [
			viewTabClass,
			active
				? 'bg-primary text-primary-content shadow-sm'
				: 'text-base-content/70 hover:bg-base-100 hover:text-base-content'
		];
	}

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

	const preferredCurrency = $derived(
		(data.user as { default_currency?: string } | null)?.default_currency || DEFAULT_CURRENCY
	);

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
		linkScope = null;
		isSocialShareModalOpen = false;
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

	function showPreviousImage() {
		if (heroImages.length < 2) return;
		const index = Math.min(currentSlide, heroImages.length - 1);
		goToSlide(index > 0 ? index - 1 : heroImages.length - 1);
	}

	function showNextImage() {
		if (heroImages.length < 2) return;
		const index = Math.min(currentSlide, heroImages.length - 1);
		goToSlide(index < heroImages.length - 1 ? index + 1 : 0);
	}

	function fitTabCount(node: HTMLElement): number | null {
		const row = node.querySelector<HTMLElement>('[data-measure-row]');
		if (!row) return null;
		const tabs = [...row.querySelectorAll<HTMLElement>('[data-tab-measure]')];
		const more = row.querySelector<HTMLElement>('[data-more-measure]');
		if (tabs.length === 0) return 0;

		const styles = getComputedStyle(row);
		const pad =
			(Number.parseFloat(styles.paddingLeft) || 0) + (Number.parseFloat(styles.paddingRight) || 0);
		const gap = Number.parseFloat(styles.columnGap || styles.gap) || 0;
		const limit = node.clientWidth - pad;
		const moreWidth = more?.getBoundingClientRect().width ?? 0;
		let used = 0;
		let count = 0;

		for (let index = 0; index < tabs.length; index += 1) {
			const width = tabs[index].getBoundingClientRect().width;
			const remaining = tabs.length - index - 1;
			const next = used + (count > 0 ? gap : 0) + width;
			const reserve = remaining > 0 ? gap + moreWidth : 0;
			if (next + reserve <= limit + 1) {
				used = next;
				count += 1;
			} else {
				break;
			}
		}

		return count;
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
		return formatDisplayDate(dateString, dateFormat);
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

	async function handleOpenEdit(
		event: CustomEvent<{ type: CollectionArrayKey; item: any; initialStep?: 'visits' | null }>
	) {
		const { type, item, initialStep = null } = event.detail;

		switch (type) {
			case 'locations': {
				locationModalInitialStep = initialStep;
				if (initialStep === 'visits' && item?.id) {
					try {
						const res = await fetch(`/api/locations/${item.id}/`);
						adventureToEdit = res.ok ? await res.json() : item;
					} catch {
						adventureToEdit = item;
					}
				} else {
					adventureToEdit = item;
				}
				isLocationModalOpen = true;
				break;
			}
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
	function alreadyPlaced(
		type: PlanObjectType,
		objectId: string,
		dayIndex: number | null,
		isGlobal: boolean
	) {
		return (collection?.itinerary ?? []).some((item) => {
			if (placementType(item) !== type || String(item.object_id) !== String(objectId)) return false;
			if (isGlobal) return Boolean(item.is_global);
			if (dayIndex == null) return !item.day_index && !item.is_global;
			return item.day_index === dayIndex;
		});
	}

	async function linkLocation(locationId: string): Promise<boolean> {
		if (!collection) return false;
		if ((collection.locations ?? []).some((item) => String(item.id) === String(locationId)))
			return true;
		const loaded = await fetch(`/api/locations/${locationId}/?include_collections=true`);
		if (!loaded.ok) {
			addToast('error', $t('adventures.collection_link_location_error'));
			return false;
		}
		const location = (await loaded.json()) as Location;
		const response = await fetch(`/api/locations/${location.id}/`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				collections: [...(location.collections || []), collection.id]
			})
		});
		if (!response.ok) {
			addToast('error', $t('adventures.collection_link_location_error'));
			return false;
		}
		collection.locations = [...(collection.locations ?? []), location];
		collection = { ...collection };
		return true;
	}

	async function placeItem(
		type: PlanObjectType,
		objectId: string,
		dayIndex: number | null,
		isGlobal: boolean
	) {
		if (!collection || !dayPlanner) return;
		if (alreadyPlaced(type, objectId, dayIndex, isGlobal)) return;
		const response = await fetch('/api/itineraries/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				collection: collection.id,
				content_type: type,
				object_id: objectId,
				day_index: isGlobal ? null : dayIndex,
				is_global: isGlobal,
				is_optional: false
			})
		});
		if (!response.ok) {
			addToast('error', $t('itinerary.save_failed'));
			return;
		}
		const data = await response.json();
		if (data?.id) {
			collection.itinerary = [...(collection.itinerary ?? []), data];
			collection = { ...collection };
		}
	}

	async function addFromLink(type: PlanObjectType, id: string) {
		const scope = linkScope;
		if (!scope || !collection) return;
		if (type === 'location') {
			const linked = await linkLocation(id);
			if (!linked) return;
		}
		if (scope.kind === 'collection' || !dayPlanner) {
			addToast('success', $t('adventures.collection_link_location_success'));
			return;
		}
		const isGlobal = scope.kind === 'global';
		const dayIndex = scope.kind === 'day' ? scope.index : null;
		await placeItem(type, id, dayIndex, isGlobal);
		addToast('success', $t('itinerary.placement_saved'));
	}

	// Folder layout follows collection type. Dates no longer decide the view.
	let isFolderView = $derived(collection?.type === 'folder');
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
	let canModifyCollection = $derived(
		(() => {
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
		})()
	);
	// Public collections: anyone can export/share; private: owner or shared users only
	let canExportCollection = $derived(!!collection?.is_public || canModifyCollection);
	// Define available views based on collection type
	let dayPlanner = $derived(collection ? showsDayPlanner(collection) : false);
	// Folders keep the catalog sidebar. Trip all-items uses the planner workspace chrome.
	let catalogView = $derived(currentView === 'all' && !dayPlanner);
	// Plan, read, trip all-items, the map, calendar, and recommendations fill the space under the tab bar.
	let lockedPane = $derived(
		currentView === 'plan' ||
			currentView === 'read' ||
			currentView === 'map' ||
			currentView === 'calendar' ||
			currentView === 'recommendations' ||
			(currentView === 'all' && dayPlanner)
	);
	let showComposer = $derived(
		!!collection &&
			canModifyCollection &&
			!collection.is_archived &&
			currentView !== 'read' &&
			currentView !== 'plan' &&
			currentView !== 'calendar' &&
			currentView !== 'recommendations'
	);
	let availableViews = $derived({
		all: true,
		plan: dayPlanner,
		read: dayPlanner,
		map:
			!dayPlanner &&
			!isFolderView &&
			(collection?.locations?.some((l) => l.latitude && l.longitude) ||
				collection?.lodging?.some((l) => l.latitude && l.longitude) ||
				collection?.transportations?.some(
					(t) =>
						(t.origin_latitude && t.origin_longitude) ||
						(t.destination_latitude && t.destination_longitude)
				) ||
				false),
		// Only an anchored, unarchived trip has calendar dates to show.
		calendar: !isFolderView && !!collection?.start_date && !collection?.is_archived,
		recommendations: canModifyCollection,
		stats: true,
		budget: !isFolderView
	});
	let viewTabs = $derived.by(() => {
		const tabs: ViewTab[] = [];
		const add = (id: ViewType, label: string, icon: ViewTab['icon']) => {
			if (availableViews[id]) tabs.push({ id, label, icon });
		};

		if (availableViews.plan) {
			add('plan', $t('collection.plan'), Timeline);
			add('read', $t('collection.read'), BookOpenVariant);
			add('all', $t('collections.all_items'), FormatListBulleted);
		}
		if (availableViews.map) add('map', $t('navbar.map'), Map);
		if (isFolderView && !tabs.some((tab) => tab.id === 'all')) {
			add('all', $t('collections.all_items'), FormatListBulleted);
		}
		if (availableViews.calendar) add('calendar', $t('navbar.calendar'), Calendar);
		if (availableViews.recommendations) {
			add('recommendations', $t('recomendations.recommendations'), Lightbulb);
		}
		if (availableViews.stats) add('stats', $t('collections.statistics'), ChartBar);
		if (availableViews.budget) add('budget', $t('collections.trip_costs'), CashMultiple);

		return tabs;
	});
	let shownTabs = $derived(viewTabs.slice(0, Math.min(visibleTabCount, viewTabs.length)));
	let overflowTabs = $derived(viewTabs.slice(shownTabs.length));
	let overflowHasActive = $derived(overflowTabs.some((tab) => tab.id === currentView));
	let slideIndex = $derived(
		heroImages.length === 0 ? 0 : Math.min(currentSlide, heroImages.length - 1)
	);
	let coverImage = $derived(heroImages[slideIndex] ?? null);
	run(() => {
		defaultView = (dayPlanner ? 'plan' : 'all') as ViewType;
	});
	// Read view from URL params and validate it's available
	run(() => {
		const requested = $page.url.searchParams.get('view');
		const view = (requested === 'itinerary' ? 'plan' : requested) as ViewType;
		if (
			view &&
			['all', 'plan', 'read', 'map', 'calendar', 'recommendations', 'stats', 'budget'].includes(
				view
			) &&
			availableViews[view]
		) {
			currentView = view;
		} else {
			currentView = defaultView;
		}
	});
	$effect.pre(() => {
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

{#snippet collectionBadges()}
	{#if collection}
		<span
			class="badge badge-sm font-medium {collection.status === 'completed'
				? 'badge-primary'
				: collection.status === 'in_progress'
					? 'badge-success'
					: collection.status === 'upcoming'
						? 'badge-info'
						: 'badge-neutral'}"
		>
			{collection.type === 'trip' ? $t('adventures.trip') : $t('adventures.folder')}
			{#if collection.status === 'upcoming'}
				· {$t('adventures.upcoming')}
			{:else if collection.status === 'in_progress'}
				· {$t('adventures.in_progress')}
			{:else if collection.status === 'completed'}
				· {$t('adventures.completed')}
			{/if}
		</span>
		{#if dayPlanner}
			<span class="badge badge-accent badge-sm gap-1 font-medium">
				<Calendar class="h-3.5 w-3.5" />
				{collection.day_count ?? 0}
				{$t('adventures.days')}
				·
				{#if collection.start_date && collection.end_date}
					{formatDate(collection.start_date)} – {formatDate(collection.end_date)}
				{:else}
					{$t('itinerary.dates_not_set')}
				{/if}
			</span>
		{:else if collection.start_date || collection.end_date}
			<span class="badge badge-accent badge-sm gap-1 font-medium">
				<Calendar class="h-3.5 w-3.5" />
				{#if collection.start_date && collection.end_date}
					{formatDate(collection.start_date)} – {formatDate(collection.end_date)}
				{:else if collection.start_date}
					{formatDate(collection.start_date)}
				{:else if collection.end_date}
					{formatDate(collection.end_date)}
				{/if}
			</span>
		{/if}
		{#if collection.locations && collection.locations.length > 0}
			<span class="badge badge-primary badge-sm font-medium">
				{collection.locations.length}
				{collection.locations.length === 1 ? $t('locations.location') : $t('locations.locations')}
			</span>
		{/if}
		{#if collection.is_archived}
			<span class="badge badge-neutral badge-sm font-medium">{$t('adventures.archived')}</span>
		{/if}
	{/if}
{/snippet}

{#snippet viewTabLabel(tab: ViewTab, hideIconOnNarrow: boolean)}
	{@const Icon = tab.icon}
	<Icon
		class="h-4 w-4 shrink-0 {hideIconOnNarrow ? 'max-[30rem]:hidden' : ''}"
		aria-hidden="true"
	/>
	{tab.label}
{/snippet}

{#snippet moreTabLabel()}
	<DotsHorizontal class="h-4 w-4 shrink-0 max-[30rem]:hidden" aria-hidden="true" />
	{$t('collection.more')}
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

{#if linkScope && collection}
	<LinkItemsModal
		{collection}
		scope={linkScope}
		onAdd={addFromLink}
		onClose={() => (linkScope = null)}
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
			locationModalInitialStep = null;
			isLocationModalOpen = false;
		}}
		user={data.user}
		{collection}
		locationToEdit={adventureToEdit}
		initialStep={locationModalInitialStep}
		on:save={(e) => {
			upsertCollectionItem('locations', e.detail);
			adventureToEdit = null;
			locationModalInitialStep = null;
			isLocationModalOpen = false;
		}}
		on:create={(e) => {
			upsertCollectionItem('locations', e.detail);
			adventureToEdit = null;
			locationModalInitialStep = null;
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

{#if !collection && !notFound}
	<div class="hero min-h-screen overflow-x-hidden">
		<div class="hero-content">
			<span class="loading loading-spinner w-24 h-24 text-primary"></span>
		</div>
	</div>
{/if}

{#if collection}
	<div
		class={catalogView
			? 'min-h-screen bg-gradient-to-b from-base-200 via-base-100 to-base-200'
			: 'flex h-[calc(100dvh-4.75rem)] min-h-0 flex-col'}
	>
		<header class="relative shrink-0 overflow-hidden bg-base-100">
			{#if coverImage}
				<div class="pointer-events-none absolute inset-0" aria-hidden="true">
					<img src={coverImage.image} alt="" class="h-full w-full object-cover opacity-40" />
					<div
						class="absolute inset-0 bg-gradient-to-r from-base-100 from-25% via-base-100/90 to-base-100/65"
					></div>
				</div>
			{/if}
			<div class="relative flex items-center gap-3 px-3 py-3 sm:gap-4 sm:px-4 sm:py-4">
				{#if coverImage}
					<div class="flex shrink-0 flex-col items-center gap-1">
						<button
							type="button"
							class="h-16 w-[4.5rem] overflow-hidden rounded-xl shadow-sm ring-1 ring-base-content/15 sm:h-[4.5rem] sm:w-24"
							onclick={() => openImageModal(slideIndex)}
							aria-label={`View full image of ${collection.name}`}
						>
							<img src={coverImage.image} alt="" class="h-full w-full object-cover" />
						</button>
						{#if heroImages.length > 1}
							<div class="flex items-center">
								<button
									type="button"
									class="btn btn-ghost btn-xs btn-circle"
									onclick={showPreviousImage}
									aria-label={$t('adventures.previous_image')}
								>
									<ChevronLeft class="h-4 w-4" />
								</button>
								<span
									class="min-w-8 text-center text-[11px] font-medium tabular-nums text-base-content/70"
								>
									{slideIndex + 1}/{heroImages.length}
								</span>
								<button
									type="button"
									class="btn btn-ghost btn-xs btn-circle"
									onclick={showNextImage}
									aria-label={$t('adventures.next_image')}
								>
									<ChevronRight class="h-4 w-4" />
								</button>
							</div>
						{/if}
					</div>
				{/if}
				<div class="min-w-0 flex-1">
					<h1 class="truncate text-2xl font-bold sm:text-3xl">
						{#if isFolderView}
							<FolderMultiple class="mr-2 inline h-7 w-7 align-text-bottom" />
						{/if}
						{collection.name}
					</h1>
					<div class="mt-1.5 flex flex-wrap items-center gap-2">
						{@render collectionBadges()}
						{#if collection.collaborators && collection.collaborators.length > 0}
							<div class="avatar-group -space-x-2">
								{#each collection.collaborators as person (person.uuid)}
									{#if person.public_profile}
										<a
											href={`/profile/${person.username}`}
											class="avatar tooltip"
											data-tip={collaboratorDisplayName(person)}
											title={collaboratorDisplayName(person)}
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
						{/if}
					</div>
				</div>
				{#if canExportCollection}
					<div class="flex shrink-0 gap-2">
						<button
							class="btn btn-outline btn-primary btn-sm gap-2"
							onclick={() => (isSocialShareModalOpen = true)}
						>
							<ImageOutline class="h-4 w-4" />
							<span class="hidden lg:inline">{$t('social_share.share_externally')}</span>
						</button>
						<button
							class="btn btn-outline btn-primary btn-sm gap-2"
							onclick={exportCollectionPdf}
							disabled={isExportingPdf}
							aria-busy={isExportingPdf}
						>
							<FilePdfBox class="h-4 w-4" />
							<span class="hidden lg:inline"
								>{isExportingPdf ? '...' : $t('adventures.export_pdf')}</span
							>
						</button>
					</div>
				{/if}
			</div>

			<nav class="relative min-w-0 px-3 pb-3 sm:px-4" aria-label={collection.name}>
				<div
					class="relative min-w-0 w-full"
					{@attach (node) => {
						const signature = viewTabs.map((tab) => tab.id + tab.label).join('|');
						void signature;
						const apply = () => {
							const next = fitTabCount(node);
							if (next !== null && next !== untrack(() => visibleTabCount)) visibleTabCount = next;
						};
						const observer = new ResizeObserver(() => apply());
						observer.observe(node);
						const frame = requestAnimationFrame(apply);
						let cancelled = false;
						document.fonts?.ready.then(() => {
							if (!cancelled) apply();
						});
						return () => {
							cancelled = true;
							cancelAnimationFrame(frame);
							observer.disconnect();
						};
					}}
				>
					<div
						class="pointer-events-none absolute inset-x-0 top-0 -z-10 h-0 overflow-hidden"
						aria-hidden="true"
					>
						<div data-measure-row class="flex w-max items-center gap-1 p-1">
							{#each viewTabs as tab (tab.id)}
								<button type="button" tabindex="-1" data-tab-measure class={viewTabClass}>
									{@render viewTabLabel(tab, true)}
								</button>
							{/each}
							<button type="button" tabindex="-1" data-more-measure class={viewTabClass}>
								{@render moreTabLabel()}
							</button>
						</div>
					</div>
					<div
						role="tablist"
						class="flex w-max max-w-full items-center gap-1 rounded-full bg-base-200/70 p-1 ring-1 ring-base-content/10"
					>
						{#each shownTabs as tab (tab.id)}
							<button
								type="button"
								role="tab"
								class={tabButtonClass(currentView === tab.id)}
								aria-selected={currentView === tab.id}
								onclick={() => switchView(tab.id)}
							>
								{@render viewTabLabel(tab, true)}
							</button>
						{/each}
						{#if overflowTabs.length > 0}
							<div class="dropdown dropdown-end">
								<button
									type="button"
									class={tabButtonClass(overflowHasActive)}
									aria-haspopup="menu"
								>
									{@render moreTabLabel()}
								</button>
								<ul
									class="dropdown-content menu z-[1100] mt-2 w-56 rounded-box border border-base-300 bg-base-100 p-2 shadow-lg"
								>
									{#each overflowTabs as tab (tab.id)}
										<li>
											<button
												type="button"
												class="gap-2"
												class:bg-base-200={currentView === tab.id}
												onclick={() => switchView(tab.id)}
											>
												{@render viewTabLabel(tab, false)}
											</button>
										</li>
									{/each}
								</ul>
							</div>
						{/if}
					</div>
				</div>
			</nav>
		</header>

		<!-- Main Content -->
		<div
			class={catalogView
				? 'container mx-auto w-full max-w-7xl px-3 pb-6 pt-1 sm:px-6 sm:pb-8'
				: 'flex min-h-0 w-full flex-1 flex-col'}
		>
			<div
				class={catalogView
					? 'grid grid-cols-1 items-start gap-6 lg:grid-cols-4'
					: 'min-h-0 flex-1 overflow-hidden px-3 pb-3 pt-1 sm:px-4'}
			>
				<!-- Left Column - Main Content -->
				<div
					class={catalogView
						? 'space-y-6 lg:col-span-3'
						: lockedPane
							? 'h-full min-h-0 overflow-hidden'
							: 'h-full min-h-0 overflow-y-auto pb-24'}
				>
					<!-- Description stays with the catalog. The planner and map start immediately. -->
					{#if collection.description && catalogView}
						<section class="rounded-2xl border border-base-300/70 bg-base-100 p-5 shadow-sm sm:p-6">
							<h2 class="mb-4 flex items-center gap-2 text-lg font-semibold">
								<TextBoxOutline class="h-5 w-5 text-primary" />
								Description
							</h2>
							<article class="prose max-w-none">
								{@html DOMPurify.sanitize(renderMarkdown(collection.description))}
							</article>
						</section>
					{/if}

					<!-- All Items View -->
					{#if currentView === 'all'}
						{#if dayPlanner}
							<div class="h-full min-h-0">
								<TripWorkspace bind:collection user={data.user} canModify={canModifyCollection}>
									{#snippet children(filters)}
										<CollectionAllItems
											bind:collection
											user={data.user}
											{isFolderView}
											{filters}
											showMapToggles
											on:openEdit={handleOpenEdit}
										/>
									{/snippet}
								</TripWorkspace>
							</div>
						{:else}
							{#if isFolderView}
								<div
									class="h-[50vh] overflow-hidden rounded-2xl border border-base-300/70 shadow-sm"
								>
									<CollectionMap
										bind:collection
										user={data.user}
										canModify={canModifyCollection}
										embedded
										showRoutes={false}
										mapClass="h-full w-full"
									/>
								</div>
							{/if}
							<CollectionAllItems
								bind:collection
								user={data.user}
								{isFolderView}
								on:openEdit={handleOpenEdit}
							/>
						{/if}
					{/if}

					<!-- Day plan and read, with the map -->
					{#if currentView === 'plan' || currentView === 'read'}
						<div class="h-full min-h-0">
							<TripWorkspace
								bind:collection
								user={data.user}
								canModify={canModifyCollection}
								readMode={currentView === 'read'}
								onOpenLink={(scope) => (linkScope = scope)}
							/>
						</div>
					{/if}

					{#if currentView === 'budget'}
						<CollectionCosts {collection} currency={preferredCurrency} />
					{/if}

					<!-- Stats View -->
					{#if currentView === 'stats'}
						<CollectionStats {collection} user={data.user} />
					{/if}

					<!-- Map View -->
					{#if currentView === 'map'}
						<div class="card flex h-full min-h-0 flex-col bg-base-200 shadow-xl">
							<div class="card-body flex min-h-0 flex-1 flex-col">
								<h2 class="card-title text-2xl mb-4">🗺️ {$t('navbar.map')}</h2>
								<div class="min-h-0 flex-1 overflow-hidden rounded-lg shadow-lg">
									<CollectionMap
										bind:collection
										user={data.user}
										canModify={canModifyCollection}
										embedded
										mapClass="h-full w-full"
									/>
								</div>
							</div>
						</div>
					{/if}

					{#if currentView === 'calendar'}
						<div class="h-full min-h-0">
							<CollectionCalendar {collection} {dateFormat} />
						</div>
					{/if}

					<!-- Recommendations View -->
					{#if currentView === 'recommendations' && canModifyCollection}
						<div class="h-full min-h-0">
							<CollectionRecommendationView bind:collection user={data.user} />
						</div>
					{/if}
				</div>

				<!-- Sidebar belongs to the item catalog. Planner, map, and calendar use the full width. -->
				{#if catalogView}
					<div class="space-y-4 lg:col-span-1 lg:sticky lg:top-4">
						<!-- Progress Tracker (only for folder views) -->
						{#if isFolderView && collection.locations && collection.locations.length > 0}
							{@const visitedCount = collection.locations.filter((l) => l.is_visited).length}
							{@const totalCount = collection.locations.length}
							{@const progressPercent = totalCount > 0 ? (visitedCount / totalCount) * 100 : 0}
							<div class="rounded-2xl border border-base-300/70 bg-base-100 shadow-sm">
								<div class="card-body">
									<h3 class="mb-4 flex items-center gap-2 text-lg font-semibold">
										<CheckCircleOutline class="h-5 w-5 text-primary" />
										{$t('worldtravel.progress')}
									</h3>
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
											<div class="text-center text-xs opacity-70">
												{Math.round(progressPercent)}%
											</div>
										{/if}
										<div class="grid grid-cols-2 gap-2 pt-2">
											<div class="stat bg-base-300 rounded-lg p-3">
												<div class="stat-title text-xs">{$t('adventures.visited')}</div>
												<div class="stat-value text-lg text-success">{visitedCount}</div>
											</div>
											<div class="stat bg-base-300 rounded-lg p-3">
												<div class="stat-title text-xs">{$t('adventures.planned')}</div>
												<div class="stat-value text-lg text-warning">
													{totalCount - visitedCount}
												</div>
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
						<div class="rounded-2xl border border-base-300/70 bg-base-100 shadow-sm">
							<div class="card-body">
								<h3 class="mb-4 flex items-center gap-2 text-lg font-semibold">
									<InformationOutline class="h-5 w-5 text-primary" />
									{$t('adventures.basic_information')}
								</h3>
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

						<!-- Additional Images (from locations) -->
						{#if heroImages && heroImages.length > 0}
							<div class="rounded-2xl border border-base-300/70 bg-base-100 shadow-sm">
								<div class="card-body">
									<h3 class="mb-4 flex items-center gap-2 text-lg font-semibold">
										<ImageMultiple class="h-5 w-5 text-primary" />
										{$t('adventures.images')}
									</h3>
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
													<div>
														{#if image.is_primary}
															<div class="absolute top-1 right-1">
																<span class="badge badge-primary badge-xs"
																	>{$t('settings.primary')}</span
																>
															</div>
														{/if}
													</div>
												{/snippet}
											</ImageFrame>
										{/each}
									</div>
									{#if heroImages.length > 12}
										<div class="text-center mt-2 text-sm opacity-70">
											+{heroImages.length - 12} more {heroImages.length - 12 === 1
												? 'image'
												: 'images'}
										</div>
									{/if}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Floating Action Button (FAB) - Only shown if user can modify collection -->
{#if showComposer}
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
				<button
					class="btn btn-primary"
					onclick={() => (linkScope = dayPlanner ? { kind: 'ideas' } : { kind: 'collection' })}
				>
					{$t('itinerary.add_existing')}
				</button>

				{#if !isFolderView}
					<button
						class="btn btn-primary"
						onclick={() => {
							transportationToEdit = null;
							isTransportationModalOpen = true;
						}}
					>
						{$t('adventures.transportation')}
					</button>
				{/if}

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

				{#if !isFolderView}
					<button
						class="btn btn-primary"
						onclick={() => {
							lodgingToEdit = null;
							isLodgingModalOpen = true;
						}}
					>
						{$t('adventures.lodging')}
					</button>
				{/if}
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
