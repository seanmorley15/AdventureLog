<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { getRandomQuote } from '$lib';
	import { redirect, type SubmitFunction } from '@sveltejs/kit';
	import { onMount } from 'svelte';

	export let data;
	console.log(data);

	import { page } from '$app/stores';

	let quote: string = '';
	let backgroundImageUrl =
		'https://images.unsplash.com/photo-1465056836041-7f43ac27dcb5?q=80&w=2942&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D';

	onMount(async () => {
		quote = getRandomQuote();
	});
</script>

<div
	class="min-h-screen bg-no-repeat bg-cover flex items-center justify-center"
	style="background-image: url('{backgroundImageUrl}')"
>
	<div class="card card-compact w-96 bg-base-100 shadow-xl p-6">
		<article class="text-center text-4xl font-extrabold">
			<h1>Sign in</h1>
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
				<button
					class="py-2 px-4 btn btn-neutral"
					type="button"
					on:click={() => goto('/settings/forgot-password')}>Forgot Password</button
				>
				<button class="py-2 px-4 btn btn-neutral" type="button" on:click={() => goto('/signup')}
					>Sign Up</button
				>
			</form>
		</div>

		{#if ($page.form?.message && $page.form?.message.length > 1) || $page.form?.type === 'error'}
			<div class="text-center text-error mt-4">
				{$page.form.message || 'Unable to login with the provided credentials.'}
			</div>
		{/if}

		<div class="flex justify-center mt-12 mr-25 ml-25">
			<blockquote class="w-80 text-center text-lg break-words">
				{#if quote != ''}
					{quote}
				{/if}
				<!-- <footer class="text-sm">- Steve Jobs</footer> -->
			</blockquote>
		</div>
	</div>
</div>

<svelte:head>
	<title>Login | AdventureLog</title>
	<meta
		name="description"
		content="Login to your AdventureLog account to start logging your adventures!"
	/>
</svelte:head>
