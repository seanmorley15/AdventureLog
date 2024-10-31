<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Adventure, Collection, User } from '$lib/types';
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

	export let type: string;
	export let user: User | null;
	export let collection: Collection | null = null;

	let isCollectionModalOpen: boolean = false;
	let isWarningModalOpen: boolean = false;

	export let adventure: Adventure;
	let activityTypes: string[] = [];
	// makes it reactivty to changes so it updates automatically
	$: {
		if (adventure.activity_types) {
			activityTypes = adventure.activity_types;
			if (activityTypes.length > 3) {
				activityTypes = activityTypes.slice(0, 3);
				let remaining = adventure.activity_types.length - 3;
				activityTypes.push('+' + remaining);
			}
		}
	}

	async function deleteAdventure() {
		let res = await fetch(`/adventures/${adventure.id}?/delete`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded'
			}
		});
		if (res.ok) {
			addToast('info', $t('adventures.adventure_delete_success'));
			dispatch('delete', adventure.id);
		} else {
			console.log('Error deleting adventure');
		}
	}

	async function removeFromCollection() {
		let res = await fetch(`/api/adventures/${adventure.id}`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ collection: null })
		});
		if (res.ok) {
			addToast('info', `${$t('adventures.collection_remove_success')}`);
			dispatch('delete', adventure.id);
		} else {
			addToast('error', `${$t('adventures.collection_remove_error')}`);
		}
	}

	async function linkCollection(event: CustomEvent<number>) {
		let collectionId = event.detail;
		let res = await fetch(`/api/adventures/${adventure.id}`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ collection: collectionId })
		});
		if (res.ok) {
			console.log('Adventure linked to collection');
			addToast('info', `${$t('adventures.collection_link_success')}`);
			isCollectionModalOpen = false;
			dispatch('delete', adventure.id);
		} else {
			addToast('error', `${$t('adventures.collection_link_error')}`);
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
	<CollectionLink on:link={linkCollection} on:close={() => (isCollectionModalOpen = false)} />
{/if}

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_adventure')}
		button_text="Delete"
		description={$t('adventures.adventure_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteAdventure}
	/>
{/if}

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-neutral text-neutral-content shadow-xl"
>
	<CardCarousel adventures={[adventure]} />

	<div class="card-body">
		<div class="flex justify-between">
			<button
				on:click={() => goto(`/adventures/${adventure.id}`)}
				class="text-2xl font-semibold -mt-2 break-words text-wrap hover:underline text-left"
			>
				{adventure.name}
			</button>
		</div>
		<div>
			<div class="badge badge-primary">{$t(`adventures.activities.${adventure.type}`)}</div>
			<div class="badge badge-success">
				{adventure.is_visited ? $t('adventures.visited') : $t('adventures.planned')}
			</div>
			<div class="badge badge-secondary">
				{adventure.is_public ? $t('adventures.public') : $t('adventures.private')}
			</div>
		</div>
		{#if adventure.location && adventure.location !== ''}
			<div class="inline-flex items-center">
				<MapMarker class="w-5 h-5 mr-1" />
				<p class="ml-.5">{adventure.location}</p>
			</div>
		{/if}
		{#if adventure.visits.length > 0}
			<!-- visited badge -->
			<div class="flex items-center">
				<Calendar class="w-5 h-5 mr-1" />
				<p class="ml-.5">
					{adventure.visits.length}
					{adventure.visits.length > 1 ? $t('adventures.visits') : $t('adventures.visit')}
				</p>
			</div>
		{/if}
		{#if adventure.activity_types && adventure.activity_types.length > 0}
			<ul class="flex flex-wrap">
				{#each activityTypes as activity}
					<div class="badge badge-primary mr-1 text-md font-semibold pb-2 pt-1 mb-1">
						{activity}
					</div>
				{/each}
			</ul>
		{/if}
		<div class="card-actions justify-end mt-2">
			<!-- action options dropdown -->
			{#if type != 'link'}
				{#if adventure.user_id == user?.pk || (collection && user && collection.shared_with.includes(user.uuid))}
					<div class="dropdown dropdown-end">
						<div tabindex="0" role="button" class="btn btn-neutral-200">
							<DotsHorizontal class="w-6 h-6" />
						</div>
						<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
						<ul
							tabindex="0"
							class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow"
						>
							<button
								class="btn btn-neutral mb-2"
								on:click={() => goto(`/adventures/${adventure.id}`)}
								><Launch class="w-6 h-6" />{$t('adventures.open_details')}</button
							>
							<button class="btn btn-neutral mb-2" on:click={editAdventure}>
								<FileDocumentEdit class="w-6 h-6" />
								{$t('adventures.edit_adventure')}
							</button>

							<!-- remove from collection -->
							{#if adventure.collection && user?.pk == adventure.user_id}
								<button class="btn btn-neutral mb-2" on:click={removeFromCollection}
									><LinkVariantRemove class="w-6 h-6" />{$t(
										'adventures.remove_from_collection'
									)}</button
								>
							{/if}
							{#if !adventure.collection}
								<button class="btn btn-neutral mb-2" on:click={() => (isCollectionModalOpen = true)}
									><Plus class="w-6 h-6" />{$t('adventures.add_to_collection')}</button
								>
							{/if}
							<button
								id="delete_adventure"
								data-umami-event="Delete Adventure"
								class="btn btn-warning"
								on:click={() => (isWarningModalOpen = true)}
								><TrashCan class="w-6 h-6" />{$t('adventures.delete')}</button
							>
						</ul>
					</div>
				{:else}
					<button
						class="btn btn-neutral-200 mb-2"
						on:click={() => goto(`/adventures/${adventure.id}`)}><Launch class="w-6 h-6" /></button
					>
				{/if}
			{/if}
			{#if type == 'link'}
				<button class="btn btn-primary" on:click={link}><Link class="w-6 h-6" /></button>
			{/if}
		</div>
	</div>
</div>
