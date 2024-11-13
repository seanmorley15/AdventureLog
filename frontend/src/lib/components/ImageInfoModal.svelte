<script lang="ts">
	import type { Background } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	export let background: Background;
	import { t } from 'svelte-i18n';

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
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">
			{$t('settings.about_this_background')}<span class=" inline-block"></span>
		</h3>
		<div class="flex flex-col items-center">
			{#if background.author != ''}
				<p class="text-center mt-2">{$t('settings.photo_by')} {background.author}</p>
			{/if}
			{#if background.location != ''}
				<p class="text-center">{$t('adventures.location')}: {background.location}</p>
			{/if}
			<p class="text-center mt-4">
				<a
					href="https://discord.gg/wRbQ9Egr8C"
					target="_blank"
					rel="noopener noreferrer"
					class="text-blue-500 hover:underline"
				>
					{$t('settings.join_discord')}
				</a>
				{$t('settings.join_discord_desc')}
			</p>
		</div>
		<button class="btn btn-primary" on:click={close}>{$t('about.close')}</button>
	</div>
</dialog>
