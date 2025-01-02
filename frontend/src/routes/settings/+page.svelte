<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { addToast } from '$lib/toasts';
	import type { ImmichIntegration, User } from '$lib/types.js';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { t } from 'svelte-i18n';
	import TotpModal from '$lib/components/TOTPModal.svelte';
	import { appTitle, appVersion } from '$lib/config.js';
	import ImmichLogo from '$lib/assets/immich.svg';

	export let data;
	console.log(data);
	let user: User;
	let emails: typeof data.props.emails;
	if (data.user) {
		user = data.user;
		emails = data.props.emails;
	}

	let new_email: string = '';

	let immichIntegration = data.props.immichIntegration;

	let newImmichIntegration: ImmichIntegration = {
		server_url: '',
		api_key: '',
		id: ''
	};

	let isMFAModalOpen: boolean = false;

	onMount(async () => {
		if (browser) {
			const queryParams = new URLSearchParams($page.url.search);
			const pageParam = queryParams.get('page');

			if (pageParam === 'success') {
				addToast('success', $t('settings.update_success'));
				console.log('Settings updated successfully!');
			}
		}
	});

	$: {
		if (browser && $page.form?.success) {
			window.location.href = '/settings?page=success';
		}
		if (browser && $page.form?.error) {
			addToast('error', $t('settings.update_error'));
		}
	}

	async function checkVisitedRegions() {
		let res = await fetch('/api/reverse-geocode/mark_visited_region/', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		let data = await res.json();
		if (res.ok) {
			addToast('success', `${data.new_regions} ${$t('adventures.regions_updated')}`);
		} else {
			addToast('error', $t('adventures.error_updating_regions'));
		}
	}

	async function removeEmail(email: { email: any; verified?: boolean; primary?: boolean }) {
		let res = await fetch('/_allauth/browser/v1/account/email/', {
			method: 'DELETE',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ email: email.email })
		});
		if (res.ok) {
			addToast('success', $t('settings.email_removed'));
			emails = emails.filter((e) => e.email !== email.email);
		} else {
			addToast('error', $t('settings.email_removed_error'));
		}
	}

	async function verifyEmail(email: { email: any; verified?: boolean; primary?: boolean }) {
		let res = await fetch('/_allauth/browser/v1/account/email/', {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ email: email.email })
		});
		if (res.ok) {
			addToast('success', $t('settings.verify_email_success'));
		} else {
			addToast('error', $t('settings.verify_email_error'));
		}
	}

	async function addEmail() {
		let res = await fetch('/_allauth/browser/v1/account/email/', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ email: new_email })
		});
		if (res.ok) {
			addToast('success', $t('settings.email_added'));
			emails = [...emails, { email: new_email, verified: false, primary: false }];
			new_email = '';
		} else {
			let error = await res.json();
			let error_code = error.errors[0].code;
			addToast('error', $t(`settings.${error_code}`) || $t('settings.generic_error'));
		}
	}

	async function primaryEmail(email: { email: any; verified?: boolean; primary?: boolean }) {
		let res = await fetch('/_allauth/browser/v1/account/email/', {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ email: email.email, primary: true })
		});
		if (res.ok) {
			addToast('success', $t('settings.email_set_primary'));
			// remove primary from all other emails and set this one as primary
			emails = emails.map((e) => {
				if (e.email === email.email) {
					e.primary = true;
				} else {
					e.primary = false;
				}
				return e;
			});
		} else {
			addToast('error', $t('settings.email_set_primary_error'));
		}
	}

	async function enableImmichIntegration() {
		if (!immichIntegration?.id) {
			let res = await fetch('/api/integrations/immich/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newImmichIntegration)
			});
			let data = await res.json();
			if (res.ok) {
				addToast('success', $t('immich.immich_enabled'));
				immichIntegration = data;
			} else {
				addToast('error', $t('immich.immich_error'));
			}
		} else {
			let res = await fetch(`/api/integrations/immich/${immichIntegration.id}/`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newImmichIntegration)
			});
			let data = await res.json();
			if (res.ok) {
				addToast('success', $t('immich.immich_updated'));
				immichIntegration = data;
			} else {
				addToast('error', $t('immich.immich_error'));
			}
		}
	}

	async function disableImmichIntegration() {
		if (immichIntegration && immichIntegration.id) {
			let res = await fetch(`/api/integrations/immich/${immichIntegration.id}/`, {
				method: 'DELETE'
			});
			if (res.ok) {
				addToast('success', $t('immich.immich_disabled'));
				immichIntegration = null;
			} else {
				addToast('error', $t('immich.immich_error'));
			}
		}
	}

	async function disableMfa() {
		const res = await fetch('/_allauth/browser/v1/account/authenticators/totp', {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('success', $t('settings.mfa_disabled'));
			data.props.authenticators = false;
		} else {
			if (res.status == 401) {
				addToast('error', $t('settings.reset_session_error'));
			}
			addToast('error', $t('settings.generic_error'));
		}
	}
</script>

{#if isMFAModalOpen}
	<TotpModal
		user={data.user}
		on:close={() => (isMFAModalOpen = false)}
		bind:is_enabled={data.props.authenticators}
	/>
{/if}

<div class="container mx-auto p-6 max-w-4xl">
	<h1 class="text-3xl font-extrabold text-center mb-6">
		{$t('settings.settings_page')}
	</h1>

	<!-- Account Settings Section -->
	<section class="space-y-8">
		<h2 class="text-2xl font-semibold text-center">
			{$t('settings.account_settings')}
		</h2>
		<div class=" bg-neutral p-6 rounded-lg shadow-md">
			<form
				method="post"
				action="?/changeDetails"
				use:enhance
				enctype="multipart/form-data"
				class="space-y-6"
			>
				<div>
					<label for="username" class="text-sm font-medium text-neutral-content"
						>{$t('auth.username')}</label
					>
					<input
						type="text"
						id="username"
						name="username"
						bind:value={user.username}
						class="block w-full mt-1 input input-bordered input-primary"
					/>
				</div>

				<div>
					<label for="first_name" class="text-sm font-medium text-neutral-content"
						>{$t('auth.first_name')}</label
					>
					<input
						type="text"
						id="first_name"
						name="first_name"
						bind:value={user.first_name}
						class="block w-full mt-1 input input-bordered input-primary"
					/>
				</div>

				<div>
					<label for="last_name" class="text-sm font-medium text-neutral-content"
						>{$t('auth.last_name')}</label
					>
					<input
						type="text"
						id="last_name"
						name="last_name"
						bind:value={user.last_name}
						class="block w-full mt-1 input input-bordered input-primary"
					/>
				</div>

				<div>
					<label for="profile_pic" class="text-sm font-medium text-neutral-content"
						>{$t('auth.profile_picture')}</label
					>
					<input
						type="file"
						id="profile_pic"
						name="profile_pic"
						class="file-input file-input-bordered file-input-primary mt-1 w-full"
					/>
				</div>

				<div class="flex items-center">
					<input
						type="checkbox"
						id="public_profile"
						name="public_profile"
						bind:checked={user.public_profile}
						class="toggle toggle-primary"
					/>
					<label for="public_profile" class="ml-2 text-sm text-neutral-content"
						>{$t('auth.public_profile')}</label
					>
				</div>

				<button class="w-full mt-4 btn btn-primary py-2">{$t('settings.update')}</button>
			</form>
		</div>
	</section>

	<!-- Password Change Section -->
	<section class="space-y-8">
		<h2 class="text-2xl font-semibold text-center mt-8">
			{$t('settings.password_change')}
		</h2>
		<div class="bg-neutral p-6 rounded-lg shadow-md">
			<form method="post" action="?/changePassword" use:enhance class="space-y-6">
				<div>
					<label for="current_password" class="text-sm font-medium text-neutral-content"
						>{$t('settings.current_password')}</label
					>
					<input
						type="password"
						id="current_password"
						name="current_password"
						class="block w-full mt-1 input input-bordered input-primary"
					/>
				</div>

				<div>
					<label for="password1" class="text-sm font-medium text-neutral-content"
						>{$t('settings.new_password')}</label
					>
					<input
						type="password"
						id="password1"
						name="password1"
						class="block w-full mt-1 input input-bordered input-primary"
					/>
				</div>

				<div>
					<label for="password2" class="text-sm font-medium text-neutral-content"
						>{$t('settings.confirm_new_password')}</label
					>
					<input
						type="password"
						id="password2"
						name="password2"
						class="block w-full mt-1 input input-bordered input-primary"
					/>
				</div>

				<div
					class="tooltip tooltip-warning"
					data-tip={$t('settings.password_change_lopout_warning')}
				>
					<button class="w-full btn btn-primary py-2 mt-4">{$t('settings.password_change')}</button>
				</div>
			</form>
		</div>
	</section>

	<!-- Email Change Section -->
	<section class="space-y-8">
		<h2 class="text-2xl font-semibold text-center mt-8">
			{$t('settings.email_change')}
		</h2>
		<div class="bg-neutral p-6 rounded-lg shadow-md">
			<div>
				{#each emails as email}
					<div class="flex items-center space-x-2 mb-2">
						<span>{email.email}</span>
						{#if email.verified}
							<div class="badge badge-success">{$t('settings.verified')}</div>
						{:else}
							<div class="badge badge-error">{$t('settings.not_verified')}</div>
						{/if}
						{#if email.primary}
							<div class="badge badge-primary">{$t('settings.primary')}</div>
						{/if}
						{#if !email.verified}
							<button class="btn btn-sm btn-secondary" on:click={() => verifyEmail(email)}
								>{$t('settings.verify')}</button
							>
						{/if}
						{#if !email.primary}
							<button class="btn btn-sm btn-secondary" on:click={() => primaryEmail(email)}
								>{$t('settings.make_primary')}</button
							>
						{/if}
						<button class="btn btn-sm btn-warning" on:click={() => removeEmail(email)}
							>{$t('adventures.remove')}</button
						>
					</div>
				{/each}
				{#if emails.length === 0}
					<p class="text-center text-neutral-content">{$t('settings.no_email_set')}</p>
				{/if}
			</div>

			<form class="mt-4" on:submit={addEmail}>
				<input
					type="email"
					id="new_email"
					name="new_email"
					bind:value={new_email}
					placeholder={$t('settings.new_email')}
					class="block w-full input input-bordered input-primary"
				/>
				<button class="w-full mt-4 btn btn-primary py-2">{$t('settings.email_change')}</button>
			</form>
		</div>
	</section>

	<!-- MFA Section -->
	<section class="space-y-8">
		<h2 class="text-2xl font-semibold text-center mt-8">
			{$t('settings.mfa_page_title')}
		</h2>
		<div class="bg-neutral p-6 rounded-lg shadow-md text-center">
			{#if !data.props.authenticators}
				<p class="text-neutral-content">{$t('settings.mfa_not_enabled')}</p>
				<button class="btn btn-primary mt-4" on:click={() => (isMFAModalOpen = true)}
					>{$t('settings.enable_mfa')}</button
				>
			{:else}
				<button class="btn btn-warning mt-4" on:click={disableMfa}
					>{$t('settings.disable_mfa')}</button
				>
			{/if}
		</div>
	</section>

	<!-- Immich Integration Section -->
	<section class="space-y-8">
		<h2 class="text-2xl font-semibold text-center mt-8">
			{$t('immich.immich_integration')}
			<img src={ImmichLogo} alt="Immich" class="inline-block w-8 h-8 -mt-1" />
		</h2>
		<div class="bg-neutral p-6 rounded-lg shadow-md">
			<p class="text-center text-neutral-content">
				{$t('immich.immich_desc')}
			</p>
			{#if immichIntegration}
				<div class="flex flex-col items-center justify-center mt-1 space-y-2">
					<div class="badge badge-success">{$t('immich.integration_enabled')}</div>
					<div class="flex space-x-2">
						<button
							class="btn btn-warning"
							on:click={() => {
								if (immichIntegration) newImmichIntegration = immichIntegration;
							}}>Edit</button
						>
						<button class="btn btn-error" on:click={disableImmichIntegration}
							>{$t('immich.disable')}</button
						>
					</div>
				</div>
			{/if}
			{#if !immichIntegration || newImmichIntegration.id}
				<div class="mt-4">
					<div>
						<label for="immich_url" class="text-sm font-medium text-neutral-content"
							>{$t('immich.server_url')}</label
						>
						<input
							type="url"
							id="immich_url"
							name="immich_url"
							bind:value={newImmichIntegration.server_url}
							placeholder="{$t('immich.server_url')} (e.g. https://immich.example.com/api)"
							class="block w-full mt-1 input input-bordered input-primary"
						/>
						{#if newImmichIntegration.server_url && !newImmichIntegration.server_url.endsWith('api')}
							<p class="text-s text-warning mt-2">
								{$t('immich.api_note')}
							</p>
						{/if}
					</div>
					<div class="mt-4">
						<label for="immich_api_key" class="text-sm font-medium text-neutral-content"
							>{$t('immich.api_key')}</label
						>
						<input
							type="text"
							id="immich_api_key"
							name="immich_api_key"
							bind:value={newImmichIntegration.api_key}
							placeholder={$t('immich.api_key')}
							class="block w-full mt-1 input input-bordered input-primary"
						/>
					</div>
					<button on:click={enableImmichIntegration} class="w-full mt-4 btn btn-primary py-2"
						>{!immichIntegration?.id
							? $t('immich.enable_immich')
							: $t('immich.update_integration')}</button
					>
				</div>
			{/if}
		</div>
	</section>

	<!-- Visited Region Check Section -->
	<section class="text-center mt-8">
		<h2 class="text-2xl font-semibold">{$t('adventures.visited_region_check')}</h2>
		<p>{$t('adventures.visited_region_check_desc')}</p>
		<button class="btn btn-neutral mt-4" on:click={checkVisitedRegions}
			>{$t('adventures.update_visited_regions')}</button
		>
	</section>

	<small class="text-center block mt-8">
		<b>For Debug Use:</b> UUID={user.uuid} | Staff user: {user.is_staff} | {appTitle}
		{appVersion}
	</small>
</div>

<svelte:head>
	<title>User Settings | AdventureLog</title>
	<meta
		name="description"
		content="Update your user account settings here. Change your username, first name, last name, and profile icon."
	/>
</svelte:head>
