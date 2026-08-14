<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { t } from 'svelte-i18n';
	import type { User } from '$lib/types.js';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';

	interface Props {
		user: User;
		deleteConfirmation: string;
		deletePassword: string;
		isDeletingAccount: boolean;
		canDeleteAccount: boolean;
		onDeleteSubmit: () => boolean;
	}

	let {
		user,
		deleteConfirmation = $bindable(),
		deletePassword = $bindable(),
		isDeletingAccount = $bindable(),
		canDeleteAccount,
		onDeleteSubmit
	}: Props = $props();
</script>

<SettingsCard className="border border-error/30">
	<SettingsSectionHeader
		icon="⚠️"
		iconBgClass="bg-error/10"
		title={$t('settings.danger_zone')}
		description={$t('settings.danger_zone_desc')}
	/>

	<div class="alert alert-error mb-6">
		<div>
			<p class="font-semibold">{$t('settings.delete_account_title')}</p>
			<p class="text-sm mt-1">{$t('settings.delete_account_warning')}</p>
			<p class="text-sm mt-1">{$t('settings.delete_account_stripe_warning')}</p>
		</div>
	</div>

	<p class="text-sm text-base-content/70 mb-6">{$t('settings.danger_zone_instructions')}</p>

	<form
		method="POST"
		action="?/deleteAccount"
		use:enhance={() => {
			if (!onDeleteSubmit()) {
				return () => {};
			}
			isDeletingAccount = true;
			return async ({ update }) => {
				await update();
				isDeletingAccount = false;
			};
		}}
		class="space-y-4 max-w-md"
	>
		<div class="form-control">
			<label class="label py-1" for="delete-confirmation">
				<span class="label-text font-medium"
					>{$t('settings.delete_account_confirmation_label')}</span
				>
			</label>
			<input
				id="delete-confirmation"
				name="confirmation"
				type="text"
				bind:value={deleteConfirmation}
				class="input input-bordered input-error w-full"
				placeholder={user.username}
				autocomplete="off"
				required
			/>
		</div>

		{#if user.has_password && !user.disable_password}
			<div class="form-control">
				<label class="label py-1" for="delete-password">
					<span class="label-text font-medium">{$t('settings.delete_account_password_label')}</span>
				</label>
				<input
					id="delete-password"
					name="password"
					type="password"
					bind:value={deletePassword}
					class="input input-bordered input-error w-full"
					autocomplete="current-password"
					required
				/>
			</div>
		{/if}

		{#if $page.form?.deleteAccountError}
			<div class="alert alert-error py-2 text-sm">
				<span>{$t($page.form.deleteAccountError)}</span>
			</div>
		{/if}

		<button type="submit" class="btn btn-error" disabled={!canDeleteAccount || isDeletingAccount}>
			{#if isDeletingAccount}
				<span class="loading loading-spinner loading-sm mr-2"></span>
			{/if}
			{$t('settings.delete_account')}
		</button>
	</form>
</SettingsCard>
