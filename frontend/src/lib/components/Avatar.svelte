<script lang="ts">
	import { goto } from '$app/navigation';

	export let user: any;

	let letter: string = user.first_name[0];

	if (user && !user.first_name && user.username) {
		letter = user.username[0];
	}
</script>

<div class="dropdown dropdown-bottom dropdown-end" tabindex="0" role="button">
	<div class="avatar placeholder">
		<div class="bg-neutral rounded-full text-neutral-200 w-10 ml-4">
			{#if user.profile_pic}
				<img src={user.profile_pic} alt="User Profile" />
			{:else}
				<span class="text-2xl -mt-1">{letter}</span>
			{/if}
		</div>
	</div>
	<!-- svelte-ignore a11y-missing-attribute -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<ul
		tabindex="0"
		class="dropdown-content z-[1] text-neutral-200 menu p-2 shadow bg-neutral mt-2 rounded-box w-52"
	>
		<!-- svelte-ignore a11y-missing-attribute -->
		<!-- svelte-ignore a11y-missing-attribute -->
		<p class="text-lg ml-4 font-bold">Hi, {user.first_name} {user.last_name}</p>
		<li><button on:click={() => goto('/profile')}>Profile</button></li>
		<li><button on:click={() => goto('/adventures')}>My Adventures</button></li>
		<li><button on:click={() => goto('/activities')}>My Activities</button></li>
		<li><button on:click={() => goto('/shared')}>Shared With Me</button></li>
		<li><button on:click={() => goto('/settings')}>User Settings</button></li>
		<form method="post">
			<li><button formaction="/?/logout">Logout</button></li>
		</form>
	</ul>
</div>
