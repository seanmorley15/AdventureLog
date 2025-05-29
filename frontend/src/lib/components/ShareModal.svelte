<script lang="ts">
	import type { Collection, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import UserCard from './UserCard.svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	export let collection: Collection;

	let allUsers: User[] = [];

	let sharedWithUsers: User[] = [];
	let notSharedWithUsers: User[] = [];

	async function share(user: User) {
		let res = await fetch(`/api/collections/${collection.id}/share/${user.uuid}/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (res.ok) {
			sharedWithUsers = sharedWithUsers.concat(user);
			if (collection.shared_with) {
				collection.shared_with.push(user.uuid);
			} else {
				collection.shared_with = [user.uuid];
			}
			notSharedWithUsers = notSharedWithUsers.filter((u) => u.uuid !== user.uuid);
			addToast(
				'success',
				`${$t('share.shared')} ${collection.name} ${$t('share.with')} ${user.first_name} ${user.last_name}`
			);
		}
	}

	async function unshare(user: User) {
		let res = await fetch(`/api/collections/${collection.id}/unshare/${user.uuid}/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (res.ok) {
			notSharedWithUsers = notSharedWithUsers.concat(user);
			if (collection.shared_with) {
				collection.shared_with = collection.shared_with.filter((u) => u !== user.uuid);
			}
			sharedWithUsers = sharedWithUsers.filter((u) => u.uuid !== user.uuid);
			addToast(
				'success',
				`${$t('share.unshared')} ${collection.name} ${$t('share.with')} ${user.first_name} ${user.last_name}`
			);
		}
	}

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		let res = await fetch(`/auth/users`);
		if (res.ok) {
			let data = await res.json();
			allUsers = data;
			sharedWithUsers = allUsers.filter((user) =>
				(collection.shared_with ?? []).includes(user.uuid)
			);
			notSharedWithUsers = allUsers.filter(
				(user) => !(collection.shared_with ?? []).includes(user.uuid)
			);
			console.log(sharedWithUsers);
			console.log(notSharedWithUsers);
		}
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div
		class="modal-box w-11/12 max-w-5xl p-6 space-y-6"
		role="dialog"
		tabindex="0"
		on:keydown={handleKeydown}
	>
		<!-- Title -->
		<div class="space-y-1">
			<h3 class="text-2xl font-bold">
				{$t('adventures.share')}
				{collection.name}
			</h3>
			<p class="text-base-content/70">{$t('share.share_desc')}</p>
		</div>

		<!-- Shared With Section -->
		<div>
			<h4 class="text-lg font-semibold mb-2">{$t('share.shared_with')}</h4>
			{#if sharedWithUsers.length > 0}
				<div
					class="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 max-h-80 overflow-y-auto pr-2"
				>
					{#each sharedWithUsers as user}
						<UserCard
							{user}
							shared_with={collection.shared_with}
							sharing={true}
							on:share={(event) => share(event.detail)}
							on:unshare={(event) => unshare(event.detail)}
						/>
					{/each}
				</div>
			{:else}
				<p class="text-neutral-content italic">{$t('share.no_users_shared')}</p>
			{/if}
		</div>

		<div class="divider"></div>

		<!-- Not Shared With Section -->
		<div>
			<h4 class="text-lg font-semibold mb-2">{$t('share.not_shared_with')}</h4>
			{#if notSharedWithUsers.length > 0}
				<div
					class="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 max-h-80 overflow-y-auto pr-2"
				>
					{#each notSharedWithUsers as user}
						<UserCard
							{user}
							shared_with={collection.shared_with}
							sharing={true}
							on:share={(event) => share(event.detail)}
							on:unshare={(event) => unshare(event.detail)}
						/>
					{/each}
				</div>
			{:else}
				<p class="text-neutral-content italic">{$t('share.no_users_shared')}</p>
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
