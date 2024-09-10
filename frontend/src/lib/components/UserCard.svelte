<script lang="ts">
	import { goto } from '$app/navigation';
	import { continentCodeToString, getFlag } from '$lib';
	import type { User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import Calendar from '~icons/mdi/calendar';

	export let sharing: boolean = false;
	export let shared_with: string[] | undefined = undefined;

	export let user: User;
</script>

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-neutral text-neutral-content shadow-xl"
>
	<div class="card-body">
		<div>
			{#if user.profile_pic}
				<div class="avatar">
					<div class="w-24 rounded-full">
						<img src={user.profile_pic} alt={user.username} />
					</div>
				</div>
			{/if}
			<h2 class="card-title overflow-ellipsis">{user.first_name} {user.last_name}</h2>
		</div>
		<p class="text-sm text-neutral-content">{user.username}</p>
		{#if user.is_staff}
			<div class="badge badge-primary">Admin</div>
		{/if}
		<!-- member since -->
		<div class="flex items-center space-x-2">
			<Calendar class="w-4 h-4 mr-1" />
			<p class="text-sm text-neutral-content">
				{user.date_joined ? 'Joined ' + new Date(user.date_joined).toLocaleDateString() : ''}
			</p>
		</div>
		<div class="card-actions justify-end">
			{#if !sharing}
				<button class="btn btn-primary" on:click={() => goto(`/user/${user.uuid}`)}>View</button>
			{:else if shared_with && !shared_with.includes(user.uuid)}
				<button class="btn btn-primary" on:click={() => dispatch('share', user)}>Share</button>
			{:else}
				<button class="btn btn-primary" on:click={() => dispatch('unshare', user)}>Unshare</button>
			{/if}
		</div>
	</div>
</div>
