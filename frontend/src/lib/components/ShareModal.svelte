<script lang="ts">
	import type { Collection, SlimCollection, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import UserCard from './UserCard.svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	import Share from '~icons/mdi/share';
	import Clear from '~icons/mdi/close';

	export let collection: SlimCollection | Collection;

	// Extended user interface to include status
	interface UserWithStatus extends User {
		status?: 'available' | 'pending';
	}

	let allUsers: UserWithStatus[] = [];
	let sharedWithUsers: UserWithStatus[] = [];
	let notSharedWithUsers: UserWithStatus[] = [];

	// Send invite to user
	async function sendInvite(user: User) {
		let res = await fetch(`/api/collections/${collection.id}/share/${user.uuid}/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (res.ok) {
			// Update user status to pending
			const userIndex = notSharedWithUsers.findIndex((u) => u.uuid === user.uuid);
			if (userIndex !== -1) {
				notSharedWithUsers[userIndex].status = 'pending';
				notSharedWithUsers = [...notSharedWithUsers]; // Trigger reactivity
			}
			addToast('success', `${$t('share.invite_sent')} ${user.first_name} ${user.last_name}`);
		} else {
			const error = await res.json();
			addToast('error', error.error || $t('share.invite_failed'));
		}
	}

	// Unshare collection from user (remove from shared_with)
	async function unshare(user: User) {
		let res = await fetch(`/api/collections/${collection.id}/unshare/${user.uuid}/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (res.ok) {
			// Move user from shared to not shared
			sharedWithUsers = sharedWithUsers.filter((u) => u.uuid !== user.uuid);
			notSharedWithUsers = [...notSharedWithUsers, { ...user, status: 'available' }];

			// Update collection shared_with array
			if (collection.shared_with) {
				collection.shared_with = collection.shared_with.filter((u) => u !== user.uuid);
			}

			addToast(
				'success',
				`${$t('share.unshared')} ${collection.name} ${$t('share.with')} ${user.first_name} ${user.last_name}`
			);
		} else {
			const error = await res.json();
			addToast('error', error.error || $t('share.unshare_failed'));
		}
	}

	// Revoke pending invite
	async function revokeInvite(user: User) {
		let res = await fetch(`/api/collections/${collection.id}/revoke-invite/${user.uuid}/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (res.ok) {
			// Update user status back to available
			const userIndex = notSharedWithUsers.findIndex((u) => u.uuid === user.uuid);
			if (userIndex !== -1) {
				notSharedWithUsers[userIndex].status = 'available';
				notSharedWithUsers = [...notSharedWithUsers]; // Trigger reactivity
			}
			addToast('success', `${$t('share.invite_revoked')} ${user.first_name} ${user.last_name}`);
		} else {
			const error = await res.json();
			addToast('error', error.error || $t('share.revoke_failed'));
		}
	}

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}

		// Fetch users that can be shared with (includes status)
		let res = await fetch(`/api/collections/${collection.id}/can-share/`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (res.ok) {
			let users = await res.json();
			allUsers = users.map((user: UserWithStatus) => ({
				...user,
				status: user.status || 'available'
			}));

			// Separate users based on sharing status
			separateUsers();
		}
	});

	function separateUsers() {
		if (!collection.shared_with) {
			collection.shared_with = [];
		}

		// Get currently shared users from allUsers that match shared_with UUIDs
		sharedWithUsers = allUsers.filter((user) => collection.shared_with?.includes(user.uuid));

		// Get not shared users (everyone else from allUsers)
		notSharedWithUsers = allUsers.filter((user) => !collection.shared_with?.includes(user.uuid));
	}

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	// Handle user card actions
	function handleUserAction(event: CustomEvent, action: string) {
		const user = event.detail;
		switch (action) {
			case 'share':
				sendInvite(user);
				break;
			case 'unshare':
				unshare(user);
				break;
			case 'revoke':
				revokeInvite(user);
				break;
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-5xl p-6 space-y-6"
		role="dialog"
		tabindex="0"
		on:keydown={handleKeydown}
	>
		<!-- Title -->
		<!-- Header -->
		<div class="flex items-center justify-between border-b border-base-300 pb-4 mb-4">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-primary/10 rounded-xl">
					<Share class="w-6 h-6 text-primary" />
				</div>
				<div>
					<h3 class="text-2xl font-bold text-primary">
						{$t('adventures.share')} <span class="text-base-content">{collection.name}</span>
					</h3>
					<p class="text-sm text-base-content/60">{$t('share.share_desc')}</p>
				</div>
			</div>
			<button class="btn btn-ghost btn-sm btn-square" on:click={close}>
				<Clear class="w-5 h-5" />
			</button>
		</div>

		<!-- Shared With Section -->
		<div>
			<h4 class="text-lg font-semibold mb-2">{$t('share.shared_with')}</h4>
			{#if sharedWithUsers.length > 0}
				<div
					class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 max-h-[22rem] overflow-y-auto pr-2"
				>
					{#each sharedWithUsers as user}
						<UserCard
							{user}
							shared_with={collection.shared_with}
							sharing={true}
							on:unshare={(event) => handleUserAction(event, 'unshare')}
						/>
					{/each}
				</div>
			{:else}
				<p class="text-neutral-content italic">{$t('share.no_users_shared')}</p>
			{/if}
		</div>

		<div class="divider"></div>

		<!-- Available Users Section -->
		<div>
			<h4 class="text-lg font-semibold mb-2">{$t('share.available_users')}</h4>
			{#if notSharedWithUsers.length > 0}
				<div
					class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 max-h-[22rem] overflow-y-auto pr-2"
				>
					{#each notSharedWithUsers as user}
						<UserCard
							{user}
							shared_with={collection.shared_with}
							sharing={true}
							on:share={(event) => handleUserAction(event, 'share')}
							on:revoke={(event) => handleUserAction(event, 'revoke')}
						/>
					{/each}
				</div>
			{:else}
				<p class="text-neutral-content italic">{$t('share.no_available_users')}</p>
			{/if}
		</div>

		<!-- Action -->
		<div class="pt-4 border-t border-base-300 flex justify-end">
			<button class="btn btn-primary" on:click={close}>
				{$t('about.close')}
			</button>
		</div>
	</div>
</dialog>
