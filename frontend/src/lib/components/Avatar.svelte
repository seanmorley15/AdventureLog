<script lang="ts">
	import { goto } from '$app/navigation';
	import { t } from 'svelte-i18n';

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
				<img src={user.profile_pic} alt={$t('navbar.profile')} />
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
		<p class="text-lg ml-4 font-bold">
			{$t('navbar.greeting')}, {user.first_name}
			{user.last_name}
		</p>
		<li><button on:click={() => goto('/profile')}>{$t('navbar.profile')}</button></li>
		<li><button on:click={() => goto('/adventures')}>{$t('navbar.my_adventures')}</button></li>
		<li><button on:click={() => goto('/activities')}>{$t('navbar.my_tags')}</button></li>
		<li><button on:click={() => goto('/shared')}>{$t('navbar.shared_with_me')}</button></li>
		<li><button on:click={() => goto('/settings')}>{$t('navbar.settings')}</button></li>
		<form method="post">
			<li><button formaction="/?/logout">{$t('navbar.logout')}</button></li>
		</form>
	</ul>
</div>
