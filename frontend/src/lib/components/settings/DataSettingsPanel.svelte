<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { t } from 'svelte-i18n';
	import type { MediaUsage } from '$lib/types.js';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';
	import SettingsSubsection from './SettingsSubsection.svelte';

	interface Props {
		mediaUsage: MediaUsage;
		formatBytes: (bytes: number) => string;
		totalMediaBytes: number;
		mediaLimitBytes: number | null;
		totalMediaFiles: number;
		overallUsagePercent: number;
		imagesPercent: number;
		attachmentsPercent: number;
		profilePicsPercent: number;
		mediaLimitLabel: string;
		acknowledgeRestoreOverride: boolean;
		isRestoring: boolean;
		onRestoreStart: () => void;
	}

	let {
		mediaUsage,
		formatBytes,
		totalMediaBytes,
		mediaLimitBytes,
		totalMediaFiles,
		overallUsagePercent,
		imagesPercent,
		attachmentsPercent,
		profilePicsPercent,
		mediaLimitLabel,
		acknowledgeRestoreOverride = $bindable(),
		isRestoring,
		onRestoreStart
	}: Props = $props();
</script>

<SettingsCard>
	<SettingsSectionHeader
		icon="📦"
		iconBgClass="bg-accent/10"
		title={$t('settings.data_and_storage')}
		description={$t('settings.data_and_storage_desc')}
	/>

	<SettingsSubsection
		title={$t('settings.media_storage')}
		description={$t('settings.media_storage_desc')}
		showDivider={false}
	/>

	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
		<p class="text-sm text-base-content/80">
			{#if mediaLimitBytes}
				{$t('settings.media_usage_summary', {
					values: {
						used: formatBytes(totalMediaBytes),
						limit: mediaLimitLabel,
						percent: overallUsagePercent
					}
				})}
			{:else}
				{$t('settings.media_usage_unlimited', { values: { used: formatBytes(totalMediaBytes) } })}
			{/if}
		</p>
		<span class="badge badge-primary badge-lg">
			{mediaLimitBytes ? `${overallUsagePercent}% used` : 'Unlimited'}
		</span>
	</div>

	<div class="stats stats-vertical lg:stats-horizontal w-full bg-base-200 shadow-sm mb-6">
		<div class="stat">
			<div class="stat-title">{$t('settings.total_used')}</div>
			<div class="stat-value text-primary text-2xl">{formatBytes(totalMediaBytes)}</div>
			<div class="stat-desc">{totalMediaFiles} {$t('adventures.files')}</div>
		</div>
		<div class="stat">
			<div class="stat-title">{$t('adventures.images')}</div>
			<div class="stat-value text-secondary text-2xl">{formatBytes(mediaUsage.images_bytes)}</div>
		</div>
		<div class="stat">
			<div class="stat-title">{$t('adventures.attachments')}</div>
			<div class="stat-value text-accent text-2xl">{formatBytes(mediaUsage.attachments_bytes)}</div>
		</div>
		<div class="stat">
			<div class="stat-title">{$t('auth.profile_picture')}</div>
			<div class="stat-value text-info text-2xl">{formatBytes(mediaUsage.profile_pics_bytes)}</div>
		</div>
	</div>

	<SettingsSubsection
		title={$t('settings.backup_restore')}
		description={$t('settings.backup_restore_desc')}
	/>

	<div class="bg-base-200 rounded-xl p-4 mb-6 text-sm">
		<h4 class="font-semibold mb-3 text-base-content">{$t('settings.whats_included')}</h4>
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
			<div class="space-y-2">
				{#each [[$t('locations.locations')], [$t('adventures.visits')], [$t('navbar.collections')], [$t('settings.media')]] as [label]}
					<div class="flex justify-between"><span>{label}</span><span>✅</span></div>
				{/each}
			</div>
			<div class="space-y-2">
				{#each [[$t('navbar.settings')], [$t('navbar.profile')], [$t('settings.integrations_settings')]] as [label]}
					<div class="flex justify-between"><span>{label}</span><span>❌</span></div>
				{/each}
			</div>
		</div>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
		<div class="p-6 bg-base-200 rounded-xl">
			<h3 class="font-semibold mb-2">📤 {$t('settings.backup_your_data')}</h3>
			<p class="text-sm text-base-content/80 mb-4">{$t('settings.backup_your_data_desc')}</p>
			<a class="btn btn-primary" href="/api/backup/export">💾 {$t('settings.download_backup')}</a>
		</div>
		<div class="p-6 bg-base-200 rounded-xl">
			<h3 class="font-semibold mb-2">📥 {$t('settings.restore_data')}</h3>
			<p class="text-sm text-base-content/80 mb-4">{$t('settings.restore_data_desc')}</p>
			<div class="alert alert-warning py-2 mb-4 text-sm">
				<span>⚠️ {$t('settings.data_override_warning')}</span>
			</div>
			<form
				method="post"
				action="?/restoreData"
				use:enhance
				onsubmit={onRestoreStart}
				enctype="multipart/form-data"
				class="space-y-3"
			>
				<input
					type="file"
					name="file"
					id="backup-file"
					class="file-input file-input-primary file-input-sm w-full"
					accept=".zip"
					required
				/>
				<label class="flex items-start gap-3 cursor-pointer">
					<input
						type="checkbox"
						name="confirm"
						value="yes"
						class="checkbox checkbox-warning checkbox-sm mt-1"
						required
						bind:checked={acknowledgeRestoreOverride}
					/>
					<span class="text-sm text-warning">{$t('settings.data_override_acknowledge')}</span>
				</label>
				{#if $page.form?.message && $page.form?.message.includes('restore')}
					<div class="alert alert-error py-2 text-sm">
						<span>{$t($page.form?.message, { values: $page.form?.values ?? {} })}</span>
					</div>
				{/if}
				<button
					type="submit"
					class="btn btn-warning btn-sm"
					disabled={!acknowledgeRestoreOverride || isRestoring}
				>
					{#if isRestoring}<span class="loading loading-spinner loading-sm"></span>{/if}
					🚀 {$t('settings.restore_data')}
				</button>
			</form>
		</div>
	</div>
</SettingsCard>
