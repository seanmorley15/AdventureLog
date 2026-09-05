<script lang="ts">
	import { enhance } from '$app/forms';
	import { t } from 'svelte-i18n';
	import { CURRENCY_LABELS, CURRENCY_OPTIONS } from '$lib/money';
	import {
		DATE_FORMAT_OPTIONS,
		DEFAULT_DATE_FORMAT,
		formatDateFormatPreview,
		normalizeDateFormat,
		type DateFormatPreference
	} from '$lib/dateFormat';
	import { basemapOptions } from '$lib';
	import type { User } from '$lib/types.js';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';
	import SettingsSubsection from './SettingsSubsection.svelte';

	interface Props {
		user: User;
		onPublicProfileToggle: (nextValue: boolean) => void;
	}

	let { user = $bindable(), onPublicProfileToggle }: Props = $props();

	const dateFormatLabelKeys: Record<DateFormatPreference, string> = {
		locale: 'settings.date_format_locale',
		mdy: 'settings.date_format_mdy',
		dmy: 'settings.date_format_dmy',
		ymd: 'settings.date_format_ymd'
	};

	const selectedDateFormat = $derived(normalizeDateFormat(user.date_format || DEFAULT_DATE_FORMAT));

	const BASEMAP_CATEGORY_ORDER = [
		'Standard',
		'3D Terrain',
		'Satellite',
		'Topographic',
		'Clean',
		'Specialized'
	] as const;

	const groupedBasemapOptions = BASEMAP_CATEGORY_ORDER.map((category) => ({
		category,
		options: basemapOptions.filter((option) => option.category === category)
	})).filter((group) => group.options.length > 0);
</script>

<SettingsCard>
	<SettingsSectionHeader
		icon="👤"
		title={$t('settings.profile_info')}
		description={$t('settings.profile_info_desc')}
	/>

	<form method="post" action="?/changeDetails" use:enhance enctype="multipart/form-data">
		<SettingsSubsection
			title={$t('settings.personal_info')}
			description={$t('settings.personal_info_desc')}
			showDivider={false}
		/>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div class="flex flex-col md:col-span-2">
				<label class="field-label" for="settings-username">{$t('auth.username')}</label>
				<input
					id="settings-username"
					type="text"
					bind:value={user.username}
					name="username"
					class="input input-primary w-full"
					placeholder={$t('settings.enter_username')}
				/>
			</div>
			<div class="flex flex-col">
				<label class="field-label" for="settings-first-name">{$t('auth.first_name')}</label>
				<input
					id="settings-first-name"
					type="text"
					bind:value={user.first_name}
					name="first_name"
					class="input input-primary w-full"
					placeholder={$t('settings.enter_first_name')}
				/>
			</div>
			<div class="flex flex-col">
				<label class="field-label" for="settings-last-name">{$t('auth.last_name')}</label>
				<input
					id="settings-last-name"
					type="text"
					bind:value={user.last_name}
					name="last_name"
					class="input input-primary w-full"
					placeholder={$t('settings.enter_last_name')}
				/>
			</div>
			<div class="flex flex-col md:col-span-2">
				<label class="field-label" for="settings-profile-pic">{$t('auth.profile_picture')}</label>
				<input
					id="settings-profile-pic"
					type="file"
					name="profile_pic"
					class="file-input file-input-primary w-full"
					accept="image/*"
				/>
			</div>
		</div>

		<div class="mt-6 rounded-xl border border-base-300 bg-base-200/70 p-4">
			<label class="flex items-start justify-between gap-4 cursor-pointer w-full">
				<span class="min-w-0">
					<span class="font-semibold text-base-content">{$t('auth.public_profile')}</span>
					<p class="field-hint">{$t('settings.public_profile_desc')}</p>
					{#if user.public_profile && (user.shared_collection_count ?? 0) > 0}
						<p class="text-sm text-warning mt-2">
							{$t('settings.public_profile_sharing_warning', {
								values: { count: user.shared_collection_count ?? 0 }
							})}
						</p>
					{/if}
					{#if user.public_profile && (user.pending_collection_invite_count ?? 0) > 0}
						<p class="text-sm text-warning mt-2">
							{$t('settings.public_profile_invite_warning', {
								values: { count: user.pending_collection_invite_count ?? 0 }
							})}
						</p>
					{/if}
				</span>
				<input
					type="checkbox"
					checked={user.public_profile}
					onchange={(e) => onPublicProfileToggle(e.currentTarget.checked)}
					name="public_profile"
					class="toggle toggle-primary shrink-0 mt-0.5"
				/>
			</label>
		</div>

		<SettingsSubsection
			title={$t('settings.preferences')}
			description={$t('settings.preferences_desc')}
		/>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div class="flex flex-col">
				<label class="field-label" for="date_format">{$t('settings.preferred_date_format')}</label>
				<select
					id="date_format"
					name="date_format"
					class="select select-primary w-full"
					value={selectedDateFormat}
					onchange={(e) => {
						user.date_format = normalizeDateFormat((e.currentTarget as HTMLSelectElement).value);
					}}
				>
					{#each DATE_FORMAT_OPTIONS as option (option)}
						<option value={option}>
							{$t(dateFormatLabelKeys[option])} ({formatDateFormatPreview(option)})
						</option>
					{/each}
				</select>
				<p class="field-hint">{$t('settings.preferred_date_format_desc')}</p>
			</div>
			<div class="flex flex-col">
				<label class="field-label" for="default_currency">{$t('settings.preferred_currency')}</label
				>
				<select
					id="default_currency"
					name="default_currency"
					class="select select-primary w-full"
					bind:value={user.default_currency}
				>
					{#each CURRENCY_OPTIONS as code (code)}
						<option value={code}>
							{code}{#if CURRENCY_LABELS[code]}
								- {CURRENCY_LABELS[code]}{/if}
						</option>
					{/each}
				</select>
				<p class="field-hint">{$t('settings.preferred_currency_desc')}</p>
			</div>
			<div class="flex flex-col md:col-span-2">
				<label class="field-label" for="map_style">{$t('settings.default_map_style')}</label>
				<select
					id="map_style"
					name="map_style"
					class="select select-primary w-full"
					bind:value={user.map_style}
				>
					{#each groupedBasemapOptions as group (group.category)}
						<optgroup label={group.category}>
							{#each group.options as option (option.value)}
								<option value={option.value}>{option.icon} {option.label}</option>
							{/each}
						</optgroup>
					{/each}
				</select>
				<p class="field-hint">{$t('settings.map_style_desc')}</p>
			</div>
		</div>

		<div class="mt-6 rounded-xl border border-base-300 bg-base-200/70 p-4">
			<label class="flex items-start justify-between gap-4 cursor-pointer w-full">
				<span class="min-w-0">
					<span class="font-semibold text-base-content">{$t('settings.use_imperial')}</span>
					<p class="field-hint">{$t('settings.use_imperial_desc')}</p>
				</span>
				<input
					type="checkbox"
					checked={user.measurement_system === 'imperial'}
					name="measurement_system"
					class="toggle toggle-primary shrink-0 mt-0.5"
					onchange={() =>
						(user.measurement_system =
							user.measurement_system === 'metric' ? 'imperial' : 'metric')}
				/>
			</label>
		</div>

		<div class="flex justify-end pt-6 mt-8 border-t border-base-300">
			<button type="submit" class="btn btn-primary">{$t('settings.update')}</button>
		</div>
	</form>
</SettingsCard>
