<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<h1 class="text-center font-bold text-4xl mb-4">Change Password</h1>
<form action="?/reset" method="post" use:enhance>
	<input type="hidden" name="uid" value={data.props.uid} />
	<input type="hidden" name="token" value={data.props.token} />
	<div class="flex items-center justify-center gap-4">
		<input
			type="password"
			class="input input-bordered w-full max-w-xs"
			id="new_password1"
			name="new_password1"
			placeholder="New Password"
		/>
		<input
			type="password"
			class="input input-bordered w-full max-w-xs"
			id="new_password2"
			name="new_password2"
			placeholder="Confirm Password"
		/>
		<button type="submit" class="btn btn-primary"> Submit </button>
		{#if $page.form?.message}
			<div class="text-center text-error mt-4">
				{$page.form?.message}
			</div>
		{/if}
	</div>
</form>
