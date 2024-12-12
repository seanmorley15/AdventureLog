<script lang="ts">
	import { enhance } from '$app/forms';

	export let data;
	console.log(data);
	import { t } from 'svelte-i18n';

	import FileImageBox from '~icons/mdi/file-image-box';

	let isImageInfoModalOpen: boolean = false;

	import { page } from '$app/stores';

	import ImageInfoModal from '$lib/components/ImageInfoModal.svelte';
	import type { Background } from '$lib/types.js';

	let quote: { quote: string; author: string } = data.props.quote;

	let background: Background = data.props.background;
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
						<label for="password">TOTP</label>
						<input
							type="password"
							name="totp"
							id="totp"
							class="block input input-bordered w-full max-w-xs"
						/><br />
					{/if}
					<button class="py-2 px-4 btn btn-primary mr-2">{$t('auth.login')}</button>

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
					{$page.form.message || $t('auth.login_error')}
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
