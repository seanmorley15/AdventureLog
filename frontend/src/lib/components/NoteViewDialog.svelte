<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Note, User } from '#lib/types.js';
	import { renderMarkdown } from '#lib/markdown.js';
	import { dateFormatFromUser, formatDisplayDate } from '#lib/dateFormat.js';
	import NoteTextOutline from '~icons/mdi/note-text-outline';
	import Calendar from '~icons/mdi/calendar';
	import LinkVariant from '~icons/mdi/link-variant';
	import Close from '~icons/mdi/close';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';

	interface Props {
		note: Note;
		user?: User | null;
		/** Shows the Edit button when set. */
		onEdit?: (() => void) | null;
		onClose: () => void;
	}

	let { note, user = null, onEdit = null, onClose }: Props = $props();

	const dateFormat = $derived(dateFormatFromUser(user));
	const hasDate = $derived(Boolean(note.date && note.date !== ''));
	const links = $derived(note.links ?? []);
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onClose()} />

<dialog class="modal modal-open" open aria-label={note.name}>
	<div class="modal-box flex max-h-[85vh] w-full max-w-2xl flex-col gap-0 p-0">
		<header class="flex items-start gap-3 border-b border-base-300/70 px-5 py-4 sm:px-6">
			<div
				class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10"
				aria-hidden="true"
			>
				<NoteTextOutline class="h-5 w-5 text-primary" />
			</div>
			<div class="min-w-0 flex-1">
				<h3 class="text-xl font-semibold leading-snug wrap-break-word">{note.name}</h3>
				<div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
					<span class="badge badge-primary badge-soft badge-sm">{$t('adventures.note')}</span>
					{#if hasDate}
						<span class="inline-flex items-center gap-1.5 text-base-content/70">
							<Calendar class="h-4 w-4 text-primary" />
							{formatDisplayDate(note.date as string, dateFormat, { timeZone: 'UTC' })}
						</span>
					{/if}
				</div>
			</div>
			<button
				type="button"
				class="btn btn-circle btn-ghost btn-sm"
				onclick={onClose}
				aria-label={$t('about.close')}
			>
				<Close class="h-4 w-4" />
			</button>
		</header>

		<div class="min-h-0 flex-1 overflow-y-auto px-5 py-4 sm:px-6">
			{#if note.content && note.content.length > 0}
				<article
					class="prose prose-sm max-w-none text-base-content prose-headings:mb-2 prose-headings:mt-5 prose-headings:text-base-content first:prose-headings:mt-0 prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-p:my-2 prose-li:my-0.5 prose-a:text-primary prose-strong:text-base-content prose-code:text-base-content"
				>
					{@html renderMarkdown(note.content)}
				</article>
			{:else}
				<p class="py-6 text-center text-sm text-base-content/60">{$t('notes.no_content')}</p>
			{/if}

			{#if links.length > 0}
				<div class="mt-5 space-y-2 border-t border-base-300/70 pt-4">
					<p class="text-sm font-semibold">{$t('adventures.links')}</p>
					<div class="flex flex-wrap gap-2">
						{#each links as link}
							<a
								class="badge badge-outline gap-1 py-3 hover:badge-primary"
								href={link}
								target="_blank"
								rel="noopener noreferrer"
							>
								<LinkVariant class="h-3 w-3 shrink-0" />
								<span class="max-w-64 truncate">{link.split('//')[1] ?? link}</span>
							</a>
						{/each}
					</div>
				</div>
			{/if}
		</div>

		<footer class="flex justify-end gap-2 border-t border-base-300/70 px-5 py-3 sm:px-6">
			{#if onEdit}
				<button type="button" class="btn btn-ghost btn-sm gap-1" onclick={onEdit}>
					<FileDocumentEdit class="h-4 w-4" />
					{$t('lodging.edit')}
				</button>
			{/if}
			<button type="button" class="btn btn-sm" onclick={onClose}>{$t('about.close')}</button>
		</footer>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button aria-label={$t('about.close')} onclick={onClose}>{$t('about.close')}</button>
	</form>
</dialog>
