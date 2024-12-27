<script lang="ts">
	import { isValidUrl } from '$lib';
	import type { Collection, Note, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import MarkdownEditor from './MarkdownEditor.svelte';
	let modal: HTMLDialogElement;
	import { marked } from 'marked'; // Import the markdown parser

	const renderMarkdown = (markdown: string) => {
		return marked(markdown);
	};

	export let note: Note | null = null;
	export let collection: Collection;
	export let user: User | null = null;

	let constrainDates: boolean = false;

	let isReadOnly =
		!(note && user?.uuid == note?.user_id) &&
		!(user && collection && collection.shared_with && collection.shared_with.includes(user.uuid)) &&
		!!note;

	let warning: string | null = '';

	let newLink: string = '';

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

	let newNote = {
		name: note?.name || '',
		content: note?.content || '',
		date: note?.date || undefined || null,
		links: note?.links || [],
		collection: collection.id,
		is_public: collection.is_public
	};

	let initialName: string = note?.name || '';

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

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box w-11/12 max-w-3xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-2xl">
			{#if note?.id && !isReadOnly}
				<p class="font-semibold text-md mb-2">
					{$t('notes.editing_note')}
					{initialName}
				</p>
			{:else if !isReadOnly}
				{$t('notes.note_editor')}
			{:else}
				{$t('notes.note_viewer')}
			{/if}
		</h3>

		<div class="modal-action items-center">
			<form method="post" style="width: 100%;" on:submit|preventDefault>
				<!-- Basic Information Section -->
				<div class="collapse collapse-plus bg-base-200 mb-4">
					<input type="checkbox" id="collapse-plus-1" checked />
					<div class="collapse-title text-lg font-bold">
						{$t('adventures.basic_information')}
					</div>
					<div class="collapse-content">
						<!-- Name Input -->
						<div class="form-control mb-2">
							<label for="name">{$t('adventures.name')}</label>
							<input
								type="text"
								id="name"
								readonly={isReadOnly}
								class="input input-bordered w-full max-w-xs"
								bind:value={newNote.name}
							/>
						</div>

						<!-- Date Input -->
						<div class="form-control mb-2">
							<label for="content">{$t('adventures.date')}</label>
							{#if collection && collection.start_date && collection.end_date && !isReadOnly}<label
									class="label cursor-pointer flex items-start space-x-2"
								>
									<span class="label-text">{$t('adventures.date_constrain')}</span>
									<input
										type="checkbox"
										class="toggle toggle-primary"
										id="constrain_dates"
										name="constrain_dates"
										on:change={() => (constrainDates = !constrainDates)}
									/></label
								>
							{/if}
							<input
								type="date"
								id="date"
								name="date"
								readonly={isReadOnly}
								min={constrainDates ? collection.start_date : ''}
								max={constrainDates ? collection.end_date : ''}
								bind:value={newNote.date}
								class="input input-bordered w-full max-w-xs mt-1"
							/>
						</div>

						<!-- Content Textarea -->

						<div>
							<label for="content">{$t('notes.content')}</label><br />
							{#if !isReadOnly}
								<MarkdownEditor bind:text={newNote.content} editor_height={'h-32'} />
							{:else if note}
								<p class="text-sm text-muted-foreground" style="white-space: pre-wrap;"></p>
								<article
									class="prose overflow-auto h-full max-w-full p-4 border border-base-300 rounded-lg mb-4 mt-4"
								>
									{@html renderMarkdown(note.content || '')}
								</article>
							{/if}
						</div>

						<!-- Links Section -->
						{#if !isReadOnly}
							<div class="form-control mb-2">
								<label for="content">{$t('adventures.links')}</label>
								<input
									type="url"
									class="input input-bordered w-full mb-1"
									placeholder="{$t('notes.add_a_link')} (e.g. https://example.com)"
									bind:value={newLink}
									on:keydown={(e) => {
										if (e.key === 'Enter') {
											e.preventDefault();
											addLink();
										}
									}}
								/>
								<button type="button" class="btn btn-sm btn-primary mt-1" on:click={addLink}>
									{$t('adventures.add')}
								</button>
							</div>
						{/if}

						<!-- Links List -->
						{#if newNote.links.length > 0}
							<ul class="list-none">
								{#each newNote.links as link, i}
									<li class="mb-4 flex justify-between items-center">
										<a href={link} class="link link-primary" target="_blank">
											{link}
										</a>
										<button
											type="button"
											class="btn btn-sm btn-error"
											disabled={isReadOnly}
											on:click={() => {
												newNote.links = newNote.links.filter((_, index) => index !== i);
											}}
										>
											{$t('adventures.remove')}
										</button>
									</li>
								{/each}
							</ul>
						{/if}
					</div>
				</div>

				<!-- Warning Message -->
				{#if warning}
					<div role="alert" class="alert alert-error mb-4">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-6 w-6 shrink-0 stroke-current"
							fill="none"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<span>{warning}</span>
					</div>
				{/if}

				<!-- Public Note Alert -->
				{#if collection.is_public}
					<div role="alert" class="alert mb-4">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							class="h-6 w-6 shrink-0 stroke-current"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							></path>
						</svg>
						<span>{$t('notes.note_public')}</span>
					</div>
				{/if}

				<!-- Action Buttons -->
				<div class="mt-4">
					<button class="btn btn-neutral" on:click={close}>
						{$t('about.close')}
					</button>
					<button class="btn btn-primary mr-1" disabled={isReadOnly} on:click={save}>
						{$t('notes.save')}
					</button>
				</div>
			</form>
		</div>
	</div>
</dialog>
