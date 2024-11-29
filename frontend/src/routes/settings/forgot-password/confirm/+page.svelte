<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;
</script>

<h1 class="text-center font-bold text-4xl mb-4">{$t('settings.change_password')}</h1>

{#if data.props.token && data.props.uid}
	<p class="text-center">{$t('settings.login_redir')}</p>
	<div
		class="modal-action items-center"
		style="display: flex; flex-direction: column; align-items: center; width: 100%;"
	>
		<form action="?/reset" method="post" use:enhance>
			<input type="hidden" name="uid" value={data.props.uid} />
			<input type="hidden" name="token" value={data.props.token} />

			<div class="mb-2 w-full">
				<input
					type="password"
					class="input input-bordered w-full"
					id="new_password1"
					name="new_password1"
					placeholder={$t('settings.new_password')}
				/>
			</div>
			<div class="mb-2 w-full">
				<input
					type="password"
					class="input input-bordered w-full"
					id="new_password2"
					name="new_password2"
					placeholder={$t('settings.confirm_new_password')}
				/>
			</div>
			<button type="submit" class="btn btn-primary w-full">{$t('settings.submit')}</button>
			{#if $page.form?.message}
				<div class="text-center text-error mt-4">
					{$t($page.form?.message)}
				</div>
			{/if}
		</form>
	</div>
{:else}
	<div class="flex justify-center">
		<div class="items-center justify-center">
			<p class="text-center">{$t('settings.token_required')}</p>

			<button class="btn btn-neutral" on:click={() => goto('/settings/forgot-password')}>
				{$t('settings.reset_password')}
			</button>
		</div>
	</div>
{/if}

<svelte:head>
	<title>Password Reset Confirm</title>
	<meta name="description" content="Confirm your password reset and make a new password." />
</svelte:head>
