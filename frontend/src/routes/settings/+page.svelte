<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { addToast } from '$lib/toasts';
	import type { ImmichIntegration, User } from '$lib/types.js';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { t } from 'svelte-i18n';
	import TotpModal from '$lib/components/TOTPModal.svelte';
	import { appTitle, appVersion, copyrightYear } from '$lib/config.js';
	import ImmichLogo from '$lib/assets/immich.svg';

	export let data;
	console.log(data);
	let user: User;
	let emails: typeof data.props.emails;
	if (data.user) {
		user = data.user;
		emails = data.props.emails;
	}

	let new_password_disable_setting: boolean = false;
	let new_email: string = '';
	let public_url: string = data.props.publicUrl;
	let immichIntegration = data.props.immichIntegration;
	let activeSection: string = 'profile';

	let newImmichIntegration: ImmichIntegration = {
		server_url: '',
		api_key: '',
		id: ''
	};

	let isMFAModalOpen: boolean = false;

	const sections = [
		{ id: 'profile', icon: '👤', label: 'Profile' },
		{ id: 'security', icon: '🔒', label: 'Security' },
		{ id: 'emails', icon: '📧', label: 'Emails' },
		{ id: 'integrations', icon: '🔗', label: 'Integrations' },
		{ id: 'admin', icon: '⚙️', label: 'Admin' },
		{ id: 'advanced', icon: '🛠️', label: 'Advanced' }
	];

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
			addToast(
				'success',
				`${data.new_regions} ${$t('adventures.regions_updated')}. ${data.new_cities} ${$t('adventures.cities_updated')}.`
			);
		} else {
			addToast('error', $t('adventures.error_updating_regions'));
		}
	}

	async function removeEmail(email: { email: any; verified?: boolean; primary?: boolean }) {
		let res = await fetch('/auth/browser/v1/account/email', {
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

	async function disablePassword() {
		if (user.disable_password) {
			let res = await fetch('/auth/disable-password/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			});
			if (res.ok) {
				addToast('success', $t('settings.password_disabled'));
			} else {
				addToast('error', $t('settings.password_disabled_error'));
				user.disable_password = false;
			}
		} else {
			let res = await fetch('/auth/disable-password/', {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json'
				}
			});
			if (res.ok) {
				addToast('success', $t('settings.password_enabled'));
			} else {
				addToast('error', $t('settings.password_enabled_error'));
				user.disable_password = true;
			}
		}
	}

	async function verifyEmail(email: { email: any; verified?: boolean; primary?: boolean }) {
		let res = await fetch('/auth/browser/v1/account/email', {
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
		let res = await fetch('/auth/browser/v1/account/email', {
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
		let res = await fetch('/auth/browser/v1/account/email', {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ email: email.email, primary: true })
		});
		if (res.ok) {
			addToast('success', $t('settings.email_set_primary'));
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
		const res = await fetch('/auth/browser/v1/account/authenticators/totp', {
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

<div class="min-h-screen bg-gradient-to-br from-base-200 to-base-300">
	<!-- Header -->
	<div class="bg-base-100 shadow-lg border-b border-base-300">
		<div class="container mx-auto px-6 py-8">
			<div class="flex items-center justify-between">
				<div>
					<h1
						class="text-4xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
					>
						{$t('settings.settings_page')}
					</h1>
					<p class="text-base-content/70 mt-2">Manage your account preferences and integrations</p>
				</div>
			</div>
		</div>
	</div>

	<div class="container mx-auto px-6 py-8 max-w-7xl">
		<div class="flex flex-col lg:flex-row gap-8">
			<!-- Sidebar Navigation -->
			<div class="lg:w-1/4">
				<div class="bg-base-100 rounded-2xl shadow-xl p-6 sticky top-8">
					<h3 class="font-semibold text-lg mb-4 text-base-content/80">Settings Menu</h3>
					<ul class="menu menu-vertical w-full space-y-1">
						{#each sections as section}
							<li>
								<button
									class="flex items-center gap-3 p-3 rounded-xl transition-all duration-200 {activeSection ===
									section.id
										? 'bg-primary text-primary-content shadow-lg'
										: 'hover:bg-base-200'}"
									on:click={() => (activeSection = section.id)}
								>
									<span class="text-xl">{section.icon}</span>
									<span class="font-medium">{section.label}</span>
								</button>
							</li>
						{/each}
					</ul>
				</div>
			</div>

			<!-- Main Content -->
			<div class="lg:w-3/4">
				<div class="space-y-8">
					<!-- Profile Section -->
					{#if activeSection === 'profile'}
						<div class="bg-base-100 rounded-2xl shadow-xl p-8">
							<div class="flex items-center gap-4 mb-6">
								<div class="p-3 bg-primary/10 rounded-xl">
									<span class="text-2xl">👤</span>
								</div>
								<div>
									<h2 class="text-2xl font-bold">Profile Information</h2>
									<p class="text-base-content/70">
										Update your personal details and profile picture
									</p>
								</div>
							</div>

							<form
								method="post"
								action="?/changeDetails"
								use:enhance
								enctype="multipart/form-data"
								class="space-y-6"
							>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
									<div class="form-control">
										<label class="label">
											<span class="label-text font-medium">{$t('auth.username')}</span>
										</label>
										<input
											type="text"
											bind:value={user.username}
											name="username"
											class="input input-bordered input-primary focus:input-primary"
											placeholder="Enter your username"
										/>
									</div>

									<div class="form-control">
										<label class="label">
											<span class="label-text font-medium">{$t('auth.first_name')}</span>
										</label>
										<input
											type="text"
											bind:value={user.first_name}
											name="first_name"
											class="input input-bordered input-primary focus:input-primary"
											placeholder="Enter your first name"
										/>
									</div>

									<div class="form-control">
										<label class="label">
											<span class="label-text font-medium">{$t('auth.last_name')}</span>
										</label>
										<input
											type="text"
											bind:value={user.last_name}
											name="last_name"
											class="input input-bordered input-primary focus:input-primary"
											placeholder="Enter your last name"
										/>
									</div>

									<div class="form-control">
										<label class="label">
											<span class="label-text font-medium">{$t('auth.profile_picture')}</span>
										</label>
										<input
											type="file"
											name="profile_pic"
											class="file-input file-input-bordered file-input-primary"
											accept="image/*"
										/>
									</div>
								</div>

								<div class="form-control">
									<label class="label cursor-pointer justify-start gap-4">
										<input
											type="checkbox"
											bind:checked={user.public_profile}
											name="public_profile"
											class="toggle toggle-primary"
										/>
										<div>
											<span class="label-text font-medium">{$t('auth.public_profile')}</span>
											<p class="text-sm text-base-content/60">
												Make your profile visible to other users
											</p>
										</div>
									</label>
								</div>

								<button class="btn btn-primary btn-wide">
									<span class="loading loading-spinner loading-sm hidden"></span>
									{$t('settings.update')}
								</button>
							</form>
						</div>
					{/if}

					<!-- Security Section -->
					{#if activeSection === 'security'}
						<div class="space-y-8">
							<!-- Password Change -->
							<div class="bg-base-100 rounded-2xl shadow-xl p-8">
								<div class="flex items-center gap-4 mb-6">
									<div class="p-3 bg-warning/10 rounded-xl">
										<span class="text-2xl">🔐</span>
									</div>
									<div>
										<h2 class="text-2xl font-bold">Change Password</h2>
										<p class="text-base-content/70">
											Update your account password for better security
										</p>
									</div>
								</div>

								<form method="post" action="?/changePassword" use:enhance class="space-y-6">
									{#if user.has_password}
										<div class="form-control">
											<label class="label">
												<span class="label-text font-medium">{$t('settings.current_password')}</span
												>
											</label>
											<input
												type="password"
												name="current_password"
												class="input input-bordered input-primary focus:input-primary"
												placeholder="Enter current password"
											/>
										</div>
									{/if}

									<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
										<div class="form-control">
											<label class="label">
												<span class="label-text font-medium">{$t('settings.new_password')}</span>
											</label>
											<input
												type="password"
												name="password1"
												class="input input-bordered input-primary focus:input-primary"
												placeholder="Enter new password"
											/>
										</div>

										<div class="form-control">
											<label class="label">
												<span class="label-text font-medium"
													>{$t('settings.confirm_new_password')}</span
												>
											</label>
											<input
												type="password"
												name="password2"
												class="input input-bordered input-primary focus:input-primary"
												placeholder="Confirm new password"
											/>
										</div>
									</div>

									{#if $page.form?.message}
										<div class="alert alert-warning">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="stroke-current shrink-0 h-6 w-6"
												fill="none"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
												/>
											</svg>
											<span>{$t($page.form?.message)}</span>
										</div>
									{/if}

									<div
										class="tooltip tooltip-warning"
										data-tip={$t('settings.password_change_lopout_warning')}
									>
										<button class="btn btn-warning">
											🔑 {$t('settings.password_change')}
										</button>
									</div>
								</form>
							</div>

							<!-- MFA Section -->
							<div class="bg-base-100 rounded-2xl shadow-xl p-8">
								<div class="flex items-center gap-4 mb-6">
									<div class="p-3 bg-success/10 rounded-xl">
										<span class="text-2xl">🛡️</span>
									</div>
									<div>
										<h2 class="text-2xl font-bold">Two-Factor Authentication</h2>
										<p class="text-base-content/70">
											Add an extra layer of security to your account
										</p>
									</div>
								</div>

								<div class="flex items-center justify-between p-4 bg-base-200 rounded-xl">
									<div class="flex items-center gap-4">
										<div
											class="badge {data.props.authenticators
												? 'badge-success'
												: 'badge-error'} gap-2"
										>
											{#if data.props.authenticators}
												✅ Enabled
											{:else}
												❌ Disabled
											{/if}
										</div>
										<span class="font-medium">
											{data.props.authenticators
												? 'MFA is currently enabled'
												: 'MFA is not enabled'}
										</span>
									</div>

									{#if !data.props.authenticators}
										{#if !emails.some((e) => e.verified)}
											<div
												class="tooltip tooltip-warning"
												data-tip="You need a verified email first"
											>
												<button class="btn btn-disabled">Enable MFA</button>
											</div>
										{:else}
											<button class="btn btn-primary" on:click={() => (isMFAModalOpen = true)}>
												Enable MFA
											</button>
										{/if}
									{:else}
										<button class="btn btn-warning" on:click={disableMfa}> Disable MFA </button>
									{/if}
								</div>

								{#if !emails.some((e) => e.verified)}
									<div class="alert alert-warning mt-4">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											class="stroke-current shrink-0 h-6 w-6"
											fill="none"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
											/>
										</svg>
										<span>{$t('settings.no_verified_email_warning')}</span>
									</div>
								{/if}
							</div>

							<!-- Social Auth & Password Disable -->
							{#if data.props.socialProviders && data.props.socialProviders.length > 0}
								<div class="bg-base-100 rounded-2xl shadow-xl p-8">
									<div class="flex items-center gap-4 mb-6">
										<div class="p-3 bg-info/10 rounded-xl">
											<span class="text-2xl">🔗</span>
										</div>
										<div>
											<h2 class="text-2xl font-bold">Social Authentication</h2>
											<p class="text-base-content/70">
												Manage social login options and password settings
											</p>
										</div>
									</div>

									<div class="space-y-6">
										<div class="p-4 bg-base-200 rounded-xl">
											<div class="flex items-center justify-between">
												<div>
													<h3 class="font-semibold">Password Authentication</h3>
													<p class="text-sm text-base-content/70">
														{user.disable_password
															? 'Password login is disabled'
															: 'Password login is enabled'}
													</p>
												</div>
												<div class="flex items-center gap-4">
													<div
														class="badge {user.disable_password ? 'badge-error' : 'badge-success'}"
													>
														{user.disable_password ? 'Disabled' : 'Enabled'}
													</div>
													<input
														type="checkbox"
														bind:checked={user.disable_password}
														on:change={disablePassword}
														class="toggle toggle-primary"
													/>
												</div>
											</div>
											{#if user.disable_password}
												<div class="alert alert-warning mt-4">
													<svg
														xmlns="http://www.w3.org/2000/svg"
														class="stroke-current shrink-0 h-6 w-6"
														fill="none"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
														/>
													</svg>
													<span>{$t('settings.password_disable_warning')}</span>
												</div>
											{/if}
										</div>

										<a
											class="btn btn-outline btn-primary w-full"
											href={`${public_url}/accounts/social/connections/`}
											target="_blank"
										>
											🔗 {$t('settings.launch_account_connections')}
										</a>
									</div>
								</div>
							{/if}
						</div>
					{/if}

					<!-- Emails Section -->
					{#if activeSection === 'emails'}
						<div class="bg-base-100 rounded-2xl shadow-xl p-8">
							<div class="flex items-center gap-4 mb-6">
								<div class="p-3 bg-secondary/10 rounded-xl">
									<span class="text-2xl">📧</span>
								</div>
								<div>
									<h2 class="text-2xl font-bold">Email Management</h2>
									<p class="text-base-content/70">
										Manage your email addresses and verification status
									</p>
								</div>
							</div>

							<!-- Current Emails -->
							{#if emails.length > 0}
								<div class="space-y-4 mb-8">
									{#each emails as email}
										<div class="p-4 bg-base-200 rounded-xl">
											<div class="flex items-center justify-between flex-wrap gap-4">
												<div class="flex items-center gap-3">
													<span class="font-medium">{email.email}</span>
													<div class="flex gap-2">
														{#if email.verified}
															<div class="badge badge-success gap-1">✅ Verified</div>
														{:else}
															<div class="badge badge-error gap-1">❌ Not Verified</div>
														{/if}
														{#if email.primary}
															<div class="badge badge-primary gap-1">⭐ Primary</div>
														{/if}
													</div>
												</div>
												<div class="flex gap-2">
													{#if !email.verified}
														<button
															class="btn btn-sm btn-secondary"
															on:click={() => verifyEmail(email)}
														>
															Verify
														</button>
													{/if}
													{#if !email.primary && email.verified}
														<button
															class="btn btn-sm btn-primary"
															on:click={() => primaryEmail(email)}
														>
															Make Primary
														</button>
													{/if}
													<button
														class="btn btn-sm btn-warning"
														on:click={() => removeEmail(email)}
													>
														Remove
													</button>
												</div>
											</div>
										</div>
									{/each}
								</div>
							{:else}
								<div class="text-center py-8">
									<div class="text-6xl mb-4">📧</div>
									<p class="text-lg text-base-content/70">{$t('settings.no_email_set')}</p>
								</div>
							{/if}

							<!-- Add New Email -->
							<div class="divider">Add New Email</div>
							<form class="space-y-4" on:submit|preventDefault={addEmail}>
								<div class="form-control">
									<label class="label">
										<span class="label-text font-medium">New Email Address</span>
									</label>
									<input
										type="email"
										bind:value={new_email}
										class="input input-bordered input-primary focus:input-primary"
										placeholder="Enter new email address"
										required
									/>
								</div>
								<button class="btn btn-primary w-full"> ➕ Add Email </button>
							</form>
						</div>
					{/if}

					<!-- Integrations Section -->
					{#if activeSection === 'integrations'}
						<div class="bg-base-100 rounded-2xl shadow-xl p-8">
							<div class="flex items-center gap-4 mb-6">
								<div class="p-3 bg-accent/10 rounded-xl">
									<span class="text-2xl">🔗</span>
								</div>
								<div>
									<h2 class="text-2xl font-bold">Integrations</h2>
									<p class="text-base-content/70">
										Connect external services to enhance your experience
									</p>
								</div>
							</div>

							<!-- Immich Integration -->
							<div class="p-6 bg-base-200 rounded-xl">
								<div class="flex items-center gap-4 mb-4">
									<img src={ImmichLogo} alt="Immich" class="w-8 h-8" />
									<div>
										<h3 class="text-xl font-bold">Immich Integration</h3>
										<p class="text-sm text-base-content/70">
											Connect your Immich photo management server
										</p>
									</div>
									{#if immichIntegration}
										<div class="badge badge-success ml-auto">Connected</div>
									{:else}
										<div class="badge badge-error ml-auto">Disconnected</div>
									{/if}
								</div>

								{#if immichIntegration && !newImmichIntegration.id}
									<div class="flex gap-4 justify-center mb-4">
										<button
											class="btn btn-warning"
											on:click={() => {
												if (immichIntegration) newImmichIntegration = immichIntegration;
											}}
										>
											✏️ Edit
										</button>
										<button class="btn btn-error" on:click={disableImmichIntegration}>
											❌ Disable
										</button>
									</div>
								{/if}

								{#if !immichIntegration || newImmichIntegration.id}
									<div class="space-y-4">
										<div class="form-control">
											<label class="label">
												<span class="label-text font-medium">Server URL</span>
											</label>
											<input
												type="url"
												bind:value={newImmichIntegration.server_url}
												class="input input-bordered input-primary focus:input-primary"
												placeholder="https://immich.example.com/api"
											/>
											{#if newImmichIntegration.server_url && !newImmichIntegration.server_url.endsWith('api')}
												<div class="label">
													<span class="label-text-alt text-warning">{$t('immich.api_note')}</span>
												</div>
											{/if}
											{#if newImmichIntegration.server_url && (newImmichIntegration.server_url.indexOf('localhost') !== -1 || newImmichIntegration.server_url.indexOf('127.0.0.1') !== -1)}
												<div class="label">
													<span class="label-text-alt text-warning"
														>{$t('immich.localhost_note')}</span
													>
												</div>
											{/if}
										</div>

										<div class="form-control">
											<label class="label">
												<span class="label-text font-medium">API Key</span>
											</label>
											<input
												type="password"
												bind:value={newImmichIntegration.api_key}
												class="input input-bordered input-primary focus:input-primary"
												placeholder="Enter your Immich API key"
											/>
										</div>

										<button on:click={enableImmichIntegration} class="btn btn-primary w-full">
											{!immichIntegration?.id ? '🔗 Enable Integration' : '💾 Update Integration'}
										</button>
									</div>
								{/if}

								<div class="mt-4 p-4 bg-info/10 rounded-lg">
									<p class="text-sm text-info-content">
										📖 Need help setting this up? Check out the
										<a
											class="link link-primary"
											href="https://adventurelog.app/docs/configuration/immich_integration.html"
											target="_blank">documentation</a
										>
									</p>
								</div>
							</div>
						</div>
					{/if}

					<!-- Admin Section -->
					{#if activeSection === 'admin' && user.is_staff}
						<div class="bg-base-100 rounded-2xl shadow-xl p-8">
							<div class="flex items-center gap-4 mb-6">
								<div class="p-3 bg-error/10 rounded-xl">
									<span class="text-2xl">⚙️</span>
								</div>
								<div>
									<h2 class="text-2xl font-bold">Administration</h2>
									<p class="text-base-content/70">Administrative tools and settings</p>
								</div>
							</div>

							<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
								<div
									class="card bg-gradient-to-br from-primary/10 to-secondary/10 border border-primary/20"
								>
									<div class="card-body text-center">
										<div class="text-4xl mb-4">🛠️</div>
										<h3 class="card-title justify-center">Admin Panel</h3>
										<p class="text-sm text-base-content/70 mb-4">
											Access the full administration interface
										</p>
										<a class="btn btn-primary" href={`${public_url}/admin/`} target="_blank">
											Launch Admin Panel
										</a>
									</div>
								</div>

								<div
									class="card bg-gradient-to-br from-info/10 to-success/10 border border-info/20"
								>
									<div class="card-body text-center">
										<div class="text-4xl mb-4">📍</div>
										<h3 class="card-title justify-center">Region Updates</h3>
										<p class="text-sm text-base-content/70 mb-4">
											Update visited regions and cities
										</p>
										<button class="btn btn-info" on:click={checkVisitedRegions}>
											Update Regions
										</button>
									</div>
								</div>
							</div>
						</div>
					{:else if activeSection === 'admin' && !user.is_staff}
						<div class="bg-base-100 rounded-2xl shadow-xl p-8 text-center">
							<div class="text-6xl mb-4">🔒</div>
							<h2 class="text-2xl font-bold mb-2">Access Restricted</h2>
							<p class="text-base-content/70">
								Administrative features are only available to staff members.
							</p>
						</div>
					{/if}

					<!-- Advanced Section -->
					{#if activeSection === 'advanced'}
						<div class="space-y-8">
							<!-- Social Auth Info -->
							<div class="bg-base-100 rounded-2xl shadow-xl p-8">
								<div class="flex items-center gap-4 mb-6">
									<div class="p-3 bg-warning/10 rounded-xl">
										<span class="text-2xl">🛠️</span>
									</div>
									<div>
										<h2 class="text-2xl font-bold">Advanced Settings</h2>
										<p class="text-base-content/70">Advanced configuration and development tools</p>
									</div>
								</div>

								<div class="space-y-6">
									<!-- Social Auth Configuration -->
									<div class="p-6 bg-base-200 rounded-xl">
										<h3 class="text-lg font-semibold mb-4">Social Authentication Setup</h3>
										<p class="text-base-content/70 mb-4">{$t('settings.social_auth_desc')}</p>

										<div class="alert alert-info">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												class="stroke-info shrink-0 w-6 h-6"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
												></path>
											</svg>
											<div>
												<span>{$t('settings.social_auth_desc_2')}</span>
												<a
													href="https://adventurelog.app/docs/configuration/social_auth.html"
													class="link link-neutral font-medium"
													target="_blank">{$t('settings.documentation_link')}</a
												>
											</div>
										</div>
									</div>

									<!-- Debug Information -->
									<div class="p-6 bg-base-200 rounded-xl">
										<h3 class="text-lg font-semibold mb-4">Debug Information</h3>
										<div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm font-mono">
											<div class="p-3 bg-base-300 rounded-lg">
												<span class="text-base-content/60">User UUID:</span>
												<br />
												<span class="text-primary font-semibold">{user.uuid}</span>
											</div>
											<div class="p-3 bg-base-300 rounded-lg">
												<span class="text-base-content/60">Staff Status:</span>
												<br />
												<span class="badge {user.is_staff ? 'badge-success' : 'badge-error'}">
													{user.is_staff ? 'Staff User' : 'Regular User'}
												</span>
											</div>
											<div class="p-3 bg-base-300 rounded-lg">
												<span class="text-base-content/60">App Version:</span>
												<br />
												<span class="text-secondary font-semibold">{appTitle} {appVersion}</span>
											</div>
											<div class="p-3 bg-base-300 rounded-lg">
												<span class="text-base-content/60">Profile Type:</span>
												<br />
												<span class="badge {user.public_profile ? 'badge-info' : 'badge-ghost'}">
													{user.public_profile ? 'Public' : 'Private'}
												</span>
											</div>
										</div>
									</div>

									<!-- Quick Actions -->
									<div class="p-6 bg-base-200 rounded-xl">
										<h3 class="text-lg font-semibold mb-4">Quick Actions</h3>
										<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
											<button class="btn btn-outline btn-info" on:click={checkVisitedRegions}>
												📍 Update Visited Regions
											</button>
											{#if user.is_staff}
												<a
													class="btn btn-outline btn-primary"
													href={`${public_url}/admin/`}
													target="_blank"
												>
													⚙️ Open Admin Panel
												</a>
											{/if}
										</div>
									</div>

									<!-- Developer message and thanks -->
									<div class="p-6 bg-base-200 rounded-xl">
										<div class="text-center space-y-3">
											<h4 class="font-medium">About AdventureLog</h4>
											<p>
												AdventureLog is open-source software released under the GPL-3.0 License.
											</p>
											<p class="text-sm text-base-content/70">
												© {copyrightYear}
												<a href="https://seanmorley.com" target="_blank" class="link">Sean Morley</a
												>. All rights reserved.
											</p>
											<div class="flex justify-center gap-3 mt-2">
												<a
													href="https://github.com/seanmorley15/AdventureLog"
													target="_blank"
													class="link link-primary text-sm"
												>
													GitHub Repository
												</a>
												<a
													href="https://github.com/seanmorley15/AdventureLog/blob/main/LICENSE"
													target="_blank"
													class="link link-secondary text-sm"
												>
													License Information
												</a>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>

<svelte:head>
	<title>User Settings | AdventureLog</title>
	<meta
		name="description"
		content="Comprehensive user settings dashboard. Manage your profile, security, emails, integrations, and more in one organized interface."
	/>
</svelte:head>
