<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import Launch from '~icons/mdi/launch';

	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import ArchiveArrowDown from '~icons/mdi/archive-arrow-down';
	import ArchiveArrowUp from '~icons/mdi/archive-arrow-up';
	import ShareVariant from '~icons/mdi/share-variant';

	import { goto } from '$app/navigation';
	import type { Location, Collection, User, SlimCollection, ContentImage } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';

	import Plus from '~icons/mdi/plus';
	import Minus from '~icons/mdi/minus';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import TrashCan from '~icons/mdi/trashcan';
	import DeleteWarning from './DeleteWarning.svelte';
	import ShareModal from './ShareModal.svelte';
	import CardCarousel from './CardCarousel.svelte';
	import ExitRun from '~icons/mdi/exit-run';

	const dispatch = createEventDispatcher();

	export let type: String | undefined | null;
	export let linkedCollectionList: string[] | null = null;
	export let user: User | null;
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
				dispatch('archive', collection.id);
			} else {
				addToast('info', $t('adventures.unarchived_collection_message'));
				dispatch('unarchive', collection.id);
			}
		} else {
			console.log('Error archiving collection');
		}
	}

	export let collection: Collection | SlimCollection;

	let location_images: ContentImage[] = [];
	if ('location_images' in collection) {
		location_images = collection.location_images;
	} else {
		location_images = collection.locations.flatMap((location: Location) => location.images);
	}

	let locationLength: number = 0;
	if ('location_count' in collection) {
		locationLength = collection.location_count;
	} else {
		locationLength = collection.locations.length;
	}

	async function deleteCollection() {
		let res = await fetch(`/api/collections/${collection.id}`, {
			method: 'DELETE'
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
	class="card w-full max-w-md bg-base-300 shadow-2xl hover:shadow-3xl transition-all duration-300 border border-base-300 hover:border-primary/20 group"
>
	<!-- Image Carousel -->
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel images={location_images} name={collection.name} icon="📚" />

		<!-- Badge Overlay -->
		<div class="absolute top-4 left-4 flex flex-col gap-2">
			<div class="badge badge-sm badge-secondary shadow-lg">
				{collection.is_public ? $t('adventures.public') : $t('adventures.private')}
			</div>
			{#if collection.is_archived}
				<div class="badge badge-sm badge-warning shadow-lg">
					{$t('adventures.archived')}
				</div>
			{/if}
		</div>
	</div>

	<!-- Content -->
	<div class="card-body p-6 space-y-4">
		<!-- Title -->
		<div class="space-y-3">
			<button
				on:click={() => goto(`/collections/${collection.id}`)}
				class="text-xl font-bold text-left hover:text-primary transition-colors duration-200 line-clamp-2 group-hover:underline"
			>
				{collection.name}
			</button>

			<!-- Adventure Count -->
			<p class="text-sm text-base-content/70">
				{locationLength}
				{$t('locations.locations')}
			</p>

			<!-- Date Range -->
			{#if collection.start_date && collection.end_date}
				<p class="text-sm font-medium">
					{$t('adventures.dates')}:
					{new Date(collection.start_date).toLocaleDateString(undefined, { timeZone: 'UTC' })} –
					{new Date(collection.end_date).toLocaleDateString(undefined, { timeZone: 'UTC' })}
				</p>
				<p class="text-sm text-base-content/60">
					{$t('adventures.duration')}: {Math.floor(
						(new Date(collection.end_date).getTime() - new Date(collection.start_date).getTime()) /
							(1000 * 60 * 60 * 24)
					) + 1} days
				</p>
			{/if}
		</div>

		<!-- Actions -->
		<div class="pt-4 border-t border-base-300">
			{#if type == 'link'}
				{#if linkedCollectionList && linkedCollectionList
						.map(String)
						.includes(String(collection.id))}
					<button
						class="btn btn-error btn-block"
						on:click={() => dispatch('unlink', collection.id)}
					>
						<Minus class="w-4 h-4" />
						{$t('adventures.remove_from_collection')}
					</button>
				{:else}
					<button
						class="btn btn-primary btn-block"
						on:click={() => dispatch('link', collection.id)}
					>
						<Plus class="w-4 h-4" />
						{$t('adventures.add_to_collection')}
					</button>
				{/if}
			{:else}
				<div class="flex justify-between items-center">
					<button
						class="btn btn-neutral btn-sm flex-1 mr-2"
						on:click={() => goto(`/collections/${collection.id}`)}
					>
						<Launch class="w-4 h-4" />
						{$t('adventures.open_details')}
					</button>
					{#if user && user.uuid == collection.user}
						<div class="dropdown dropdown-end">
							<button type="button" class="btn btn-square btn-sm btn-base-300">
								<DotsHorizontal class="w-5 h-5" />
							</button>
							<ul
								class="dropdown-content menu bg-base-100 rounded-box z-[1] w-64 p-2 shadow-xl border border-base-300"
							>
								{#if type != 'viewonly'}
									<li>
										<button class="flex items-center gap-2" on:click={editAdventure}>
											<FileDocumentEdit class="w-4 h-4" />
											{$t('adventures.edit_collection')}
										</button>
									</li>
									<li>
										<button
											class="flex items-center gap-2"
											on:click={() => (isShareModalOpen = true)}
										>
											<ShareVariant class="w-4 h-4" />
											{$t('adventures.share')}
										</button>
									</li>
									{#if collection.is_archived}
										<li>
											<button
												class="flex items-center gap-2"
												on:click={() => archiveCollection(false)}
											>
												<ArchiveArrowUp class="w-4 h-4" />
												{$t('adventures.unarchive')}
											</button>
										</li>
									{:else}
										<li>
											<button
												class="flex items-center gap-2"
												on:click={() => archiveCollection(true)}
											>
												<ArchiveArrowDown class="w-4 h-4" />
												{$t('adventures.archive')}
											</button>
										</li>
									{/if}
									<div class="divider my-1"></div>
									<li>
										<button
											id="delete_collection"
											data-umami-event="Delete Collection"
											class="text-error flex items-center gap-2"
											on:click={() => (isWarningModalOpen = true)}
										>
											<TrashCan class="w-4 h-4" />
											{$t('adventures.delete')}
										</button>
									</li>
								{/if}
								{#if type == 'viewonly'}
									<li>
										<button
											class="flex items-center gap-2"
											on:click={() => goto(`/collections/${collection.id}`)}
										>
											<Launch class="w-4 h-4" />
											{$t('adventures.open_details')}
										</button>
									</li>
								{/if}
							</ul>
						</div>
					{:else if user && collection.shared_with && collection.shared_with.includes(user.uuid)}
						<!-- dropdown with leave button -->
						<div class="dropdown dropdown-end">
							<button type="button" class="btn btn-square btn-sm btn-base-300">
								<DotsHorizontal class="w-5 h-5" />
							</button>
							<ul
								class="dropdown-content menu bg-base-100 rounded-box z-[1] w-64 p-2 shadow-xl border border-base-300"
							>
								<li>
									<button
										class="text-error flex items-center gap-2"
										on:click={() => dispatch('leave', collection.id)}
									>
										<ExitRun class="w-4 h-4" />
										{$t('adventures.leave_collection')}
									</button>
								</li>
							</ul>
						</div>
					{/if}
				</div>
			{/if}
		</div>
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
