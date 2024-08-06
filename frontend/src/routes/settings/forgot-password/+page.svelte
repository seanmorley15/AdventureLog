<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
</script>

<h1 class="text-center font-extrabold text-4xl mb-6">Reset Password</h1>

<div class="flex justify-center">
	<form method="post" action="?/forgotPassword" class="w-full max-w-xs" use:enhance>
		<label for="email">Email</label>
		<input
			name="email"
			type="email"
			id="email"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/><br />
		<button class="py-2 px-4 btn btn-primary mr-2">Reset Password</button>
		{#if $page.form?.message}
			<div class="text-center text-error mt-4">
				{$page.form?.message}
			</div>
		{/if}
		{#if $page.form?.success}
			<div class="text-center text-success mt-4">
				If the email address you provided is associated with an account, you will receive an email
				with instructions to reset your password!
			</div>
		{/if}
	</form>
</div>

<svelte:head>
	<title>Forgot Password</title>
	<meta name="description" content="Reset your password for AdventureLog." />
</svelte:head>
