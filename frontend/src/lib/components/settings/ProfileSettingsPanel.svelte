<script lang="ts">
	import { enhance } from '$app/forms';
	import { t, locale } from 'svelte-i18n';
	import { CURRENCY_OPTIONS, currencyName } from '#lib/money.js';
	import {
		DATE_FORMAT_OPTIONS,
		DEFAULT_DATE_FORMAT,
		formatDateFormatPreview,
		normalizeDateFormat,
		type DateFormatPreference
	} from '#lib/dateFormat.js';
	import { getBasemapOptions } from '#lib';
	import type { ProfileVisibility, User } from '#lib/types.js';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';
	import SettingsSubsection from './SettingsSubsection.svelte';

	interface Props {
		user: User;
		/** Returns false to keep the current choice (the user backed out). */
		onProfileVisibilityChange: (next: ProfileVisibility) => boolean;
		/** False when the server is for signed-in users only (`ALLOW_PUBLIC_ACCESS`). */
		allowPublicAccess?: boolean;
	}

	let { user = $bindable(), onProfileVisibilityChange, allowPublicAccess = true }: Props = $props();

	// Who can see the profile, narrowest first (#1226).
	const PROFILE_VISIBILITY: { value: ProfileVisibility; label: string; hint: string }[] = [
		{
			value: 'private',
			label: 'settings.profile_visibility_private',
			hint: 'settings.profile_visibility_private_hint'
		},
		{
			value: 'signed_in',
			label: 'settings.profile_visibility_signed_in',
			hint: 'settings.profile_visibility_signed_in_hint'
		},
		{
			value: 'public',
			label: 'settings.profile_visibility_public',
			hint: 'settings.profile_visibility_public_hint'
		}
	];
	const profileVisibility = $derived<ProfileVisibility>(
		user.profile_visibility ?? (user.public_profile ? 'public' : 'private')
	);

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

	const availableBasemapOptions = getBasemapOptions();
	const defaultBasemapOption = availableBasemapOptions.find((option) => option.value === 'default');
	const showsStoredFallback = $derived(
		!availableBasemapOptions.some((option) => option.value === user.map_style)
	);

	const groupedBasemapOptions = BASEMAP_CATEGORY_ORDER.map((category) => ({
		category,
		options: availableBasemapOptions.filter((option) => option.category === category)
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

		<fieldset class="mt-6 rounded-xl border border-base-300 bg-base-200/70 p-4">
			<legend class="px-1 font-semibold text-base-content">
				{$t('settings.profile_visibility')}
			</legend>
			<p class="field-hint">{$t('settings.profile_visibility_desc')}</p>
			<div class="mt-3 grid gap-2 sm:grid-cols-3">
				{#each PROFILE_VISIBILITY as option (option.value)}
					{@const unavailable = option.value === 'public' && !allowPublicAccess}
					<label
						class={[
							'flex cursor-pointer gap-3 rounded-lg border p-3',
							profileVisibility === option.value
								? 'border-primary bg-primary/10'
								: 'border-base-300 bg-base-100',
							unavailable && 'cursor-not-allowed opacity-60'
						]}
					>
						<input
							type="radio"
							name="profile_visibility"
							class="radio radio-primary radio-sm mt-0.5"
							value={option.value}
							checked={profileVisibility === option.value}
							disabled={unavailable}
							onchange={(e) => {
								if (onProfileVisibilityChange(option.value)) return;
								const kept = e.currentTarget.form?.querySelector<HTMLInputElement>(
									`input[name="profile_visibility"][value="${profileVisibility}"]`
								);
								if (kept) kept.checked = true;
							}}
						/>
						<span class="min-w-0">
							<span class="block text-sm font-semibold">{$t(option.label)}</span>
							<span class="block text-xs text-base-content/70">
								{unavailable ? $t('settings.profile_visibility_public_off') : $t(option.hint)}
							</span>
						</span>
					</label>
				{/each}
			</div>
			{#if profileVisibility !== 'private' && (user.shared_collection_count ?? 0) > 0}
				<p class="text-sm text-warning mt-3">
					{$t('settings.public_profile_sharing_warning', {
						values: { count: user.shared_collection_count ?? 0 }
					})}
				</p>
			{/if}
			{#if profileVisibility !== 'private' && (user.pending_collection_invite_count ?? 0) > 0}
				<p class="text-sm text-warning mt-2">
					{$t('settings.public_profile_invite_warning', {
						values: { count: user.pending_collection_invite_count ?? 0 }
					})}
				</p>
			{/if}
		</fieldset>

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
							{code} - {currencyName(code, $locale)}
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
					{#if showsStoredFallback}
						<option value={user.map_style} hidden>
							{defaultBasemapOption?.icon}
							{defaultBasemapOption?.label}
						</option>
					{/if}
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
