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
		<!-- Profile Picture and User Info -->
		<div class="flex flex-col items-center">
			{#if user.profile_pic}
				<div class="avatar mb-4">
					<div class="w-24 rounded-full ring ring-primary ring-offset-neutral ring-offset-2">
						<img src={user.profile_pic} alt={user.username} />
					</div>
				</div>
			{/if}

			<h2 class="card-title text-center text-lg font-bold">
				{user.first_name}
				{user.last_name}
			</h2>
			<p class="text-sm text-center">{user.username}</p>

			<!-- Admin Badge -->
			{#if user.is_staff}
				<div class="badge badge-primary mt-2">Admin</div>
			{/if}
		</div>

		<!-- Member Since -->
		<div class="flex items-center justify-center mt-4 space-x-2 text-sm">
			<Calendar class="w-5 h-5 text-primary" />
			<p>
				{user.date_joined ? 'Joined ' + new Date(user.date_joined).toLocaleDateString() : ''}
			</p>
		</div>

		<!-- Card Actions -->
		<div class="card-actions justify-center mt-6">
			{#if !sharing}
				<button class="btn btn-primary" on:click={() => goto(`/profile/${user.username}`)}>
					View Profile
				</button>
			{:else if shared_with && !shared_with.includes(user.uuid)}
				<button class="btn btn-success" on:click={() => dispatch('share', user)}> Share </button>
			{:else}
				<button class="btn btn-error" on:click={() => dispatch('unshare', user)}> Unshare </button>
			{/if}
		</div>
	</div>
</div>
