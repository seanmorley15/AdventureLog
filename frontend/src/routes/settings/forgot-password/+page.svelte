<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { t } from 'svelte-i18n';
</script>

<h1 class="text-center font-extrabold text-4xl mb-6">{$t('settings.reset_password')}</h1>

<div class="flex justify-center">
	<form method="post" action="?/forgotPassword" class="w-full max-w-xs" use:enhance>
		<label for="email">{$t('auth.email')}</label>
		<input
			name="email"
			type="email"
			id="email"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/><br />
		<button class="py-2 px-4 btn btn-primary mr-2">{$t('settings.reset_password')}</button>
		{#if $page.form?.message}
			<div class="text-center text-error mt-4">
				{$t(`settings.${$page.form?.message}`)}
			</div>
		{/if}
		{#if $page.form?.success}
			<div class="text-center text-success mt-4">
				{$t('settings.possible_reset')}
			</div>
		{/if}
	</form>
</div>

<svelte:head>
	<title>Forgot Password</title>
	<meta name="description" content="Reset your password for AdventureLog." />
</svelte:head>
