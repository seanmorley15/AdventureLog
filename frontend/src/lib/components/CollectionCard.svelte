<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import Launch from '~icons/mdi/launch';

	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import ArchiveArrowDown from '~icons/mdi/archive-arrow-down';
	import ArchiveArrowUp from '~icons/mdi/archive-arrow-up';

	import { goto } from '$app/navigation';
	import type { Adventure, Collection } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';

	import Plus from '~icons/mdi/plus';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import TrashCan from '~icons/mdi/trashcan';
	import DeleteWarning from './DeleteWarning.svelte';
	import ShareModal from './ShareModal.svelte';
	import CardCarousel from './CardCarousel.svelte';

	const dispatch = createEventDispatcher();

	export let type: String | undefined | null;
	export let adventures: Adventure[] = [];
	let isShareModalOpen: boolean = false;

	function editAdventure() {
		dispatch('edit', collection);
	}

	async function archiveCollection(is_archived: boolean) {
		console.log(JSON.stringify({ is_archived: is_archived }));
		let res = await fetch(`/api/collections/${collection.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ is_archived: is_archived })
		});
		if (res.ok) {
			if (is_archived) {
				addToast('info', $t('adventures.archived_collection_message'));
			} else {
				addToast('info', $t('adventures.unarchived_collection_message'));
			}
			dispatch('delete', collection.id);
		} else {
			console.log('Error archiving collection');
		}
	}

	export let collection: Collection;

	async function deleteCollection() {
		let res = await fetch(`/collections/${collection.id}?/delete`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded'
			}
		});
		if (res.ok) {
			addToast('info', $t('adventures.delete_collection_success'));
			dispatch('delete', collection.id);
		} else {
			console.log('Error deleting collection');
		}
	}

	let isWarningModalOpen: boolean = false;
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_collection')}
		button_text={$t('adventures.delete')}
		description={$t('adventures.delete_collection_warning')}
		is_warning={true}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteCollection}
	/>
{/if}

{#if isShareModalOpen}
	<ShareModal {collection} on:close={() => (isShareModalOpen = false)} />
{/if}

<div
	class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-neutral text-neutral-content shadow-xl"
>
	<CardCarousel {adventures} />
	<div class="card-body">
		<div class="flex justify-between">
			<button
				on:click={() => goto(`/collections/${collection.id}`)}
				class="text-2xl font-semibold -mt-2 break-words text-wrap hover:underline"
			>
				{collection.name}
			</button>
		</div>
		<div class="inline-flex gap-2 mb-2">
			<div class="badge badge-secondary">
				{collection.is_public ? $t('adventures.public') : $t('adventures.private')}
			</div>
			{#if collection.is_archived}
				<div class="badge badge-warning">{$t('adventures.archived')}</div>
			{/if}
		</div>
		<p>{collection.adventures.length} {$t('navbar.adventures')}</p>
		{#if collection.start_date && collection.end_date}
			<p>
				{$t('adventures.dates')}: {new Date(collection.start_date).toLocaleDateString(undefined, {
					timeZone: 'UTC'
				})} -
				{new Date(collection.end_date).toLocaleDateString(undefined, { timeZone: 'UTC' })}
			</p>
			<!-- display the duration in days -->
			<p>
				{$t('adventures.duration')}: {Math.floor(
					(new Date(collection.end_date).getTime() - new Date(collection.start_date).getTime()) /
						(1000 * 60 * 60 * 24)
				) + 1}{' '}
				days
			</p>{/if}

		<div class="card-actions justify-end">
			{#if type == 'link'}
				<button class="btn btn-primary" on:click={() => dispatch('link', collection.id)}>
					<Plus class="w-5 h-5 mr-1" />
				</button>
			{:else}
				<div class="dropdown dropdown-end">
					<div tabindex="0" role="button" class="btn btn-neutral-200">
						<DotsHorizontal class="w-6 h-6" />
					</div>
					<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
					<ul
						tabindex="0"
						class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow"
					>
						{#if type != 'link' && type != 'viewonly'}
							<button
								class="btn btn-neutral mb-2"
								on:click={() => goto(`/collections/${collection.id}`)}
								><Launch class="w-5 h-5 mr-1" />{$t('adventures.open_details')}</button
							>
							{#if !collection.is_archived}
								<button class="btn btn-neutral mb-2" on:click={editAdventure}>
									<FileDocumentEdit class="w-6 h-6" />{$t('adventures.edit_collection')}
								</button>
								<button class="btn btn-neutral mb-2" on:click={() => (isShareModalOpen = true)}>
									<FileDocumentEdit class="w-6 h-6" />{$t('adventures.share')}
								</button>
							{/if}
							{#if collection.is_archived}
								<button class="btn btn-neutral mb-2" on:click={() => archiveCollection(false)}>
									<ArchiveArrowUp class="w-6 h-6 mr-1" />{$t('adventures.unarchive')}
								</button>
							{:else}
								<button class="btn btn-neutral mb-2" on:click={() => archiveCollection(true)}>
									<ArchiveArrowDown class="w-6 h-6 mr" />{$t('adventures.archive')}
								</button>
							{/if}
							<button
								id="delete_adventure"
								data-umami-event="Delete Adventure"
								class="btn btn-warning"
								on:click={() => (isWarningModalOpen = true)}
								><TrashCan class="w-6 h-6" />{$t('adventures.delete')}</button
							>
						{/if}
						{#if type == 'viewonly'}
							<button
								class="btn btn-neutral mb-2"
								on:click={() => goto(`/collections/${collection.id}`)}
								><Launch class="w-5 h-5 mr-1" />{$t('adventures.open_details')}</button
							>
						{/if}
					</ul>
				</div>
			{/if}
		</div>
	</div>
</div>
