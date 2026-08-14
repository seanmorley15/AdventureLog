<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { t } from 'svelte-i18n';
	import PasswordRequirements from '$lib/components/auth/PasswordRequirements.svelte';

	let { data } = $props();

	let password = $state('');
	let confirmPassword = $state('');
</script>

<section class="flex flex-col items-center justify-center min-h-screen px-4 py-8 bg-base-100">
	<h1 class="text-4xl font-bold text-center mb-6 text-primary">
		{$t('settings.change_password')}
	</h1>

	<div class="w-full max-w-md p-6 shadow-lg rounded-lg bg-base-200">
		<form method="POST" use:enhance class="flex flex-col space-y-4">
			<div class="flex flex-col">
				<label class="field-label" for="password">{$t('auth.password')}</label>
				<input
					type="password"
					id="password"
					name="password"
					placeholder={$t('auth.enter_password')}
					minlength={data.passwordPolicy.min_length}
					bind:value={password}
					required
					class="input w-full"
				/>
			</div>

			<div class="flex flex-col">
				<label class="field-label" for="confirm_password">{$t('auth.confirm_password')}</label>
				<input
					type="password"
					id="confirm_password"
					name="confirm_password"
					placeholder={$t('auth.confirm_password')}
					minlength={data.passwordPolicy.min_length}
					bind:value={confirmPassword}
					required
					class="input w-full"
				/>
			</div>

			<PasswordRequirements policy={data.passwordPolicy} {password} />

			<div class="flex flex-col mt-2">
				<button type="submit" class="btn btn-primary w-full">
					{$t('settings.reset_password')}
				</button>
			</div>

			{#if $page.form?.message}
				<div class="mt-2 text-center text-error">
					{$t($page.form?.message, { values: $page.form?.values ?? {} })}
				</div>
			{/if}
		</form>
	</div>
</section>

<svelte:head>
	<title>Change Password</title>
	<meta
		name="description"
		content="Confirm your password reset and create a new password for AdventureLog."
	/>
</svelte:head>
