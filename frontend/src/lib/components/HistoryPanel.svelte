<script lang="ts">
	import { t } from 'svelte-i18n';
	import { createEventDispatcher } from 'svelte';
	import { addToast } from '$lib/toasts';

	const dispatch = createEventDispatcher();

	interface AuditLog {
		id: string;
		user_username: string;
		action: 'create' | 'update' | 'delete';
		object_repr: string;
		changes: Record<string, { old: string; new: string }>;
		timestamp: string;
		content_type_name?: string;
		is_revertible?: boolean;
	}

	export let history: AuditLog[] = [];
	export let itemId: string = '';
	export let canRevert: boolean = false;
	// API endpoint type: 'locations', 'transportations', or 'lodging'
	export let apiEndpoint: 'locations' | 'transportations' | 'lodging' = 'locations';

	// Backward compatibility: locationId is an alias for itemId
	export let locationId: string = '';
	$: effectiveItemId = itemId || locationId;

	let reverting: string | null = null;

	async function handleRevert(log: AuditLog) {
		if (!effectiveItemId || reverting) return;

		reverting = log.id;

		try {
			const response = await fetch(`/api/${apiEndpoint}/${effectiveItemId}/revert/${log.id}/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			if (response.ok) {
				const data = await response.json();
				addToast('success', data.success || 'Reverted successfully');
				dispatch('reverted', { logId: log.id });
			} else {
				const error = await response.json();
				addToast('error', error.error || 'Failed to revert');
			}
		} catch (err) {
			addToast('error', 'Failed to revert');
		} finally {
			reverting = null;
		}
	}
</script>

<div class="card bg-base-200 p-4">
	<h3 class="font-bold mb-4 flex items-center gap-2">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="w-4 h-4"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
		>
			<circle cx="12" cy="12" r="10" />
			<polyline points="12 6 12 12 16 14" />
		</svg>
		{$t('history.title')}
	</h3>

	{#if history.length === 0}
		<p class="text-sm opacity-70">{$t('history.no_history')}</p>
	{:else}
		<ul class="space-y-3">
			{#each history as log}
				<li class="flex flex-col gap-1 border-l-2 border-base-300 pl-3">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-2">
							<span
								class="badge badge-sm
								{log.action === 'create' ? 'badge-success' : ''}
								{log.action === 'update' ? 'badge-info' : ''}
								{log.action === 'delete' ? 'badge-error' : ''}"
							>
								{#if log.action === 'create'}
									{$t('history.created')}
								{:else if log.action === 'update'}
									{$t('history.updated')}
								{:else}
									{$t('history.deleted')}
								{/if}
							</span>
							<span class="text-sm">
								{$t('history.by')}
								<strong>{log.user_username || 'Unknown'}</strong>
							</span>
						</div>
						{#if canRevert && log.is_revertible}
							<button
								class="btn btn-xs btn-ghost btn-outline"
								on:click={() => handleRevert(log)}
								disabled={reverting === log.id}
							>
								{#if reverting === log.id}
									<span class="loading loading-spinner loading-xs"></span>
								{:else}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										class="w-3 h-3"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
									>
										<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
										<path d="M3 3v5h5" />
									</svg>
									{$t('history.revert')}
								{/if}
							</button>
						{/if}
					</div>
					<div class="text-xs opacity-70">
						{#if log.content_type_name && log.content_type_name !== 'location'}
							<span class="badge badge-xs badge-outline mr-1">{log.content_type_name}</span>
						{/if}
						{new Date(log.timestamp).toLocaleString()}
					</div>
					{#if Object.keys(log.changes).length > 0}
						<details class="mt-1">
							<summary class="text-xs cursor-pointer hover:text-primary">
								{$t('history.changes')} ({Object.keys(log.changes).length})
							</summary>
							<div class="text-xs bg-base-300 p-2 rounded mt-1 overflow-x-auto">
								<table class="table table-xs">
									<thead>
										<tr>
											<th>Field</th>
											<th>Old</th>
											<th>New</th>
										</tr>
									</thead>
									<tbody>
										{#each Object.entries(log.changes) as [field, change]}
											<tr>
												<td class="font-mono">{field}</td>
												<td class="text-error">{change.old}</td>
												<td class="text-success">{change.new}</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						</details>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>
