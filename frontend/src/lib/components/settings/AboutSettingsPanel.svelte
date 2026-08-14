<script lang="ts">
	import { t } from 'svelte-i18n';
	import { copyrightYear } from '$lib/config.js';
	import AppVersionDisplay from '$lib/components/shared/AppVersionDisplay.svelte';
	import type { User } from '$lib/types.js';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';
	import SettingsSubsection from './SettingsSubsection.svelte';

	interface Props {
		user: User;
	}

	let { user }: Props = $props();
</script>

<SettingsCard>
	<SettingsSectionHeader
		icon="ℹ️"
		iconBgClass="bg-info/10"
		title={$t('settings.about')}
		description={$t('settings.about_desc')}
	/>

	<SettingsSubsection
		title={$t('settings.account_details')}
		description={$t('settings.account_details_desc')}
		showDivider={false}
	/>

	<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm mb-8">
		<div class="p-4 bg-base-200 rounded-xl">
			<span class="text-base-content/80">UUID</span>
			<p class="text-primary font-mono font-semibold mt-1 break-all">{user.uuid}</p>
		</div>
		<div class="p-4 bg-base-200 rounded-xl">
			<span class="text-base-content/80">{$t('settings.staff_status')}</span>
			<p class="mt-1">
				<span class="badge {user.is_staff ? 'badge-success' : 'badge-ghost'}">
					{user.is_staff ? $t('settings.staff_user') : $t('settings.regular_user')}
				</span>
			</p>
		</div>
		<div class="p-4 bg-base-200 rounded-xl">
			<span class="text-base-content/80">{$t('settings.app_version')}</span>
			<div class="mt-1"><AppVersionDisplay size="sm" /></div>
		</div>
		<div class="p-4 bg-base-200 rounded-xl">
			<span class="text-base-content/80">{$t('settings.profile_visibility')}</span>
			<p class="mt-1">
				<span class="badge {user.public_profile ? 'badge-info' : 'badge-ghost'}">
					{user.public_profile ? $t('adventures.public') : $t('adventures.private')}
				</span>
			</p>
		</div>
	</div>

	<SettingsSubsection
		title="{$t('about.about')} AdventureLog"
		description={$t('settings.about_app_desc')}
	/>

	<div class="text-center space-y-3 py-2">
		<p class="text-sm text-base-content/80">{$t('about.license')}</p>
		<p class="text-sm text-base-content/70">
			© {copyrightYear}
			<a href="https://seanmorley.com" target="_blank" rel="noreferrer" class="link">Sean Morley</a
			>.
			{$t('settings.all_rights_reserved')}
		</p>
		<div class="flex justify-center gap-4 flex-wrap">
			<a
				href="https://github.com/seanmorley15/AdventureLog"
				target="_blank"
				rel="noreferrer"
				class="link link-primary text-sm">GitHub</a
			>
			<a
				href="https://github.com/seanmorley15/AdventureLog/blob/main/LICENSE"
				target="_blank"
				rel="noreferrer"
				class="link link-secondary text-sm">{$t('settings.license')}</a
			>
			<a
				href="https://adventurelog.app/docs/configuration/social_auth.html"
				target="_blank"
				rel="noreferrer"
				class="link link-neutral text-sm">{$t('settings.documentation_link')}</a
			>
		</div>
	</div>
</SettingsCard>
