<script lang="ts">
	import { enhance } from '$app/forms';
	let isSubmitting: boolean = false;

	export let data;
	console.log(data);
	import { t } from 'svelte-i18n';

	import FileImageBox from '~icons/mdi/file-image-box';

	let isImageInfoModalOpen: boolean = false;

	let socialProviders = data.props?.socialProviders ?? [];

	import GitHub from '~icons/mdi/github';
	import OpenIdConnect from '~icons/mdi/openid';

	import { page } from '$app/stores';
	import { gsap } from 'gsap';
	import { onMount } from 'svelte';

	function handleEnhanceSubmit() {
		isSubmitting = true;
		// If the form is aborted or done, reset the state
		return async ({ update, result }: { update: any; result: any }) => {
			if (result.type === 'success') {
				// Keep isSubmitting as true for success to show loading state
				await update(result);
			} else {
				isSubmitting = false;
				await update(result);
			}
		};
	}

	onMount(() => {
		// Minimal fade-in only
		gsap.fromTo(
			'.main-container',
			{ opacity: 0 },
			{ opacity: 1, duration: 0.6, ease: 'power2.out' }
		);
	});

	import ImageInfoModal from '$lib/components/ImageInfoModal.svelte';
	import type { Background } from '$lib/types.js';

	let quote: { quote: string; author: string } = data.props?.quote ?? { quote: '', author: '' };
	let background: Background = data.props?.background ?? { url: '' };
</script>

{#if isImageInfoModalOpen}
	<ImageInfoModal {background} on:close={() => (isImageInfoModalOpen = false)} />
{/if}

<div class="min-h-screen bg-base-200">
	<!-- Background image if provided -->
	{#if background.url}
		<div
			class="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-60"
			style="background-image: url('{background.url}')"
		></div>
	{/if}

	<div class="main-container relative z-10 min-h-screen flex items-center justify-center p-4">
		<div class="w-full max-w-5xl">
			<div class="card bg-base-100 shadow-2xl">
				<div class="card-body p-0">
					<div class="grid lg:grid-cols-2 min-h-[600px]">
						<!-- Login Section -->
						<div class="p-8 lg:p-12 flex flex-col justify-center">
							<!-- Header -->
							<div class="text-center mb-8">
								<div class="mb-4">
									<h1 class="text-3xl font-bold text-primary mb-1">AdventureLog</h1>
									<div class="w-12 h-1 bg-primary mx-auto rounded"></div>
								</div>
								<h2 class="text-4xl font-bold text-base-content mb-2">{$t('auth.login')}</h2>
							</div>

							<!-- Form -->
							<div class="max-w-sm mx-auto w-full">
								<form method="post" use:enhance={handleEnhanceSubmit} class="space-y-4">
									<!-- Username -->
									<div class="form-control">
										<label class="label" for="username">
											<span class="label-text font-medium">{$t('auth.username')}</span>
										</label>
										<input
											name="username"
											id="username"
											type="text"
											class="input input-bordered w-full focus:input-primary"
											placeholder={$t('auth.enter_username')}
											autocomplete="username"
										/>
									</div>

									<!-- Password -->
									<div class="form-control">
										<label class="label" for="password">
											<span class="label-text font-medium">{$t('auth.password')}</span>
										</label>
										<input
											type="password"
											name="password"
											id="password"
											class="input input-bordered w-full focus:input-primary"
											placeholder={$t('auth.enter_password')}
											autocomplete="current-password"
										/>
									</div>

									<!-- TOTP -->
									{#if $page.form?.mfa_required}
										<div class="form-control">
											<label class="label" for="totp">
												<span class="label-text font-medium">{$t('auth.totp')}</span>
											</label>
											<input
												type="text"
												name="totp"
												id="totp"
												inputmode="numeric"
												pattern="[0-9]*"
												autocomplete="one-time-code"
												class="input input-bordered w-full focus:input-primary"
												placeholder="000000"
												maxlength="6"
											/>
										</div>
									{/if}

									<!-- Submit Button -->
									<div class="form-control mt-6">
										<button type="submit" class="btn btn-primary w-full" disabled={isSubmitting}>
											{#if isSubmitting}
												<span class="loading loading-spinner"></span>
												<span class="ml-2">Logging in…</span>
											{:else}
												{$t('auth.login')}
											{/if}
										</button>
									</div>

									<!-- Error Message -->
									{#if ($page.form?.message && $page.form?.message.length > 1) || $page.form?.type === 'error'}
										<div class="alert alert-error mt-4">
											<span>{$t($page.form.message) || $t('auth.login_error')}</span>
										</div>
									{/if}

									<!-- Social Login -->
									{#if socialProviders.length > 0}
										<div class="divider text-sm">{$t('auth.or_3rd_party')}</div>

										<div class="space-y-2">
											{#each socialProviders as provider}
												<a
													href={provider.url}
													class="btn btn-outline w-full flex items-center gap-2"
												>
													{#if provider.provider === 'github'}
														<GitHub class="w-4 h-4" />
													{:else if provider.provider === 'openid_connect'}
														<OpenIdConnect class="w-4 h-4" />
													{/if}
													Continue with {provider.name}
												</a>
											{/each}
										</div>
									{/if}

									<!-- Footer Links -->
									<div class="flex justify-between text-sm mt-6 pt-4 border-t border-base-300">
										<a href="/signup" class="link link-primary">
											{$t('auth.signup')}
										</a>
										<a href="/user/reset-password" class="link link-primary">
											{$t('auth.forgot_password')}
										</a>
									</div>
								</form>
							</div>
						</div>

						<!-- Quote/Info Section -->
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

	<!-- Image Info Button -->
	{#if background.url}
		<button
			class="btn btn-circle btn-sm fixed bottom-4 right-4 bg-base-100/80 border-base-300 z-20"
			on:click={() => (isImageInfoModalOpen = true)}
		>
			<FileImageBox class="w-4 h-4" />
		</button>
	{/if}
</div>

<svelte:head>
	<title>Login | AdventureLog</title>
	<meta
		name="description"
		content="Login to your AdventureLog account to start logging your adventures!"
	/>
</svelte:head>

<style>
	.input:focus {
		outline: 2px solid hsl(var(--p));
		outline-offset: 2px;
	}
</style>
