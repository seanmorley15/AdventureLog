<script lang="ts">
	import { goto } from '$app/navigation';
	import type { User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import UserAvatar from '$lib/components/UserAvatar.svelte';
	import Calendar from '~icons/mdi/calendar';
	import Account from '~icons/mdi/account';
	import ShieldAccount from '~icons/mdi/shield-account';
	import ChevronRight from '~icons/mdi/chevron-right';

	interface Props {
		sharing?: boolean;
		shared_with?: string[] | undefined;
		user: User & { status?: 'available' | 'pending' };
	}

	let { sharing = false, shared_with = undefined, user }: Props = $props();

	const dispatch = createEventDispatcher<{
		share: User;
		unshare: User;
		revoke: User;
	}>();

	let isShared = $derived(shared_with?.includes(user.uuid) || false);
	let isPending = $derived(user.status === 'pending');
	let isAvailable = $derived(user.status === 'available');

	let displayName =
		$derived([user.first_name, user.last_name].filter(Boolean).join(' ').trim() || user.username);

	let joinedLabel = $derived(user.date_joined
		? new Date(user.date_joined).toLocaleDateString(undefined, {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
				timeZone: 'UTC'
			})
		: '');

	function openProfile() {
		goto(`/profile/${user.username}`);
	}

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

{#if sharing}
	<div
		class="card w-full max-w-xs bg-base-100 text-base-content shadow-lg border border-base-300/60 hover:shadow-xl transition-all"
	>
		<div class="card-body items-center text-center gap-4 p-5">
			<div class="avatar">
				<div class="w-20 rounded-full ring-2 ring-primary/30 ring-offset-2 ring-offset-base-100">
					<UserAvatar
						{user}
						alt={displayName}
						className="w-20 h-20 rounded-full"
						textClass="text-2xl"
					/>
				</div>
			</div>

			<div class="min-w-0 w-full">
				<h3 class="font-bold truncate">{displayName}</h3>
				<p class="text-sm text-base-content/60 truncate">@{user.username}</p>
				{#if isPending}
					<div class="badge badge-warning badge-sm mt-2">{$t('share.pending')}</div>
				{:else if isShared}
					<div class="badge badge-success badge-sm mt-2">{$t('share.shared')}</div>
				{:else if isAvailable}
					<div class="badge badge-ghost badge-sm mt-2">{$t('share.available')}</div>
				{/if}
			</div>

			<div class="card-actions w-full">
				{#if isShared}
					<button type="button" class="btn btn-sm btn-error w-full" onclick={handleUnshare}>
						{$t('adventures.remove')}
					</button>
				{:else if isPending}
					<button
						type="button"
						class="btn btn-sm btn-warning btn-outline w-full"
						onclick={handleRevoke}
					>
						{$t('share.revoke_invite')}
					</button>
				{:else if isAvailable}
					<button type="button" class="btn btn-sm btn-success w-full" onclick={handleShare}>
						{$t('share.send_invite')}
					</button>
				{/if}
			</div>
		</div>
	</div>
{:else}
	<button
		type="button"
		class="group card w-full bg-base-100 border border-base-300/60 shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200 text-left overflow-hidden"
		onclick={openProfile}
	>
		<div class="h-16 bg-gradient-to-r from-primary/15 via-secondary/10 to-accent/10"></div>

		<div class="px-5 pb-5 -mt-10">
			<div class="flex items-end justify-between gap-3">
				<div class="avatar">
					<div class="w-20 rounded-2xl ring-4 ring-base-100 shadow-lg overflow-hidden bg-base-200">
						<UserAvatar
							{user}
							alt={displayName}
							className="w-20 h-20 rounded-2xl"
							textClass="text-2xl"
						/>
					</div>
				</div>
				{#if user.is_staff}
					<span class="badge badge-primary badge-sm gap-1 mb-1 shrink-0">
						<ShieldAccount class="w-3.5 h-3.5" />
						{$t('settings.admin')}
					</span>
				{/if}
			</div>

			<div class="mt-3 min-w-0">
				<h3
					class="text-lg font-bold leading-tight truncate group-hover:text-primary transition-colors"
				>
					{displayName}
				</h3>
				<p class="text-sm text-base-content/60 truncate">@{user.username}</p>
			</div>

			<div class="mt-4 flex items-center justify-between gap-2 text-sm text-base-content/60">
				{#if joinedLabel}
					<span class="inline-flex items-center gap-1.5 min-w-0">
						<Calendar class="w-4 h-4 shrink-0 text-primary/70" />
						<span class="truncate">{$t('adventures.joined')} {joinedLabel}</span>
					</span>
				{:else}
					<span class="inline-flex items-center gap-1.5">
						<Account class="w-4 h-4 shrink-0 text-primary/70" />
						{$t('users.public_profile')}
					</span>
				{/if}
				<ChevronRight
					class="w-5 h-5 shrink-0 text-base-content/30 group-hover:text-primary group-hover:translate-x-0.5 transition-all"
				/>
			</div>
		</div>
	</button>
{/if}
