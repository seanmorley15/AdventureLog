<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { addToast } from '$lib/toasts';
	import type { User } from '$lib/types.js';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { t } from 'svelte-i18n';
	import TotpModal from '$lib/components/TOTPModal.svelte';

	export let data;
	let user: User;
	let emails: typeof data.props.emails;
	if (data.user) {
		user = data.user;
		emails = data.props.emails;
	}

	let new_email: string = '';

	let is2FAModalOpen: boolean = false;

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
			addToast('error', $t('settings.email_added_error'));
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

	async function disableMfa() {
		const res = await fetch('/_allauth/browser/v1/account/authenticators/totp', {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('success', '2FA disabled');
			data.props.authenticators = false;
		} else {
			if (res.status == 401) {
				addToast('error', 'Logout and back in to refresh your session and try again.');
			}
			addToast('error', $t('settings.generic_error'));
		}
	}
</script>

{#if is2FAModalOpen}
	<TotpModal
		user={data.user}
		on:close={() => (is2FAModalOpen = false)}
		bind:is_enabled={data.props.authenticators}
	/>
{/if}

<h1 class="text-center font-extrabold text-4xl mb-6">{$t('settings.settings_page')}</h1>

<h1 class="text-center font-extrabold text-xl">{$t('settings.account_settings')}</h1>
<div class="flex justify-center">
	<form
		method="post"
		action="?/changeDetails"
		use:enhance
		class="w-full max-w-xs"
		enctype="multipart/form-data"
	>
		<label for="username">{$t('auth.username')}</label>
		<input
			bind:value={user.username}
			name="username"
			id="username"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/><br />
		<label for="first_name">{$t('auth.first_name')}</label>
		<input
			type="text"
			bind:value={user.first_name}
			name="first_name"
			id="first_name"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/><br />

		<label for="last_name">{$t('auth.last_name')}</label>
		<input
			type="text"
			bind:value={user.last_name}
			name="last_name"
			id="last_name"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/><br />
		<label for="profilePicture">{$t('auth.profile_picture')}</label>
		<input
			type="file"
			name="profile_pic"
			id="profile_pic"
			class="file-input file-input-bordered w-full max-w-xs mb-2"
		/><br />
		<div class="form-control">
			<div class="tooltip tooltip-info" data-tip={$t('auth.public_tooltip')}>
				<label class="label cursor-pointer">
					<span class="label-text">{$t('auth.public_profile')}</span>

					<input
						id="public_profile"
						name="public_profile"
						type="checkbox"
						class="toggle"
						checked={user.public_profile}
					/>
				</label>
			</div>
		</div>
		<button class="py-2 mt-2 px-4 btn btn-primary">{$t('settings.update')}</button>
	</form>
</div>

{#if $page.form?.message}
	<div class="text-center text-error mt-4">
		{$t($page.form.message)}
	</div>
{/if}

<h1 class="text-center font-extrabold text-xl mt-4 mb-2">{$t('settings.password_change')}</h1>
<div class="flex justify-center">
	<form action="?/changePassword" method="post" class="w-full max-w-xs" use:enhance>
		<input
			type="password"
			name="current_password"
			placeholder={$t('settings.current_password')}
			id="current_password"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/>
		<br />
		<input
			type="password"
			name="password1"
			placeholder={$t('settings.new_password')}
			id="password1"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/>
		<br />
		<input
			type="password"
			name="password2"
			id="password2"
			placeholder={$t('settings.confirm_new_password')}
			class="block mb-2 input input-bordered w-full max-w-xs"
		/>
		<div class="tooltip tooltip-warning" data-tip={$t('settings.password_change_lopout_warning')}>
			<button class="py-2 px-4 btn btn-primary mt-2">{$t('settings.password_change')}</button>
		</div>
		<br />
	</form>
</div>

<h1 class="text-center font-extrabold text-xl mt-4 mb-2">{$t('settings.email_change')}</h1>

<div class="flex justify-center mb-4">
	<div>
		{#each emails as email}
			<p class="mb-2">
				{email.email}
				{#if email.verified}
					<div class="badge badge-success">{$t('settings.verified')}</div>
				{:else}
					<div class="badge badge-error">{$t('settings.not_verified')}</div>
				{/if}
				{#if email.primary}
					<div class="badge badge-primary">{$t('settings.primary')}</div>
				{/if}
				{#if !email.verified}
					<button class="btn btn-sm btn-secondary ml-2" on:click={() => verifyEmail(email)}
						>{$t('settings.verify')}</button
					>
				{/if}
				{#if !email.primary}
					<button class="btn btn-sm btn-secondary ml-2" on:click={() => primaryEmail(email)}
						>{$t('settings.make_primary')}</button
					>
				{/if}
				<button class="btn btn-sm btn-warning ml-2" on:click={() => removeEmail(email)}
					>{$t('adventures.remove')}</button
				>
			</p>
		{/each}
		{#if emails.length === 0}
			<p>{$t('settings.no_emai_set')}</p>
		{/if}
	</div>
</div>

<div class="flex justify-center mt-4">
	<form class="w-full max-w-xs" on:submit={addEmail}>
		<div class="mb-4">
			<input
				type="email"
				name="new_email"
				placeholder={$t('settings.new_email')}
				bind:value={new_email}
				id="new_email"
				class="block mb-2 input input-bordered w-full max-w-xs"
			/>
		</div>
		<div>
			<button class="py-2 px-4 mb-4 btn btn-primary">{$t('settings.email_change')}</button>
		</div>
	</form>
</div>

<h1 class="text-center font-extrabold text-xl mt-4 mb-2">Multi-factor Authentication Settings</h1>

<div class="flex justify-center mb-4">
	<div>
		{#if !data.props.authenticators}
			<p>MFA not enabled</p>
			<button class="btn btn-primary mt-2" on:click={() => (is2FAModalOpen = true)}
				>Enable MFA</button
			>
		{:else}
			<button class="btn btn-warning mt-2" on:click={disableMfa}>Disable MFA</button>
		{/if}
	</div>
</div>

<div class="flex flex-col items-center mt-4">
	<h1 class="text-center font-extrabold text-xl mt-4 mb-2">
		{$t('adventures.visited_region_check')}
	</h1>
	<p>
		{$t('adventures.visited_region_check_desc')}
	</p>
	<p>{$t('adventures.update_visited_regions_disclaimer')}</p>

	<button class="btn btn-neutral mt-2 mb-2" on:click={checkVisitedRegions}
		>{$t('adventures.update_visited_regions')}</button
	>
</div>

<small class="text-center"
	><b>For Debug Use:</b> UUID={user.uuid} | Staff user: {user.is_staff}</small
>

<svelte:head>
	<title>User Settings | AdventureLog</title>
	<meta
		name="description"
		content="Update your user account settings here. Change your username, first name, last name, and profile icon."
	/>
</svelte:head>
