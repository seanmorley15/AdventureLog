<script lang="ts">
	import { enhance } from '$app/forms';
	import { getRandomBackground, getRandomQuote } from '$lib';
	import { onMount } from 'svelte';

	export let data;
	console.log(data);

	import FileImageBox from '~icons/mdi/file-image-box';
	import Account from '~icons/mdi/account';
	import MapMarkerOutline from '~icons/mdi/map-marker-outline';

	import { page } from '$app/stores';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';

	let quote: { quote: string; author: string } = { quote: '', author: '' };

	let background = getRandomBackground();

	onMount(async () => {
		quote = getRandomQuote();
	});
</script>

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
				<h1>Login</h1>
			</article>

			<div class="flex justify-center">
				<form method="post" use:enhance class="w-full max-w-xs">
					<label for="username">Username</label>
					<input
						name="username"
						id="username"
						class="block mb-2 input input-bordered w-full max-w-xs"
					/><br />
					<label for="password">Password</label>
					<input
						type="password"
						name="password"
						id="password"
						class="block mb-2 input input-bordered w-full max-w-xs"
					/><br />
					<button class="py-2 px-4 btn btn-primary mr-2">Login</button>

					<div class="flex justify-between mt-4">
						<p><a href="/signup" class="underline">Sign Up</a></p>
						<p><a href="/settings/forgot-password" class="underline">Forgot Password</a></p>
					</div>
				</form>
			</div>

			{#if ($page.form?.message && $page.form?.message.length > 1) || $page.form?.type === 'error'}
				<div class="text-center text-error mt-4">
					{$page.form.message || 'Unable to login with the provided credentials.'}
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
		<div tabindex="0" role="button" class="btn m-1 btn-circle btn-md">
			<FileImageBox class="w-4 h-4" />
		</div>
		<ul
			class="dropdown-content menu bg-base-100 rounded-box z-[1] w-auto min-w-[200%] p-2 shadow right-0"
		>
			<p class="whitespace-nowrap text-left">
				<Account class="w-4 h-4 inline-block" />
				{background.author}
				<MapMarkerOutline class="w-4 h-4 inline-block" />
				{background.location}
				<button
					on:click={() => (window.location.href = 'https://forms.gle/2uZNnz8QS3VjuYtQ8')}
					class="btn btn-sm btn-neutral inline-block ml-4">Submit an Image</button
				>
			</p>
		</ul>
	</div>
</div>
<svelte:head>
	<title>Login | AdventureLog</title>
	<meta
		name="description"
		content="Login to your AdventureLog account to start logging your adventures!"
	/>
</svelte:head>
