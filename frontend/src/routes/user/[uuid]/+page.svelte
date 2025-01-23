<script lang="ts">
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;
	const user = data.props.user;
</script>

{#if user.profile_pic}
	<div class="avatar flex items-center justify-center mt-4">
		<div class="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2 shadow-md">
			<img src={user.profile_pic} alt={user.username} />
		</div>
	</div>
{/if}

<h1 class="text-center font-semibold text-4xl mt-4 text-primary">
	{user.first_name}
	{user.last_name}
</h1>
<h2 class="text-center font-semibold text-2xl">{user.username}</h2>

<div class="flex justify-center mt-4">
	{#if user.is_staff}
		<div class="badge badge-primary">Admin</div>
	{/if}
</div>

<div class="flex justify-center mt-4">
	<p class="text-lg font-medium">{$t('profile.member_since')}</p>
	<div class="flex items-center ml-2">
		<iconify-icon icon="mdi:calendar" class="text-2xl text-primary"></iconify-icon>
		<p class="ml-2 text-lg">
			{new Date(user.date_joined).toLocaleDateString(undefined, { timeZone: 'UTC' })}
		</p>
	</div>
</div>

<svelte:head>
	<title>{user.username} | AdventureLog</title>
	<meta name="description" content="{user.first_name}'s profile on AdventureLog." />
</svelte:head>
