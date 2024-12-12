<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import type { PageData } from '../../../$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;
</script>

<h1 class="text-center font-bold text-4xl mb-4">{$t('settings.change_password')}</h1>

<form method="POST" use:enhance>
	<div class="mb-4">
		<label for="password" class="block mb-2">{$t('auth.new_password')}</label>
		<input
			type="password"
			id="password"
			name="password"
			required
			class="w-full p-2 border rounded"
		/>
	</div>
	<div class="mb-4">
		<label for="confirm_password" class="block mb-2">{$t('auth.confirm_password')}</label>
		<input
			type="password"
			id="confirm_password"
			name="confirm_password"
			required
			class="w-full p-2 border rounded"
		/>
	</div>
	<button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded"
		>{$t('auth.reset_password')}</button
	>

	{#if $page.form?.message}
		<div class="text-center text-error mt-4">
			{$page.form?.message}
		</div>
	{/if}
</form>

<svelte:head>
	<title>Password Reset Confirm</title>
	<meta name="description" content="Confirm your password reset and make a new password." />
</svelte:head>
