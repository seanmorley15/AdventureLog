<script lang="ts">
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';

	interface CollectionInvite {
		id: string;
		collection: string; // UUID of the collection
		name: string; // Name of the collection
		created_at: string; // ISO 8601 date string
	}

	let invites: CollectionInvite[] = [];
	let loading = true;

	async function fetchInvites() {
		try {
			const res = await fetch('/api/collections/invites/', {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			if (res.ok) {
				invites = await res.json();
			} else {
				addToast('error', $t('invites.fetch_failed'));
			}
		} catch (error) {
			addToast('error', $t('invites.fetch_failed'));
		} finally {
			loading = false;
		}
	}

	async function acceptInvite(invite: CollectionInvite) {
		try {
			const res = await fetch(`/api/collections/${invite.collection}/accept-invite/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			if (res.ok) {
				// Remove invite from list
				invites = invites.filter((i) => i.id !== invite.id);
				addToast('success', `${$t('invites.accepted')} "${invite.name}"`);
			} else {
				const error = await res.json();
				addToast('error', error.error || $t('invites.accept_failed'));
			}
		} catch (error) {
			addToast('error', $t('invites.accept_failed'));
		}
	}

	async function declineInvite(invite: CollectionInvite) {
		try {
			const res = await fetch(`/api/collections/${invite.collection}/decline-invite/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			if (res.ok) {
				// Remove invite from list
				invites = invites.filter((i) => i.id !== invite.id);
				addToast('success', `${$t('invites.declined')} "${invite.name}"`);
			} else {
				const error = await res.json();
				addToast('error', error.error || $t('invites.decline_failed'));
			}
		} catch (error) {
			addToast('error', $t('invites.decline_failed'));
		}
	}

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString();
	}

	onMount(() => {
		fetchInvites();
	});
</script>

<div class="space-y-4">
	<div class="flex items-center justify-between">
		<h2 class="text-2xl font-bold">{$t('invites.title')}</h2>
		<button class="btn btn-sm btn-ghost" on:click={fetchInvites} disabled={loading}>
			{#if loading}
				<span class="loading loading-spinner loading-sm"></span>
			{:else}
				{$t('common.refresh')}
			{/if}
		</button>
	</div>

	{#if loading}
		<div class="flex justify-center py-8">
			<span class="loading loading-spinner loading-lg"></span>
		</div>
	{:else if invites.length === 0}
		<div class="text-center py-8">
			<div class="text-base-content/60 mb-2">
				{$t('invites.no_invites')}
			</div>
			<p class="text-sm text-base-content/40">
				{$t('invites.no_invites_desc')}
			</p>
		</div>
	{:else}
		<div class="space-y-3">
			{#each invites as invite}
				<div class="card bg-base-100 shadow-sm border border-base-300">
					<div class="card-body p-4">
						<div class="flex items-start justify-between">
							<div class="flex-1">
								<h3 class="font-semibold text-lg mb-1">
									{invite.name}
								</h3>
								<p class="text-xs text-base-content/50">
									{$t('invites.invited_on')}
									{formatDate(invite.created_at)}
								</p>
							</div>
							<div class="flex gap-2 ml-4">
								<button class="btn btn-success btn-sm" on:click={() => acceptInvite(invite)}>
									{$t('invites.accept')}
								</button>
								<button
									class="btn btn-error btn-sm btn-outline"
									on:click={() => declineInvite(invite)}
								>
									{$t('invites.decline')}
								</button>
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
