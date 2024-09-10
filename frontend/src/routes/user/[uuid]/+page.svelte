<script lang="ts">
	import type { PageData } from './$types';

	export let data: PageData;
	const user = data.props.user;
	console.log(user);
</script>

<div class="avatar flex items-center justify-center mt-4">
	<div class="w-48 rounded-md">
		<img src={user.profile_pic} alt={user.username} />
	</div>
</div>

<h1 class="text-center font-semibold text-4xl mt-4">{user.first_name} {user.last_name}</h1>
<h2 class="text-center font-semibold text-2xl">{user.username}</h2>

<div class="flex justify-center mt-4">
	{#if user.is_staff}
		<div class="badge badge-primary">Admin</div>
	{/if}
</div>

<svelte:head>
	<title>{user.username} | AdventureLog</title>
	<meta name="description" content="View your adventure collections." />
</svelte:head>
