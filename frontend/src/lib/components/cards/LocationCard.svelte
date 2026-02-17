<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Location, Collection, User } from '$lib/types';
	const dispatch = createEventDispatcher();

	import Launch from '~icons/mdi/launch';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import TrashCan from '~icons/mdi/trash-can-outline';
	import Calendar from '~icons/mdi/calendar';
	import MapMarker from '~icons/mdi/map-marker';
	import { addToast } from '$lib/toasts';
	import Link from '~icons/mdi/link-variant';
	import LinkVariantRemove from '~icons/mdi/link-variant-remove';
	import Plus from '~icons/mdi/plus';
	import CollectionLink from '../CollectionLink.svelte';
	import DeleteWarning from '../DeleteWarning.svelte';
	import CardCarousel from '../CardCarousel.svelte';
	import { t } from 'svelte-i18n';
	import CollectionItineraryPlanner from '../collections/CollectionItineraryPlanner.svelte';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Globe from '~icons/mdi/globe';
	import { CardActionsMenu, CardStatusBadge, CardPrivacyBadge, RatingDisplay, PriceBadge, AvgPriceBadge, PriceTierBadge, CopyLinkButton, TagsDisplay, VisitCountBadge, getVisitSummary } from '../shared/cards';

	export let type: string | null = null;
	export let user: User | null;
	export let collection: Collection | null = null;
	export let readOnly: boolean = false;
	export let compact: boolean = false; // For compact grid display in itinerary
	export let itineraryItem: CollectionItineraryPlanner | null = null;

	let isCollectionModalOpen: boolean = false;
	let isWarningModalOpen: boolean = false;
	let actionsMenu: { close: () => void };

	export let adventure: Location;

	// Get visit summary for visit count
	$: visitSummary = getVisitSummary(adventure?.visits);

	// Creator avatar helpers
	$: creatorInitials =
		adventure.user?.first_name && adventure.user?.last_name
			? `${adventure.user.first_name[0]}${adventure.user.last_name[0]}`
			: adventure.user?.first_name?.[0] || adventure.user?.username?.[0] || '?';

	$: creatorDisplayName = adventure.user?.first_name
		? `${adventure.user.first_name} ${adventure.user.last_name || ''}`.trim()
		: adventure.user?.username || 'Unknown User';

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
		let res = await fetch(`/api/itineraries/${itineraryItemId}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('info', $t('itinerary.item_remove_success'));
			dispatch('removeFromItinerary', itineraryItem);
		} else {
			addToast('error', $t('itinerary.item_remove_error'));
		}
	}

	async function linkCollection(event: CustomEvent<string>) {
		let collectionId = event.detail;
		// Create a copy to avoid modifying the original directly
		const updatedCollections = adventure.collections ? [...adventure.collections] : [];

		// Add the new collection if not already present
		if (!updatedCollections.some((c) => String(c) === String(collectionId))) {
			updatedCollections.push(collectionId);
		}

		let res = await fetch(`/api/locations/${adventure.id}`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ collections: updatedCollections })
		});

		if (res.ok) {
			// Only update the adventure.collections after server confirms success
			adventure.collections = updatedCollections;
			addToast('info', `${$t('adventures.collection_link_location_success')}`);
		} else {
			addToast('error', `${$t('adventures.collection_link_location_error')}`);
		}
	}

	async function removeFromCollection(event: CustomEvent<string>) {
		let collectionId = event.detail;
		if (!collectionId) {
			addToast('error', `${$t('adventures.collection_remove_location_error')}`);
			return;
		}

		// Create a copy to avoid modifying the original directly
		if (adventure.collections) {
			const updatedCollections = adventure.collections.filter(
				(c) => String(c) !== String(collectionId)
			);

			let res = await fetch(`/api/locations/${adventure.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ collections: updatedCollections })
			});

			if (res.ok) {
				// Only update adventure.collections after server confirms success
				adventure.collections = updatedCollections;
				addToast('info', `${$t('adventures.collection_remove_location_success')}`);
			} else {
				addToast('error', `${$t('adventures.collection_remove_location_error')}`);
			}
		}
	}

	function editAdventure() {
		dispatch('edit', adventure);
	}

	function link() {
		dispatch('link', adventure);
	}
</script>

{#if isCollectionModalOpen}
	<CollectionLink
		on:link={(e) => linkCollection(e)}
		on:unlink={(e) => removeFromCollection(e)}
		on:close={() => (isCollectionModalOpen = false)}
		linkedCollectionList={adventure.collections}
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

<div
	class="card w-full max-w-md bg-base-300 shadow hover:shadow-md transition-all duration-200 border border-base-300 group"
	aria-label="location-card"
>
	<!-- Image Section with Overlay -->
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel images={adventure.images} icon={adventure.category?.icon} name={adventure.name} />

		<CardStatusBadge isVisited={adventure.is_visited} />
		<CardPrivacyBadge isPublic={adventure.is_public} />

		<!-- Category Badge -->
		{#if adventure.category}
			<div class="absolute bottom-4 left-4">
				<a
					href="/locations?types={adventure.category.name}"
					class="badge badge-primary shadow-lg font-medium cursor-pointer hover:brightness-110 transition-all"
				>
					{adventure.category.display_name}
					{adventure.category.icon}
				</a>
			</div>
		{/if}

		<!-- Creator Avatar -->
		{#if adventure.user && collection}
			<div class="absolute bottom-4 right-4">
				<div class="tooltip tooltip-left" data-tip={creatorDisplayName}>
					<div class="avatar">
						<div class="w-7 h-7 rounded-full ring-2 ring-white/40 shadow">
							{#if adventure.user.profile_pic}
								<img
									src={adventure.user.profile_pic}
									alt={creatorDisplayName}
									class="rounded-full object-cover"
								/>
							{:else}
								<div
									class="w-7 h-7 bg-gradient-to-br from-primary to-secondary rounded-full flex items-center justify-center text-primary-content font-semibold text-xs"
								>
									{creatorInitials.toUpperCase()}
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Content Section -->
	<div
		class="card-body space-y-2"
		class:p-3={compact}
		class:p-4={!compact}
		class:space-y-2={compact}
		class:space-y-3={!compact}
	>
		<!-- Header: title + compact actions -->
		<div class="flex items-start justify-between gap-2">
			<a
				href="/locations/{adventure.id}"
				class="hover:text-primary transition-colors duration-200 line-clamp-2"
				class:text-base={compact}
				class:text-lg={!compact}
				class:font-semibold={!compact}
				class:font-medium={compact}
			>
				{adventure.name}
			</a>

			<div class="flex items-center gap-2">
				<button
					class="btn btn-sm p-1 text-base-content"
					aria-label="open-details"
					on:click={() => goto(`/locations/${adventure.id}`)}
				>
					<Launch class="w-4 h-4" />
				</button>
				{#if !readOnly}
					{#if (adventure.user && adventure.user.uuid == user?.uuid) || (collection && user && collection.shared_with?.includes(user.uuid)) || (collection && user && collection.user == user.uuid)}
						<CardActionsMenu bind:this={actionsMenu} ariaLabel={$t('adventures.location_actions') || 'Location actions'} let:close>
							<li>
								<button
									on:click={() => {
										close();
										editAdventure();
									}}
									class="flex items-center gap-2"
								>
									<FileDocumentEdit class="w-4 h-4" />
									{$t('adventures.edit_location')}
								</button>
							</li>
							{#if user?.uuid == adventure.user?.uuid}
								<li>
									<button
										on:click={() => {
											close();
											isCollectionModalOpen = true;
										}}
										class="flex items-center gap-2"
									>
										<Plus class="w-4 h-4" />
										{$t('collection.manage_collections')}
									</button>
								</li>
							{:else if collection && user && collection.user == user.uuid}
								<li>
									<button
										on:click={() => {
											close();
											removeFromCollection(new CustomEvent('unlink', { detail: collection.id }));
										}}
										class="flex items-center gap-2"
									>
										<LinkVariantRemove class="w-4 h-4" />
										{$t('adventures.remove_from_collection')}
									</button>
								</li>
							{/if}

							{#if adventure.is_public}
								<li>
									<CopyLinkButton url={`${typeof window !== 'undefined' ? window.location.origin : ''}/locations/${adventure.id}`} />
								</li>
							{/if}

							{#if itineraryItem && itineraryItem.id}
								<div class="divider my-1"></div>
								{#if !itineraryItem.is_global}
									<li>
										<button
											on:click={() => {
												close();
												dispatch('moveToGlobal', { type: 'location', id: adventure.id });
											}}
											class=" flex items-center gap-2"
										>
											<Globe class="w-4 h-4" />
											{$t('itinerary.move_to_trip_context') || 'Move to Trip Context'}
										</button>
									</li>
									<li>
										<button
											on:click={() => {
												close();
												changeDay();
											}}
											class=" flex items-center gap-2"
										>
											<Calendar class="w-4 h-4" />
											{$t('itinerary.change_day')}
										</button>
									</li>
									<li>
										<button
											on:click={() => {
												close();
												removeFromItinerary();
											}}
											class="text-error flex items-center gap-2"
										>
											<CalendarRemove class="w-4 h-4 text-error" />
											{$t('itinerary.remove_from_itinerary')}
										</button>
									</li>
								{/if}
								{#if itineraryItem.is_global}
									<li>
										<button
											on:click={() => {
												close();
												removeFromItinerary();
											}}
											class="text-error flex items-center gap-2"
										>
											<CalendarRemove class="w-4 h-4 text-error" />
											{$t('itinerary.remove_from_trip_context')}
										</button>
									</li>
								{/if}
							{/if}

							{#if user.uuid == adventure.user?.uuid}
								<div class="divider my-1"></div>
								<li>
									<button
										id="delete_adventure"
										data-umami-event="Delete Adventure"
										class="text-error flex items-center gap-2"
										on:click={() => {
											close();
											isWarningModalOpen = true;
										}}
									>
										<TrashCan class="w-4 h-4" />
										{$t('adventures.delete')}
									</button>
								</li>
							{/if}
						</CardActionsMenu>
					{/if}
				{/if}
			</div>
		</div>

		<!-- Inline stats: location, rating, visits -->
		<div
			class="flex flex-wrap items-center text-base-content/70 min-w-0"
			class:gap-2={compact}
			class:gap-3={!compact}
			class:text-xs={compact}
			class:text-sm={!compact}
		>
			{#if adventure.location}
				<div class="flex items-center gap-1 min-w-0">
					<MapMarker class="w-4 h-4 text-primary" />
					<span class="truncate max-w-[18rem]">{adventure.location}</span>
				</div>
			{/if}

			<RatingDisplay
				averageRating={adventure.average_rating}
				fallbackRating={adventure.rating}
				ratingCount={adventure.rating_count}
			/>

			<PriceTierBadge priceTier={adventure.price_tier} />

			<VisitCountBadge visitCount={visitSummary.visitCount} />
		</div>

		<!-- Tags -->
		<TagsDisplay tags={adventure.tags} />
	</div>

	{#if !readOnly}
		{#if type == 'link'}
			<div class="card-body p-4 pt-0">
				<button class="btn btn-primary btn-block btn-sm" on:click={link}>
					<Link class="w-4 h-4 mr-2" />
					Link Adventure
				</button>
			</div>
		{/if}
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
