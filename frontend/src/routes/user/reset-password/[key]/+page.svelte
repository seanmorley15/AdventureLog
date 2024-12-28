<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	// import type { PageData } from '../../../$types';
	import { t } from 'svelte-i18n';

	// export let data: PageData;
</script>

<section class="flex flex-col items-center justify-center min-h-screen px-4 py-8 bg-base-100">
	<h1 class="text-4xl font-bold text-center mb-6 text-primary">
		{$t('settings.change_password')}
	</h1>

	<div class="w-full max-w-md p-6 shadow-lg rounded-lg bg-base-200">
		<form method="POST" use:enhance class="flex flex-col space-y-6">
			<div class="form-control">
				<label for="password" class="label">
					<span class="label-text">{$t('auth.new_password')}</span>
				</label>
				<input
					type="password"
					id="password"
					name="password"
					placeholder="Enter new password"
					required
					class="input input-bordered w-full"
				/>
			</div>

			<div class="form-control">
				<label for="confirm_password" class="label">
					<span class="label-text">{$t('auth.confirm_password')}</span>
				</label>
				<input
					type="password"
					id="confirm_password"
					name="confirm_password"
					placeholder="Confirm new password"
					required
					class="input input-bordered w-full"
				/>
			</div>

			<div class="form-control mt-4">
				<button type="submit" class="btn btn-primary w-full">
					{$t('settings.reset_password')}
				</button>
			</div>

			{#if $page.form?.message}
				<div class="mt-4 text-center text-error">
					{$t($page.form?.message)}
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
