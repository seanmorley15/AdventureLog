<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { openLocationDrawer } from '#lib/location-drawer.svelte.js';
	import type { Location, Collection, User, CollectionItineraryItem } from '#lib/types.js';
	const dispatch = createEventDispatcher();

	import Launch from '~icons/mdi/launch';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import ContentCopy from '~icons/mdi/content-copy';
	import TrashCan from '~icons/mdi/trash-can-outline';
	import Calendar from '~icons/mdi/calendar';
	import MapMarkerOutline from '~icons/mdi/map-marker-outline';
	import LinkIcon from '~icons/mdi/link-variant';
	import Check from '~icons/mdi/check';
	import CheckCircle from '~icons/mdi/check-circle';
	import CircleOutline from '~icons/mdi/circle-outline';
	import Cash from '~icons/mdi/cash';
	import LinkVariantRemove from '~icons/mdi/link-variant-remove';
	import Plus from '~icons/mdi/plus';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Globe from '~icons/mdi/globe';
	import ImageOutline from '~icons/mdi/image-outline';
	import { addToast } from '#lib/toasts.js';
	import { copyToClipboard } from '#lib/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import CollectionPicker from '../collections/CollectionPicker.svelte';
	import { unlinkLocationFromCollection } from '#lib/collection-membership.js';
	import DeleteWarning from '../DeleteWarning.svelte';
	import CardCarousel from '../CardCarousel.svelte';
	import CardActionsMenu from './parts/CardActionsMenu.svelte';
	import CardRating from './parts/CardRating.svelte';
	import CardVisibility from './parts/CardVisibility.svelte';
	import CountryFlag from '../shared/CountryFlag.svelte';
	import SocialShareModal from '../SocialShareModal.svelte';
	import { t } from 'svelte-i18n';
	import { dateFormatFromUser, formatDisplayDate } from '#lib/dateFormat.js';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '#lib/money.js';

	let isCollectionModalOpen: boolean = $state(false);
	let isWarningModalOpen: boolean = $state(false);
	let isSocialShareModalOpen: boolean = $state(false);
	let copied: boolean = $state(false);

	async function copyLink() {
		try {
			const url = `${location.origin}/locations/${adventure.id}`;
			await copyToClipboard(url);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch (e) {
			addToast('error', $t('adventures.copy_failed') || 'Copy failed');
		}
	}

	interface Props {
		type?: string | null;
		user: User | null;
		collection?: Collection | null;
		readOnly?: boolean;
		compact?: boolean; // For compact grid display in itinerary
		itineraryItem?: CollectionItineraryItem | null;
		isEditLoading?: boolean;
		adventure: Location;
	}

	let {
		type = null,
		user,
		collection = null,
		readOnly = false,
		compact = false,
		itineraryItem = null,
		isEditLoading = false,
		adventure = $bindable()
	}: Props = $props();
	let displayActivityTypes = $derived((adventure.tags ?? []).slice(0, 3));
	let remainingCount = $derived(
		(adventure.tags?.length ?? 0) > 3 ? (adventure.tags?.length ?? 0) - 3 : 0
	);

	const dateFormat = $derived(dateFormatFromUser(user));

	// Visits only come with the full location record, not the slim list used on /locations.
	let visitCount = $derived(adventure.visits?.length ?? 0);
	let lastVisitDate = $derived.by(() => {
		const dates = (adventure.visits ?? [])
			.map((v) => v.end_date || v.start_date)
			.filter(Boolean)
			.sort();
		const latest = dates[dates.length - 1];
		return latest ? formatDisplayDate(latest, dateFormat) : '';
	});

	// "Abisko, Norrbotten" reads better than the raw address when the place is structured.
	let placeLine = $derived(
		[adventure.city?.name, adventure.region?.name].filter(Boolean).join(', ') ||
			adventure.location ||
			''
	);

	function changeDay() {
		dispatch('changeDay', { type: 'location', item: adventure, forcePicker: true });
	}

	async function deleteAdventure() {
		let res = await fetch(`/api/locations/${adventure.id}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('info', $t('adventures.location_delete_success'));
			dispatch('delete', adventure.id);
		} else {
			console.log('Error deleting adventure');
		}
	}

	async function removeFromItinerary() {
		let itineraryItemId = itineraryItem?.id;
		let res = await fetch(
			`/api/collections/${itineraryItem?.collection}/itinerary-items/${itineraryItemId}/`,
			{
				method: 'DELETE'
			}
		);
		if (res.ok) {
			addToast('info', $t('itinerary.item_remove_success'));
			dispatch('removeFromItinerary', itineraryItem);
		} else {
			addToast('error', $t('itinerary.item_remove_error'));
		}
	}

	// Placements of this place on the open collection's plan, for the unlink warning.
	let planPlacements = $derived(
		collection
			? (collection.itinerary ?? []).filter(
					(item) => String(item.object_id) === String(adventure.id)
				).length
			: 0
	);

	async function removeFromThisCollection() {
		if (!collection?.id) return;
		if (
			planPlacements > 0 &&
			!confirm(
				$t('collection.unlink_plan_warning', {
					values: { days: String(planPlacements), name: collection.name }
				})
			)
		) {
			return;
		}
		const removed = await unlinkLocationFromCollection(adventure.id, collection.id);
		if (removed === null) {
			addToast('error', `${$t('adventures.collection_remove_location_error')}`);
			return;
		}
		adventure.collections = (adventure.collections ?? []).filter(
			(c) => String(c) !== String(collection.id)
		);
		addToast('info', `${$t('adventures.collection_remove_location_success')}`);
		dispatch('unlink', adventure);
	}

	let isDuplicating = $state(false);

	async function duplicateAdventure() {
		if (isDuplicating) return;
		isDuplicating = true;
		try {
			const duplicatePayload = collection?.id ? { collection: collection.id } : null;
			const res = await fetch(`/api/locations/${adventure.id}/duplicate/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(duplicatePayload ?? {})
			});
			if (res.ok) {
				const newLocation = await res.json();

				// Keep local UI in sync immediately in collection context.
				if (collection?.id) {
					const nextCollections = Array.isArray(newLocation.collections)
						? newLocation.collections
						: [];
					if (!nextCollections.includes(collection.id)) {
						newLocation.collections = [...nextCollections, collection.id];
					}
				}

				addToast('success', $t('adventures.location_duplicate_success'));
				dispatch('duplicate', newLocation);
			} else {
				addToast('error', $t('adventures.location_duplicate_error'));
			}
		} catch (e) {
			addToast('error', $t('adventures.location_duplicate_error'));
		} finally {
			isDuplicating = false;
		}
	}

	function editAdventure() {
		dispatch('edit', adventure);
	}

	function editVisits() {
		dispatch('editVisits', adventure);
	}

	function link() {
		dispatch('link', adventure);
	}
	let adventurePriceLabel = $derived(
		formatMoney(toMoneyValue(adventure?.price, adventure?.price_currency, DEFAULT_CURRENCY))
	);
	// Creator avatar helpers
	let creatorDisplayName = $derived(
		adventure.user?.first_name
			? `${adventure.user.first_name} ${adventure.user.last_name || ''}`.trim()
			: adventure.user?.username || 'Unknown User'
	);
</script>

{#if isCollectionModalOpen}
	<CollectionPicker
		locationId={adventure.id}
		locationName={adventure.name}
		onchange={(ids) => {
			adventure.collections = ids;
			if (collection?.id && !ids.includes(String(collection.id))) dispatch('unlink', adventure);
		}}
		onclose={() => (isCollectionModalOpen = false)}
	/>
{/if}

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_location')}
		button_text="Delete"
		description={$t('adventures.location_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteAdventure}
	/>
{/if}

{#if isSocialShareModalOpen}
	<SocialShareModal
		type="location"
		id={adventure.id}
		name={adventure.name}
		isPublic={!!adventure.is_public}
		on:close={() => (isSocialShareModalOpen = false)}
	/>
{/if}

<div
	class="card h-full flex flex-col rounded-2xl border border-base-300/60 bg-base-100 shadow-xs transition-colors hover:border-base-300"
	aria-label="location-card"
>
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel images={adventure.images} icon={adventure.category?.icon} name={adventure.name} />

		<div class="absolute right-2 top-2">
			<CardVisibility visibility={adventure.is_public ? 'public' : 'private'} />
		</div>

		{#if adventure.category}
			<a
				href="/locations?types={adventure.category.name}"
				class="absolute bottom-2 left-2 inline-flex max-w-[60%] items-center gap-1.5 rounded-full bg-base-100/85 px-2.5 py-1 text-xs font-medium text-base-content shadow-xs backdrop-blur-sm transition-colors hover:bg-base-100"
			>
				<span aria-hidden="true">{adventure.category.icon}</span>
				<span class="truncate">{adventure.category.display_name}</span>
			</a>
		{/if}
	</div>

	<div class="flex flex-1 flex-col gap-3 {compact ? 'p-3' : 'p-4'}">
		<div class="flex items-start justify-between gap-2">
			<a
				href="/locations/{adventure.id}"
				class="line-clamp-2 min-w-0 font-semibold leading-snug transition-colors hover:text-primary {compact
					? 'text-base'
					: 'text-lg'}"
			>
				{adventure.name}
			</a>

			<div class="-mr-1 -mt-1 flex shrink-0 items-center">
				<button
					class="btn btn-ghost btn-square btn-sm"
					aria-label={$t('adventures.open_details')}
					onclick={() => openLocationDrawer(adventure.id)}
				>
					<Launch class="h-5 w-5" />
				</button>
				{#if !readOnly}
					{#if (adventure.user && adventure.user.uuid == user?.uuid) || (collection && user && collection.shared_with?.includes(user.uuid)) || (collection && user && collection.user == user.uuid)}
						<CardActionsMenu
							label={$t('adventures.location_actions') || 'Location actions'}
							busy={isEditLoading}
						>
							{#snippet children({ close })}
								<li>
									<button onclick={editAdventure} disabled={isEditLoading}>
										{#if isEditLoading}
											<span class="loading loading-spinner loading-xs"></span>
										{:else}
											<FileDocumentEdit class="h-4 w-4" />
										{/if}
										{$t('adventures.edit_location')}
									</button>
								</li>
								<li>
									<button type="button" onclick={editVisits} disabled={isEditLoading}>
										{#if isEditLoading}
											<span class="loading loading-spinner loading-xs"></span>
										{:else}
											<Calendar class="h-4 w-4" />
										{/if}
										{$t('adventures.manage_visits')}
									</button>
								</li>
								{#if user?.uuid == adventure.user?.uuid}
									<li>
										<button
											onclick={() => {
												close();
												duplicateAdventure();
											}}
											disabled={isDuplicating}
										>
											<ContentCopy class="h-4 w-4" />
											{isDuplicating ? '...' : $t('adventures.duplicate')}
										</button>
									</li>
								{/if}
								{#if collection}
									<li>
										<button
											onclick={() => {
												close();
												removeFromThisCollection();
											}}
										>
											<LinkVariantRemove class="h-4 w-4" />
											<span class="truncate">
												{$t('collection.remove_from_named', { values: { name: collection.name } })}
											</span>
										</button>
									</li>
								{/if}
								{#if user?.uuid == adventure.user?.uuid}
									<li>
										<button
											onclick={() => {
												close();
												isCollectionModalOpen = true;
											}}
										>
											<Plus class="h-4 w-4" />
											{$t('collection.manage_collections')}
										</button>
									</li>
								{/if}
								{#if adventure.is_public}
									<li>
										<button
											onclick={() => {
												close();
												copyLink();
											}}
										>
											{#if copied}
												<Check class="h-4 w-4 text-success" />
												<span>{$t('adventures.link_copied')}</span>
											{:else}
												<LinkIcon class="h-4 w-4" />
												{$t('adventures.copy_link')}
											{/if}
										</button>
									</li>
								{/if}
								{#if adventure.user && adventure.user.uuid == user?.uuid}
									<li>
										<button
											onclick={() => {
												close();
												isSocialShareModalOpen = true;
											}}
										>
											<ImageOutline class="h-4 w-4" />
											{$t('social_share.share_externally')}
										</button>
									</li>
								{/if}

								{#if itineraryItem && itineraryItem.id}
									<div class="divider my-1"></div>
									{#if !itineraryItem.is_global}
										<li>
											<button
												onclick={() => {
													close();
													dispatch('moveToGlobal', { type: 'location', id: adventure.id });
												}}
											>
												<Globe class="h-4 w-4" />
												{$t('itinerary.move_to_trip_context') || 'Move to Trip Context'}
											</button>
										</li>
										<li>
											<button
												onclick={() => {
													close();
													changeDay();
												}}
											>
												<Calendar class="h-4 w-4" />
												{$t('itinerary.change_day')}
											</button>
										</li>
										<li>
											<button
												class="text-error"
												onclick={() => {
													close();
													removeFromItinerary();
												}}
											>
												<CalendarRemove class="h-4 w-4" />
												{$t('itinerary.remove_from_itinerary')}
											</button>
										</li>
									{:else}
										<li>
											<button
												class="text-error"
												onclick={() => {
													close();
													removeFromItinerary();
												}}
											>
												<CalendarRemove class="h-4 w-4" />
												{$t('itinerary.remove_from_trip_context')}
											</button>
										</li>
									{/if}
								{/if}

								{#if user?.uuid == adventure.user?.uuid}
									<div class="divider my-1"></div>
									<li>
										<button
											id="delete_adventure"
											data-umami-event="Delete Adventure"
											class="text-error"
											onclick={() => {
												close();
												isWarningModalOpen = true;
											}}
										>
											<TrashCan class="h-4 w-4" />
											{$t('adventures.delete')}
										</button>
									</li>
								{/if}
							{/snippet}
						</CardActionsMenu>
					{/if}
				{/if}
			</div>
		</div>

		{#if placeLine}
			<p class="-mt-1.5 flex min-w-0 items-center gap-1.5 text-sm text-base-content/70">
				{#if adventure.country}
					<CountryFlag
						src={adventure.country.flag_url}
						code={adventure.country.country_code}
						name={adventure.country.name}
					/>
				{:else}
					<MapMarkerOutline class="h-4 w-4 shrink-0 text-primary" />
				{/if}
				<span class="truncate">{placeLine}</span>
			</p>
		{/if}

		<!-- Status first, then the facts that vary place to place. -->
		<div class="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm">
			{#if adventure.is_visited}
				<span class="inline-flex items-center gap-1.5 font-medium text-success">
					<CheckCircle class="h-4 w-4" />
					{$t('adventures.visited')}
				</span>
			{:else}
				<span class="inline-flex items-center gap-1.5 text-base-content/60">
					<CircleOutline class="h-4 w-4" />
					{$t('adventures.not_visited')}
				</span>
			{/if}
			{#if visitCount > 0}
				<span class="text-base-content/60">
					{$t('cards.visit_count', { values: { count: visitCount } })}{#if lastVisitDate}
						· {lastVisitDate}{/if}
				</span>
			{/if}
			<CardRating rating={adventure.rating} />
			{#if adventurePriceLabel}
				<span class="inline-flex items-center gap-1 text-base-content/70">
					<Cash class="h-4 w-4" />
					{adventurePriceLabel}
				</span>
			{/if}
		</div>

		{#if displayActivityTypes.length > 0}
			<div class="flex flex-wrap gap-1.5">
				{#each displayActivityTypes as tag}
					<span class="badge badge-ghost badge-sm">{tag}</span>
				{/each}
				{#if remainingCount > 0}
					<span class="badge badge-ghost badge-sm">+{remainingCount}</span>
				{/if}
			</div>
		{/if}

		{#if adventure.user && collection}
			<div class="mt-auto flex items-center gap-2 pt-1 text-xs text-base-content/60">
				<UserAvatar
					user={adventure.user}
					alt={creatorDisplayName}
					className="h-5 w-5 shrink-0 rounded-full"
					imgClass="h-5 w-5 shrink-0 rounded-full object-cover"
					textClass="text-[9px]"
				/>
				<span class="truncate">
					{$t('cards.added_by', { values: { name: creatorDisplayName } })}
				</span>
			</div>
		{/if}
	</div>

	{#if !readOnly && type == 'link'}
		<div class="px-4 pb-4">
			<button class="btn btn-primary btn-block btn-sm" onclick={link}>
				<LinkIcon class="h-4 w-4" />
				{$t('cards.link_location')}
			</button>
		</div>
	{/if}
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
