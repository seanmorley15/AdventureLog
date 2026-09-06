<script lang="ts">
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<section class="flex flex-col items-center justify-center min-h-screen px-4 py-8 bg-base-100">
	<div class="w-full max-w-lg p-6 shadow-lg rounded-lg bg-base-200 text-center">
		{#if data.verified}
			<h1 class="text-4xl font-bold text-success mb-4">
				{$t('settings.email_verified')}
			</h1>
			<p class="text-lg text-base-content mb-6">
				{$t('settings.email_verified_success')}
			</p>
			<a href="/login" class="btn btn-primary">{$t('auth.login')}</a>
		{:else}
			<h1 class="text-4xl font-bold text-error mb-4">
				{$t('settings.email_verified_error')}
			</h1>
			<p class="text-lg text-base-content mb-6">
				{$t('settings.email_verified_erorr_desc')}
			</p>
			<a href="/login" class="btn btn-outline">{$t('auth.login')}</a>
		{/if}
	</div>
</section>

<svelte:head>
	<title>Email Verification</title>
	<meta name="description" content="View your email verification status for AdventureLog." />
</svelte:head>
