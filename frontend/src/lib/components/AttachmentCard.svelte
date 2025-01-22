<script lang="ts">
	import type { Attachment } from '$lib/types';
	import { t } from 'svelte-i18n';

	export let attachment: Attachment;
	export let allowEdit: boolean = false;

	import { createEventDispatcher } from 'svelte';
	import { addToast } from '$lib/toasts';

	const dispatch = createEventDispatcher();

	async function deleteAttachment() {
		let res = await fetch(`/api/attachments/${attachment.id}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('info', $t('adventures.attachment_delete_success'));
			dispatch('delete', attachment.id);
		} else {
			console.log('Error deleting attachment');
		}
	}

	// Check if the attachment is an image or not
	function getCardBackground() {
		const isImage = ['.jpg', '.jpeg', '.png', '.gif', '.webp'].some((ext) =>
			attachment.file.endsWith(ext)
		);
		return isImage ? `url(${attachment.file})` : '';
	}
</script>

<div class="relative rounded-lg shadow-lg group hover:shadow-xl transition-shadow overflow-hidden">
	<!-- Card Image or Placeholder -->
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<div
		class="w-full h-48 bg-cover bg-center group-hover:opacity-90 transition-opacity"
		style="background-image: {getCardBackground()}"
		on:click={() => window.open(attachment.file, '_blank')}
		role="button"
		tabindex="0"
		aria-label={attachment.file.split('/').pop()}
	>
		{#if !['.jpg', '.jpeg', '.png', '.gif', '.webp'].some((ext) => attachment.file.endsWith(ext))}
			<div
				class="flex justify-center items-center w-full h-full text-white text-lg font-bold bg-gradient-to-r from-secondary via-base to-primary text-center"
			>
				<p>
					{attachment.name} <br />
					{attachment.extension.toUpperCase()}
				</p>
			</div>
			<!-- show the name under the extension -->
		{/if}
	</div>

	<!-- Attachment Label -->
	<div
		class="absolute top-0 right-0 bg-primary text-white px-3 py-1 text-sm font-medium rounded-bl-lg shadow-md"
	>
		{$t('adventures.attachment')}
	</div>
	<div
		class="absolute top-0 left-0 bg-secondary text-white px-2 py-1 text-sm font-medium rounded-br-lg shadow-md"
	>
		{attachment.extension}
	</div>

	<!-- Action Bar -->
	<div
		class="absolute bottom-0 w-full bg-gradient-to-t from-black/50 to-transparent p-3 rounded-b-lg flex justify-between items-center"
	>
		<span class="text-white text-sm font-medium truncate">
			{attachment.name}
		</span>
		<div class="flex space-x-2">
			{#if !allowEdit}
				<button
					class="btn btn-sm btn-secondary btn-outline"
					type="button"
					on:click={() => window.open(attachment.file, '_blank')}
				>
					{$t('notes.open')}
				</button>
			{/if}
			{#if allowEdit}
				<button
					class="btn btn-sm btn-info btn-outline"
					type="button"
					on:click={() => dispatch('edit', attachment)}
				>
					{$t('transportation.edit')}
				</button>
				<button class="btn btn-sm btn-danger btn-outline" type="button" on:click={deleteAttachment}>
					{$t('adventures.delete')}
				</button>
			{/if}
		</div>
	</div>
</div>
