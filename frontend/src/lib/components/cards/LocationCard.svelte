<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Location, Collection, User } from '$lib/types';
	const dispatch = createEventDispatcher();

	import Launch from '~icons/mdi/launch';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import ContentCopy from '~icons/mdi/content-copy';
	import TrashCan from '~icons/mdi/trash-can-outline';
	import Calendar from '~icons/mdi/calendar';
	import Clock from '~icons/mdi/clock-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import LinkIcon from '~icons/mdi/link-variant';
	import Check from '~icons/mdi/check';
	import { addToast } from '$lib/toasts';
	import { copyToClipboard } from '$lib/index';
	import Link from '~icons/mdi/link-variant';
	import LinkVariantRemove from '~icons/mdi/link-variant-remove';
	import Plus from '~icons/mdi/plus';
	import CollectionLink from '../CollectionLink.svelte';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import DeleteWarning from '../DeleteWarning.svelte';
	import CardCarousel from '../CardCarousel.svelte';
	import { t } from 'svelte-i18n';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import CollectionItineraryPlanner from '../collections/CollectionItineraryPlanner.svelte';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Globe from '~icons/mdi/globe';
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '$lib/money';

	export let type: string | null = null;
	export let user: User | null;
	export let collection: Collection | null = null;
	export let readOnly: boolean = false;
	export let compact: boolean = false; // For compact grid display in itinerary
	export let itineraryItem: CollectionItineraryPlanner | null = null;

	let isCollectionModalOpen: boolean = false;
	let isWarningModalOpen: boolean = false;
	let copied: boolean = false;
	let isActionsMenuOpen: boolean = false;
	let actionsMenuRef: HTMLDivElement | null = null;
	const ACTIONS_CLOSE_EVENT = 'card-actions-close';
	const handleCloseEvent = () => (isActionsMenuOpen = false);

	function handleDocumentClick(event: MouseEvent) {
		if (!isActionsMenuOpen) return;
		const target = event.target as Node | null;
		if (actionsMenuRef && target && !actionsMenuRef.contains(target)) {
			isActionsMenuOpen = false;
		}
	}

	function closeAllLocationMenus() {
		window.dispatchEvent(new CustomEvent(ACTIONS_CLOSE_EVENT));
	}

	onMount(() => {
		document.addEventListener('click', handleDocumentClick);
		window.addEventListener(ACTIONS_CLOSE_EVENT, handleCloseEvent);
		return () => {
			document.removeEventListener('click', handleDocumentClick);
			window.removeEventListener(ACTIONS_CLOSE_EVENT, handleCloseEvent);
		};
	});

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

	export let adventure: Location;
	let displayActivityTypes: string[] = [];
	let remainingCount = 0;

	// Price formatting
	$: adventurePriceLabel = formatMoney(
		toMoneyValue(adventure?.price, adventure?.price_currency, DEFAULT_CURRENCY)
	);

	// Process activity types for display
	$: {
		if (adventure.tags) {
			if (adventure.tags.length <= 3) {
				displayActivityTypes = adventure.tags;
				remainingCount = 0;
			} else {
				displayActivityTypes = adventure.tags.slice(0, 3);
				remainingCount = adventure.tags.length - 3;
			}
		}
	}

	// Creator avatar helpers
	$: creatorInitials =
		adventure.user?.first_name && adventure.user?.last_name
			? `${adventure.user.first_name[0]}${adventure.user.last_name[0]}`
			: adventure.user?.first_name?.[0] || adventure.user?.username?.[0] || '?';

	$: creatorDisplayName = adventure.user?.first_name
		? `${adventure.user.first_name} ${adventure.user.last_name || ''}`.trim()
		: adventure.user?.username || 'Unknown User';

	// Helper functions for display

	function renderStars(rating: number) {
		const stars = [];
		for (let i = 1; i <= 5; i++) {
			stars.push(i <= rating);
		}
		return stars;
	}

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

	let isDuplicating = false;

	async function duplicateAdventure() {
		if (isDuplicating) return;
		isDuplicating = true;
		try {
			const duplicatePayload = collection?.id ? { collection_id: collection.id } : null;
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

		<!-- Status Overlay (icon-only) -->
		<div class="absolute top-2 left-4 flex items-center gap-3">
			<div
				class="tooltip tooltip-right"
				data-tip={adventure.is_visited ? $t('adventures.visited') : $t('adventures.not_visited')}
			>
				{#if adventure.is_visited}
					<div class="badge badge-sm badge-success p-1 rounded-full shadow-sm">
						<Calendar class="w-4 h-4" />
					</div>
				{:else}
					<div class="badge badge-sm badge-warning p-1 rounded-full shadow-sm">
						<Clock class="w-4 h-4" />
					</div>
				{/if}
			</div>
		</div>

		<!-- Privacy Indicator -->
		<div class="absolute top-2 right-4">
			<div
				class="tooltip tooltip-left"
				data-tip={adventure.is_public ? $t('adventures.public') : $t('adventures.private')}
			>
				<div
					class="badge badge-sm p-1 rounded-full text-base-content shadow-sm"
					role="img"
					aria-label={adventure.is_public ? $t('adventures.public') : $t('adventures.private')}
				>
					{#if adventure.is_public}
						<Eye class="w-4 h-4" />
					{:else}
						<EyeOff class="w-4 h-4" />
					{/if}
				</div>
			</div>
		</div>

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
						<div
							class="dropdown dropdown-end relative z-50"
							class:dropdown-open={isActionsMenuOpen}
							bind:this={actionsMenuRef}
						>
							<button
								type="button"
								class="btn btn-square btn-sm p-1 text-base-content"
								aria-haspopup="menu"
								aria-label={$t('adventures.location_actions') || 'Location actions'}
								on:click|stopPropagation={() => {
									if (isActionsMenuOpen) {
										isActionsMenuOpen = false;
										return;
									}
									closeAllLocationMenus();
									isActionsMenuOpen = true;
								}}
							>
								<DotsHorizontal class="w-5 h-5" />
							</button>
							<ul
								tabindex="-1"
								class="dropdown-content menu bg-base-100 rounded-box z-[9999] w-52 p-2 shadow-lg border border-base-300"
							>
								<li>
									<button
										on:click={() => {
											isActionsMenuOpen = false;
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
												isActionsMenuOpen = false;
												duplicateAdventure();
											}}
											class="flex items-center gap-2"
											disabled={isDuplicating}
										>
											<ContentCopy class="w-4 h-4" />
											{isDuplicating ? '...' : $t('adventures.duplicate')}
										</button>
									</li>
								{/if}
								{#if user?.uuid == adventure.user?.uuid}
									<li>
										<button
											on:click={() => {
												isActionsMenuOpen = false;
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
												isActionsMenuOpen = false;
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
										<button
											on:click={() => {
												isActionsMenuOpen = false;
												copyLink();
											}}
											class="flex items-center gap-2"
										>
											{#if copied}
												<Check class="w-4 h-4 text-success" />
												<span>{$t('adventures.link_copied')}</span>
											{:else}
												<LinkIcon class="w-4 h-4" />
												{$t('adventures.copy_link')}
											{/if}
										</button>
									</li>
								{/if}

								{#if itineraryItem && itineraryItem.id}
									<div class="divider my-1"></div>
									{#if !itineraryItem.is_global}
										<li>
											<button
												on:click={() => {
													isActionsMenuOpen = false;
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
													isActionsMenuOpen = false;
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
													isActionsMenuOpen = false;
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
													isActionsMenuOpen = false;
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
												isActionsMenuOpen = false;
												isWarningModalOpen = true;
											}}
										>
											<TrashCan class="w-4 h-4" />
											{$t('adventures.delete')}
										</button>
									</li>
								{/if}
							</ul>
						</div>
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

			{#if adventure.rating}
				<div class="flex items-center gap-1">
					<div class="flex -ml-1">
						{#each renderStars(adventure.rating) as filled}
							{#if filled}
								<Star class="w-4 h-4 text-warning fill-current" />
							{:else}
								<StarOutline class="w-4 h-4 text-base-content/30" />
							{/if}
						{/each}
					</div>
					<span class="text-xs text-base-content/60">({adventure.rating}/5)</span>
				</div>
			{/if}

			{#if adventurePriceLabel}
				<span class="badge badge-ghost badge-sm whitespace-nowrap">💰 {adventurePriceLabel}</span>
			{/if}
		</div>

		<!-- Tags (compact) -->
		{#if displayActivityTypes.length > 0}
			<div class="flex flex-wrap gap-2">
				{#each displayActivityTypes as tag}
					<span class="badge badge-ghost badge-sm">{tag}</span>
				{/each}
				{#if remainingCount > 0}
					<span class="badge badge-ghost badge-sm">+{remainingCount}</span>
				{/if}
			</div>
		{/if}
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
