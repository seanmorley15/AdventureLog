<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { appVersion, copyrightYear, versionChangelog } from '$lib/config';

	const dispatch = createEventDispatcher();
	let modal: HTMLDialogElement;

	let integrations: Record<string, boolean> | null = null;

	onMount(async () => {
		modal = document.getElementById('about_modal') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		const response = await fetch('/api/integrations');
		if (response.ok) {
			integrations = await response.json();
		} else {
			integrations = null;
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

<dialog id="about_modal" class="modal backdrop-blur-md bg-opacity-70">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box rounded-xl shadow-lg backdrop-blur-lg bg-white/80 dark:bg-gray-900/80 transition-transform duration-300 ease-out transform scale-100"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Branding -->
		<div class="text-center">
			<h3
				class="text-2xl font-extrabold text-gray-800 dark:text-white flex items-center justify-center"
			>
				{$t('about.about')} AdventureLog
				<img src="/favicon.png" alt="Map Logo" class="w-12 h-12 ml-3 inline-block" />
			</h3>
			<p class="mt-2 text-gray-500 dark:text-gray-300 text-sm">
				AdventureLog
				<a
					href={versionChangelog}
					target="_blank"
					rel="noopener noreferrer"
					class="text-primary hover:underline"
				>
					{appVersion}
				</a>
			</p>
		</div>

		<!-- Links and Details -->
		<div class="mt-4 text-center">
			<p class="text-sm text-gray-600 dark:text-gray-400">
				© {copyrightYear}
				<a
					href="https://seanmorley.com"
					target="_blank"
					rel="noopener noreferrer"
					class="text-primary hover:underline"
				>
					Sean Morley
				</a>
			</p>
			<p class="text-sm text-gray-600 dark:text-gray-400">{$t('about.license')}</p>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				<a
					href="https://github.com/seanmorley15/AdventureLog"
					target="_blank"
					rel="noopener noreferrer"
					class="text-primary hover:underline"
				>
					{$t('about.source_code')}
				</a>
			</p>
			<p class="text-sm text-gray-600 dark:text-gray-400">{$t('about.message')}</p>
		</div>

		<!-- Divider -->
		<div class="my-6 border-t border-gray-200 dark:border-gray-700"></div>

		<!-- OSS Acknowledgments -->
		<div class="text-left">
			<h3 class="text-lg font-semibold text-gray-800 dark:text-white">
				{$t('about.oss_attributions')}
			</h3>
			{#if integrations && integrations?.google_maps}
				<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
					{$t('about.nominatim_1')}
					<a
						href="https://developers.google.com/maps/terms"
						target="_blank"
						rel="noopener noreferrer"
						class="text-primary hover:underline"
					>
						Google Maps
					</a>
					.
				</p>
			{:else if integrations && !integrations?.google_maps}
				<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
					{$t('about.nominatim_1')}
					<a
						href="https://operations.osmfoundation.org/policies/nominatim/"
						target="_blank"
						rel="noopener noreferrer"
						class="text-primary hover:underline"
					>
						OpenStreetMap
					</a>
					. {$t('about.nominatim_2')}
				</p>
			{:else}
				<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
					{$t('about.generic_attributions')}
				</p>
			{/if}

			<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">{$t('about.other_attributions')}</p>
		</div>

		<!-- Close Button -->
		<div class="flex justify-center mt-6">
			<button
				class="px-6 py-2 text-sm font-medium text-white bg-primary rounded-full shadow-md hover:shadow-lg hover:scale-105 transform transition"
				on:click={close}
			>
				{$t('about.close')}
			</button>
		</div>
	</div>
</dialog>

<style>
	.modal {
		display: grid;
		place-items: center;
		background: rgba(0, 0, 0, 0.5);
		animation: fadeIn 0.3s ease-in-out;
	}
	.modal-box {
		max-width: 600px;
		padding: 2rem;
		animation: slideUp 0.4s ease-out;
	}
	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}
	@keyframes slideUp {
		from {
			transform: translateY(20%);
			opacity: 0;
		}
		to {
			transform: translateY(0);
			opacity: 1;
		}
	}
</style>
