<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Adventure } from '$lib/types';
	const dispatch = createEventDispatcher();

	import Launch from '~icons/mdi/launch';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import TrashCan from '~icons/mdi/trash-can-outline';
	import Calendar from '~icons/mdi/calendar';
	import MapMarker from '~icons/mdi/map-marker';
	import { addToast } from '$lib/toasts';
	import Link from '~icons/mdi/link-variant';
	import CheckBold from '~icons/mdi/check-bold';
	import FormatListBulletedSquare from '~icons/mdi/format-list-bulleted-square';
	import LinkVariantRemove from '~icons/mdi/link-variant-remove';
	import Plus from '~icons/mdi/plus';
	import CollectionLink from './CollectionLink.svelte';

	export let type: string;

	let isCollectionModalOpen: boolean = false;

	export let adventure: Adventure;

	async function deleteAdventure() {
		let res = await fetch(`/adventures/${adventure.id}?/delete`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded'
			}
		});
		if (res.ok) {
			console.log('Adventure deleted');
			addToast('info', 'Adventure deleted successfully!');
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
			console.log('Adventure removed from collection');
			addToast('info', 'Adventure removed from collection successfully!');
			dispatch('delete', adventure.id);
		} else {
			console.log('Error removing adventure from collection');
		}
	}

	function changeType(newType: string) {
		return async () => {
			let res = await fetch(`/api/adventures/${adventure.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ type: newType })
			});
			if (res.ok) {
				console.log('Adventure type changed');
				addToast('info', 'Adventure type changed successfully!');
				adventure.type = newType;
			} else {
				console.log('Error changing adventure type');
			}
		};
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
			addToast('info', 'Adventure linked to collection successfully!');
			isCollectionModalOpen = false;
			dispatch('delete', adventure.id);
		} else {
			console.log('Error linking adventure to collection');
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

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-primary-content shadow-xl overflow-hidden text-base-content"
>
	<figure>
		<!-- svelte-ignore a11y-img-redundant-alt -->
		{#if adventure.image && adventure.image !== ''}
			<img src={adventure.image} alt="Adventure Image" class="w-full h-48 object-cover" />
		{:else}
			<img
				src={'https://placehold.co/300?text=No%20Image%20Found&font=roboto'}
				alt="No image available"
				class="w-full h-48 object-cover"
			/>
		{/if}
	</figure>

	<div class="card-body">
		<h2 class="card-title break-words text-wrap">
			{adventure.name}
		</h2>
		{#if adventure.type == 'visited'}
			<div class="badge badge-primary">Visited</div>
		{:else}
			<div class="badge badge-secondary">Planned</div>
		{/if}
		{#if adventure.location && adventure.location !== ''}
			<div class="inline-flex items-center">
				<MapMarker class="w-5 h-5 mr-1" />
				<p class="ml-.5">{adventure.location}</p>
			</div>
		{/if}
		{#if adventure.date && adventure.date !== ''}
			<div class="inline-flex items-center">
				<Calendar class="w-5 h-5 mr-1" />
				<p>{new Date(adventure.date).toLocaleDateString()}</p>
			</div>
		{/if}
		{#if adventure.activity_types && adventure.activity_types.length > 0}
			<ul class="flex flex-wrap">
				{#each adventure.activity_types as activity}
					<div class="badge badge-primary mr-1 text-md font-semibold pb-2 pt-1 mb-1">
						{activity}
					</div>
				{/each}
			</ul>
		{/if}
		<div class="card-actions justify-end mt-2">
			{#if type == 'visited'}
				<button class="btn btn-primary" on:click={() => goto(`/adventures/${adventure.id}`)}
					><Launch class="w-6 h-6" /></button
				>
				<button class="btn btn-primary" on:click={editAdventure}>
					<FileDocumentEdit class="w-6 h-6" />
				</button>
				<button class="btn btn-secondary" on:click={deleteAdventure}
					><TrashCan class="w-6 h-6" /></button
				>
			{/if}
			{#if type == 'planned'}
				<button class="btn btn-primary" on:click={() => goto(`/adventures/${adventure.id}`)}
					><Launch class="w-6 h-6" /></button
				>
				<button class="btn btn-primary" on:click={editAdventure}>
					<FileDocumentEdit class="w-6 h-6" />
				</button>
				<button class="btn btn-secondary" on:click={deleteAdventure}
					><TrashCan class="w-6 h-6" /></button
				>
			{/if}
			{#if type == 'link'}
				<button class="btn btn-primary" on:click={link}><Link class="w-6 h-6" /></button>
			{/if}
			{#if adventure.type == 'visited'}
				<button class="btn btn-secondary" on:click={changeType('planned')}
					><FormatListBulletedSquare class="w-6 h-6" /></button
				>
			{/if}

			{#if adventure.type == 'planned'}
				<button class="btn btn-secondary" on:click={changeType('visited')}
					><CheckBold class="w-6 h-6" /></button
				>
			{/if}
			{#if adventure.collection}
				<button class="btn btn-secondary" on:click={removeFromCollection}
					><LinkVariantRemove class="w-6 h-6" /></button
				>
			{/if}
			{#if !adventure.collection}
				<button class="btn btn-secondary" on:click={() => (isCollectionModalOpen = true)}
					><Plus class="w-6 h-6" /></button
				>
			{/if}
		</div>
	</div>
</div>
