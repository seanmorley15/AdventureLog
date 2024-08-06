<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<h1 class="text-center font-bold text-4xl mb-4">Change Password</h1>

{#if data.props.token && data.props.uid}
	<p class="text-center">You will then be redirected to the login page.</p>
	<div
		class="modal-action items-center"
		style="display: flex; flex-direction: column; align-items: center; width: 100%;"
	>
		<form action="?/reset" method="post" use:enhance>
			<input type="hidden" name="uid" value={data.props.uid} />
			<input type="hidden" name="token" value={data.props.token} />

			<div class="mb-2 w-full">
				<input
					type="password"
					class="input input-bordered w-full"
					id="new_password1"
					name="new_password1"
					placeholder="New Password"
				/>
			</div>
			<div class="mb-2 w-full">
				<input
					type="password"
					class="input input-bordered w-full"
					id="new_password2"
					name="new_password2"
					placeholder="Confirm Password"
				/>
			</div>
			<button type="submit" class="btn btn-primary w-full">Submit</button>
			{#if $page.form?.message}
				<div class="text-center text-error mt-4">
					{$page.form?.message}
				</div>
			{/if}
		</form>
	</div>
{:else}
	<div class="flex justify-center">
		<div class="items-center justify-center">
			<p class="text-center">Token and UID are required for password reset.</p>

			<button class="btn btn-neutral" on:click={() => goto('/settings/forgot-password')}>
				Reset Password
			</button>
		</div>
	</div>
{/if}

<svelte:head>
	<title>Password Reset Confirm</title>
	<meta name="description" content="Confirm your password reset and make a new password." />
</svelte:head>
