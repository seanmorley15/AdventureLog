<script lang="ts">
	import UserCard from '$lib/components/UserCard.svelte';
	import type { User } from '$lib/types';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;
	let users: User[] = data.props.users;
	console.log(users);
</script>

<h1 class="text-center font-bold text-4xl mb-4">AdventureLog {$t('navbar.users')}</h1>
<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
	{#each users as user (user.uuid)}
		<UserCard {user} />
	{/each}
</div>

{#if users.length === 0}
	<p class="text-center">{$t('users.no_users_found')}</p>
{/if}

<svelte:head>
	<title>Users</title>
	<meta name="description" content="View your location collections." />
</svelte:head>
