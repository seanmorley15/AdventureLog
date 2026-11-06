<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Location, Collection, User, SlimCollection, ContentImage } from '#lib/types.js';
	import { addToast } from '#lib/toasts.js';
	import { t } from 'svelte-i18n';
	import { jobErrorMessage, runExport } from '#lib/jobs.js';
	import { copyToClipboard } from '#lib/index.js';
	import { dateFormatFromUser, formatDisplayDate } from '#lib/dateFormat.js';
	import { inclusiveDayCount } from '#lib/dateUtils.js';

	import Launch from '~icons/mdi/launch';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import ArchiveArrowDown from '~icons/mdi/archive-arrow-down';
	import ArchiveArrowUp from '~icons/mdi/archive-arrow-up';
	import ArchiveOutline from '~icons/mdi/archive-outline';
	import ShareVariant from '~icons/mdi/share-variant';
	import TrashCan from '~icons/mdi/trash-can-outline';
	import ExitRun from '~icons/mdi/exit-run';
	import Check from '~icons/mdi/check';
	import CheckCircle from '~icons/mdi/check-circle';
	import CalendarClock from '~icons/mdi/calendar-clock';
	import CalendarRange from '~icons/mdi/calendar-range';
	import ProgressClock from '~icons/mdi/progress-clock';
	import MapMarkerMultiple from '~icons/mdi/map-marker-multiple';
	import FolderOutline from '~icons/mdi/folder-outline';
	import AirplaneTakeoff from '~icons/mdi/airplane-takeoff';
	import LinkIcon from '~icons/mdi/link';
	import DownloadIcon from '~icons/mdi/download';
	import FilePdfBox from '~icons/mdi/file-pdf-box';
	import ContentCopy from '~icons/mdi/content-copy';
	import ImageOutline from '~icons/mdi/image-outline';
	import ImageMultipleOutline from '~icons/mdi/image-multiple-outline';

	import DeleteWarning from '../DeleteWarning.svelte';
	import CollectionShareSheet from '../collections/CollectionShareSheet.svelte';
	import SocialShareModal from '../SocialShareModal.svelte';
	import CardCarousel from '../CardCarousel.svelte';
	import UserAvatar from '../UserAvatar.svelte';
	import CardActionsMenu from './parts/CardActionsMenu.svelte';
	import CardVisibility from './parts/CardVisibility.svelte';

	const dispatch = createEventDispatcher();

	let isShareModalOpen: boolean = $state(false);
	let isSocialShareModalOpen: boolean = $state(false);
	let copied: boolean = $state(false);

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

	let isDuplicating = $state(false);

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

	let isExporting = $state(false);

	/** Exports run on the server in the background: start one, wait for the file, then save it. */
	async function exportCollectionFile(url: string, successKey: string, failedKey: string) {
		if (isExporting) return;
		isExporting = true;
		addToast('info', $t('jobs.preparing'));
		try {
			await runExport(url);
			addToast('success', $t(successKey));
		} catch (e) {
			addToast('error', jobErrorMessage(e, $t(failedKey)));
		} finally {
			isExporting = false;
		}
	}

	async function exportCollectionZip() {
		await exportCollectionFile(
			`/api/collections/${collection.id}/archive/`,
			'adventures.export_success',
			'adventures.export_failed'
		);
	}

	async function exportCollectionPdf() {
		await exportCollectionFile(
			`/api/collections/${collection.id}/pdf/`,
			'adventures.export_pdf_success',
			'adventures.export_pdf_failed'
		);
	}

	async function archiveCollection(is_archived: boolean) {
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

	interface Props {
		type: String | undefined | null;
		user: User | null;
		readOnly?: boolean;
		collection: Collection | SlimCollection;
	}

	let { type, user, readOnly = false, collection }: Props = $props();
	let visibility = $derived(collection.visibility ?? (collection.is_public ? 'public' : 'private'));

	let location_images: ContentImage[] = $derived.by(() => {
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
			return [coverImage, ...remainingImages];
		}
		return images;
	});
	let hasCover = $derived(location_images.length > 0);

	let locationLength: number = $derived(
		'location_count' in collection ? collection.location_count : collection.locations.length
	);

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

	let isWarningModalOpen: boolean = $state(false);

	const dateFormat = $derived(dateFormatFromUser(user));

	// Dated trips count from the dates; day-based trips without dates carry a day count instead.
	let durationDays = $derived(
		inclusiveDayCount(collection.start_date, collection.end_date) ?? collection.day_count ?? null
	);

	// One status, in order of what matters most right now.
	let status = $derived.by(() => {
		if (collection.is_archived) {
			return { text: $t('adventures.archived'), tone: 'badge-warning', icon: ArchiveOutline };
		}
		if (collection.status === 'upcoming') {
			const days = collection.days_until_start;
			return {
				text:
					days === null || days === undefined
						? $t('adventures.upcoming')
						: days === 0
							? $t('cards.starts_today')
							: $t('cards.in_days', { values: { count: days } }),
				tone: 'badge-info',
				icon: CalendarClock
			};
		}
		if (collection.status === 'in_progress') {
			let text = $t('adventures.in_progress');
			if (collection.start_date && durationDays) {
				const start = new Date(`${collection.start_date.split('T')[0]}T00:00:00`);
				const today = new Date();
				today.setHours(0, 0, 0, 0);
				const day = Math.round((today.getTime() - start.getTime()) / 86_400_000) + 1;
				if (day >= 1 && day <= durationDays) {
					text = $t('cards.day_of', { values: { day, total: durationDays } });
				}
			}
			return { text, tone: 'badge-success', icon: ProgressClock };
		}
		if (collection.status === 'completed') {
			return { text: $t('adventures.completed'), tone: 'badge-primary', icon: CheckCircle };
		}
		return null;
	});

	// Anyone besides the owner, so a solo collection doesn't show a lonely avatar.
	let sharedWith = $derived(
		(collection.collaborators ?? []).length > 1 ? (collection.collaborators ?? []) : []
	);
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
	<CollectionShareSheet {collection} onClose={() => (isShareModalOpen = false)} />
{/if}

{#if isSocialShareModalOpen}
	<SocialShareModal
		type="collection"
		id={collection.id}
		name={collection.name}
		isPublic={!!collection.is_public}
		on:close={() => (isSocialShareModalOpen = false)}
	/>
{/if}

<div
	class="card h-full flex flex-col rounded-2xl border border-base-300/60 bg-base-100 shadow-xs transition-colors hover:border-base-300"
	aria-label="collection-card"
>
	<!-- The name sits on the cover, so a collection reads as a cover, not another place. -->
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel
			images={location_images}
			name={collection.name}
			icon={ImageMultipleOutline}
			showCount={false}
		/>

		<div class="absolute left-2 top-2">
			<div
				class="tooltip tooltip-right"
				data-tip={collection.type === 'trip' ? $t('adventures.trip') : $t('adventures.folder')}
			>
				<span
					class="flex h-7 w-7 items-center justify-center rounded-full bg-base-100/85 text-base-content shadow-xs backdrop-blur-sm"
					role="img"
					aria-label={collection.type === 'trip' ? $t('adventures.trip') : $t('adventures.folder')}
				>
					{#if collection.type === 'trip'}
						<AirplaneTakeoff class="h-4 w-4" />
					{:else}
						<FolderOutline class="h-4 w-4" />
					{/if}
				</span>
			</div>
		</div>

		<div class="absolute right-2 top-2">
			<CardVisibility {visibility} />
		</div>

		<div
			class="pointer-events-none absolute inset-x-0 bottom-0 flex flex-col items-start gap-1.5 p-3 {hasCover
				? 'bg-gradient-to-t from-black/75 via-black/35 to-transparent pt-14 text-white'
				: 'text-base-content'}"
		>
			{#if status}
				{@const StatusIcon = status.icon}
				<span class="badge badge-sm gap-1 shadow-xs {status.tone}">
					<StatusIcon class="h-3.5 w-3.5" />
					{status.text}
				</span>
			{/if}
			<a
				href="/collections/{collection.id}"
				class="pointer-events-auto line-clamp-2 text-lg font-semibold leading-snug hover:underline"
			>
				{collection.name}
			</a>
		</div>
	</div>

	<div class="flex flex-1 flex-col gap-3 p-4">
		{#if collection.description}
			<p class="line-clamp-2 text-sm text-base-content/70">{collection.description}</p>
		{/if}

		<div class="flex items-start justify-between gap-3">
			<div class="flex min-w-0 flex-col gap-1.5 text-sm text-base-content/70">
				{#if collection.start_date && collection.end_date}
					<p class="flex items-center gap-1.5">
						<CalendarRange class="h-4 w-4 shrink-0 text-primary" />
						<span class="min-w-0">
							{formatDisplayDate(collection.start_date, dateFormat, { timeZone: 'UTC' })} – {formatDisplayDate(
								collection.end_date,
								dateFormat,
								{ timeZone: 'UTC' }
							)}
							{#if durationDays}
								<span class="text-base-content/50">
									· {$t('cards.day_count', { values: { count: durationDays } })}
								</span>
							{/if}
						</span>
					</p>
				{:else if durationDays}
					<p class="flex items-center gap-1.5">
						<CalendarRange class="h-4 w-4 shrink-0 text-primary" />
						{$t('cards.day_count', { values: { count: durationDays } })}
					</p>
				{/if}
				<p class="flex items-center gap-1.5">
					<MapMarkerMultiple class="h-4 w-4 shrink-0 text-primary" />
					{$t('cards.location_count', { values: { count: locationLength } })}
				</p>
			</div>

			<div class="-mr-1 -mt-1 flex shrink-0 items-center">
				<button
					class="btn btn-ghost btn-square btn-sm"
					aria-label={$t('adventures.open_details')}
					onclick={() => goto(`/collections/${collection.id}`)}
				>
					<Launch class="h-5 w-5" />
				</button>

				{#if !readOnly}
					{#if user && user.uuid == collection.user}
						<CardActionsMenu label={$t('cards.collection_actions')}>
							{#snippet children({ close })}
								{#if type != 'viewonly'}
									<li>
										<button
											onclick={() => {
												close();
												editAdventure();
											}}
										>
											<FileDocumentEdit class="h-4 w-4" />
											{$t('adventures.edit_collection')}
										</button>
									</li>
									<li>
										<button
											onclick={() => {
												close();
												isShareModalOpen = true;
											}}
										>
											<ShareVariant class="h-4 w-4" />
											{$t('adventures.share')}
										</button>
									</li>
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
									{#if visibility === 'public'}
										<li>
											<button onclick={copyLink}>
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
									<li>
										<button
											onclick={() => {
												close();
												archiveCollection(!collection.is_archived);
											}}
										>
											{#if collection.is_archived}
												<ArchiveArrowUp class="h-4 w-4" />
												{$t('adventures.unarchive')}
											{:else}
												<ArchiveArrowDown class="h-4 w-4" />
												{$t('adventures.archive')}
											{/if}
										</button>
									</li>
									<li>
										<button
											onclick={() => {
												close();
												exportCollectionPdf();
											}}
										>
											<FilePdfBox class="h-4 w-4" />
											{$t('adventures.export_pdf')}
										</button>
									</li>
									<li>
										<button
											onclick={() => {
												close();
												exportCollectionZip();
											}}
										>
											<DownloadIcon class="h-4 w-4" />
											{$t('adventures.export_zip')}
										</button>
									</li>
									<li>
										<button
											onclick={() => {
												close();
												duplicateCollection();
											}}
											disabled={isDuplicating}
										>
											<ContentCopy class="h-4 w-4" />
											{isDuplicating ? '...' : $t('adventures.duplicate')}
										</button>
									</li>
									<div class="divider my-1"></div>
									<li>
										<button
											id="delete_collection"
											data-umami-event="Delete Collection"
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
								{:else}
									<li>
										<button onclick={() => goto(`/collections/${collection.id}`)}>
											<Launch class="h-4 w-4" />
											{$t('adventures.open_details')}
										</button>
									</li>
								{/if}
							{/snippet}
						</CardActionsMenu>
					{:else if user && collection.shared_with && collection.shared_with.includes(user.uuid)}
						<CardActionsMenu label={$t('cards.collection_actions')}>
							{#snippet children({ close })}
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
								<li>
									<button class="text-error" onclick={() => dispatch('leave', collection.id)}>
										<ExitRun class="h-4 w-4" />
										{$t('adventures.leave_collection')}
									</button>
								</li>
							{/snippet}
						</CardActionsMenu>
					{/if}
				{/if}
			</div>
		</div>

		{#if sharedWith.length > 0}
			<div class="mt-auto flex items-center pt-1">
				<div class="flex -space-x-2">
					{#each sharedWith.slice(0, 4) as person (person.uuid)}
						<div class="rounded-full ring-2 ring-base-100">
							<UserAvatar
								user={person}
								alt={person.username}
								className="h-6 w-6 shrink-0 rounded-full"
								imgClass="h-6 w-6 shrink-0 rounded-full object-cover"
								textClass="text-[10px]"
							/>
						</div>
					{/each}
				</div>
				{#if sharedWith.length > 4}
					<span class="ml-2 text-xs text-base-content/60">+{sharedWith.length - 4}</span>
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
