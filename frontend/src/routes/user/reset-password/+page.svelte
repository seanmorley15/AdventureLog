<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { t } from 'svelte-i18n';
</script>

<section class="flex flex-col items-center justify-center min-h-screen px-4 py-8 bg-base-100">
	<h1 class="text-4xl font-bold text-center mb-6 text-primary">{$t('settings.reset_password')}</h1>

	<div class="w-full max-w-md p-6 shadow-lg rounded-lg bg-base-200">
		<form method="post" action="?/forgotPassword" class="flex flex-col space-y-4" use:enhance>
			<div class="form-control">
				<label for="email" class="label">
					<span class="label-text">{$t('auth.email')}</span>
				</label>
				<input
					name="email"
					type="email"
					id="email"
					placeholder="Enter your email"
					class="input input-bordered w-full"
					required
				/>
			</div>

			<div class="form-control mt-4">
				<button type="submit" class="btn btn-primary w-full">
					{$t('settings.reset_password')}
				</button>
			</div>

			{#if $page.form?.message}
				<div class="mt-4 text-center text-error">
					{$t(`settings.${$page.form?.message}`)}
				</div>
			{/if}

			{#if $page.form?.success}
				<div class="mt-4 text-center text-success">
					{$t('settings.possible_reset')}
				</div>
			{/if}
		</form>
	</div>
</section>

<svelte:head>
	<title>Reset Password</title>
	<meta name="description" content="Reset your password for AdventureLog." />
</svelte:head>
