<script lang="ts">
	import { enhance } from '$app/forms';
	import { t } from 'svelte-i18n';
	import { CURRENCY_LABELS, CURRENCY_OPTIONS } from '$lib/money';
	import { basemapOptions } from '$lib';
	import type { User } from '$lib/types.js';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';
	import SettingsSubsection from './SettingsSubsection.svelte';

	export let user: User;
	export let onPublicProfileToggle: (nextValue: boolean) => void;
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
			<div class="form-control">
				<!-- svelte-ignore a11y-label-has-associated-control -->
				<label class="label"
					><span class="label-text font-medium">{$t('auth.username')}</span></label
				>
				<input
					type="text"
					bind:value={user.username}
					name="username"
					class="input input-bordered input-primary w-full"
					placeholder={$t('settings.enter_username')}
				/>
			</div>
			<div class="form-control">
				<!-- svelte-ignore a11y-label-has-associated-control -->
				<label class="label"
					><span class="label-text font-medium">{$t('auth.first_name')}</span></label
				>
				<input
					type="text"
					bind:value={user.first_name}
					name="first_name"
					class="input input-bordered input-primary w-full"
					placeholder={$t('settings.enter_first_name')}
				/>
			</div>
			<div class="form-control">
				<!-- svelte-ignore a11y-label-has-associated-control -->
				<label class="label"
					><span class="label-text font-medium">{$t('auth.last_name')}</span></label
				>
				<input
					type="text"
					bind:value={user.last_name}
					name="last_name"
					class="input input-bordered input-primary w-full"
					placeholder={$t('settings.enter_last_name')}
				/>
			</div>
			<div class="form-control">
				<!-- svelte-ignore a11y-label-has-associated-control -->
				<label class="label"
					><span class="label-text font-medium">{$t('auth.profile_picture')}</span></label
				>
				<input
					type="file"
					name="profile_pic"
					class="file-input file-input-bordered file-input-primary w-full"
					accept="image/*"
				/>
			</div>
			<div class="form-control md:col-span-2">
				<label class="label cursor-pointer justify-start gap-4">
					<input
						type="checkbox"
						checked={user.public_profile}
						on:change={(e) => onPublicProfileToggle(e.currentTarget.checked)}
						name="public_profile"
						class="toggle toggle-primary"
					/>
					<div>
						<span class="label-text font-medium">{$t('auth.public_profile')}</span>
						<p class="text-sm text-base-content/60">{$t('settings.public_profile_desc')}</p>
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
					</div>
				</label>
			</div>
		</div>

		<SettingsSubsection
			title={$t('settings.preferences')}
			description={$t('settings.preferences_desc')}
		/>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div class="form-control">
				<label class="label cursor-pointer justify-start gap-4">
					<input
						type="checkbox"
						checked={user.measurement_system === 'imperial'}
						name="measurement_system"
						class="toggle toggle-primary"
						on:change={() =>
							(user.measurement_system =
								user.measurement_system === 'metric' ? 'imperial' : 'metric')}
					/>
					<div>
						<span class="label-text font-medium">{$t('settings.use_imperial')}</span>
						<p class="text-sm text-base-content/60">{$t('settings.use_imperial_desc')}</p>
					</div>
				</label>
			</div>
			<div class="form-control">
				<label class="label" for="default_currency">
					<span class="label-text font-medium">{$t('settings.preferred_currency')}</span>
				</label>
				<select
					id="default_currency"
					name="default_currency"
					class="select select-bordered select-primary w-full"
					bind:value={user.default_currency}
				>
					{#each CURRENCY_OPTIONS as code}
						<option value={code}>
							{code}{#if CURRENCY_LABELS[code]}
								- {CURRENCY_LABELS[code]}{/if}
						</option>
					{/each}
				</select>
				<p class="text-sm text-base-content/60 mt-1">{$t('settings.preferred_currency_desc')}</p>
			</div>
			<div class="form-control md:col-span-2">
				<label class="label" for="map_style">
					<span class="label-text font-medium">{$t('settings.default_map_style')}</span>
				</label>
				<select
					id="map_style"
					name="map_style"
					class="select select-bordered select-primary w-full"
					bind:value={user.map_style}
				>
					{#each basemapOptions as option}
						<option value={option.value}>{option.label} ({option.category})</option>
					{/each}
				</select>
				<p class="text-sm text-base-content/60 mt-1">{$t('settings.map_style_desc')}</p>
			</div>
		</div>

		<div class="pt-6">
			<button class="btn btn-primary">{$t('settings.update')}</button>
		</div>
	</form>
</SettingsCard>
