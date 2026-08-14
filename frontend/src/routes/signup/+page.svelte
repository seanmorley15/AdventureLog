<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { t } from 'svelte-i18n';
	import FileImageBox from '~icons/mdi/file-image-box';
	import ImageInfoModal from '$lib/components/ImageInfoModal.svelte';
	import PasswordRequirements from '$lib/components/auth/PasswordRequirements.svelte';
	import type { Background } from '$lib/types.js';
	import { signupLegalRequired, type SignupLegalLinks } from '$lib/signup-legal';
	import type { PasswordPolicy } from '$lib/password-policy';

	let { data } = $props();

	let quote: { quote: string; author: string } = $derived(data.props.quote);
	let background: Background = $derived(data.props.background);
	let is_disabled = $derived(data.props.is_disabled as boolean);
	let is_disabled_message = $derived(data.props.is_disabled_message as string);
	let inviteKey = $derived(data.props.invite_key as string | null);
	let inviteSignup = $derived(data.props.inviteSignup as {
		valid: boolean;
		email?: string | null;
		expired?: boolean;
		accepted?: boolean;
		registered?: boolean;
		message?: string | null;
	} | null);
	let passwordPolicy = $derived(data.props.passwordPolicy as PasswordPolicy);
	let signupLegalLinks = $derived(data.props.signupLegalLinks as SignupLegalLinks);
	let legalRequired = $derived(signupLegalRequired(signupLegalLinks));

	let isImageInfoModalOpen = $state(false);
	let password = $state('');
	let confirmPassword = $state('');
	let acceptedTerms = $state(false);
	let inviteEmail = $state('');
	$effect.pre(() => {
		if (inviteKey) {
			inviteEmail = inviteSignup?.email ?? '';
		}
	});
</script>

{#if isImageInfoModalOpen}
	<ImageInfoModal {background} on:close={() => (isImageInfoModalOpen = false)} />
{/if}

<div class="min-h-screen bg-base-200">
	{#if background.url}
		<div
			class="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-90"
			style="background-image: url('{background.url}')"
		></div>
	{/if}

	<div class="main-container relative z-10 min-h-screen flex items-center justify-center p-4">
		<div class="w-full max-w-5xl">
			<div class="card bg-base-100 shadow-2xl">
				<div class="card-body p-0">
					<div class="grid lg:grid-cols-2 min-h-[600px]">
						<div class="p-8 lg:p-12 flex flex-col justify-center">
							{#if !is_disabled}
								<div class="text-center mb-8">
									<div class="mb-4">
										<h1 class="text-3xl font-bold text-primary mb-1">AdventureLog</h1>
										<div class="w-12 h-1 bg-primary mx-auto rounded-sm"></div>
									</div>
									<h2 class="text-4xl font-bold text-base-content mb-2">
										{inviteSignup?.valid ? $t('auth.invite_signup_title') : $t('auth.signup')}
									</h2>
									{#if inviteSignup?.valid}
										<p class="text-base-content/70 mt-2">{$t('auth.invite_signup_desc')}</p>
									{/if}
								</div>

								<div class="max-w-sm mx-auto w-full">
									<form method="post" use:enhance class="space-y-4">
										{#if inviteKey}
											<input type="hidden" name="invite_key" value={inviteKey} />
										{/if}
										<div class="flex flex-col">
											<label class="field-label" for="username">{$t('auth.username')}</label>
											<input
												name="username"
												id="username"
												type="text"
												class="input w-full focus:input-primary"
												placeholder={$t('auth.enter_username')}
												autocomplete="username"
												required
											/>
										</div>

										<div class="flex flex-col">
											<label class="field-label" for="email">{$t('auth.email')}</label>
											<input
												name="email"
												id="email"
												type="email"
												class="input w-full focus:input-primary"
												placeholder={$t('auth.enter_email')}
												autocomplete="email"
												value={inviteEmail}
												readonly={!!inviteSignup?.valid}
												required
											/>
										</div>

										<div class="grid grid-cols-2 gap-3">
											<div class="flex flex-col">
												<label class="field-label" for="first_name">{$t('auth.first_name')}</label>
												<input
													name="first_name"
													id="first_name"
													type="text"
													class="input w-full focus:input-primary"
													placeholder={$t('auth.enter_first_name')}
													autocomplete="given-name"
													required
												/>
											</div>
											<div class="flex flex-col">
												<label class="field-label" for="last_name">{$t('auth.last_name')}</label>
												<input
													name="last_name"
													id="last_name"
													type="text"
													class="input w-full focus:input-primary"
													placeholder={$t('auth.enter_last_name')}
													autocomplete="family-name"
													required
												/>
											</div>
										</div>

										<div class="flex flex-col">
											<label class="field-label" for="password">{$t('auth.password')}</label>
											<input
												type="password"
												name="password1"
												id="password"
												class="input w-full focus:input-primary"
												placeholder={$t('auth.enter_password')}
												autocomplete="new-password"
												minlength={passwordPolicy.min_length}
												bind:value={password}
												required
											/>
										</div>

										<div class="flex flex-col">
											<label class="field-label" for="password2">{$t('auth.confirm_password')}</label>
											<input
												type="password"
												name="password2"
												id="password2"
												class="input w-full focus:input-primary"
												placeholder={$t('auth.confirm_password')}
												autocomplete="new-password"
												minlength={passwordPolicy.min_length}
												bind:value={confirmPassword}
												required
											/>
										</div>

										<PasswordRequirements policy={passwordPolicy} {password} />

										{#if legalRequired}
											<div class="flex flex-col">
												<label class="field-toggle">
													<input
														type="checkbox"
														name="accept_terms"
														class="checkbox checkbox-primary mt-0.5"
														bind:checked={acceptedTerms}
														required
													/>
													<span class="text-left leading-snug text-base-content">
														{$t('auth.agree_to_prefix')}
														{#if signupLegalLinks.terms_of_service_url}
															<a
																href={signupLegalLinks.terms_of_service_url}
																target="_blank"
																rel="noopener noreferrer"
																class="link link-primary"
															>
																{$t('auth.terms_of_service')}
															</a>
														{/if}
														{#if signupLegalLinks.terms_of_service_url && signupLegalLinks.privacy_policy_url}
															{$t('auth.and')}
														{/if}
														{#if signupLegalLinks.privacy_policy_url}
															<a
																href={signupLegalLinks.privacy_policy_url}
																target="_blank"
																rel="noopener noreferrer"
																class="link link-primary"
															>
																{$t('auth.privacy_policy')}
															</a>
														{/if}
													</span>
												</label>
											</div>
										{/if}

										<div class="flex flex-col mt-6">
											<button
												type="submit"
												class="btn btn-primary w-full"
												disabled={legalRequired && !acceptedTerms}
											>
												{$t('auth.signup')}
											</button>
										</div>

										{#if $page.form?.email_verification_required}
											<div class="alert alert-warning mt-4">
												<span>{$t('auth.user_email_verification_required')}</span>
											</div>
										{:else if $page.form?.message}
											<div class="alert alert-error mt-4">
												<span
													>{$t($page.form.message, {
														values: $page.form.values ?? {}
													})}</span
												>
											</div>
										{/if}

										<div class="flex justify-between text-sm mt-6 pt-4 border-t border-base-300">
											<a href="/login" class="link link-primary">
												{$t('auth.login')}
											</a>
											<a href="/user/reset-password" class="link link-primary">
												{$t('auth.forgot_password')}
											</a>
										</div>
									</form>
								</div>
							{:else if inviteSignup && !inviteSignup.valid}
								<div class="text-center">
									<div class="mb-6">
										<div
											class="w-16 h-16 mx-auto bg-warning/10 rounded-full flex items-center justify-center mb-4"
										>
											<svg
												class="w-8 h-8 text-warning"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
												/>
											</svg>
										</div>
										<h1 class="text-4xl font-bold text-base-content mb-4">
											{$t('auth.invite_invalid_title')}
										</h1>
										<p class="text-lg text-base-content/70 max-w-md mx-auto">
											{#if inviteSignup.expired}
												{$t('auth.invite_expired_desc')}
											{:else if inviteSignup.accepted}
												{$t('auth.invite_accepted_desc')}
											{:else if inviteSignup.registered}
												{$t('auth.invite_registered_desc')}
											{:else}
												{$t('auth.invite_invalid_desc')}
											{/if}
										</p>
									</div>

									<div class="mt-8">
										<a href="/login" class="btn btn-primary">{$t('auth.login')}</a>
									</div>
								</div>
							{:else}
								<div class="text-center">
									<div class="mb-6">
										<div
											class="w-16 h-16 mx-auto bg-warning/10 rounded-full flex items-center justify-center mb-4"
										>
											<svg
												class="w-8 h-8 text-warning"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
												/>
											</svg>
										</div>
										<h1 class="text-4xl font-bold text-base-content mb-4">
											{$t('auth.registration_disabled')}
										</h1>
										<p class="text-lg text-base-content/70 max-w-md mx-auto">
											{is_disabled_message}
										</p>
									</div>

									<div class="mt-8">
										<a href="/login" class="btn btn-primary"> Go to Login </a>
									</div>
								</div>
							{/if}
						</div>

						<div
							class="bg-primary/5 p-8 lg:p-12 flex items-center justify-center border-l border-base-300"
						>
							<div class="text-center max-w-md">
								{#if quote && quote.quote}
									<div class="space-y-4">
										<div class="text-6xl text-primary/30 mb-2">"</div>
										<blockquote class="text-lg font-medium text-base-content leading-relaxed">
											{quote.quote}
										</blockquote>
										<footer class="text-base-content/70 font-medium">
											— {quote.author}
										</footer>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>

	{#if background.url}
		<button
			class="btn btn-circle btn-sm fixed bottom-4 right-4 bg-base-100/80 border-base-300 z-20"
			onclick={() => (isImageInfoModalOpen = true)}
		>
			<FileImageBox class="w-4 h-4" />
		</button>
	{/if}
</div>

<svelte:head>
	<title>Sign Up | AdventureLog</title>
	<meta
		name="description"
		content="Sign up for AdventureLog to explore the world and document your adventures!"
	/>
</svelte:head>

<style>
	.input:focus {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
</style>
