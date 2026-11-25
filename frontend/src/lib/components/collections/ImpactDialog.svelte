<script lang="ts" module>
	import type { ReleasePreview } from '#lib/traveler-impact.js';

	/** The part of a preview every dialog needs, plus whatever it adds. */
	export type ImpactPreview = ReleasePreview & { places?: number; removed_placements?: number };
</script>

<script lang="ts">
	import { onMount, type Snippet } from 'svelte';
	import { t } from 'svelte-i18n';
	import TravelerImpact from './TravelerImpact.svelte';
	import AlertTriangle from '~icons/mdi/alert';

	/**
	 * A confirm dialog that asks the server what would happen first (a `…-preview/` request), then says so:
	 * who keeps a copy, what others keep, what is deleted. Confirm waits for the preview, and an
	 * error blocks it with a retry. When nothing would be released or deleted and ``quiet`` says
	 * the rest is light, it never opens: the action just runs.
	 */
	interface Props {
		title: string;
		confirmLabel: string;
		meUuid?: string | null;
		load: () => Promise<ImpactPreview>;
		/** Runs the real action. Return false to stay open (say why with a toast first). */
		onconfirm: () => Promise<boolean>;
		onclose: () => void;
		/** True when a preview needs no dialog: nothing released or deleted, and the rest is light. */
		quiet?: (preview: ImpactPreview) => boolean;
		/** Text under the title, then anything the caller adds (a plan warning). */
		description?: string;
		extra?: Snippet<[ImpactPreview]>;
		/** Make the confirm button an error (destructive) one. */
		danger?: boolean;
	}

	let {
		title,
		confirmLabel,
		meUuid = null,
		load,
		onconfirm,
		onclose,
		quiet,
		description = '',
		extra,
		danger = false
	}: Props = $props();

	let dialog: HTMLDialogElement;
	let preview = $state<ImpactPreview | null>(null);
	let phase = $state<'loading' | 'ready' | 'error'>('loading');
	// What the server said when the preview failed (a 403, a rate limit), if anything.
	let previewError = $state('');
	let acting = false;
	let busy = $state(false);

	async function loadPreview() {
		phase = 'loading';
		try {
			preview = await load();
		} catch (error) {
			previewError = error instanceof Error ? error.message : '';
			phase = 'error';
			if (!dialog.open) dialog.showModal();
			return;
		}
		phase = 'ready';
		if (quiet?.(preview)) {
			// Nothing to tell them: do it, with no dialog in the way.
			if (!(await run())) finish();
			return;
		}
		if (!dialog.open) dialog.showModal();
	}

	// With a ``quiet`` rule the dialog stays shut until the preview says it is needed; without one it opens at once.
	onMount(() => {
		if (!quiet) dialog.showModal();
		loadPreview();
	});

	/** Close whatever is open; the dialog's own close event tells the parent. A dialog that never opened tells it now. */
	function finish() {
		if (dialog?.open) dialog.close();
		else onclose();
	}

	/** True when the dialog is done (the action ran), false when it should stay or stop. */
	async function run(): Promise<boolean> {
		if (acting || phase !== 'ready') return false;
		acting = true;
		busy = true;
		try {
			const done = await onconfirm();
			if (done) finish();
			return done;
		} finally {
			acting = false;
			busy = false;
		}
	}
</script>

<dialog bind:this={dialog} class="modal" {onclose}>
	<div class="modal-box max-w-md">
		<h3 class="flex items-center gap-2 text-xl font-bold">
			<AlertTriangle class="h-6 w-6 text-warning" />
			{title}
		</h3>
		{#if description}
			<p class="py-3 text-base-content/70">{description}</p>
		{/if}

		{#if phase === 'loading'}
			<p class="flex items-center gap-2 py-2 text-sm text-base-content/70">
				<span class="loading loading-spinner loading-sm"></span>
				{$t('traveler_impact.checking')}
			</p>
		{:else if phase === 'error'}
			<div role="alert" class="alert alert-error alert-soft mt-3 text-sm">
				<span>{previewError || $t('traveler_impact.preview_failed')}</span>
				<button class="btn btn-sm" onclick={loadPreview}>{$t('adventures.leave_retry')}</button>
			</div>
		{:else if preview}
			{@render extra?.(preview)}
			<TravelerImpact
				people={preview.people_released}
				includesYou={preview.includes_you}
				{meUuid}
				visitsDeleted={preview.visits_deleted}
				othersUploads={preview.others_uploads}
				places={preview.places ?? 0}
			/>
		{/if}

		<div class="modal-action">
			<form method="dialog">
				<button class="btn btn-ghost" disabled={busy}>{$t('adventures.cancel')}</button>
			</form>
			<button
				class="btn {danger ? 'btn-error' : 'btn-warning'}"
				disabled={busy || phase !== 'ready'}
				onclick={run}
			>
				{confirmLabel}
			</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
