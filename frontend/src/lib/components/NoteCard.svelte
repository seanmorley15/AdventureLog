<script lang="ts">
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import type { Collection, Note, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import { marked } from 'marked'; // Import the markdown parser

	const renderMarkdown = (markdown: string) => {
		return marked(markdown);
	};

	import Launch from '~icons/mdi/launch';
	import TrashCan from '~icons/mdi/trash-can';
	import Calendar from '~icons/mdi/calendar';
	import DeleteWarning from './DeleteWarning.svelte';
	import { isEntityOutsideCollectionDateRange } from '$lib/dateUtils';

	export let note: Note;
	export let user: User | null = null;
	export let collection: Collection | null = null;

	let isWarningModalOpen: boolean = false;
	let outsideCollectionRange: boolean = false;

	$: {
		if (collection) {
			outsideCollectionRange = isEntityOutsideCollectionDateRange(note, collection);
		}
	}

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

<div
	class="card w-full max-w-md bg-base-300 text-base-content shadow-2xl hover:shadow-3xl transition-all duration-300 border border-base-300 hover:border-primary/20 group"
>
	<div class="card-body p-6 space-y-4">
		<!-- Header -->
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
			<h2 class="text-xl font-bold break-words">{note.name}</h2>
			<div class="flex flex-wrap gap-2">
				<div class="badge badge-primary">{$t('adventures.note')}</div>
				{#if outsideCollectionRange}
					<div class="badge badge-error">{$t('adventures.out_of_range')}</div>
				{/if}
			</div>
		</div>

		<!-- Note Content -->
		{#if note.content && note.content?.length > 0}
			<article
				class="prose overflow-auto max-h-72 max-w-full p-4 border border-base-300 bg-base-100 rounded-lg"
			>
				{@html renderMarkdown(note.content || '')}
			</article>
		{/if}

		<!-- Links -->
		{#if note.links && note.links?.length > 0}
			<div class="space-y-1">
				<p class="text-sm font-medium">
					{note.links.length}
					{note.links.length > 1 ? $t('adventures.links') : $t('adventures.link')}
				</p>
				<ul class="list-disc pl-5 text-sm">
					{#each note.links.slice(0, 3) as link}
						<li>
							<a class="link link-primary" href={link} target="_blank" rel="noopener noreferrer">
								{link.split('//')[1]?.split('/', 1)[0]}
							</a>
						</li>
					{/each}
					{#if note.links.length > 3}
						<li>…</li>
					{/if}
				</ul>
			</div>
		{/if}

		<!-- Date -->
		{#if note.date && note.date !== ''}
			<div class="inline-flex items-center gap-2 text-sm">
				<Calendar class="w-5 h-5 text-primary" />
				<p>{new Date(note.date).toLocaleDateString(undefined, { timeZone: 'UTC' })}</p>
			</div>
		{/if}

		<!-- Actions -->
		<div class="pt-4 border-t border-base-300 flex justify-end gap-2">
			<button class="btn btn-neutral btn-sm flex items-center gap-1" on:click={editNote}>
				<Launch class="w-5 h-5" />
				{$t('notes.open')}
			</button>
			{#if note.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
				<button
					id="delete_adventure"
					data-umami-event="Delete Adventure"
					class="btn btn-secondary btn-sm flex items-center gap-1"
					on:click={() => (isWarningModalOpen = true)}
				>
					<TrashCan class="w-5 h-5" />
					{$t('adventures.delete')}
				</button>
			{/if}
		</div>
	</div>
</div>
