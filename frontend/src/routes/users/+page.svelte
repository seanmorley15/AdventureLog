<script lang="ts">
	import UserCard from '$lib/components/UserCard.svelte';
	import type { User } from '$lib/types';
	import type { PageData } from './$types';

	export let data: PageData;
	let users: User[] = data.props.users;
	console.log(users);
</script>

<h1 class="text-center font-bold text-4xl mb-4">AdventureLog Users</h1>
<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
	{#each users as user (user.uuid)}
		<UserCard {user} />
	{/each}
</div>

{#if users.length === 0}
	<p class="text-center">No users found with public profiles.</p>
{/if}
