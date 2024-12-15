<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import type { PageData } from '../../../$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;
</script>

<h1 class="text-center font-bold text-4xl mb-4">{$t('settings.change_password')}</h1>

<form method="POST" use:enhance class="flex flex-col items-center justify-center space-y-4">
	<div class="w-full max-w-xs">
		<label for="password" class="label">
			<span class="label-text">{$t('auth.new_password')}</span>
		</label>
		<input
			type="password"
			id="password"
			name="password"
			required
			class="input input-bordered w-full"
		/>
	</div>

	<div class="w-full max-w-xs">
		<label for="confirm_password" class="label">
			<span class="label-text">{$t('auth.confirm_password')}</span>
		</label>
		<input
			type="password"
			id="confirm_password"
			name="confirm_password"
			required
			class="input input-bordered w-full"
		/>
	</div>

	<button type="submit" class="btn btn-primary">
		{$t('settings.reset_password')}
	</button>

	{#if $page.form?.message}
		<div class="text-error">
			{$t($page.form?.message)}
		</div>
	{/if}
</form>

<svelte:head>
	<title>Password Reset Confirm</title>
	<meta name="description" content="Confirm your password reset and make a new password." />
</svelte:head>
