<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { t } from 'svelte-i18n';
	import type { APIKey, User } from '$lib/types.js';
	import PasswordRequirements from '$lib/components/auth/PasswordRequirements.svelte';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';

	type Provider = { name: string; usage_required: boolean };
	type PasswordPolicy = { min_length: number; validators_enabled: boolean };

	export let user: User;
	export let emails: { email: string; verified?: boolean; primary?: boolean }[];
	export let authenticators: boolean;
	export let socialProviders: Provider[];
	export let publicUrl: string;
	export let passwordPolicy: PasswordPolicy;
	export let newPassword: string;
	export let confirmPassword: string;
	export let apiKeys: APIKey[];
	export let newApiKeyName: string;
	export let newlyCreatedKey: string | null;
	export let keyCopied: boolean;
	export let onEnableMfa: () => void;
	export let onDisableMfa: () => void;
	export let onDisablePassword: () => void;
	export let onCreateApiKey: () => void;
	export let onCopyKey: () => void;
	export let onDeleteApiKey: (id: string) => void;
	export let onDismissNewKey: () => void;
</script>

<div class="space-y-8">
	<SettingsCard>
		<SettingsSectionHeader
			icon="🔐"
			iconBgClass="bg-warning/10"
			title={$t('settings.change_password')}
			description={$t('settings.pass_change_desc')}
		/>
		<form method="post" action="?/changePassword" use:enhance class="space-y-6">
			{#if user.has_password}
				<div class="form-control max-w-md">
					<!-- svelte-ignore a11y-label-has-associated-control -->
					<label class="label">
						<span class="label-text font-medium">{$t('settings.current_password')}</span>
					</label>
					<input
						type="password"
						name="current_password"
						class="input input-bordered input-primary w-full"
						placeholder={$t('settings.enter_current_password')}
					/>
				</div>
			{/if}
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl">
				<div class="form-control">
					<!-- svelte-ignore a11y-label-has-associated-control -->
					<label class="label">
						<span class="label-text font-medium">{$t('settings.new_password')}</span>
					</label>
					<input
						type="password"
						name="password1"
						class="input input-bordered input-primary w-full"
						minlength={passwordPolicy.min_length}
						bind:value={newPassword}
					/>
				</div>
				<div class="form-control">
					<!-- svelte-ignore a11y-label-has-associated-control -->
					<label class="label">
						<span class="label-text font-medium">{$t('settings.confirm_new_password')}</span>
					</label>
					<input
						type="password"
						name="password2"
						class="input input-bordered input-primary w-full"
						minlength={passwordPolicy.min_length}
						bind:value={confirmPassword}
					/>
				</div>
			</div>
			<PasswordRequirements policy={passwordPolicy} password={newPassword} />
			{#if $page.form?.message}
				<div class="alert alert-warning max-w-2xl">
					<span>{$t($page.form?.message, { values: $page.form?.values ?? {} })}</span>
				</div>
			{/if}
			<div class="tooltip tooltip-warning" data-tip={$t('settings.password_change_lopout_warning')}>
				<button class="btn btn-warning">🔑 {$t('settings.password_change')}</button>
			</div>
		</form>
	</SettingsCard>

	<SettingsCard>
		<SettingsSectionHeader
			icon="🛡️"
			iconBgClass="bg-success/10"
			title={$t('settings.mfa_page_title')}
			description={$t('settings.mfa_desc')}
		/>
		<div class="flex items-center justify-between p-4 bg-base-200 rounded-xl gap-4 flex-wrap">
			<div class="flex items-center gap-4">
				<span class="badge {authenticators ? 'badge-success' : 'badge-error'}">
					{authenticators ? `✅ ${$t('settings.enabled')}` : `❌ ${$t('settings.disabled')}`}
				</span>
				<span class="font-medium">
					{authenticators ? $t('settings.mfa_is_enabled') : $t('settings.mfa_not_enabled')}
				</span>
			</div>
			{#if !authenticators}
				{#if !emails.some((e) => e.verified)}
					<button class="btn btn-disabled">{$t('settings.enable_mfa')}</button>
				{:else}
					<button class="btn btn-primary" on:click={onEnableMfa}>{$t('settings.enable_mfa')}</button
					>
				{/if}
			{:else}
				<button class="btn btn-warning" on:click={onDisableMfa}>{$t('settings.disable_mfa')}</button
				>
			{/if}
		</div>
		{#if !emails.some((e) => e.verified)}
			<div class="alert alert-warning mt-4">
				<span>{$t('settings.no_verified_email_warning')}</span>
			</div>
		{/if}
	</SettingsCard>

	{#if socialProviders?.length > 0}
		<SettingsCard>
			<SettingsSectionHeader
				icon="🔗"
				iconBgClass="bg-info/10"
				title={$t('settings.sign_in_methods')}
				description={$t('settings.social_auth_desc_1')}
			/>
			<div class="p-4 bg-base-200 rounded-xl mb-4">
				<div class="flex items-center justify-between gap-4 flex-wrap">
					<div>
						<h3 class="font-semibold">{$t('settings.password_auth')}</h3>
						<p class="text-sm text-base-content/70">
							{user.disable_password || socialProviders.some((p) => p.usage_required)
								? $t('settings.password_login_disabled')
								: $t('settings.password_login_enabled')}
						</p>
					</div>
					<input
						type="checkbox"
						bind:checked={user.disable_password}
						on:change={onDisablePassword}
						disabled={socialProviders.some((p) => p.usage_required)}
						class="toggle toggle-primary"
					/>
				</div>
				{#if user.disable_password}
					<div class="alert alert-warning mt-4 py-2">
						<span class="text-sm">{$t('settings.password_disable_warning')}</span>
					</div>
				{/if}
			</div>
			<a
				class="btn btn-outline btn-primary"
				href={`${publicUrl}/accounts/social/connections/`}
				target="_blank"
				rel="noreferrer"
			>
				🔗 {$t('settings.launch_account_connections')}
			</a>
		</SettingsCard>
	{/if}

	<SettingsCard>
		<SettingsSectionHeader
			icon="🔑"
			iconBgClass="bg-warning/10"
			title={$t('api_keys.title')}
			description={$t('api_keys.description')}
		/>
		{#if newlyCreatedKey}
			<div class="mb-6 rounded-2xl border border-warning/40 bg-warning/5 overflow-hidden">
				<div
					class="flex items-center justify-between px-5 py-3 bg-warning/10 border-b border-warning/20"
				>
					<span class="text-sm font-semibold text-warning">{$t('api_keys.new_key_title')}</span>
					<button type="button" class="btn btn-ghost btn-xs" on:click={onDismissNewKey}>✕</button>
				</div>
				<div class="px-5 py-4">
					<div class="flex items-center gap-2 bg-base-200 rounded-xl px-4 py-3">
						<code class="flex-1 text-sm font-mono break-all select-all">{newlyCreatedKey}</code>
						<button
							class="btn btn-sm {keyCopied ? 'btn-success' : 'btn-ghost'}"
							on:click={onCopyKey}
						>
							{keyCopied ? $t('api_keys.copied') : $t('api_keys.copy')}
						</button>
					</div>
				</div>
			</div>
		{/if}
		{#if apiKeys.length > 0}
			<div class="space-y-3 mb-6">
				{#each apiKeys as key (key.id)}
					<div class="flex items-center justify-between p-4 bg-base-200 rounded-xl gap-4">
						<div class="min-w-0">
							<p class="font-semibold truncate">{key.name}</p>
							<p class="text-sm font-mono text-base-content/60">{key.key_prefix}…</p>
						</div>
						<button class="btn btn-error btn-sm shrink-0" on:click={() => onDeleteApiKey(key.id)}>
							{$t('api_keys.revoke')}
						</button>
					</div>
				{/each}
			</div>
		{:else}
			<p class="text-base-content/50 mb-6">{$t('api_keys.no_keys')}</p>
		{/if}
		<div class="flex gap-3 flex-col sm:flex-row">
			<input
				type="text"
				bind:value={newApiKeyName}
				placeholder={$t('api_keys.key_name_placeholder')}
				class="input input-bordered input-primary flex-1"
				maxlength="100"
			/>
			<button class="btn btn-primary" on:click={onCreateApiKey} disabled={!newApiKeyName.trim()}>
				{$t('api_keys.create')}
			</button>
		</div>
	</SettingsCard>
</div>
