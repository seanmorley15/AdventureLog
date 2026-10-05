<script lang="ts">
	import { createBubbler, preventDefault } from 'svelte/legacy';

	const bubble = createBubbler();
	import { isValidUrl } from '$lib';
	import type { Collection, Note, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import MarkdownEditor from './MarkdownEditor.svelte';
	let modal: HTMLDialogElement;
	import { marked } from 'marked';
	import DateInput from './shared/DateInput.svelte';
	import InfoIcon from '~icons/mdi/information';
	import CalendarIcon from '~icons/mdi/calendar';
	import LinkIcon from '~icons/mdi/link';
	import NoteIcon from '~icons/mdi/note-text';
	import SaveIcon from '~icons/mdi/content-save';
	import CloseIcon from '~icons/mdi/close';
	import FileIcon from '~icons/mdi/file-document-outline';

	const renderMarkdown = (markdown: string) => {
		return marked(markdown);
	};

	interface Props {
		note?: Note | null;
		collection: Collection;
		user?: User | null;
		initialVisitDate?: string | null;
	}

	let { note = null, collection, user = null, initialVisitDate = null }: Props = $props();

	let constrainDates: boolean = $state(true);

	let isReadOnly = $derived(
		!(note && user?.uuid == note?.user) &&
			!(
				user &&
				collection &&
				collection.shared_with &&
				collection.shared_with.includes(user.uuid)
			) &&
			!!note
	);

	let warning: string | null = $state('');

	let newLink: string = $state('');

	function addLink() {
		// check to make it a valid URL
		if (!isValidUrl(newLink)) {
			warning = $t('notes.invalid_url');
			return;
		} else {
			warning = null;
		}

		if (newLink.trim().length > 0) {
			newNote.links = [...newNote.links, newLink];
			newLink = '';
		}
		console.log(newNote.links);
	}

	const getSeedDate = (): string | null => {
		// Prefer the existing note date, otherwise fall back to the itinerary day we launched from
		if (note?.date) return note.date;
		if (initialVisitDate) return initialVisitDate;
		return null;
	};

	let newNote = $state({
		name: '',
		content: '',
		date: null as string | null | undefined,
		links: [] as string[],
		collection: '',
		is_public: false
	});
	let previousNoteId: string | null | undefined = undefined;

	$effect.pre(() => {
		const sourceId = note?.id ?? null;
		if (sourceId === previousNoteId) return;

		previousNoteId = sourceId;
		newNote = {
			name: note?.name || '',
			content: note?.content || '',
			date: getSeedDate() || null,
			links: note?.links || [],
			collection: collection.id,
			is_public: collection.is_public
		};
	});

	const hasVisitDateSuggestion = $derived(!!initialVisitDate && !note?.date);

	function useVisitDate() {
		if (isReadOnly) return;
		if (initialVisitDate) {
			newNote = { ...newNote, date: initialVisitDate };
		}
	}

	let initialName = $derived(note?.name || '');

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	async function save() {
		// handles empty date
		if (newNote.date == '') {
			newNote.date = null;
		}

		if (note && note.id) {
			console.log('newNote', newNote);
			const res = await fetch(`/api/notes/${note.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newNote)
			});
			if (res.ok) {
				let data = await res.json();
				if (data) {
					dispatch('save', data);
				}
			} else {
				console.error('Failed to save note');
			}
		} else {
			console.log('newNote', newNote);
			const res = await fetch(`/api/notes/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newNote)
			});
			if (res.ok) {
				let data = await res.json();
				if (data) {
					dispatch('create', data);
				}
			} else {
				let data = await res.json();
				console.error($t('notes.failed_to_save'), data);
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal modal-bottom md:modal-middle backdrop-blur-xs">
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="modal-box note-modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl flex flex-col p-0 overflow-hidden rounded-none md:rounded-2xl"
		role="dialog"
		onkeydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section -->
		<div
			class="shrink-0 bg-base-100/90 backdrop-blur-lg border-b border-base-300 px-4 md:px-6 py-3 md:py-4"
		>
			<div class="flex items-center justify-between gap-3">
				<div class="flex items-center gap-3 min-w-0">
					<div class="p-2 bg-primary/10 rounded-xl">
						<NoteIcon class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{#if note?.id && !isReadOnly}
								{$t('notes.editing_note')}
							{:else if !isReadOnly}
								{$t('notes.note_editor')}
							{:else}
								{$t('notes.note_viewer')}
							{/if}
						</h1>
						<p class="text-sm text-base-content/80">
							{#if note?.id && !isReadOnly}
								{$t('notes.update_note_details')} "{initialName}"
							{:else if !isReadOnly}
								{$t('notes.create_new_note')}
							{:else}
								{$t('notes.viewing_note')} "{note?.name || ''}"
							{/if}
						</p>
					</div>
				</div>

				<!-- Close Button -->
				<button
					type="button"
					class="btn btn-ghost btn-square shrink-0"
					aria-label={$t('about.close')}
					title={$t('about.close')}
					onclick={close}
				>
					<CloseIcon class="w-5 h-5" />
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="flex-1 min-h-0 overflow-hidden flex flex-col">
			<form
				class="h-full min-h-0 flex flex-col"
				method="post"
				onsubmit={preventDefault(bubble('submit'))}
			>
				<div
					class="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-4 md:py-5 bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5"
				>
					<div class="max-w-full mx-auto space-y-6">
						<div class="card bg-base-100 border border-base-300 shadow-lg">
							<div class="card-body p-6">
								<div class="flex items-center gap-3 mb-6">
									<div class="p-2 bg-primary/10 rounded-lg">
										<InfoIcon class="w-5 h-5 text-primary" />
									</div>
									<h2 class="text-xl font-bold">{$t('adventures.basic_information')}</h2>
								</div>

								<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
									<div class="space-y-4">
										<div class="flex flex-col">
											<label class="field-label" for="name">
												{$t('adventures.name')}<span class="text-error ml-1">*</span>
											</label>
											<input
												type="text"
												id="name"
												name="name"
												readonly={isReadOnly}
												bind:value={newNote.name}
												class="input w-full bg-base-100/80 focus:bg-base-100"
												placeholder={$t('notes.enter_note_title')}
												required
											/>
										</div>

										<div class="flex flex-col">
											<label class="field-label flex items-center gap-2" for="date">
												<CalendarIcon class="w-4 h-4" />
												{$t('adventures.date')}
											</label>
											{#if !isReadOnly && hasVisitDateSuggestion}
												<div
													class="flex flex-wrap items-center gap-2 mb-2 text-xs text-base-content/70"
												>
													<span class="badge badge-primary badge-soft">Itinerary day</span>
													<span>Prefilled to match your selected day.</span>
													<button type="button" class="btn btn-ghost btn-xs" onclick={useVisitDate}>
														Reapply date
													</button>
												</div>
											{/if}
											{#if collection && collection.start_date && collection.end_date && !isReadOnly}
												<label class="field-toggle mb-2">
													<input
														type="checkbox"
														class="toggle toggle-primary toggle-sm"
														id="constrain_dates"
														name="constrain_dates"
														bind:checked={constrainDates}
													/>
													<span class="text-sm text-base-content/70"
														>{$t('adventures.date_constrain')}</span
													>
												</label>
											{/if}
											<DateInput
												id="date"
												name="date"
												readonly={isReadOnly}
												min={constrainDates ? collection.start_date || undefined : undefined}
												max={constrainDates ? collection.end_date || undefined : undefined}
												bind:value={newNote.date}
												clearable={!isReadOnly}
											/>
										</div>
									</div>

									<div class="space-y-4">
										<div class="flex flex-col">
											<label class="field-label flex items-center gap-2" for="new-link">
												<LinkIcon class="w-4 h-4" />
												{$t('adventures.links')}
											</label>
											{#if !isReadOnly}
												<div class="join w-full">
													<input
														type="url"
														id="new-link"
														class="input join-item flex-1 bg-base-100/80 focus:bg-base-100"
														placeholder="https://example.com"
														bind:value={newLink}
														onkeydown={(e) => {
															if (e.key === 'Enter') {
																e.preventDefault();
																addLink();
															}
														}}
													/>
													<button
														type="button"
														class="btn btn-primary join-item"
														aria-label={$t('adventures.add')}
														title={$t('adventures.add')}
														onclick={addLink}
													>
														{$t('adventures.add')}
													</button>
												</div>
											{/if}
										</div>

										{#if newNote.links.length > 0}
											<div class="space-y-2">
												{#each newNote.links as link, i (link)}
													<div
														class="flex items-center gap-2 p-3 bg-base-200/50 rounded-xl border border-base-300/50"
													>
														<LinkIcon class="w-4 h-4 text-primary shrink-0" />
														<a
															href={link}
															class="link link-primary text-sm truncate flex-1"
															target="_blank"
															rel="noopener noreferrer"
														>
															{link}
														</a>
														{#if !isReadOnly}
															<button
																type="button"
																class="btn btn-ghost btn-xs text-error"
																aria-label={$t('adventures.remove')}
																title={$t('adventures.remove')}
																onclick={() => {
																	newNote.links = newNote.links.filter((_, index) => index !== i);
																}}
															>
																<CloseIcon class="w-4 h-4" />
															</button>
														{/if}
													</div>
												{/each}
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>

						<div class="card bg-base-100 border border-base-300 shadow-lg">
							<div class="card-body p-6">
								<div class="flex items-center gap-3 mb-6">
									<div class="p-2 bg-primary/10 rounded-lg">
										<FileIcon class="w-5 h-5 text-primary" />
									</div>
									<h2 class="text-xl font-bold">{$t('notes.content')}</h2>
								</div>

								{#if !isReadOnly}
									<MarkdownEditor bind:text={newNote.content} editor_height="h-96" />
								{:else if note}
									<div
										class="bg-base-100 border border-base-300/50 rounded-xl p-6 max-h-96 overflow-y-auto"
									>
										<article class="prose max-w-full">
											{@html renderMarkdown(note.content || '')}
										</article>
									</div>
								{/if}
							</div>
						</div>

						{#if warning}
							<div role="alert" class="alert alert-error rounded-xl border border-error/20">
								<InfoIcon class="h-6 w-6 shrink-0" />
								<span class="font-medium">{warning}</span>
							</div>
						{/if}

						{#if collection.is_public}
							<div role="alert" class="alert alert-info rounded-xl border border-info/20">
								<InfoIcon class="h-6 w-6 shrink-0" />
								<span class="font-medium">{$t('notes.note_public')}</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Action Buttons -->
				<div
					class="shrink-0 border-t border-base-300 bg-base-100/90 backdrop-blur-lg px-4 md:px-6 py-3 md:py-4 flex gap-3 justify-end"
				>
					<button type="button" class="btn btn-ghost gap-2" onclick={close}>
						<CloseIcon class="w-4 h-4" />
						{$t('about.close')}
					</button>
					{#if !isReadOnly}
						<button type="button" class="btn btn-primary gap-2" onclick={save}>
							<SaveIcon class="w-5 h-5" />
							{$t('notes.save')}
						</button>
					{/if}
				</div>
			</form>
		</div>
	</div>
</dialog>

<style>
	.note-modal-box {
		width: 100%;
		max-width: 100%;
		height: 100dvh;
		max-height: 100dvh;
	}

	@media (min-width: 768px) {
		.note-modal-box {
			width: min(96vw, 72rem);
			max-width: 72rem;
			height: min(90dvh, 56rem);
			max-height: 90dvh;
		}
	}
</style>
