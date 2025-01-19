<script lang="ts">
	import { enhance } from '$app/forms';

	export let data;
	console.log(data);
	import { t } from 'svelte-i18n';

	import FileImageBox from '~icons/mdi/file-image-box';

	let isImageInfoModalOpen: boolean = false;

	let socialProviders = data.props?.socialProviders ?? [];

	import GitHub from '~icons/mdi/github';
	import OpenIdConnect from '~icons/mdi/openid';

	import { page } from '$app/stores';
	import { gsap } from 'gsap'; // Import GSAP
	import { onMount } from 'svelte';

	onMount(() => {
		gsap.from('.card', {
			opacity: 0,
			y: 50,
			duration: 1,
			ease: 'power3.out'
		});
		gsap.from('.text-center', {
			opacity: 0,
			x: -50,
			duration: 1,
			ease: 'power2.out'
		});
		gsap.from('.input', {
			opacity: 0,
			y: 30,
			duration: 1,
			ease: 'power2.out'
		});
	});

	import ImageInfoModal from '$lib/components/ImageInfoModal.svelte';
	import type { Background } from '$lib/types.js';

	let quote: { quote: string; author: string } = data.props?.quote ?? { quote: '', author: '' };

	let background: Background = data.props?.background ?? { url: '' };
</script>

{#if isImageInfoModalOpen}
	<ImageInfoModal {background} on:close={() => (isImageInfoModalOpen = false)} />
{/if}

<div
	class="min-h-screen bg-no-repeat bg-cover flex items-center justify-center"
	style="background-image: url('{background.url}')"
>
	<div
		class="card card-compact m-12 w-full max-w-4xl bg-base-100 shadow-xl p-6 flex flex-col md:flex-row"
	>
		<div class="flex-1">
			<h3 class="text-center">AdventureLog</h3>
			<article class="text-center text-4xl mb-4 font-extrabold">
				<h1>{$t('auth.login')}</h1>
			</article>

			<div class="flex justify-center">
				<form method="post" use:enhance class="w-full max-w-xs">
					<label for="username">{$t('auth.username')}</label>
					<input
						name="username"
						id="username"
						class="block input input-bordered w-full max-w-xs"
					/><br />
					<label for="password">{$t('auth.password')}</label>
					<input
						type="password"
						name="password"
						id="password"
						class="block input input-bordered w-full max-w-xs"
					/><br />
					{#if $page.form?.mfa_required}
						<label for="totp">TOTP</label>
						<input
							type="text"
							name="totp"
							id="totp"
							inputmode="numeric"
							pattern="[0-9]*"
							autocomplete="one-time-code"
							class="block input input-bordered w-full max-w-xs"
						/><br />
					{/if}
					<button class="py-2 px-4 btn btn-primary mr-2">{$t('auth.login')}</button>

					{#if socialProviders.length > 0}
						<div class="divider text-center text-sm my-4">{$t('auth.or_3rd_party')}</div>
						<div class="flex justify-center">
							{#each socialProviders as provider}
								<a href={provider.url} class="btn btn-primary mr-2 flex items-center">
									{#if provider.provider === 'github'}
										<GitHub class="w-4 h-4 mr-2" />
									{:else if provider.provider === 'openid_connect'}
										<OpenIdConnect class="w-4 h-4 mr-2" />
									{/if}
									{provider.name}
								</a>
							{/each}
						</div>
					{/if}

					<div class="flex justify-between mt-4">
						<p><a href="/signup" class="underline">{$t('auth.signup')}</a></p>
						<p>
							<a href="/user/reset-password" class="underline">{$t('auth.forgot_password')}</a>
						</p>
					</div>
				</form>
			</div>

			{#if ($page.form?.message && $page.form?.message.length > 1) || $page.form?.type === 'error'}
				<div class="text-center text-error mt-4">
					{$t($page.form.message) || $t('auth.login_error')}
				</div>
			{/if}
		</div>

		<div class="flex-1 flex justify-center items-center mt-12 md:mt-0 md:ml-6">
			<blockquote class="w-80 text-center text-2xl font-semibold break-words">
				{#if quote != null}
					{quote.quote}
				{/if}
				<footer class="text-sm mt-1">{quote.author}</footer>
			</blockquote>
		</div>
	</div>
</div>

<div class="fixed bottom-4 right-4 z-[999]">
	<div class="dropdown dropdown-left dropdown-end">
		<button class="btn m-1 btn-circle btn-md" on:click={() => (isImageInfoModalOpen = true)}>
			<FileImageBox class="w-4 h-4" />
		</button>
	</div>
</div>

<svelte:head>
	<title>Login | AdventureLog</title>
	<meta
		name="description"
		content="Login to your AdventureLog account to start logging your adventures!"
	/>
</svelte:head>
