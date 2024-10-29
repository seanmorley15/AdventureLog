<script lang="ts">
	import { enhance } from '$app/forms';
	import { t } from 'svelte-i18n';

	export let data;
	console.log(data);

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

<div
	class="min-h-screen bg-no-repeat bg-cover flex items-center justify-center"
	style="background-image: url('{background.url}')"
>
	<div
		class="card card-compact m-12 w-full max-w-4xl bg-base-100 shadow-xl p-6 flex flex-col md:flex-row"
	>
		<div class="flex-1">
			{#if !is_disabled}
				<h3 class="text-center">AdventureLog</h3>
				<article class="text-center text-4xl mb-4 font-extrabold">
					<h1>{$t('auth.signup')}</h1>
				</article>

				<div class="flex justify-center">
					<form method="post" use:enhance class="w-full max-w-xs">
						<label for="username">{$t('auth.username')}</label>
						<input
							name="username"
							id="username"
							class="block input input-bordered w-full max-w-xs"
						/><br />
						<label for="email">{$t('auth.email')}</label>
						<input
							name="email"
							id="email"
							type="email"
							class="block input input-bordered w-full max-w-xs"
						/><br />
						<label for="first_name">{$t('auth.first_name')}</label>
						<input
							name="first_name"
							id="first_name"
							type="text"
							class="block input input-bordered w-full max-w-xs"
						/><br />
						<label for="last_name">{$t('auth.last_name')}</label>
						<input
							name="last_name"
							id="last_name"
							type="text"
							class="block input input-bordered w-full max-w-xs"
						/><br />
						<label for="password">{$t('auth.password')}</label>
						<input
							type="password"
							name="password1"
							id="password"
							class="block input input-bordered w-full max-w-xs"
						/><br />
						<label for="password">{$t('auth.confirm_password')}</label>
						<input
							type="password"
							name="password2"
							id="password2"
							class="block input input-bordered w-full max-w-xs"
						/><br />

						<button class="py-2 px-4 btn btn-primary mr-2">{$t('auth.signup')}</button>

						<div class="flex justify-between mt-4">
							<p><a href="/login" class="underline">{$t('auth.login')}</a></p>
							<p>
								<a href="/settings/forgot-password" class="underline"
									>{$t('auth.forgot_password')}</a
								>
							</p>
						</div>
					</form>
				</div>

				{#if $page.form?.message}
					<div class="text-center text-error mt-4">{$page.form?.message}</div>
				{/if}
			{:else}
				<div class="flex justify-center">
					<div class="text-center mb-4">
						<h1 class="text-4xl font-extrabold">{$t('auth.registration_disabled')}</h1>
						<p class="text-lg mt-4">{is_disabled_message}</p>
					</div>
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
	<title>Signup</title>
	<meta name="description" content="Signup for AdventureLog to explore the world!" />
</svelte:head>

<!-- <form method="post" use:enhance class="w-full max-w-xs">
	<label for="username">Username</label>
	<input
		name="username"
		id="username"
		class="block mb-2 input input-bordered w-full max-w-xs"
	/><br />
	<label for="first_name">Email</label>
	<input
		name="email"
		id="email"
		type="email"
		class="block mb-2 input input-bordered w-full max-w-xs"
	/><br />
	<label for="first_name">First Name</label>
	<input
		name="first_name"
		id="first_name"
		type="text"
		class="block mb-2 input input-bordered w-full max-w-xs"
	/><br />
	<label for="first_name">Last Name</label>
	<input
		name="last_name"
		id="last_name"
		type="text"
		class="block mb-2 input input-bordered w-full max-w-xs"
	/><br />
	<label for="password">Password</label>
	<input
		type="password"
		name="password1"
		id="password1"
		class="block mb-2 input input-bordered w-full max-w-xs"
	/><br /><label for="password">Confirm Password</label>
	<input
		type="password"
		name="password2"
		id="password2"
		class="block mb-2 input input-bordered w-full max-w-xs"
	/><br />
	<button class="py-2 px-4 btn btn-primary">Signup</button>
	{#if $page.form?.message}
		<div class="text-center text-error mt-4">{$page.form?.message}</div>
	{/if}
</form> -->
