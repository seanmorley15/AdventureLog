<script lang="ts">
	import { goto } from '$app/navigation';
	import { continentCodeToString, getFlag } from '$lib';
	import type { User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';

	import Calendar from '~icons/mdi/calendar';

	export let sharing: boolean = false;
	export let shared_with: string[] | undefined = undefined;
	export let user: User & { status?: 'available' | 'pending' };

	$: isShared = shared_with?.includes(user.uuid) || false;
	$: isPending = user.status === 'pending';
	$: isAvailable = user.status === 'available';

	function handleShare() {
		dispatch('share', user);
	}

	function handleUnshare() {
		dispatch('unshare', user);
	}

	function handleRevoke() {
		dispatch('revoke', user);
	}
</script>

<div
	class="card w-full max-w-xs bg-base-200 text-base-content shadow-lg border border-base-300 hover:shadow-xl transition-all"
>
	<div class="card-body items-center text-center space-y-4">
		<!-- Profile Picture -->
		<div class="avatar">
			<div class="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
				{#if user.profile_pic}
					<img src={user.profile_pic} alt={user.username} />
				{:else}
					<div
						class="bg-base-300 w-full h-full flex items-center justify-center text-xl font-semibold"
					>
						{user.first_name?.[0] || user.username?.[0]}{user.last_name?.[0] || user.username?.[1]}
					</div>
				{/if}
			</div>
		</div>

		<!-- User Info -->
		<div>
			<h2 class="text-lg font-bold leading-tight">
				{user.first_name}
				{user.last_name}
			</h2>
			<p class="text-sm opacity-70">@{user.username}</p>

			{#if user.is_staff}
				<div class="badge badge-outline badge-primary mt-2">{$t('settings.admin')}</div>
			{/if}

			<!-- Status Badge for sharing mode -->
			{#if sharing}
				{#if isPending}
					<div class="badge badge-warning badge-sm mt-2">
						{$t('share.pending')}
					</div>
				{:else if isShared}
					<div class="badge badge-success badge-sm mt-2">
						{$t('share.shared')}
					</div>
				{:else if isAvailable}
					<div class="badge badge-ghost badge-sm mt-2">
						{$t('share.available')}
					</div>
				{/if}
			{/if}
		</div>

		<!-- Join Date -->
		<div class="flex items-center gap-2 text-sm text-base-content/70">
			<Calendar class="w-4 h-4 text-primary" />
			<span>
				{user.date_joined
					? `${$t('adventures.joined')} ` + new Date(user.date_joined).toLocaleDateString()
					: ''}
			</span>
		</div>

		<!-- Actions -->
		<div class="card-actions w-full justify-center pt-2">
			{#if !sharing}
				<button
					class="btn btn-sm btn-primary w-full"
					on:click={() => goto(`/profile/${user.username}`)}
				>
					{$t('adventures.view_profile')}
				</button>
			{:else if isShared}
				<button class="btn btn-sm btn-error w-full" on:click={handleUnshare}>
					{$t('adventures.remove')}
				</button>
			{:else if isPending}
				<button class="btn btn-sm btn-warning btn-outline w-full" on:click={handleRevoke}>
					{$t('share.revoke_invite')}
				</button>
			{:else if isAvailable}
				<button class="btn btn-sm btn-success w-full" on:click={handleShare}>
					{$t('share.send_invite')}
				</button>
			{/if}
		</div>
	</div>
</div>
