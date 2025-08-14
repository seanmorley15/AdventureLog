<script lang="ts">
	import { enhance } from '$app/forms';
	import { t } from 'svelte-i18n';

	export let data;
	console.log(data);
	import { gsap } from 'gsap';
	import { onMount } from 'svelte';

	onMount(() => {
		// Minimal fade-in only
		gsap.fromTo(
			'.main-container',
			{ opacity: 0 },
			{ opacity: 1, duration: 0.6, ease: 'power2.out' }
		);
	});

	import FileImageBox from '~icons/mdi/file-image-box';

	let isImageInfoModalOpen: boolean = false;

	import { page } from '$app/stores';

	import ImageInfoModal from '$lib/components/ImageInfoModal.svelte';
	import type { Background } from '$lib/types.js';

	let quote: { quote: string; author: string } = data.props.quote;
	let background: Background = data.props.background;
	let is_disabled = data.props.is_disabled as boolean;
	let is_disabled_message = data.props.is_disabled_message as string;
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
					<div class="grid lg:grid-cols-2 min-h-[700px]">
						<!-- Signup Section -->
						<div class="p-8 lg:p-12 flex flex-col justify-center">
							{#if !is_disabled}
								<!-- Header -->
								<div class="text-center mb-8">
									<div class="mb-4">
										<h1 class="text-3xl font-bold text-primary mb-1">AdventureLog</h1>
										<div class="w-12 h-1 bg-primary mx-auto rounded"></div>
									</div>
									<h2 class="text-4xl font-bold text-base-content mb-2">{$t('auth.signup')}</h2>
								</div>

								<!-- Form -->
								<div class="max-w-sm mx-auto w-full">
									<form method="post" use:enhance class="space-y-4">
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
												placeholder="Choose a username"
												autocomplete="username"
												required
											/>
										</div>

										<!-- Email -->
										<div class="form-control">
											<label class="label" for="email">
												<span class="label-text font-medium">{$t('auth.email')}</span>
											</label>
											<input
												name="email"
												id="email"
												type="email"
												class="input input-bordered w-full focus:input-primary"
												placeholder="Enter your email"
												autocomplete="email"
												required
											/>
										</div>

										<!-- Name Fields Row -->
										<div class="grid grid-cols-2 gap-3">
											<div class="form-control">
												<label class="label" for="first_name">
													<span class="label-text font-medium">{$t('auth.first_name')}</span>
												</label>
												<input
													name="first_name"
													id="first_name"
													type="text"
													class="input input-bordered w-full focus:input-primary"
													placeholder="First name"
													autocomplete="given-name"
													required
												/>
											</div>
											<div class="form-control">
												<label class="label" for="last_name">
													<span class="label-text font-medium">{$t('auth.last_name')}</span>
												</label>
												<input
													name="last_name"
													id="last_name"
													type="text"
													class="input input-bordered w-full focus:input-primary"
													placeholder="Last name"
													autocomplete="family-name"
													required
												/>
											</div>
										</div>

										<!-- Password -->
										<div class="form-control">
											<label class="label" for="password">
												<span class="label-text font-medium">{$t('auth.password')}</span>
											</label>
											<input
												type="password"
												name="password1"
												id="password"
												class="input input-bordered w-full focus:input-primary"
												placeholder="Create a password"
												autocomplete="new-password"
												required
											/>
										</div>

										<!-- Confirm Password -->
										<div class="form-control">
											<label class="label" for="password2">
												<span class="label-text font-medium">{$t('auth.confirm_password')}</span>
											</label>
											<input
												type="password"
												name="password2"
												id="password2"
												class="input input-bordered w-full focus:input-primary"
												placeholder="Confirm your password"
												autocomplete="new-password"
												required
											/>
										</div>

										<!-- Submit Button -->
										<div class="form-control mt-6">
											<button type="submit" class="btn btn-primary w-full">
												{$t('auth.signup')}
											</button>
										</div>

										<!-- Error Message -->
										{#if $page.form?.message}
											<div class="alert alert-error mt-4">
												<span>{$t($page.form.message)}</span>
											</div>
										{/if}

										<!-- Footer Links -->
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
							{:else}
								<!-- Registration Disabled -->
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

						<!-- Info Section -->
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
	<title>Sign Up | AdventureLog</title>
	<meta
		name="description"
		content="Sign up for AdventureLog to explore the world and document your adventures!"
	/>
</svelte:head>

<style>
	.input:focus {
		outline: 2px solid hsl(var(--p));
		outline-offset: 2px;
	}
</style>
