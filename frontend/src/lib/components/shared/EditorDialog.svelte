<script lang="ts">
	import type { Snippet } from 'svelte';
	import { t } from 'svelte-i18n';

	interface Props {
		title: string;
		subtitle?: string;
		onClose: () => void;
		children: Snippet;
	}

	let { title, subtitle = '', onClose, children }: Props = $props();

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') onClose();
	}
</script>

<dialog class="modal modal-open modal-bottom md:modal-middle backdrop-blur-xs" open>
	<div
		class="modal-box editor-dialog-box w-11/12 max-w-6xl bg-base-100 border border-base-300 shadow-2xl flex flex-col p-0 overflow-hidden rounded-none md:rounded-2xl"
		role="dialog"
		aria-labelledby="editor-dialog-title"
		tabindex="0"
		onkeydown={handleKeydown}
	>
		<div class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-3 md:px-6 md:py-4">
			<div class="flex items-center justify-between gap-3">
				<div class="flex min-w-0 items-center gap-3">
					<div class="shrink-0 rounded-xl bg-primary/10 p-2">
						<svg class="h-8 w-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
							/>
						</svg>
					</div>
					<div class="min-w-0">
						<h1
							id="editor-dialog-title"
							class="truncate text-2xl font-bold text-primary md:text-3xl"
						>
							{title}
						</h1>
						{#if subtitle}
							<p class="truncate text-sm text-base-content/80">{subtitle}</p>
						{/if}
					</div>
				</div>
				<button
					type="button"
					class="btn btn-ghost btn-square shrink-0"
					aria-label={$t('about.close')}
					title={$t('about.close')}
					onclick={onClose}
				>
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
		</div>
		<div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 md:px-6 md:py-5">
			{@render children()}
		</div>
	</div>
	<button type="button" class="modal-backdrop" aria-label={$t('about.close')} onclick={onClose}
	></button>
</dialog>

<style>
	.editor-dialog-box {
		width: 100%;
		max-width: 100%;
		height: 100dvh;
		max-height: 100dvh;
	}

	@media (min-width: 768px) {
		.editor-dialog-box {
			width: min(96vw, 72rem);
			max-width: 72rem;
			height: min(90dvh, 56rem);
			max-height: 90dvh;
		}
	}
</style>
