<script lang="ts">
	import { page } from '$app/state';
	import { t } from 'svelte-i18n';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import { addToast } from '#lib/toasts.js';
	import { errorKind, errorTone, isRetryable, type ErrorKind } from '#lib/errors.js';

	import CompassOff from '~icons/mdi/compass-off-outline';
	import Lock from '~icons/mdi/lock-outline';
	import AccountLock from '~icons/mdi/account-lock-outline';
	import ServerOff from '~icons/mdi/server-off';
	import CloudOff from '~icons/mdi/cloud-off-outline';
	import WifiOff from '~icons/mdi/wifi-off';
	import TimerSand from '~icons/mdi/timer-sand';
	import AlertCircle from '~icons/mdi/alert-circle-outline';
	import Refresh from '~icons/mdi/refresh';
	import ArrowLeft from '~icons/mdi/arrow-left';
	import HomeOutline from '~icons/mdi/home-outline';
	import Login from '~icons/mdi/login';
	import ContentCopy from '~icons/mdi/content-copy';

	// `online` is false while the browser has no connection; on the server it is undefined.
	let online = $state<boolean | undefined>(undefined);

	const kind: ErrorKind = $derived(errorKind(page.status, online === false));
	const tone = $derived(errorTone(kind));
	const retryable = $derived(isRetryable(kind));
	const reference = $derived(page.error?.errorId);
	const showAdminHelp = $derived(kind === 'server' || kind === 'unavailable');
	const onAuthPage = $derived(page.url.pathname === '/login' || page.url.pathname === '/signup');

	const icons = {
		bad_request: AlertCircle,
		unauthorized: AccountLock,
		forbidden: Lock,
		not_found: CompassOff,
		too_many: TimerSand,
		server: ServerOff,
		unavailable: CloudOff,
		offline: WifiOff,
		generic: AlertCircle
	};

	// A history entry to go back to exists unless this page was opened directly.
	const canGoBack = $derived(typeof history !== 'undefined' && history.length > 1);

	async function copyReference() {
		if (!reference) return;
		try {
			await navigator.clipboard.writeText(reference);
			addToast('success', $t('errors.reference_copied'));
		} catch {
			// Copying is a convenience; the reference stays visible to read out.
		}
	}
</script>

<svelte:window bind:online />
<svelte:head>
	<title>{page.status} | AdventureLog</title>
</svelte:head>

<ErrorState
	status={kind === 'offline' ? null : page.status}
	icon={icons[kind]}
	{tone}
	title={$t(`errors.${kind}_title`)}
	description={$t(`errors.${kind}_description`)}
>
	{#snippet actions()}
		{#if kind === 'unauthorized'}
			<a href="/login" class="btn btn-primary gap-2">
				<Login class="h-5 w-5" />
				{$t('errors.sign_in')}
			</a>
		{:else if retryable}
			<button class="btn btn-primary gap-2" onclick={() => location.reload()}>
				<Refresh class="h-5 w-5" />
				{$t('errors.try_again')}
			</button>
		{/if}
		{#if canGoBack}
			<button class="btn btn-ghost gap-2" onclick={() => history.back()}>
				<ArrowLeft class="h-5 w-5" />
				{$t('errors.go_back')}
			</button>
		{/if}
		<a
			href="/"
			class="btn {retryable || kind === 'unauthorized' ? 'btn-ghost' : 'btn-primary'} gap-2"
		>
			<HomeOutline class="h-5 w-5" />
			{$t('errors.go_home')}
		</a>
	{/snippet}

	{#if reference || showAdminHelp || onAuthPage}
		<div class="space-y-3 text-left">
			{#if showAdminHelp}
				<div class="rounded-box border border-base-300 bg-base-100/80 p-4 text-sm">
					<div class="font-semibold">{$t('errors.admin_help_title')}</div>
					<p class="mt-1 text-base-content/70">{$t('errors.admin_help_body')}</p>
					{#if onAuthPage}
						<p class="mt-2 text-base-content/70">{$t('errors.login_hint')}</p>
					{/if}
					<a
						class="link link-primary mt-2 inline-block"
						target="_blank"
						rel="noopener"
						href="https://adventurelog.app/docs/troubleshooting/common_issues"
					>
						{$t('errors.admin_help_link')}
					</a>
				</div>
			{/if}
			{#if reference}
				<button
					class="mx-auto flex items-center gap-2 text-xs text-base-content/50 hover:text-base-content"
					onclick={copyReference}
					title={$t('errors.reference_copied')}
				>
					{$t('errors.reference')}:
					<span class="font-mono">{reference}</span>
					<ContentCopy class="h-3.5 w-3.5" />
				</button>
			{/if}
		</div>
	{/if}
</ErrorState>
