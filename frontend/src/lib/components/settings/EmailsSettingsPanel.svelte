<script lang="ts">
	import { preventDefault } from 'svelte/legacy';

	import { t } from 'svelte-i18n';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';

	interface Props {
		emails: { email: string; verified?: boolean; primary?: boolean }[];
		newEmail: string;
		onVerify: (email: { email: string; verified?: boolean; primary?: boolean }) => void;
		onMakePrimary: (email: { email: string; verified?: boolean; primary?: boolean }) => void;
		onRemove: (email: { email: string; verified?: boolean; primary?: boolean }) => void;
		onAdd: () => void;
	}

	let {
		emails,
		newEmail = $bindable(),
		onVerify,
		onMakePrimary,
		onRemove,
		onAdd
	}: Props = $props();
</script>

<SettingsCard>
	<SettingsSectionHeader
		icon="📧"
		iconBgClass="bg-secondary/10"
		title={$t('settings.email_management')}
		description={$t('settings.email_management_desc')}
	/>

	{#if emails.length > 0}
		<div class="space-y-3 mb-8">
			{#each emails as email}
				<div class="p-4 bg-base-200 rounded-xl">
					<div class="flex items-center justify-between flex-wrap gap-4">
						<div class="flex items-center gap-3 min-w-0">
							<span class="font-medium truncate">{email.email}</span>
							<div class="flex gap-2 shrink-0">
								{#if email.verified}
									<span class="badge badge-success">✅ {$t('settings.verified')}</span>
								{:else}
									<span class="badge badge-error">❌ {$t('settings.not_verified')}</span>
								{/if}
								{#if email.primary}
									<span class="badge badge-primary">⭐ {$t('settings.primary')}</span>
								{/if}
							</div>
						</div>
						<div class="flex gap-2 flex-wrap">
							{#if !email.verified}
								<button class="btn btn-sm btn-secondary" onclick={() => onVerify(email)}>
									{$t('settings.verify')}
								</button>
							{/if}
							{#if !email.primary && email.verified}
								<button class="btn btn-sm btn-primary" onclick={() => onMakePrimary(email)}>
									{$t('settings.make_primary')}
								</button>
							{/if}
							<button
								class="btn btn-sm btn-warning"
								onclick={() => onRemove(email)}
								disabled={emails.length === 1 || email.primary}
							>
								{$t('adventures.remove')}
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="text-center py-8 mb-8">
			<div class="text-6xl mb-4">📧</div>
			<p class="text-lg text-base-content/80">{$t('settings.no_email_set')}</p>
		</div>
	{/if}

	<div class="divider font-semibold text-base-content">{$t('settings.add_new_email')}</div>
	<form class="space-y-4" onsubmit={preventDefault(onAdd)}>
		<div class="flex flex-col">
			<label class="field-label" for="settings-new-email">{$t('settings.add_new_email_address')}</label>
			<input
				id="settings-new-email"
				type="email"
				bind:value={newEmail}
				class="input input-primary w-full"
				placeholder={$t('settings.enter_new_email')}
				required
			/>
		</div>
		<button class="btn btn-primary">➕ {$t('settings.add_email')}</button>
	</form>
</SettingsCard>
