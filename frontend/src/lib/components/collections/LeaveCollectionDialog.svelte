<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { apiErrorMessage } from '#lib/api/index.js';
	import { addToast } from '#lib/toasts.js';
	import AlertTriangle from '~icons/mdi/alert';

	interface Props {
		collectionId: string;
		onclose: () => void;
		onleft: (collectionId: string) => void;
	}

	let { collectionId, onclose, onleft }: Props = $props();

	let dialog: HTMLDialogElement;
	let locations = $state(0);
	let othersUploads = $state(0);
	let keepCopies = $state(true);
	let busy = $state(false);

	// What leaving would do, so the person can choose before anything changes.
	onMount(async () => {
		dialog?.showModal();
		try {
			const res = await fetch(`/api/collections/${collectionId}/leave/?dry_run=1`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({})
			});
			if (res.ok) {
				const data = await res.json();
				locations = data.locations ?? 0;
				othersUploads = data.others_uploads ?? 0;
			}
		} catch {
			// The preview is a courtesy; leaving still works without it.
		}
	});

	async function leave() {
		busy = true;
		try {
			const res = await fetch(`/api/collections/${collectionId}/leave/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ keep_copies: locations === 0 ? true : keepCopies })
			});
			if (res.ok) {
				addToast('info', $t('adventures.left_collection_message'));
				onleft(collectionId);
				onclose();
			} else {
				const data = await res.json().catch(() => ({}));
				addToast('error', apiErrorMessage(data, $t('share.update_failed')));
			}
		} finally {
			busy = false;
		}
	}
</script>

<dialog bind:this={dialog} class="modal" {onclose}>
	<div class="modal-box max-w-md">
		<h3 class="flex items-center gap-2 text-xl font-bold">
			<AlertTriangle class="h-6 w-6 text-warning" />
			{$t('adventures.leave_collection')}
		</h3>
		<p class="py-3 text-base-content/70">{$t('adventures.leave_collection_warning')}</p>

		{#if locations > 0}
			<label class="label cursor-pointer justify-start gap-3">
				<input type="checkbox" class="checkbox checkbox-primary" bind:checked={keepCopies} />
				<span class="text-sm">
					{$t('adventures.leave_keep_copies', { values: { count: locations } })}
				</span>
			</label>
			{#if !keepCopies}
				<p class="text-sm text-base-content/70">{$t('adventures.leave_copies_off')}</p>
			{/if}
		{/if}

		{#if othersUploads > 0}
			<div role="alert" class="alert alert-warning alert-soft mt-3 text-sm">
				{$t('adventures.leave_others_uploads', { values: { count: othersUploads } })}
			</div>
		{/if}

		<div class="modal-action">
			<form method="dialog">
				<button class="btn btn-ghost" disabled={busy}>{$t('adventures.cancel')}</button>
			</form>
			<button class="btn btn-warning" disabled={busy} onclick={leave}>
				{$t('adventures.leave')}
			</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
