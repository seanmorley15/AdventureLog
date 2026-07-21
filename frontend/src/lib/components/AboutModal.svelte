<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { copyrightYear, versionChangelog, appVersion } from '$lib/config';
	import { copyToClipboard } from '$lib/index';
	import { addToast } from '$lib/toasts';
	import AppVersionDisplay from '$lib/components/shared/AppVersionDisplay.svelte';

	import CloseIcon from '~icons/mdi/close';
	import AccountIcon from '~icons/mdi/account-circle';
	import TagIcon from '~icons/mdi/tag-outline';
	import InformationIcon from '~icons/mdi/information-outline';
	import ScaleBalanceIcon from '~icons/mdi/scale-balance';
	import GitHubIcon from '~icons/mdi/github';
	import HeartIcon from '~icons/mdi/heart';
	import BookOpenIcon from '~icons/mdi/book-open-page-variant';
	import DiscordIcon from '~icons/mdi/discord';
	import OpenInNewIcon from '~icons/mdi/open-in-new';
	import ContentCopyIcon from '~icons/mdi/content-copy';
	import CheckIcon from '~icons/mdi/check';

	const dispatch = createEventDispatcher();
	let modal: HTMLDialogElement;

	let integrations: Record<string, boolean> | null = null;
	let versionCopied = false;
	let copyResetTimeout: ReturnType<typeof setTimeout> | undefined;

	onMount(() => {
		modal = document.getElementById('about_modal') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}

		void (async () => {
			const response = await fetch('/api/integrations');
			if (response.ok) {
				integrations = await response.json();
			} else {
				integrations = null;
			}
		})();

		return () => {
			if (copyResetTimeout) clearTimeout(copyResetTimeout);
		};
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === modal) {
			close();
		}
	}

	async function copyVersion() {
		try {
			await copyToClipboard(appVersion);
			versionCopied = true;
			addToast('success', $t('adventures.copied_to_clipboard'));
			if (copyResetTimeout) clearTimeout(copyResetTimeout);
			copyResetTimeout = setTimeout(() => {
				versionCopied = false;
			}, 2000);
		} catch {
			addToast('error', $t('adventures.copy_failed'));
		}
	}
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<dialog id="about_modal" class="modal backdrop-blur-sm" on:click={handleBackdropClick}>
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-2xl p-0 bg-base-100 border border-base-300 shadow-2xl max-h-[90vh] flex flex-col"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Hero -->
		<div
			class="relative bg-gradient-to-r from-primary via-primary/90 to-secondary/80 text-primary-content px-6 pt-6 pb-5 shrink-0"
		>
			<button
				type="button"
				class="btn btn-ghost btn-sm btn-circle absolute top-4 right-4 text-primary-content hover:bg-base-100/20"
				aria-label={$t('about.close')}
				title={$t('about.close')}
				on:click={close}
			>
				<CloseIcon class="w-5 h-5" />
			</button>

			<div class="flex items-start gap-4 pr-10">
				<div
					class="h-14 w-14 rounded-2xl bg-base-100/20 backdrop-blur flex items-center justify-center shadow-inner shrink-0"
				>
					<img src="/favicon.png" alt="AdventureLog" class="w-9 h-9" />
				</div>
				<div class="min-w-0">
					<p class="text-xs uppercase tracking-widest font-semibold opacity-75">
						{$t('about.about')}
					</p>
					<h1 class="text-2xl font-bold leading-tight">AdventureLog</h1>
				</div>
			</div>
		</div>

		<!-- Body -->
		<div class="p-6 space-y-5 overflow-y-auto flex-1">
			<!-- Version -->
			<div class="rounded-2xl border border-base-300/70 bg-base-200/40 p-4 space-y-3">
				<div class="flex items-center gap-2 text-primary">
					<TagIcon class="w-5 h-5 shrink-0" />
					<h2 class="font-semibold text-sm">{$t('about.version')}</h2>
				</div>

				<AppVersionDisplay />

				<div
					class="flex items-center gap-2 rounded-xl border border-base-300/80 bg-base-100/80 px-3 py-2"
				>
					<code class="flex-1 min-w-0 truncate font-mono text-sm text-base-content/80"
						>{appVersion}</code
					>
					<button
						type="button"
						class="btn btn-ghost btn-xs btn-square shrink-0 {versionCopied
							? 'text-success'
							: 'text-base-content/60'}"
						aria-label={$t('about.copy_version')}
						title={$t('about.copy_version')}
						on:click={copyVersion}
					>
						{#if versionCopied}
							<CheckIcon class="w-4 h-4" />
						{:else}
							<ContentCopyIcon class="w-4 h-4" />
						{/if}
					</button>
				</div>

				<a
					href={versionChangelog}
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center gap-1 text-sm link link-primary font-medium"
				>
					{$t('about.view_changelog')}
					<OpenInNewIcon class="w-3.5 h-3.5" />
				</a>
			</div>

			<!-- Developer -->
			<div
				class="flex flex-col sm:flex-row sm:items-center gap-4 rounded-2xl border border-base-300/70 bg-base-200/40 p-4"
			>
				<div class="flex items-center gap-3 min-w-0">
					<div
						class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0"
					>
						<AccountIcon class="w-5 h-5 text-primary" />
					</div>
					<div class="min-w-0">
						<p class="text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-0.5">
							{$t('about.developer')}
						</p>
						<a
							href="https://seanmorley.com"
							target="_blank"
							rel="noopener noreferrer"
							class="font-semibold link link-primary truncate block"
						>
							Sean Morley
						</a>
					</div>
				</div>
				<p class="text-sm text-base-content/65 m-0 sm:ml-auto sm:text-right sm:max-w-[14rem]">
					{$t('about.message')}
				</p>
			</div>

			<!-- Info grid -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="rounded-2xl border border-base-300/70 bg-base-200/40 p-4 space-y-3">
					<div class="flex items-center gap-2 text-primary">
						<InformationIcon class="w-5 h-5 shrink-0" />
						<h2 class="font-semibold text-sm">{$t('about.attributions')}</h2>
					</div>
					<div class="space-y-2 text-sm text-base-content/70">
						{#if integrations?.google_maps}
							<p class="m-0">
								{$t('about.nominatim_1')}
								<a
									href="https://developers.google.com/maps/terms"
									target="_blank"
									rel="noopener noreferrer"
									class="link link-primary font-medium"
								>
									Google Maps Platform
								</a>
							</p>
						{:else if integrations && !integrations.google_maps}
							<p class="m-0">
								{$t('about.nominatim_1')}
								<a
									href="https://operations.osmfoundation.org/policies/nominatim/"
									target="_blank"
									rel="noopener noreferrer"
									class="link link-primary font-medium"
								>
									OpenStreetMap Nominatim
								</a>
							</p>
						{:else}
							<p class="m-0">{$t('about.generic_attributions')}</p>
						{/if}
						<p class="m-0 text-xs text-base-content/55">{$t('about.other_attributions')}</p>
					</div>
				</div>

				<div class="rounded-2xl border border-base-300/70 bg-base-200/40 p-4 space-y-3">
					<div class="flex items-center gap-2 text-primary">
						<ScaleBalanceIcon class="w-5 h-5 shrink-0" />
						<h2 class="font-semibold text-sm">{$t('about.license_info')}</h2>
					</div>
					<div class="space-y-2 text-sm text-base-content/70">
						<p class="m-0">
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
						<p class="m-0">{$t('about.license')}</p>
						<a
							href="https://github.com/seanmorley15/AdventureLog/blob/main/LICENSE"
							target="_blank"
							rel="noopener noreferrer"
							class="inline-flex items-center gap-1 link link-primary text-sm font-medium"
						>
							{$t('about.view_license')}
							<OpenInNewIcon class="w-3.5 h-3.5" />
						</a>
					</div>
				</div>
			</div>

			<!-- Community links -->
			<div class="space-y-3">
				<p class="text-xs font-semibold uppercase tracking-wider text-base-content/50 m-0">
					{$t('navbar.support')}
				</p>
				<div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
					<a
						href="https://github.com/seanmorley15/AdventureLog"
						target="_blank"
						rel="noopener noreferrer"
						class="group flex flex-col items-center gap-2 rounded-xl border border-base-300/70 bg-base-200/30 p-3 text-center transition-colors hover:bg-base-200 hover:border-primary/30"
					>
						<GitHubIcon
							class="w-5 h-5 text-base-content/70 group-hover:text-primary transition-colors"
						/>
						<span class="text-xs font-medium">GitHub</span>
					</a>
					<a
						href="https://seanmorley.com/sponsor"
						target="_blank"
						rel="noopener noreferrer"
						class="group flex flex-col items-center gap-2 rounded-xl border border-base-300/70 bg-base-200/30 p-3 text-center transition-colors hover:bg-base-200 hover:border-primary/30"
					>
						<HeartIcon
							class="w-5 h-5 text-base-content/70 group-hover:text-primary transition-colors"
						/>
						<span class="text-xs font-medium">{$t('about.sponsor')}</span>
					</a>
					<a
						href="https://adventurelog.app"
						target="_blank"
						rel="noopener noreferrer"
						class="group flex flex-col items-center gap-2 rounded-xl border border-base-300/70 bg-base-200/30 p-3 text-center transition-colors hover:bg-base-200 hover:border-primary/30"
					>
						<BookOpenIcon
							class="w-5 h-5 text-base-content/70 group-hover:text-primary transition-colors"
						/>
						<span class="text-xs font-medium">{$t('navbar.documentation')}</span>
					</a>
					<a
						href="https://discord.gg/wRbQ9Egr8C"
						target="_blank"
						rel="noopener noreferrer"
						class="group flex flex-col items-center gap-2 rounded-xl border border-base-300/70 bg-base-200/30 p-3 text-center transition-colors hover:bg-base-200 hover:border-primary/30"
					>
						<DiscordIcon
							class="w-5 h-5 text-base-content/70 group-hover:text-primary transition-colors"
						/>
						<span class="text-xs font-medium">Discord</span>
					</a>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div
			class="flex items-center justify-between gap-4 px-6 py-4 border-t border-base-300 shrink-0 bg-base-100/80"
		>
			<p class="text-sm text-base-content/60 m-0">{$t('about.thank_you')}</p>
			<button class="btn btn-primary btn-sm" on:click={close}>
				{$t('about.close')}
			</button>
		</div>
	</div>
</dialog>
