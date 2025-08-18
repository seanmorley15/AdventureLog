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

<dialog id="about_modal" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-2xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header -->
		<div class="flex items-center justify-between mb-6">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-primary/10 rounded-lg">
					<img src="/favicon.png" alt="AdventureLog" class="w-12 h-12" />
				</div>
				<div>
					<h1 class="text-2xl font-bold text-primary">
						{$t('about.about')} AdventureLog
					</h1>
				</div>
			</div>

			<button class="btn btn-ghost btn-sm btn-square" on:click={close}>
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

		<!-- Content -->
		<div class="space-y-4">
			<!-- Version & Developer Info -->
			<div class="card bg-base-200/30 border border-base-300">
				<div class="card-body p-4">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div>
							<div class="text-sm text-base-content/60">{$t('about.version')}</div>
							<div class="text-lg font-bold text-primary">{appVersion}</div>
							<a
								href={versionChangelog}
								target="_blank"
								rel="noopener noreferrer"
								class="text-sm link link-primary"
							>
								{$t('about.view_changelog')} →
							</a>
						</div>
						<div>
							<div class="text-sm text-base-content/60">{$t('about.developer')}</div>
							<a
								href="https://seanmorley.com"
								target="_blank"
								rel="noopener noreferrer"
								class="text-lg font-semibold link link-primary"
							>
								Sean Morley
							</a>
							<div class="text-sm text-base-content/60">{$t('about.message')}</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Map Services -->
			<div class="card bg-base-200/30 border border-base-300">
				<div class="card-body p-4">
					<h3 class="font-bold text-primary mb-3 flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						{$t('about.attributions')}
					</h3>
					{#if integrations && integrations?.google_maps}
						<div class="flex items-center gap-2">
							<span class="text-sm text-base-content/60">{$t('about.nominatim_1')}</span>
							<a
								href="https://developers.google.com/maps/terms"
								target="_blank"
								rel="noopener noreferrer"
								class="link link-primary font-semibold"
							>
								Google Maps Platform
							</a>
						</div>
					{:else if integrations && !integrations?.google_maps}
						<div class="flex items-center gap-2">
							<span class="text-sm text-base-content/60">{$t('about.nominatim_1')}</span>
							<a
								href="https://operations.osmfoundation.org/policies/nominatim/"
								target="_blank"
								rel="noopener noreferrer"
								class="link link-primary font-semibold"
							>
								OpenStreetMap Nominatim
							</a>
						</div>
					{:else}
						<div class="text-sm text-base-content/60">{$t('about.generic_attributions')}</div>
					{/if}
					<p class="text-sm text-base-content/60">{$t('about.other_attributions')}</p>
				</div>
			</div>

			<!-- Liscense info -->
			<div class="card bg-base-200/30 border border-base-300">
				<div class="card-body p-4">
					<h3 class="font-bold text-primary mb-3 flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
							/>
						</svg>
						{$t('about.license_info')}
					</h3>
					<p class="text-sm text-base-content/60 mb-2">
						© {copyrightYear}
						<a
							href="https://seanmorley.com"
							target="_blank"
							rel="noopener noreferrer"
							class="link link-primary"
						>
							Sean Morley
						</a>
					</p>
					<p class="text-sm text-base-content/60">
						{$t('about.license')}
					</p>

					<a
						href="https://github.com/seanmorley15/AdventureLog/blob/main/LICENSE"
						target="_blank"
						rel="noopener noreferrer"
						class="link link-primary mt-2"
					>
						{$t('about.view_license')} →
					</a>
				</div>
			</div>

			<!-- Links -->
			<div class="card bg-base-200/30 border border-base-300">
				<div class="card-body p-4">
					<div class="flex flex-wrap gap-3">
						<a
							href="https://github.com/seanmorley15/AdventureLog"
							target="_blank"
							rel="noopener noreferrer"
							class="btn btn-outline btn-sm"
						>
							GitHub →
						</a>
						<a
							href="https://seanmorley.com/sponsor"
							target="_blank"
							rel="noopener noreferrer"
							class="btn btn-outline btn-sm"
						>
							{$t('about.sponsor')} →
						</a>
						<!-- documentation -->
						<a
							href="https://adventurelog.app"
							target="_blank"
							rel="noopener noreferrer"
							class="btn btn-outline btn-sm"
						>
							{$t('navbar.documentation')} →
						</a>
						<!-- discord -->
						<a
							href="https://discord.gg/wRbQ9Egr8C"
							target="_blank"
							rel="noopener noreferrer"
							class="btn btn-outline btn-sm"
						>
							Discord →
						</a>
					</div>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div class="flex items-center justify-between mt-6 pt-4 border-t border-base-300">
			<div class="text-sm text-base-content/60">
				{$t('about.thank_you')}
			</div>
			<button class="btn btn-primary btn-sm" on:click={close}>
				{$t('about.close')}
			</button>
		</div>
	</div>
</dialog>
