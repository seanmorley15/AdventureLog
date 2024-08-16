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
	let errors: { message?: string } = {};
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
	{#if !data.is_disabled}
		<div class="card card-compact w-96 bg-base-100 shadow-xl p-6 mt-4 mb-4">
			<article class="text-center text-4xl font-extrabold">
				<h1>Signup</h1>
			</article>

			<div class="flex justify-center">
				<form method="post" use:enhance class="w-full max-w-xs">
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
				</form>
			</div>

			{#if errors.message}
				<div class="text-center text-error mt-4">
					{errors.message}
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
	{:else}
		<div class="card card-compact w-96 bg-base-100 shadow-xl p-6 mt-4 mb-4">
			<article class="text-center text-4xl font-extrabold">
				<h1>Signup is disabled for this server.</h1>
			</article>

			{#if errors.message}
				<div class="text-center text-error mt-4">
					{errors.message}
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
	{/if}
</div>

<svelte:head>
	<title>Signup</title>
	<meta name="description" content="Signup for AdventureLog to explore the world!" />
</svelte:head>
