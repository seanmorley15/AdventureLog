<script lang="ts">
	import type { Background } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	export let background: Background;
	import { t } from 'svelte-i18n';

	import AccountIcon from '~icons/mdi/account';
	import LocationIcon from '~icons/mdi/map-marker';
	import DiscordIcon from '~icons/mdi/discord';

	onMount(() => {
		modal = document.getElementById('image_info_modal') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function close() {
		if (modal) {
			modal.close();
		}
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === modal) {
			close();
		}
	}
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<dialog id="image_info_modal" class="modal modal-open" on:click={handleBackdropClick}>
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box w-full max-w-md" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<!-- Header -->
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-xl font-bold text-base-content">
				{$t('settings.about_this_background')}
			</h3>
			<button class="btn btn-sm btn-circle btn-ghost" on:click={close} aria-label="Close">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					/>
				</svg>
			</button>
		</div>

		<!-- Background Info -->
		<div class="space-y-4">
			<!-- Image Preview -->
			{#if background.url}
				<div class="w-full h-32 bg-base-200 rounded-lg overflow-hidden">
					<img src={background.url} alt="Background preview" class="w-full h-full object-cover" />
				</div>
			{/if}

			<!-- Author Info -->
			{#if background.author && background.author.trim() !== ''}
				<div class="flex items-center gap-3 p-3 bg-base-100 rounded-lg">
					<div
						class="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0"
					>
						<AccountIcon class="w-4 h-4 text-primary" />
					</div>
					<div>
						<p class="text-sm font-medium text-base-content/70">{$t('settings.photo_by')}</p>
						<p class="font-medium text-base-content">{background.author}</p>
					</div>
				</div>
			{/if}

			<!-- Location Info -->
			{#if background.location && background.location.trim() !== ''}
				<div class="flex items-center gap-3 p-3 bg-base-100 rounded-lg">
					<div
						class="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0"
					>
						<LocationIcon class="w-4 h-4 text-primary" />
					</div>
					<div>
						<p class="text-sm font-medium text-base-content/70">{$t('adventures.location')}</p>
						<p class="font-medium text-base-content">{background.location}</p>
					</div>
				</div>
			{/if}

			<!-- Community Info -->
			<div class="bg-primary/5 rounded-lg p-4">
				<div class="flex items-start gap-3">
					<div
						class="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
					>
						<DiscordIcon class="w-4 h-4 text-primary" />
					</div>
					<div>
						<p class="font-medium text-base-content mb-1">{$t('settings.join_discord')}</p>
						<p class="text-sm text-base-content/70 mb-3">
							{$t('settings.join_discord_desc')}
						</p>
						<a
							href="https://discord.gg/wRbQ9Egr8C"
							target="_blank"
							rel="noopener noreferrer"
							class="btn btn-primary btn-sm"
						>
							<DiscordIcon class="w-4 h-4" />
							{$t('settings.join_discord')}
						</a>
					</div>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div class="modal-action mt-6">
			<button class="btn btn-primary w-full" on:click={close}>
				{$t('about.close')}
			</button>
		</div>
	</div>
</dialog>

<style>
	.modal-open {
		pointer-events: auto;
		visibility: visible;
		opacity: 1;
	}
</style>
