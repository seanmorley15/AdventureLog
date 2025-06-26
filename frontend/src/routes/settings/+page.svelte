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
	import GoogleMapsLogo from '$lib/assets/google_maps.svg';

	export let data;
	console.log(data);
	let user: User;
	let emails: typeof data.props.emails;
	if (data.user) {
		user = data.user;
		emails = data.props.emails;
	}

	let new_email: string = '';
	let public_url: string = data.props.publicUrl;
	let immichIntegration = data.props.immichIntegration;
	let googleMapsEnabled = data.props.googleMapsEnabled;
	let activeSection: string = 'profile';
	let acknowledgeRestoreOverride: boolean = false;

	let newImmichIntegration: ImmichIntegration = {
		server_url: '',
		api_key: '',
		id: '',
		copy_locally: true
	};

	let isMFAModalOpen: boolean = false;

	const sections = [
		{ id: 'profile', icon: '👤', label: () => $t('navbar.profile') },
		{ id: 'security', icon: '🔒', label: () => $t('settings.security') },
		{ id: 'emails', icon: '📧', label: () => $t('settings.emails') },
		{ id: 'integrations', icon: '🔗', label: () => $t('settings.integrations') },
		{ id: 'import_export', icon: '📦', label: () => $t('settings.backup_restore') },
		{ id: 'admin', icon: '⚙️', label: () => $t('settings.admin') },
		{ id: 'advanced', icon: '🛠️', label: () => $t('settings.advanced') }
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

	function handleImmichError(data: {
		code: string;
		details: any;
		message: any;
		error: any;
		server_url: any[];
		api_key: any[];
	}) {
		if (data.code === 'immich.connection_failed') {
			return `${$t('immich.connection_error')}: ${data.details || data.message}`;
		} else if (data.code === 'immich.integration_exists') {
			return $t('immich.integration_already_exists');
		} else if (data.code === 'immich.integration_not_found') {
			return $t('immich.integration_not_found');
		} else if (data.error && data.message) {
			return data.message;
		} else {
			// Handle validation errors
			const errors = [];
			if (data.server_url) errors.push(`Server URL: ${data.server_url.join(', ')}`);
			if (data.api_key) errors.push(`API Key: ${data.api_key.join(', ')}`);
			return errors.length > 0
				? `${$t('immich.validation_error')}: ${errors.join('; ')}`
				: $t('immich.immich_error');
		}
	}

	async function enableImmichIntegration() {
		const isUpdate = !!immichIntegration?.id;
		const url = isUpdate
			? `/api/integrations/immich/${immichIntegration?.id ?? ''}/`
			: '/api/integrations/immich/';
		const method = isUpdate ? 'PUT' : 'POST';

		try {
			const res = await fetch(url, {
				method,
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(newImmichIntegration)
			});

			const data = await res.json();

			if (res.ok) {
				addToast('success', $t(isUpdate ? 'immich.immich_updated' : 'immich.immich_enabled'));
				immichIntegration = data;
			} else {
				addToast('error', handleImmichError(data));
			}
		} catch (error) {
			addToast('error', $t('immich.network_error'));
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
					<h1 class="text-4xl font-bold bg-clip-text text-primary pb-1">
						{$t('settings.settings_page')}
					</h1>
				</div>
			</div>
		</div>
	</div>

	<div class="container mx-auto px-6 py-8 max-w-7xl">
		<div class="flex flex-col lg:flex-row gap-8">
			<!-- Sidebar Navigation -->
			<div class="lg:w-1/4">
				<div class="bg-base-100 rounded-2xl shadow-xl p-6 sticky top-8">
					<h3 class="font-semibold text-lg mb-4 text-base-content/80">
						{$t('settings.settings_menu')}
					</h3>
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
									<span class="font-medium">{section.label()}</span>
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
									<h2 class="text-2xl font-bold">{$t('settings.profile_info')}</h2>
									<p class="text-base-content/70">
										{$t('settings.profile_info_desc')}
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
										<!-- svelte-ignore a11y-label-has-associated-control -->
										<label class="label">
											<span class="label-text font-medium">{$t('auth.username')}</span>
										</label>
										<input
											type="text"
											bind:value={user.username}
											name="username"
											class="input input-bordered input-primary focus:input-primary"
											placeholder={$t('settings.enter_username')}
										/>
									</div>

									<div class="form-control">
										<!-- svelte-ignore a11y-label-has-associated-control -->
										<label class="label">
											<span class="label-text font-medium">{$t('auth.first_name')}</span>
										</label>
										<input
											type="text"
											bind:value={user.first_name}
											name="first_name"
											class="input input-bordered input-primary focus:input-primary"
											placeholder={$t('settings.enter_first_name')}
										/>
									</div>

									<div class="form-control">
										<!-- svelte-ignore a11y-label-has-associated-control -->
										<label class="label">
											<span class="label-text font-medium">{$t('auth.last_name')}</span>
										</label>
										<input
											type="text"
											bind:value={user.last_name}
											name="last_name"
											class="input input-bordered input-primary focus:input-primary"
											placeholder={$t('settings.enter_last_name')}
										/>
									</div>

									<div class="form-control">
										<!-- svelte-ignore a11y-label-has-associated-control -->
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
												{$t('settings.public_profile_desc')}
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
										<h2 class="text-2xl font-bold">{$t('settings.change_password')}</h2>
										<p class="text-base-content/70">
											{$t('settings.pass_change_desc')}
										</p>
									</div>
								</div>

								<form method="post" action="?/changePassword" use:enhance class="space-y-6">
									{#if user.has_password}
										<div class="form-control">
											<!-- svelte-ignore a11y-label-has-associated-control -->
											<label class="label">
												<span class="label-text font-medium">{$t('settings.current_password')}</span
												>
											</label>
											<input
												type="password"
												name="current_password"
												class="input input-bordered input-primary focus:input-primary"
												placeholder={$t('settings.enter_current_password')}
											/>
										</div>
									{/if}

									<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
										<div class="form-control">
											<!-- svelte-ignore a11y-label-has-associated-control -->
											<label class="label">
												<span class="label-text font-medium">{$t('settings.new_password')}</span>
											</label>
											<input
												type="password"
												name="password1"
												class="input input-bordered input-primary focus:input-primary"
												placeholder={$t('settings.enter_new_password')}
											/>
										</div>

										<div class="form-control">
											<!-- svelte-ignore a11y-label-has-associated-control -->
											<label class="label">
												<span class="label-text font-medium"
													>{$t('settings.confirm_new_password')}</span
												>
											</label>
											<input
												type="password"
												name="password2"
												class="input input-bordered input-primary focus:input-primary"
												placeholder={$t('settings.confirm_new_password')}
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
										<h2 class="text-2xl font-bold">{$t('settings.mfa_page_title')}</h2>
										<p class="text-base-content/70">
											{$t('settings.mfa_desc')}
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
												✅ {$t('settings.enabled')}
											{:else}
												❌ {$t('settings.disabled')}
											{/if}
										</div>
										<span class="font-medium">
											{data.props.authenticators
												? $t('settings.mfa_is_enabled')
												: $t('settings.mfa_not_enabled')}
										</span>
									</div>

									{#if !data.props.authenticators}
										{#if !emails.some((e) => e.verified)}
											<div
												class="tooltip tooltip-warning"
												data-tip={$t('settings.no_verified_email_warning')}
											>
												<button class="btn btn-disabled">{$t('settings.enable_mfa')}</button>
											</div>
										{:else}
											<button class="btn btn-primary" on:click={() => (isMFAModalOpen = true)}>
												{$t('settings.enable_mfa')}
											</button>
										{/if}
									{:else}
										<button class="btn btn-warning" on:click={disableMfa}>
											{$t('settings.disable_mfa')}
										</button>
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
											<h2 class="text-2xl font-bold">{$t('settings.social_auth')}</h2>
											<p class="text-base-content/70">
												{$t('settings.social_auth_desc_1')}
											</p>
										</div>
									</div>

									<div class="space-y-6">
										<div class="p-4 bg-base-200 rounded-xl">
											<div class="flex items-center justify-between">
												<div>
													<h3 class="font-semibold">{$t('settings.password_auth')}</h3>
													<p class="text-sm text-base-content/70">
														{user.disable_password
															? $t('settings.password_login_disabled')
															: $t('settings.password_login_enabled')}
													</p>
												</div>
												<div class="flex items-center gap-4">
													<div
														class="badge {user.disable_password ? 'badge-error' : 'badge-success'}"
													>
														{user.disable_password
															? $t('settings.disabled')
															: $t('settings.enabled')}
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
									<h2 class="text-2xl font-bold">{$t('settings.email_management')}</h2>
									<p class="text-base-content/70">
										{$t('settings.email_management_desc')}
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
															<div class="badge badge-success gap-1">
																✅ {$t('settings.verified')}
															</div>
														{:else}
															<div class="badge badge-error gap-1">❌ Not Verified</div>
														{/if}
														{#if email.primary}
															<div class="badge badge-primary gap-1">
																⭐ {$t('settings.primary')}
															</div>
														{/if}
													</div>
												</div>
												<div class="flex gap-2">
													{#if !email.verified}
														<button
															class="btn btn-sm btn-secondary"
															on:click={() => verifyEmail(email)}
														>
															{$t('settings.verify')}
														</button>
													{/if}
													{#if !email.primary && email.verified}
														<button
															class="btn btn-sm btn-primary"
															on:click={() => primaryEmail(email)}
														>
															{$t('settings.make_primary')}
														</button>
													{/if}
													<button
														class="btn btn-sm btn-warning"
														on:click={() => removeEmail(email)}
													>
														{$t('adventures.remove')}
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
							<div class="divider">{$t('settings.add_new_email')}</div>
							<form class="space-y-4" on:submit|preventDefault={addEmail}>
								<div class="form-control">
									<!-- svelte-ignore a11y-label-has-associated-control -->
									<label class="label">
										<span class="label-text font-medium"
											>{$t('settings.add_new_email_address')}</span
										>
									</label>
									<input
										type="email"
										bind:value={new_email}
										class="input input-bordered input-primary focus:input-primary"
										placeholder={$t('settings.enter_new_email')}
										required
									/>
								</div>
								<button class="btn btn-primary w-full"> ➕ {$t('settings.add_email')} </button>
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
									<h2 class="text-2xl font-bold">{$t('settings.integrations')}</h2>
									<p class="text-base-content/70">
										{$t('settings.integrations_desc')}
									</p>
								</div>
							</div>

							<!-- Immich Integration -->
							<div class="p-6 bg-base-200 rounded-xl mb-4">
								<div class="flex items-center gap-4 mb-4">
									<img src={ImmichLogo} alt="Immich" class="w-8 h-8" />
									<div>
										<h3 class="text-xl font-bold">Immich</h3>
										<p class="text-sm text-base-content/70">
											{$t('immich.immich_integration_desc')}
										</p>
									</div>
									{#if immichIntegration}
										<div class="badge badge-success ml-auto">{$t('settings.connected')}</div>
									{:else}
										<div class="badge badge-error ml-auto">{$t('settings.disconnected')}</div>
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
											✏️ {$t('lodging.edit')}
										</button>
										<button class="btn btn-error" on:click={disableImmichIntegration}>
											❌ {$t('immich.disable')}
										</button>
									</div>
								{/if}

								{#if !immichIntegration || newImmichIntegration.id}
									<div class="space-y-4">
										<div class="form-control">
											<!-- svelte-ignore a11y-label-has-associated-control -->
											<label class="label">
												<span class="label-text font-medium">{$t('immich.server_url')}</span>
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
											<!-- svelte-ignore a11y-label-has-associated-control -->
											<label class="label">
												<span class="label-text font-medium">{$t('immich.api_key')}</span>
											</label>
											<input
												type="password"
												bind:value={newImmichIntegration.api_key}
												class="input input-bordered input-primary focus:input-primary"
												placeholder={$t('immich.api_key_placeholder')}
											/>
										</div>

										<!-- Toggle for copy_locally -->
										<div class="form-control">
											<label class="label cursor-pointer justify-start gap-4">
												<input
													type="checkbox"
													bind:checked={newImmichIntegration.copy_locally}
													class="toggle toggle-primary"
												/>
												<div>
													<span class="label-text font-medium">
														{$t('immich.copy_locally') || 'Copy Locally'}
													</span>
													<p class="text-sm text-base-content/70">
														{$t('immich.copy_locally_desc') ||
															'If enabled, files will be copied locally.'}
													</p>
												</div>
											</label>
										</div>

										<button on:click={enableImmichIntegration} class="btn btn-primary w-full">
											{!immichIntegration?.id
												? `🔗 ${$t('immich.enable_integration')}`
												: `💾 ${$t('immich.update_integration')}`}
										</button>
									</div>
								{/if}

								<div class="mt-4 p-4 bg-info/10 rounded-lg">
									<p class="text-sm">
										📖 {$t('immich.need_help')}
										<a
											class="link link-primary"
											href="https://adventurelog.app/docs/configuration/immich_integration.html"
											target="_blank">{$t('navbar.documentation')}</a
										>
									</p>
								</div>
							</div>

							<!-- Google maps integration - displayt only if its connected -->
							<div class="p-6 bg-base-200 rounded-xl">
								<div class="flex items-center gap-4 mb-4">
									<img src={GoogleMapsLogo} alt="Google Maps" class="w-8 h-8" />
									<div>
										<h3 class="text-xl font-bold">Google Maps</h3>
										<p class="text-sm text-base-content/70">
											{$t('google_maps.google_maps_integration_desc')}
										</p>
									</div>
									{#if googleMapsEnabled}
										<div class="badge badge-success ml-auto">{$t('settings.connected')}</div>
									{:else}
										<div class="badge badge-error ml-auto">{$t('settings.disconnected')}</div>
									{/if}
								</div>
								<div class="mt-4 p-4 bg-info/10 rounded-lg">
									<p class="text-sm">
										📖 {$t('immich.need_help')}
										<a
											class="link link-primary"
											href="https://adventurelog.app/docs/configuration/google_maps_integration.html"
											target="_blank">{$t('navbar.documentation')}</a
										>
									</p>
								</div>
							</div>
						</div>
					{/if}

					<!-- import export -->
					{#if activeSection === 'import_export'}
						<div class="bg-base-100 rounded-2xl shadow-xl p-8">
							<div class="flex items-center gap-4 mb-6">
								<div class="p-3 bg-accent/10 rounded-xl">
									<span class="text-2xl">📦</span>
								</div>
								<div>
									<div>
										<h2 class="text-2xl font-bold">{$t('settings.backup_restore')}</h2>
										<p class="text-base-content/70">
											{$t('settings.backup_restore_desc')}
										</p>
									</div>
								</div>
							</div>

							<!-- Backup Coverage -->
							<div class="bg-base-200 rounded-xl p-4 mb-6">
								<h4 class="text-sm font-semibold mb-3 text-base-content/70">
									{$t('settings.whats_included')}
								</h4>
								<div class="grid grid-cols-2 gap-4 text-sm">
									<!-- Backed Up -->
									<div class="space-y-2">
										<div class="flex items-center justify-between">
											<span>📍 {$t('locations.locations')}</span>
											<span>✅</span>
										</div>
										<div class="flex items-center justify-between">
											<span>🚶 {$t('adventures.visits')}</span>
											<span>✅</span>
										</div>
										<div class="flex items-center justify-between">
											<span>📚 {$t('navbar.collections')}</span>
											<span>✅</span>
										</div>
										<div class="flex items-center justify-between">
											<span>🖼️ {$t('settings.media')}</span>
											<span>✅</span>
										</div>
										<div class="flex items-center justify-between">
											<span>🌍 {$t('settings.world_travel_visits')}</span>
											<span>✅</span>
										</div>
									</div>
									<!-- Not Backed Up -->
									<div class="space-y-2">
										<div class="flex items-center justify-between">
											<span>⚙️ {$t('navbar.settings')}</span>
											<span>❌</span>
										</div>
										<div class="flex items-center justify-between">
											<span>👤 {$t('navbar.profile')}</span>
											<span>❌</span>
										</div>
										<div class="flex items-center justify-between">
											<span>🔗 {$t('settings.integrations_settings')}</span>
											<span>❌</span>
										</div>
										<div class="flex items-center justify-between opacity-30">
											<span></span>
											<span></span>
										</div>
									</div>
								</div>
							</div>

							<div class="space-y-6">
								<!-- Backup Data -->
								<div class="p-6 bg-base-200 rounded-xl">
									<h3 class="text-lg font-semibold mb-4">📤 {$t('settings.backup_your_data')}</h3>
									<p class="text-base-content/70 mb-4">
										{$t('settings.backup_your_data_desc')}
									</p>
									<div class="flex gap-4">
										<a class="btn btn-primary" href="/api/backup/export">
											💾 {$t('settings_download_backup')}
										</a>
									</div>
								</div>

								<!-- Restore Data -->
								<div class="p-6 bg-base-200 rounded-xl">
									<h3 class="text-lg font-semibold mb-4">📥 {$t('settings.restore_data')}</h3>
									<p class="text-base-content/70 mb-4">
										{$t('settings.restore_data_desc')}
									</p>

									<!-- Warning Alert -->
									<div class="alert alert-warning mb-4">
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
										<div>
											<h4 class="font-bold">⚠️ {$t('settings.data_override_warning')}</h4>
											<p class="text-sm">
												{$t('settings.data_override_warning_desc')}
											</p>
										</div>
									</div>

									<!-- File Upload Form -->
									<form
										method="post"
										action="?/restoreData"
										use:enhance
										enctype="multipart/form-data"
										class="space-y-4"
									>
										<div class="form-control">
											<!-- svelte-ignore a11y-label-has-associated-control -->
											<label class="label">
												<span class="label-text font-medium"
													>{$t('settings.select_backup_file')}</span
												>
											</label>
											<input
												type="file"
												name="file"
												class="file-input file-input-bordered file-input-primary w-full"
												accept=".zip"
												required
											/>
										</div>

										<!-- Acknowledgment Checkbox -->
										<div class="form-control">
											<label class="label cursor-pointer justify-start gap-4">
												<input
													type="checkbox"
													name="confirm"
													value="yes"
													class="checkbox checkbox-warning"
													required
													bind:checked={acknowledgeRestoreOverride}
												/>
												<div>
													<span class="label-text font-medium text-warning"
														>{$t('settings.data_override_acknowledge')}</span
													>
													<p class="text-xs text-base-content/60 mt-1">
														{$t('settings.data_override_acknowledge_desc')}
													</p>
												</div>
											</label>
										</div>

										{#if $page.form?.message && $page.form?.message.includes('restore')}
											<div class="alert alert-error">
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
														d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
													/>
												</svg>
												<span>{$t($page.form?.message)}</span>
											</div>
										{/if}

										<div class="flex gap-4">
											<button
												type="submit"
												class="btn btn-warning"
												disabled={!acknowledgeRestoreOverride}
											>
												🚀 {$t('settings.restore_data')}
											</button>
										</div>
									</form>
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
									<h2 class="text-2xl font-bold">{$t('settings.administration')}</h2>
									<p class="text-base-content/70">{$t('settings.administration_desc')}</p>
								</div>
							</div>

							<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
								<div
									class="card bg-gradient-to-br from-primary/10 to-secondary/10 border border-primary/20"
								>
									<div class="card-body text-center">
										<div class="text-4xl mb-4">🛠️</div>
										<h3 class="card-title justify-center">{$t('navbar.admin_panel')}</h3>
										<p class="text-sm text-base-content/70 mb-4">
											{$t('settings.admin_panel_desc')}
										</p>
										<a class="btn btn-primary" href={`${public_url}/admin/`} target="_blank">
											{$t('settings.launch_administration_panel')}
										</a>
									</div>
								</div>

								<div
									class="card bg-gradient-to-br from-info/10 to-success/10 border border-info/20"
								>
									<div class="card-body text-center">
										<div class="text-4xl mb-4">📍</div>
										<h3 class="card-title justify-center">{$t('settings.region_updates')}</h3>
										<p class="text-sm text-base-content/70 mb-4">
											{$t('settings.region_updates_desc')}
										</p>
										<button class="btn btn-info" on:click={checkVisitedRegions}>
											{$t('adventures.update_visited_regions')}
										</button>
									</div>
								</div>
							</div>
						</div>
					{:else if activeSection === 'admin' && !user.is_staff}
						<div class="bg-base-100 rounded-2xl shadow-xl p-8 text-center">
							<div class="text-6xl mb-4">🔒</div>
							<h2 class="text-2xl font-bold mb-2">{$t('settings.access_restricted')}</h2>
							<p class="text-base-content/70">
								{$t('settings.access_restricted_desc')}
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
										<h2 class="text-2xl font-bold">{$t('settings.advanced_settings')}</h2>
										<p class="text-base-content/70">
											{$t('settings.advanced_settings_desc')}
										</p>
									</div>
								</div>

								<div class="space-y-6">
									<!-- Social Auth Configuration -->
									<div class="p-6 bg-base-200 rounded-xl">
										<h3 class="text-lg font-semibold mb-4">{$t('settings.social_auth_setup')}</h3>
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
										<h3 class="text-lg font-semibold mb-4">{$t('settings.debug_information')}</h3>
										<div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm font-mono">
											<div class="p-3 bg-base-300 rounded-lg">
												<span class="text-base-content/60">UUID:</span>
												<br />
												<span class="text-primary font-semibold">{user.uuid}</span>
											</div>
											<div class="p-3 bg-base-300 rounded-lg">
												<span class="text-base-content/60">{$t('settings.staff_status')}:</span>
												<br />
												<span class="badge {user.is_staff ? 'badge-success' : 'badge-error'}">
													{user.is_staff ? $t('settings.staff_user') : $t('settings.regular_user')}
												</span>
											</div>
											<div class="p-3 bg-base-300 rounded-lg">
												<span class="text-base-content/60">{$t('settings.app_version')}:</span>
												<br />
												<span class="text-secondary font-semibold">{appTitle} {appVersion}</span>
											</div>
											<div class="p-3 bg-base-300 rounded-lg">
												<span class="text-base-content/60">Profile Type:</span>
												<br />
												<span class="badge {user.public_profile ? 'badge-info' : 'badge-ghost'}">
													{user.public_profile ? $t('adventures.public') : $t('adventures.private')}
												</span>
											</div>
										</div>
									</div>

									<!-- Quick Actions -->
									<div class="p-6 bg-base-200 rounded-xl">
										<h3 class="text-lg font-semibold mb-4">{$t('settings.quick_actions')}</h3>
										<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
											<button class="btn btn-outline btn-info" on:click={checkVisitedRegions}>
												📍 {$t('adventures.update_visited_regions')}
											</button>
											{#if user.is_staff}
												<a
													class="btn btn-outline btn-primary"
													href={`${public_url}/admin/`}
													target="_blank"
												>
													⚙️ {$t('settings.launch_administration_panel')}
												</a>
											{/if}
										</div>
									</div>

									<!-- Developer message and thanks -->
									<div class="p-6 bg-base-200 rounded-xl">
										<div class="text-center space-y-3">
											<h4 class="font-medium">{$t('about.about')} AdventureLog</h4>
											<p>
												{$t('about.license')}
											</p>
											<p class="text-sm text-base-content/70">
												© {copyrightYear}
												<a href="https://seanmorley.com" target="_blank" class="link">Sean Morley</a
												>. {$t('settings.all_rights_reserved')}
											</p>
											<div class="flex justify-center gap-3 mt-2">
												<a
													href="https://github.com/seanmorley15/AdventureLog"
													target="_blank"
													class="link link-primary text-sm"
												>
													GitHub
												</a>
												<a
													href="https://github.com/seanmorley15/AdventureLog/blob/main/LICENSE"
													target="_blank"
													class="link link-secondary text-sm"
												>
													{$t('settings.license')}
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
