<script lang="ts">
	import { t } from 'svelte-i18n';
	import { addToast } from '#lib/toasts.js';
	import type { Collection, Note, User } from '#lib/types.js';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import { renderMarkdown } from '#lib/markdown.js';

	import TrashCan from '~icons/mdi/trash-can';
	import Calendar from '~icons/mdi/calendar';
	import DeleteWarning from '../DeleteWarning.svelte';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import LinkVariant from '~icons/mdi/link-variant';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import Launch from '~icons/mdi/launch';
	import Close from '~icons/mdi/close';
	import Globe from '~icons/mdi/globe';
	import type { CollectionItineraryItem } from '#lib/types.js';
	import CardActionsMenu from './parts/CardActionsMenu.svelte';
	import NoteTextOutline from '~icons/mdi/note-text-outline';
	import { dateFormatFromUser, formatDisplayDate } from '#lib/dateFormat.js';

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

	let canEdit = $derived(
		!readOnly &&
			(note.user == user?.uuid ||
				(collection && user && collection.shared_with?.includes(user.uuid)))
	);

	const dateFormat = $derived(dateFormatFromUser(user));

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
		let res = await fetch(
			`/api/collections/${itineraryItem?.collection}/itinerary-items/${itineraryItemId}/`,
			{
				method: 'DELETE'
			}
		);
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
		button_text={$t('adventures.delete')}
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
								<span>{formatDisplayDate(note.date, dateFormat, { timeZone: 'UTC' })}</span>
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
	class="card h-full flex flex-col rounded-2xl border border-base-300/60 bg-base-100 shadow-xs transition-colors hover:border-base-300"
	aria-label="note-card"
>
	<div class="flex flex-1 flex-col gap-3 p-4">
		<div class="flex items-start gap-3">
			<div
				class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10"
				aria-hidden="true"
			>
				<NoteTextOutline class="h-5 w-5 text-primary" />
			</div>
			<div class="min-w-0 flex-1">
				<h2 class="line-clamp-2 text-lg font-semibold leading-snug">{note.name}</h2>
				<p class="text-sm text-base-content/60">{$t('adventures.note')}</p>
			</div>

			<div class="-mr-1 -mt-1 flex shrink-0 items-center">
				<button
					class="btn btn-ghost btn-square btn-sm"
					onclick={() => (isDetailsOpen = true)}
					aria-label={$t('adventures.view')}
					type="button"
				>
					<Launch class="h-5 w-5" />
				</button>
				{#if canEdit}
					<CardActionsMenu label={$t('cards.item_actions')}>
						{#snippet children({ close })}
							<li>
								<button
									onclick={() => {
										close();
										editNote();
									}}
								>
									<FileDocumentEdit class="h-4 w-4" />
									{$t('lodging.edit')}
								</button>
							</li>
							{#if itineraryItem && itineraryItem.id}
								<div class="divider my-1"></div>
								{#if !itineraryItem.is_global}
									<li>
										<button
											onclick={() => {
												close();
												dispatch('moveToGlobal', { type: 'note', id: note.id });
											}}
										>
											<Globe class="h-4 w-4" />
											{$t('itinerary.move_to_trip_context')}
										</button>
									</li>
									<li>
										<button
											onclick={() => {
												close();
												changeDay();
											}}
										>
											<Calendar class="h-4 w-4" />
											{$t('itinerary.change_day')}
										</button>
									</li>
								{/if}
								<li>
									<button
										class="text-error"
										onclick={() => {
											close();
											removeFromItinerary();
										}}
									>
										<CalendarRemove class="h-4 w-4" />
										{itineraryItem.is_global
											? $t('itinerary.remove_from_trip_context')
											: $t('itinerary.remove_from_itinerary')}
									</button>
								</li>
							{/if}
							<div class="divider my-1"></div>
							<li>
								<button
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
						{/snippet}
					</CardActionsMenu>
				{/if}
			</div>
		</div>

		{#if note.content && note.content?.length > 0}
			<article
				class="prose prose-sm line-clamp-4 max-h-32 max-w-none overflow-hidden text-sm text-base-content/70"
			>
				{@html renderMarkdown(note.content || '')}
			</article>
		{/if}

		{#if (note.date && note.date !== '') || (note.links && note.links.length > 0)}
			<div class="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1.5 pt-1 text-sm">
				{#if note.date && note.date !== ''}
					<span class="inline-flex items-center gap-1.5 text-base-content/70">
						<Calendar class="h-4 w-4 text-primary" />
						{formatDisplayDate(note.date, dateFormat, { timeZone: 'UTC' })}
					</span>
				{/if}
				{#if note.links && note.links.length > 0}
					{#each note.links.slice(0, 2) as link}
						<a
							class="badge badge-ghost badge-sm gap-1 transition-colors hover:badge-primary"
							href={link}
							target="_blank"
							rel="noopener noreferrer"
						>
							<LinkVariant class="h-3 w-3" />
							{link.split('//')[1]?.split('/', 1)[0] ?? link}
						</a>
					{/each}
					{#if note.links.length > 2}
						<span class="badge badge-ghost badge-sm">
							{$t('cards.more_links', { values: { count: note.links.length - 2 } })}
						</span>
					{/if}
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
