<script lang="ts">
	import type { PageData } from '../$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;
</script>

<section class="flex flex-col items-center justify-center min-h-screen px-4 py-8 bg-base-100">
	<div class="w-full max-w-lg p-6 shadow-lg rounded-lg bg-base-200 text-center">
		{#if data.verified}
			<h1 class="text-4xl font-bold text-success mb-4">
				{$t('settings.email_verified')}
			</h1>
			<p class="text-lg text-base-content">
				{$t('settings.email_verified_success')}
			</p>
		{:else}
			<h1 class="text-4xl font-bold text-error mb-4">
				{$t('settings.email_verified_error')}
			</h1>
			<p class="text-lg text-base-content">
				{$t('settings.email_verified_erorr_desc')}
			</p>
		{/if}
	</div>
</section>

<svelte:head>
	<title>Email Verification</title>
	<meta name="description" content="View your email verification status for AdventureLog." />
</svelte:head>
