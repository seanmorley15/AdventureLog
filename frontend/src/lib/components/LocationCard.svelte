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
	import CollectionLink from './CollectionLink.svelte';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import DeleteWarning from './DeleteWarning.svelte';
	import CardCarousel from './CardCarousel.svelte';
	import { t } from 'svelte-i18n';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import { isEntityOutsideCollectionDateRange } from '$lib/dateUtils';

	export let type: string | null = null;
	export let user: User | null;
	export let collection: Collection | null = null;
	export let readOnly: boolean = false;

	let isCollectionModalOpen: boolean = false;
	let isWarningModalOpen: boolean = false;

	export let adventure: Location;
	let displayActivityTypes: string[] = [];
	let remainingCount = 0;

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

	let outsideCollectionRange: boolean = false;

	$: {
		if (collection && collection.start_date && collection.end_date) {
			outsideCollectionRange = adventure.visits.every((visit) =>
				isEntityOutsideCollectionDateRange(visit, collection)
			);
		} else {
			outsideCollectionRange = false;
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
	function formatVisitCount() {
		const count = adventure.visits.length;
		return count > 1 ? `${count} ${$t('adventures.visits')}` : `${count} ${$t('adventures.visit')}`;
	}

	function renderStars(rating: number) {
		const stars = [];
		for (let i = 1; i <= 5; i++) {
			stars.push(i <= rating);
		}
		return stars;
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
	class="card w-full max-w-md bg-base-300 shadow-2xl hover:shadow-3xl transition-all duration-300 border border-base-300 hover:border-primary/20 group"
>
	<!-- Image Section with Overlay -->
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel images={adventure.images} icon={adventure.category?.icon} name={adventure.name} />

		<!-- Status Overlay -->
		<div class="absolute top-4 left-4 flex flex-col gap-2">
			<div
				class="badge badge-sm {adventure.is_visited ? 'badge-success' : 'badge-warning'} shadow-lg"
			>
				{adventure.is_visited ? $t('adventures.visited') : $t('adventures.planned')}
			</div>
			{#if outsideCollectionRange}
				<div class="badge badge-sm badge-error shadow-lg">{$t('adventures.out_of_range')}</div>
			{/if}
		</div>

		<!-- Privacy Indicator -->
		<div class="absolute top-4 right-4">
			<div
				class="tooltip tooltip-left"
				data-tip={adventure.is_public ? $t('adventures.public') : $t('adventures.private')}
			>
				<div
					class="btn btn-circle btn-sm btn-ghost bg-black/20 backdrop-blur-sm border-0 text-white"
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
				<div class="badge badge-primary shadow-lg font-medium">
					{adventure.category.display_name}
					{adventure.category.icon}
				</div>
			</div>
		{/if}

		<!-- Creator Avatar -->
		{#if adventure.user && collection}
			<div class="absolute bottom-4 right-4">
				<div class="tooltip tooltip-left" data-tip={creatorDisplayName}>
					<div class="avatar">
						<div class="w-8 h-8 rounded-full ring-2 ring-white/50 shadow-lg">
							{#if adventure.user.profile_pic}
								<img
									src={adventure.user.profile_pic}
									alt={creatorDisplayName}
									class="rounded-full object-cover"
								/>
							{:else}
								<div
									class="w-8 h-8 bg-gradient-to-br from-primary to-secondary rounded-full flex items-center justify-center text-primary-content font-semibold text-xs shadow-lg"
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
	<div class="card-body p-6 space-y-4">
		<!-- Header Section -->
		<div class="space-y-3">
			<a
				href="/locations/{adventure.id}"
				class="text-xl font-bold text-left hover:text-primary transition-colors duration-200 line-clamp-2 group-hover:underline block"
			>
				{adventure.name}
			</a>

			<!-- Location -->
			{#if adventure.location}
				<div class="flex items-center gap-2 text-base-content/70">
					<MapMarker class="w-4 h-4 text-primary" />
					<span class="text-sm font-medium truncate">{adventure.location}</span>
				</div>
			{/if}

			<!-- Rating -->
			{#if adventure.rating}
				<div class="flex items-center gap-2">
					<div class="flex">
						{#each renderStars(adventure.rating) as filled}
							{#if filled}
								<Star class="w-4 h-4 text-warning fill-current" />
							{:else}
								<StarOutline class="w-4 h-4 text-base-content/30" />
							{/if}
						{/each}
					</div>
					<span class="text-sm text-base-content/60">({adventure.rating}/5)</span>
				</div>
			{/if}
		</div>

		<!-- Stats Section -->
		{#if adventure.visits.length > 0}
			<div class="flex items-center gap-2 p-3 bg-base-200 rounded-lg">
				<Calendar class="w-4 h-4 text-primary" />
				<span class="text-sm font-medium">{formatVisitCount()}</span>
			</div>
		{/if}

		<!-- Actions Section -->
		{#if !readOnly}
			<div class="pt-4 border-t border-base-300">
				{#if type != 'link'}
					<div class="flex justify-between items-center">
						<button
							class="btn btn-base-300 btn-sm flex-1 mr-2"
							on:click={() => goto(`/locations/${adventure.id}`)}
						>
							<Launch class="w-4 h-4" />
							{$t('adventures.open_details')}
						</button>

						{#if (adventure.user && adventure.user.uuid == user?.uuid) || (collection && user && collection.shared_with?.includes(user.uuid)) || (collection && user && collection.user == user.uuid)}
							<div class="dropdown dropdown-end">
								<div tabindex="0" role="button" class="btn btn-square btn-sm btn-base-300">
									<DotsHorizontal class="w-5 h-5" />
								</div>
								<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
								<ul
									tabindex="0"
									class="dropdown-content menu bg-base-100 rounded-box z-[1] w-56 p-2 shadow-xl border border-base-300"
								>
									<li>
										<button on:click={editAdventure} class="flex items-center gap-2">
											<FileDocumentEdit class="w-4 h-4" />
											{$t('adventures.edit_location')}
										</button>
									</li>

									{#if user?.uuid == adventure.user?.uuid}
										<li>
											<button
												on:click={() => (isCollectionModalOpen = true)}
												class="flex items-center gap-2"
											>
												<Plus class="w-4 h-4" />
												{$t('collection.manage_collections')}
											</button>
										</li>
									{:else if collection && user && collection.user == user.uuid}
										<li>
											<button
												on:click={() =>
													removeFromCollection(
														new CustomEvent('unlink', { detail: collection.id })
													)}
												class="flex items-center gap-2"
											>
												<LinkVariantRemove class="w-4 h-4" />
												{$t('adventures.remove_from_collection')}
											</button>
										</li>
									{/if}
									{#if user.uuid == adventure.user?.uuid}
										<div class="divider my-1"></div>
										<li>
											<button
												id="delete_adventure"
												data-umami-event="Delete Adventure"
												class="text-error flex items-center gap-2"
												on:click={() => (isWarningModalOpen = true)}
											>
												<TrashCan class="w-4 h-4" />
												{$t('adventures.delete')}
											</button>
										</li>
									{/if}
								</ul>
							</div>
						{/if}
					</div>
				{:else}
					<button class="btn btn-primary btn-block" on:click={link}>
						<Link class="w-4 h-4" />
						Link Adventure
					</button>
				{/if}
			</div>
		{/if}
	</div>
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
