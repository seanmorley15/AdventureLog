<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import { t } from 'svelte-i18n';
	import type { User } from '#lib/types.js';
	import type { DeletionPreview } from '#lib/traveler-impact.js';
	import TravelerImpact from '#lib/components/collections/TravelerImpact.svelte';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';

	interface Props {
		user: User;
		deleteConfirmation: string;
		deletePassword: string;
		isDeletingAccount: boolean;
		canDeleteAccount: boolean;
		onDeleteSubmit: () => boolean;
		/** What deleting would do to shared trips, when the server has said. */
		deletionPreview?: DeletionPreview | null;
	}

	let {
		user,
		deleteConfirmation = $bindable(),
		deletePassword = $bindable(),
		isDeletingAccount = $bindable(),
		canDeleteAccount,
		onDeleteSubmit,
		deletionPreview = null
	}: Props = $props();

	let accountDeletionBlocked = $derived(user.is_staff);
</script>

<SettingsCard className="border border-error/30">
	<SettingsSectionHeader
		icon="⚠️"
		iconBgClass="bg-error/10"
		title={$t('settings.danger_zone')}
		description={$t('settings.danger_zone_desc')}
	/>

	{#if accountDeletionBlocked}
		<div class="alert alert-warning mb-6">
			<div>
				<p class="font-semibold">{$t('settings.delete_account_staff_blocked')}</p>
				<p class="text-sm mt-1">{$t('settings.delete_account_staff_blocked_desc')}</p>
			</div>
		</div>
	{:else}
		<div class="alert alert-error mb-6">
			<div>
				<p class="font-semibold">{$t('settings.delete_account_title')}</p>
				<p class="text-sm mt-1">{$t('settings.delete_account_warning')}</p>
				<p class="text-sm mt-1">{$t('settings.delete_account_stripe_warning')}</p>
			</div>
		</div>
	{/if}

	{#if !accountDeletionBlocked && deletionPreview}
		<div class="rounded-lg border border-base-300 bg-base-200/60 p-4 mb-6 space-y-2 text-sm">
			<p class="font-semibold">{$t('traveler_impact.account_title')}</p>
			<p>
				{$t('traveler_impact.account_deleted', {
					values: { locations: deletionPreview.locations, collections: deletionPreview.collections }
				})}
			</p>
			{#if deletionPreview.shared_collections_left > 0}
				<p>
					{$t('traveler_impact.account_left', {
						values: { count: deletionPreview.shared_collections_left }
					})}
				</p>
			{/if}
			{#if deletionPreview.visits_detached > 0}
				<p>
					{$t('traveler_impact.account_detached', {
						values: { count: deletionPreview.visits_detached }
					})}
				</p>
			{/if}
			{#if deletionPreview.visits_deleted > 0}
				<p>
					{$t('traveler_impact.account_visits_deleted', {
						values: { count: deletionPreview.visits_deleted }
					})}
				</p>
			{/if}
			{#if deletionPreview.others_uploads > 0}
				<p>
					{$t('traveler_impact.others_uploads', {
						values: { count: deletionPreview.others_uploads }
					})}
				</p>
			{/if}
			<TravelerImpact
				people={deletionPreview.people_released}
				places={deletionPreview.places_copied}
				othersKeep={false}
			/>
		</div>
	{/if}

	{#if !accountDeletionBlocked}
		<p class="text-sm text-base-content/80 mb-6">{$t('settings.danger_zone_instructions')}</p>
	{/if}

	<form
		method="POST"
		action="?/deleteAccount"
		use:enhance={() => {
			if (accountDeletionBlocked || !onDeleteSubmit()) {
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
		<fieldset
			disabled={accountDeletionBlocked}
			class={['space-y-4', accountDeletionBlocked && 'opacity-50 cursor-not-allowed']}
		>
			<div class="flex flex-col">
				<label class="field-label" for="delete-confirmation"
					>{$t('settings.delete_account_confirmation_label')}</label
				>
				<input
					id="delete-confirmation"
					name="confirmation"
					type="text"
					bind:value={deleteConfirmation}
					class="input input-error w-full"
					placeholder={user.username}
					autocomplete="off"
					required
				/>
			</div>

			{#if user.has_password && !user.disable_password}
				<div class="flex flex-col">
					<label class="field-label" for="delete-password"
						>{$t('settings.delete_account_password_label')}</label
					>
					<input
						id="delete-password"
						name="password"
						type="password"
						bind:value={deletePassword}
						class="input input-error w-full"
						autocomplete="current-password"
						required
					/>
				</div>
			{/if}

			{#if page.form?.deleteAccountError}
				<div class="alert alert-error py-2 text-sm">
					<span>{$t(page.form.deleteAccountError)}</span>
				</div>
			{/if}

			<button
				type="submit"
				class="btn btn-error"
				disabled={accountDeletionBlocked || !canDeleteAccount || isDeletingAccount}
			>
				{#if isDeletingAccount}
					<span class="loading loading-spinner loading-sm mr-2"></span>
				{/if}
				{$t('settings.delete_account')}
			</button>
		</fieldset>
	</form>
</SettingsCard>
