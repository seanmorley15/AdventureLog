<script lang="ts">
	import { t } from 'svelte-i18n';
	import {
		appCodename,
		appTitle,
		appVersion,
		copyrightYear,
		versionChangelog
	} from '#lib/config.js';
	import type { User } from '#lib/types.js';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';
	import SettingsSubsection from './SettingsSubsection.svelte';

	interface Props {
		user: User;
	}

	let { user }: Props = $props();
	const profileVisibility = $derived(
		user.profile_visibility ?? (user.public_profile ? 'public' : 'private')
	);

	const links = [
		{
			label: 'about_link_docs',
			href: 'https://adventurelog.app',
			class: 'btn-primary'
		},
		{
			label: 'about_link_discord',
			href: 'https://discord.gg/wRbQ9Egr8C',
			class: 'btn-outline'
		},
		{
			label: 'about_link_github',
			href: 'https://github.com/seanmorley15/AdventureLog',
			class: 'btn-outline'
		},
		{ label: 'about_link_changelog', href: versionChangelog, class: 'btn-outline' },
		{ label: 'about_link_sponsor', href: 'https://seanmorley.com/sponsor', class: 'btn-outline' }
	];

	// The standard GPL-3.0 "how to apply" notice, filled in for this project. Legal text: not translated.
	const licenseNotice =
		$derived(`AdventureLog - a self-hosted travel companion for logging, planning and mapping your adventures.
Copyright (C) ${copyrightYear}  Sean Morley

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.`);
</script>

<SettingsCard>
	<SettingsSectionHeader
		icon="ℹ️"
		iconBgClass="bg-info/10"
		title={$t('about.about')}
		description={$t('settings.about_desc')}
	/>

	<div class="flex flex-col items-center gap-2 rounded-2xl bg-base-200 p-6 text-center">
		<img src="/favicon.png" alt="" class="h-14 w-14" />
		<h3 class="text-2xl font-bold">{appTitle}</h3>
		<p class="flex items-baseline gap-2">
			<span class="font-mono text-sm text-base-content/70">{appVersion}</span>
			<span class="font-semibold italic text-secondary">{appCodename}</span>
		</p>
		<p class="max-w-lg text-sm text-base-content/80">{$t('settings.about_tagline')}</p>
	</div>

	<div class="mt-4 flex flex-wrap justify-center gap-2">
		{#each links as link (link.label)}
			<a href={link.href} target="_blank" rel="noreferrer" class="btn btn-sm {link.class}">
				{$t(`settings.${link.label}`)}
			</a>
		{/each}
	</div>

	<SettingsSubsection
		title={$t('settings.about_license_title')}
		description={$t('settings.about_license_desc')}
	/>

	<pre
		class="overflow-x-auto rounded-xl bg-base-200 p-4 font-mono text-xs leading-relaxed text-base-content/80">{licenseNotice}</pre>
	<a
		href="https://github.com/seanmorley15/AdventureLog/blob/main/LICENSE"
		target="_blank"
		rel="noreferrer"
		class="link link-primary mt-3 inline-block text-sm">{$t('about.view_license')}</a
	>

	<SettingsSubsection
		title={$t('settings.account_details')}
		description={$t('settings.account_details_desc')}
	/>

	<div class="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
		<div class="rounded-xl bg-base-200 p-4 sm:col-span-2">
			<span class="text-base-content/80">UUID</span>
			<p class="mt-1 break-all font-mono font-semibold text-primary">{user.uuid}</p>
		</div>
		<div class="rounded-xl bg-base-200 p-4">
			<span class="text-base-content/80">{$t('settings.staff_status')}</span>
			<p class="mt-1">
				<span class="badge {user.is_staff ? 'badge-success' : 'badge-ghost'}">
					{user.is_staff ? $t('settings.staff_user') : $t('settings.regular_user')}
				</span>
			</p>
		</div>
		<div class="rounded-xl bg-base-200 p-4">
			<span class="text-base-content/80">{$t('settings.profile_visibility')}</span>
			<p class="mt-1">
				<span class="badge {profileVisibility === 'private' ? 'badge-ghost' : 'badge-info'}">
					{$t(`settings.profile_visibility_${profileVisibility}`)}
				</span>
			</p>
		</div>
	</div>
</SettingsCard>
