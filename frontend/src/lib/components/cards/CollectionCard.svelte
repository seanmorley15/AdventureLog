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
	import { copyToClipboard } from '$lib/index';

	import Plus from '~icons/mdi/plus';
	import Minus from '~icons/mdi/minus';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import TrashCan from '~icons/mdi/trashcan';
	import DeleteWarning from '../DeleteWarning.svelte';
	import ShareModal from '../ShareModal.svelte';
	import CardCarousel from '../CardCarousel.svelte';
	import ExitRun from '~icons/mdi/exit-run';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import Check from '~icons/mdi/check';
	import MapMarker from '~icons/mdi/map-marker-multiple';
	import LinkIcon from '~icons/mdi/link';
	import DownloadIcon from '~icons/mdi/download';
	import ContentCopy from '~icons/mdi/content-copy';

	const dispatch = createEventDispatcher();

	export let type: String | undefined | null;
	export let linkedCollectionList: string[] | null = null;
	export let user: User | null;
	let isShareModalOpen: boolean = false;
	let copied: boolean = false;

	async function copyLink() {
		try {
			const url = `${location.origin}/collections/${collection.id}`;
			await copyToClipboard(url);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch (e) {
			addToast('error', $t('adventures.copy_failed') || 'Copy failed');
		}
	}

	let isDuplicating = false;

	async function duplicateCollection() {
		if (isDuplicating) return;
		isDuplicating = true;
		try {
			const res = await fetch(`/api/collections/${collection.id}/duplicate/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});
			if (res.ok) {
				const newCollection = await res.json();
				addToast('success', $t('adventures.collection_duplicate_success'));
				dispatch('duplicate', newCollection);
			} else {
				addToast('error', $t('adventures.collection_duplicate_error'));
			}
		} catch (e) {
			addToast('error', $t('adventures.collection_duplicate_error'));
		} finally {
			isDuplicating = false;
		}
	}

	function editAdventure() {
		dispatch('edit', collection);
	}

	async function exportCollectionZip() {
		try {
			const res = await fetch(`/api/collections/${collection.id}/export`);
			if (!res.ok) {
				addToast('error', $t('adventures.export_failed') || 'Export failed');
				return;
			}
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `collection-${String(collection.name).replace(/\s+/g, '_')}.zip`;
			a.click();
			URL.revokeObjectURL(url);
			addToast('success', $t('adventures.export_success') || 'Exported collection');
		} catch (e) {
			addToast('error', $t('adventures.export_failed') || 'Export failed');
		}
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
	$: {
		let images: ContentImage[] = [];
		if ('location_images' in collection) {
			images = collection.location_images;
		} else {
			images = collection.locations.flatMap((location: Location) => location.images);
		}

		const primaryImage = 'primary_image' in collection ? collection.primary_image : null;
		if (primaryImage) {
			const coverImage = { ...primaryImage, is_primary: true };
			const remainingImages = images
				.filter((img) => img.id !== primaryImage.id)
				.map((img) => ({ ...img, is_primary: false }));
			location_images = [coverImage, ...remainingImages];
		} else {
			location_images = images;
		}
	}

	let locationLength: number = 0;
	$: locationLength =
		'location_count' in collection ? collection.location_count : collection.locations.length;

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
	class="card w-full max-w-md bg-base-300 shadow hover:shadow-md transition-all duration-200 border border-base-300 group"
>
	<!-- Image Carousel -->
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel images={location_images} name={collection.name} icon="📚" />

		<!-- Status Badge Overlay -->
		<div class="absolute top-2 left-4 flex items-center gap-2">
			{#if collection.status === 'folder'}
				<div class="badge badge-sm badge-neutral shadow-sm">
					📁 {$t('adventures.folder')}
				</div>
			{:else if collection.status === 'upcoming'}
				<div class="badge badge-sm badge-info shadow-sm">
					🚀 {$t('adventures.upcoming')}
				</div>
				{#if collection.days_until_start !== null}
					<div class="badge badge-sm badge-accent shadow-sm">
						⏳ {collection.days_until_start}
						{collection.days_until_start === 1 ? $t('adventures.day') : $t('adventures.days')}
					</div>
				{/if}
			{:else if collection.status === 'in_progress'}
				<div class="badge badge-sm badge-success shadow-sm">
					🎯 {$t('adventures.in_progress')}
				</div>
			{:else if collection.status === 'completed'}
				<div class="badge badge-sm badge-primary shadow-sm">
					<Check class="w-4 h-4" />
					{$t('adventures.completed')}
				</div>
			{/if}
			{#if collection.is_archived}
				<div class="badge badge-sm badge-warning shadow-sm">
					{$t('adventures.archived')}
				</div>
			{/if}
		</div>

		<!-- Privacy Indicator -->
		<div class="absolute top-2 right-4">
			<div
				class="tooltip tooltip-left"
				data-tip={collection.is_public ? $t('adventures.public') : $t('adventures.private')}
			>
				<div
					class="badge badge-sm {collection.is_public
						? 'badge-secondary'
						: 'badge-ghost'} shadow-lg"
					aria-label={collection.is_public ? $t('adventures.public') : $t('adventures.private')}
				>
					{#if collection.is_public}
						<Eye class="w-4 h-4" />
					{:else}
						<EyeOff class="w-4 h-4" />
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Content -->
	<div class="card-body p-4 space-y-3">
		<!-- Title -->
		<a
			href="/collections/{collection.id}"
			class="hover:text-primary transition-colors duration-200 line-clamp-2 text-lg font-semibold"
			>{collection.name}</a
		>

		<!-- Stats -->
		<div class="flex flex-wrap items-center gap-2 text-sm text-base-content/70">
			<!-- Location Count -->
			<div class="flex items-center gap-1">
				<MapMarker class="w-4 h-4 text-primary" />
				<span>
					{locationLength}
					{locationLength === 1 ? $t('locations.location') : $t('locations.locations')}
				</span>
			</div>

			<!-- Date Range & Duration -->
			{#if collection.start_date && collection.end_date}
				<span class="text-base-content/60 px-1">•</span>
				<div class="flex items-center gap-1">
					<span>
						{Math.floor(
							(new Date(collection.end_date).getTime() -
								new Date(collection.start_date).getTime()) /
								(1000 * 60 * 60 * 24)
						) + 1}
						{Math.floor(
							(new Date(collection.end_date).getTime() -
								new Date(collection.start_date).getTime()) /
								(1000 * 60 * 60 * 24)
						) +
							1 ===
						1
							? $t('adventures.day')
							: $t('adventures.days')}
					</span>
				</div>
			{/if}
		</div>

		<!-- Date Range (if exists) -->
		{#if collection.start_date && collection.end_date}
			<div class="text-xs text-base-content/60">
				{new Date(collection.start_date).toLocaleDateString(undefined, {
					timeZone: 'UTC',
					month: 'short',
					day: 'numeric',
					year: 'numeric'
				})} – {new Date(collection.end_date).toLocaleDateString(undefined, {
					timeZone: 'UTC',
					month: 'short',
					day: 'numeric',
					year: 'numeric'
				})}
			</div>
		{/if}

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
									{#if collection.is_public}
										<li>
											<button on:click={copyLink} class="flex items-center gap-2">
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
									<li>
										<button class="flex items-center gap-2" on:click={exportCollectionZip}>
											<DownloadIcon class="w-4 h-4" />
											{$t('adventures.export_zip')}
										</button>
									</li>
									<li>
										<button
											class="flex items-center gap-2"
											on:click={duplicateCollection}
											disabled={isDuplicating}
										>
											<ContentCopy class="w-4 h-4" />
											{isDuplicating ? '...' : $t('adventures.duplicate')}
										</button>
									</li>
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
