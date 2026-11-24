<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { addToast } from '#lib/toasts.js';
	import { jobErrorMessage, runExport } from '#lib/jobs.js';

	import Clear from '~icons/mdi/close';
	import AirplaneTakeoff from '~icons/mdi/airplane-takeoff';
	import FolderOutline from '~icons/mdi/folder-outline';
	import DownloadIcon from '~icons/mdi/download';

	interface Props {
		collection: { id: string; name: string; type: 'folder' | 'trip' | string };
		/** Signed in: the PDF is made in the background. Otherwise it is made while the page waits. */
		signedIn: boolean;
		/** The secret of a guest link, when the page was opened with one. */
		secret?: string | null;
		measurementSystem?: 'metric' | 'imperial' | null;
		onClose: () => void;
	}

	let {
		collection,
		signedIn,
		secret = null,
		measurementSystem = 'metric',
		onClose
	}: Props = $props();

	type Paper = 'a4' | 'letter';
	const STORAGE_KEY = 'adventurelog.pdf_export';

	const isTrip = $derived(collection.type === 'trip');

	let paper = $state<Paper>('a4');
	let photos = $state(true);
	let journal = $state(false);
	let busy = $state(false);
	let modal: HTMLDialogElement | undefined;

	onMount(() => {
		// Letter for people on imperial units, and a folder is a workbook, so it starts with room
		// to write; a trip is a book to read.
		if (measurementSystem === 'imperial') paper = 'letter';
		journal = collection.type === 'folder';
		// Paper and photos are the person's habit; remember them. Write-in space depends on the kind.
		try {
			const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
			if (saved.paper === 'a4' || saved.paper === 'letter') paper = saved.paper;
			if (typeof saved.photos === 'boolean') photos = saved.photos;
		} catch {
			// storage can be blocked or hold something else
		}
		modal?.showModal();
	});

	function close() {
		modal?.close();
		onClose();
	}

	function remember() {
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify({ paper, photos }));
		} catch {
			// not worth failing the download over
		}
	}

	function savedFilename(res: Response): string {
		const named = /filename="?([^";]+)"?/.exec(res.headers.get('Content-Disposition') ?? '');
		if (named) return named[1];
		const safe =
			String(collection.name)
				.replace(/[^\w\s-]/g, '')
				.replace(/\s+/g, '_') || 'collection';
		return `${safe}_${isTrip ? 'trip_book' : 'field_guide'}.pdf`;
	}

	async function download() {
		if (busy) return;
		busy = true;
		remember();
		const options = { paper, photos, journal };
		const url = `/api/collections/${collection.id}/pdf/`;
		try {
			if (signedIn && !secret) {
				// The PDF is made in the background and downloads when it is ready.
				addToast('info', $t('jobs.preparing'));
				await runExport(url, { body: options });
			} else {
				// A guest link carries its secret in the address, so make the PDF now.
				const query = new URLSearchParams({
					paper,
					photos: String(photos),
					journal: String(journal)
				});
				if (secret) query.set('s', secret);
				const res = await fetch(`${url}?${query}`);
				if (!res.ok) {
					addToast('error', $t('adventures.export_pdf_failed'));
					return;
				}
				const blobUrl = URL.createObjectURL(await res.blob());
				const link = document.createElement('a');
				link.href = blobUrl;
				link.download = savedFilename(res);
				link.click();
				URL.revokeObjectURL(blobUrl);
			}
			addToast('success', $t('adventures.export_pdf_success'));
			close();
		} catch (e) {
			addToast('error', jobErrorMessage(e, $t('adventures.export_pdf_failed')));
		} finally {
			busy = false;
		}
	}
</script>

<svelte:window onkeydown={(event) => event.key === 'Escape' && !busy && close()} />

<dialog bind:this={modal} class="modal backdrop-blur-xs" onclose={onClose}>
	<div class="modal-box w-11/12 max-w-lg p-6 space-y-5">
		<div class="flex items-start justify-between gap-4 border-b border-base-300 pb-4">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-primary/10 rounded-xl">
					{#if isTrip}
						<AirplaneTakeoff class="w-6 h-6 text-primary" />
					{:else}
						<FolderOutline class="w-6 h-6 text-primary" />
					{/if}
				</div>
				<div>
					<h3 class="text-2xl font-bold text-primary">
						{$t(isTrip ? 'pdf_export.title_trip' : 'pdf_export.title_folder')}
					</h3>
					<p class="text-sm text-base-content/60">{collection.name}</p>
				</div>
			</div>
			<button
				class="btn btn-ghost btn-sm btn-square"
				onclick={close}
				disabled={busy}
				aria-label={$t('about.close')}
			>
				<Clear class="w-5 h-5" />
			</button>
		</div>

		<p class="text-sm text-base-content/80">
			{$t(isTrip ? 'pdf_export.description_trip' : 'pdf_export.description_folder')}
		</p>

		<div class="space-y-4">
			<div class="flex items-center justify-between gap-4">
				<span class="font-medium">{$t('pdf_export.paper')}</span>
				<div role="radiogroup" class="join" aria-label={$t('pdf_export.paper')}>
					{#each ['a4', 'letter'] as size}
						<button
							type="button"
							role="radio"
							aria-checked={paper === size}
							class="btn btn-sm join-item {paper === size ? 'btn-primary' : 'btn-outline'}"
							onclick={() => (paper = size as Paper)}
						>
							{$t(`pdf_export.paper_${size}`)}
						</button>
					{/each}
				</div>
			</div>

			<label class="flex items-center justify-between gap-4 cursor-pointer">
				<span>
					<span class="block font-medium">{$t('pdf_export.photos')}</span>
					<span class="block text-xs text-base-content/60">{$t('pdf_export.photos_hint')}</span>
				</span>
				<input type="checkbox" class="toggle toggle-primary" bind:checked={photos} />
			</label>

			<label class="flex items-center justify-between gap-4 cursor-pointer">
				<span>
					<span class="block font-medium">
						{$t(isTrip ? 'pdf_export.journal_trip' : 'pdf_export.journal_folder')}
					</span>
					<span class="block text-xs text-base-content/60">
						{$t(isTrip ? 'pdf_export.journal_trip_hint' : 'pdf_export.journal_folder_hint')}
					</span>
				</span>
				<input type="checkbox" class="toggle toggle-primary" bind:checked={journal} />
			</label>
		</div>

		<p class="text-xs text-base-content/50">{$t('pdf_export.maps_note')}</p>

		<div class="modal-action mt-2">
			<button class="btn btn-ghost" onclick={close} disabled={busy}>{$t('about.close')}</button>
			<button class="btn btn-primary gap-2" onclick={download} disabled={busy} aria-busy={busy}>
				{#if busy}
					<span class="loading loading-spinner loading-sm"></span>
				{:else}
					<DownloadIcon class="w-4 h-4" />
				{/if}
				{$t('pdf_export.download')}
			</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button aria-label={$t('about.close')} disabled={busy}>close</button>
	</form>
</dialog>
