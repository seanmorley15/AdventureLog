<script lang="ts">
	import { stopPropagation } from 'svelte/legacy';

	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import type { Collection, Note, User } from '$lib/types';
	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	import { marked } from 'marked'; // Import the markdown parser

	const renderMarkdown = (markdown: string) => {
		return marked(markdown);
	};

	import TrashCan from '~icons/mdi/trash-can';
	import Calendar from '~icons/mdi/calendar';
	import DeleteWarning from '../DeleteWarning.svelte';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import LinkVariant from '~icons/mdi/link-variant';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Launch from '~icons/mdi/launch';
	import Close from '~icons/mdi/close';
	import Globe from '~icons/mdi/globe';
	import type { CollectionItineraryItem } from '$lib/types';
	import { shouldFlipDropdownUp } from '$lib/utils/flipDropdown';

	let isActionsMenuOpen = $state(false);
	let openUpward = $state(false);
	let actionsMenuRef: HTMLDivElement | null = $state(null);
	const ACTIONS_CLOSE_EVENT = 'card-actions-close';
	const handleCloseEvent = () => (isActionsMenuOpen = false);

	function handleDocumentClick(event: MouseEvent) {
		if (!isActionsMenuOpen) return;
		const target = event.target as Node | null;
		if (actionsMenuRef && target && !actionsMenuRef.contains(target)) {
			isActionsMenuOpen = false;
		}
	}

	function closeAllNoteMenus() {
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

	interface Props {
		note: Note;
		user?: User | null;
		collection?: Collection | null;
		readOnly?: boolean;
		itineraryItem?: CollectionItineraryItem | null;
	}

	let {
		note,
		user = null,
		collection = null,
		readOnly = false,
		itineraryItem = null
	}: Props = $props();

	let isWarningModalOpen: boolean = $state(false);
	let isDetailsOpen: boolean = $state(false);

	let canEdit =
		$derived(!readOnly &&
		(note.user == user?.uuid ||
			(collection && user && collection.shared_with?.includes(user.uuid))));

	function editNote() {
		dispatch('edit', note);
	}

	async function deleteNote() {
		const res = await fetch(`/api/notes/${note.id}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('success', $t('notes.note_deleted'));
			isWarningModalOpen = false;
			dispatch('delete', note.id);
		} else {
			addToast($t('notes.note_delete_error'), 'error');
		}
	}

	function changeDay() {
		dispatch('changeDay', { type: 'note', item: note, forcePicker: true });
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
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_note')}
		button_text="Delete"
		description={$t('adventures.note_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteNote}
	/>
{/if}

{#if isDetailsOpen}
	<dialog class="modal modal-open" open>
		<div class="modal-box max-w-3xl space-y-4">
			<div class="flex items-start justify-between gap-3">
				<div class="space-y-2">
					<h3 class="text-xl font-semibold leading-tight">{note.name}</h3>
					<div class="flex flex-wrap items-center gap-3 text-sm text-base-content/70">
						<div class="badge badge-primary badge-sm">{$t('adventures.note')}</div>
						{#if note.date && note.date !== ''}
							<div class="flex items-center gap-2">
								<Calendar class="w-4 h-4 text-primary" />
								<span>{new Date(note.date).toLocaleDateString(undefined, { timeZone: 'UTC' })}</span
								>
							</div>
						{/if}
						{#if note.links && note.links?.length > 0}
							<div class="badge badge-ghost badge-sm">
								<LinkVariant class="w-3 h-3 mr-1" />
								{note.links.length}
								{note.links.length > 1 ? $t('adventures.links') : $t('adventures.link')}
							</div>
						{/if}
					</div>
				</div>
				<button
					type="button"
					class="btn btn-circle btn-ghost btn-sm"
					onclick={() => (isDetailsOpen = false)}
					aria-label={$t('about.close')}
				>
					<Close class="w-4 h-4" />
				</button>
			</div>

			{#if note.content && note.content?.length > 0}
				<article class="prose max-w-none text-base-content">
					{@html renderMarkdown(note.content || '')}
				</article>
			{:else}
				<p class="text-sm text-base-content/70">No content available.</p>
			{/if}

			{#if note.links && note.links?.length > 0}
				<div class="space-y-2">
					<p class="text-sm font-semibold text-base-content">{$t('adventures.links')}</p>
					<div class="flex flex-wrap gap-2">
						{#each note.links as link}
							<a
								class="badge badge-outline gap-1"
								href={link}
								target="_blank"
								rel="noopener noreferrer"
							>
								<LinkVariant class="w-3 h-3" />
								<span class="break-all text-left">{link}</span>
							</a>
						{/each}
					</div>
				</div>
			{/if}

			<div class="modal-action">
				<button class="btn" onclick={() => (isDetailsOpen = false)}>Close</button>
			</div>
		</div>
		<form method="dialog" class="modal-backdrop">
			<button aria-label="close" onclick={() => (isDetailsOpen = false)}>Close</button>
		</form>
	</dialog>
{/if}

<div
	class="card w-full max-w-md bg-base-300 shadow-sm hover:shadow-md transition-all duration-200 border border-base-300 group"
	aria-label="note-card"
>
	<div class="card-body p-4 space-y-3">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<div class="flex-1 min-w-0">
				<h2 class="text-lg font-semibold line-clamp-2">{note.name}</h2>
				<div class="flex flex-wrap items-center gap-2 mt-2">
					<div class="badge badge-primary badge-sm">{$t('adventures.note')}</div>
				</div>
			</div>

			<div class="flex items-center gap-2">
				<button
					class="btn btn-square btn-sm p-1 text-base-content"
					onclick={() => (isDetailsOpen = true)}
					aria-label={$t('adventures.view')}
					type="button"
				>
					<Launch class="w-5 h-5" />
				</button>

				{#if canEdit}
					<div
						class="dropdown dropdown-end relative z-50"
						class:dropdown-open={isActionsMenuOpen}
						class:dropdown-top={openUpward}
						bind:this={actionsMenuRef}
					>
						<button
							type="button"
							class="btn btn-square btn-sm p-1 text-base-content"
							aria-haspopup="menu"
							onclick={stopPropagation(() => {
								if (isActionsMenuOpen) {
									isActionsMenuOpen = false;
									return;
								}
								closeAllNoteMenus();
								openUpward = shouldFlipDropdownUp(actionsMenuRef);
								isActionsMenuOpen = true;
							})}
						>
							<DotsHorizontal class="w-5 h-5" />
						</button>
						<ul
							tabindex="-1"
							class="dropdown-content menu bg-base-100 rounded-box z-[9999] w-52 p-2 shadow-lg border border-base-300 max-h-[min(24rem,calc(100vh-2rem))] overflow-y-auto"
						>
							<li>
								<button
									onclick={() => {
										isActionsMenuOpen = false;
										editNote();
									}}
									class="flex items-center gap-2"
								>
									<FileDocumentEdit class="w-4 h-4" />
									{$t('lodging.edit')}
								</button>
							</li>
							{#if itineraryItem && itineraryItem.id}
								<div class="divider my-1"></div>
								{#if !itineraryItem.is_global}
									<li>
										<button
											onclick={() => {
												isActionsMenuOpen = false;
												dispatch('moveToGlobal', { type: 'note', id: note.id });
											}}
											class="flex items-center gap-2"
										>
											<Globe class="w-4 h-4" />
											{$t('itinerary.move_to_trip_context')}
										</button>
									</li>
									<li>
										<button
											onclick={() => {
												isActionsMenuOpen = false;
												changeDay();
											}}
											class="flex items-center gap-2"
										>
											<CalendarRemove class="w-4 h-4 text" />
											{$t('itinerary.change_day')}
										</button>
									</li>
								{/if}
								<li>
									<button
										onclick={() => {
											isActionsMenuOpen = false;
											removeFromItinerary();
										}}
										class="text-error flex items-center gap-2"
									>
										<CalendarRemove class="w-4 h-4 text-error" />
										{#if itineraryItem.is_global}
											{$t('itinerary.remove_from_trip_context') || 'Remove from Trip Context'}
										{:else}
											{$t('itinerary.remove_from_itinerary')}
										{/if}
									</button>
								</li>
							{/if}
							<div class="divider my-1"></div>
							<li>
								<button
									class="text-error flex items-center gap-2"
									onclick={() => {
										isActionsMenuOpen = false;
										isWarningModalOpen = true;
									}}
								>
									<TrashCan class="w-4 h-4" />
									{$t('adventures.delete')}
								</button>
							</li>
						</ul>
					</div>
				{/if}
			</div>
		</div>

		<!-- Note Content Preview -->
		{#if note.content && note.content?.length > 0}
			<article
				class="prose prose-sm max-w-none overflow-hidden max-h-32 text-sm text-base-content/70 line-clamp-4"
			>
				{@html renderMarkdown(note.content || '')}
			</article>
		{/if}

		<!-- Inline Stats -->
		<div class="flex flex-wrap items-center gap-3 text-sm text-base-content/70">
			{#if note.date && note.date !== ''}
				<div class="flex items-center gap-1">
					<Calendar class="w-4 h-4 text-primary" />
					<span>{new Date(note.date).toLocaleDateString(undefined, { timeZone: 'UTC' })}</span>
				</div>
			{/if}

			{#if note.links && note.links?.length > 0}
				<div class="badge badge-ghost badge-sm">
					<LinkVariant class="w-3 h-3 mr-1" />
					{note.links.length}
					{note.links.length > 1 ? $t('adventures.links') : $t('adventures.link')}
				</div>
			{/if}
		</div>

		<!-- Links Preview (compact) -->
		{#if note.links && note.links?.length > 0}
			<div class="flex flex-wrap gap-2">
				{#each note.links.slice(0, 2) as link}
					<a
						class="badge badge-outline badge-sm hover:badge-primary transition-colors"
						href={link}
						target="_blank"
						rel="noopener noreferrer"
					>
						<LinkVariant class="w-3 h-3 mr-1" />
						{link.split('//')[1]?.split('/', 1)[0]}
					</a>
				{/each}
				{#if note.links.length > 2}
					<span class="badge badge-ghost badge-sm">+{note.links.length - 2}</span>
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

	.line-clamp-4 {
		display: -webkit-box;
		-webkit-line-clamp: 4;
		line-clamp: 4;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
