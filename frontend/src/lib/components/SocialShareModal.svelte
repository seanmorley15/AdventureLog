<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import { copyToClipboard } from '$lib/index';

	import Share from '~icons/mdi/share-variant';
	import Clear from '~icons/mdi/close';
	import Download from '~icons/mdi/download';
	import ContentCopy from '~icons/mdi/content-copy';
	import LinkIcon from '~icons/mdi/link';
	import Check from '~icons/mdi/check';
	import ImageOutline from '~icons/mdi/image-outline';

	const dispatch = createEventDispatcher();

	interface Props {
		type: 'collection' | 'location';
		id: string;
		name: string;
		isPublic?: boolean;
	}

	let {
		type,
		id,
		name,
		isPublic = false
	}: Props = $props();

	type Aspect = 'square' | 'story' | 'landscape';

	const aspects: Aspect[] = ['square', 'story', 'landscape'];

	let modal: HTMLDialogElement;
	let selectedAspect: Aspect = $state('square');
	let previewLoading = $state(true);
	let previewError = $state(false);
	let copiedLink = $state(false);
	let canNativeShare = $state(false);

	let publicUrl =
		$derived(typeof window !== 'undefined'
			? `${window.location.origin}/${type === 'collection' ? 'collections' : 'locations'}/${id}`
			: '');
	let imageUrl = $derived(`/api/${type === 'collection' ? 'collections' : 'locations'}/${id}/share-image/${selectedAspect}/`);
	let previewUrl = $derived(`${imageUrl}${imageUrl.includes('?') ? '&' : '?'}t=${selectedAspect}`);

	onMount(() => {
		modal = document.getElementById('social_share_modal') as HTMLDialogElement;
		modal?.showModal();
		canNativeShare = typeof navigator !== 'undefined' && !!navigator.share;
	});

	function close() {
		dispatch('close');
		modal?.close();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') close();
	}

	function handlePreviewLoad() {
		previewLoading = false;
		previewError = false;
	}

	function handlePreviewError() {
		previewLoading = false;
		previewError = true;
	}

	function aspectLabel(aspect: Aspect): string {
		if (aspect === 'square') return $t('social_share.aspect_square');
		if (aspect === 'story') return $t('social_share.aspect_story');
		return $t('social_share.aspect_landscape');
	}

	function previewMaxHeight(aspect: Aspect): string {
		if (aspect === 'story') return '420px';
		if (aspect === 'landscape') return '220px';
		return '320px';
	}

	async function fetchImageBlob(): Promise<Blob | null> {
		try {
			const res = await fetch(`${imageUrl}?download=1`);
			if (!res.ok) {
				addToast('error', $t('social_share.share_image_failed'));
				return null;
			}
			return await res.blob();
		} catch {
			addToast('error', $t('social_share.share_image_failed'));
			return null;
		}
	}

	function safeFilename(): string {
		const safeName =
			String(name)
				.replace(/[^\w\s-]/g, '')
				.replace(/\s+/g, '_') || 'share';
		return `${safeName}_${type}_${selectedAspect}.png`;
	}

	async function downloadImage() {
		const blob = await fetchImageBlob();
		if (!blob) return;
		const objectUrl = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = objectUrl;
		a.download = safeFilename();
		a.click();
		URL.revokeObjectURL(objectUrl);
		addToast('success', $t('social_share.download_success'));
	}

	async function copyImage() {
		const blob = await fetchImageBlob();
		if (!blob) return;
		try {
			if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') {
				throw new Error('Clipboard API unavailable');
			}
			await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
			addToast('success', $t('social_share.copy_image_success'));
		} catch {
			addToast('error', $t('social_share.copy_image_failed'));
		}
	}

	async function copyLink() {
		try {
			await copyToClipboard(publicUrl);
			copiedLink = true;
			setTimeout(() => (copiedLink = false), 2000);
		} catch {
			addToast('error', $t('adventures.copy_failed'));
		}
	}

	async function nativeShare() {
		const blob = await fetchImageBlob();
		if (!blob) return;
		try {
			const file = new File([blob], safeFilename(), { type: 'image/png' });
			await navigator.share({
				title: name,
				text: name,
				url: isPublic ? publicUrl : undefined,
				files: [file]
			});
		} catch (err) {
			if (err instanceof Error && err.name === 'AbortError') return;
			addToast('error', $t('social_share.share_native_failed'));
		}
	}

	function selectAspect(aspect: Aspect) {
		selectedAspect = aspect;
		previewLoading = true;
		previewError = false;
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<dialog id="social_share_modal" class="modal backdrop-blur-xs">
	<div class="modal-box w-11/12 max-w-3xl p-6 space-y-5">
		<div class="flex items-center justify-between border-b border-base-300 pb-4">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-primary/10 rounded-xl">
					<Share class="w-6 h-6 text-primary" />
				</div>
				<div>
					<h3 class="text-2xl font-bold text-primary">
						{$t('social_share.share_externally')}
					</h3>
					<p class="text-sm text-base-content/60">{$t('social_share.modal_desc')}</p>
				</div>
			</div>
			<button
				class="btn btn-ghost btn-sm btn-square"
				onclick={close}
				aria-label={$t('about.close')}
			>
				<Clear class="w-5 h-5" />
			</button>
		</div>

		{#if !isPublic}
			<div class="alert alert-info text-sm py-3">
				<span>
					{$t(
						type === 'collection'
							? 'social_share.private_notice_collection'
							: 'social_share.private_notice_location'
					)}
				</span>
			</div>
		{/if}

		<div role="tablist" class="tabs tabs-box bg-base-200">
			{#each aspects as aspect}
				<button
					role="tab"
					class="tab {selectedAspect === aspect ? 'tab-active' : ''}"
					onclick={() => selectAspect(aspect)}
				>
					{aspectLabel(aspect)}
				</button>
			{/each}
		</div>

		<div
			class="relative flex items-center justify-center bg-base-200 rounded-xl overflow-hidden min-h-[180px]"
			style="max-height: {previewMaxHeight(selectedAspect)}"
		>
			{#if previewLoading && !previewError}
				<div class="flex flex-col items-center gap-2 py-10 text-base-content/60">
					<span class="loading loading-spinner loading-md"></span>
					<span class="text-sm">{$t('social_share.preview_loading')}</span>
				</div>
			{/if}
			{#if previewError}
				<div class="flex flex-col items-center gap-2 py-10 text-error">
					<ImageOutline class="w-10 h-10 opacity-60" />
					<span class="text-sm">{$t('social_share.share_image_failed')}</span>
				</div>
			{/if}
			<img
				src={previewUrl}
				alt={name}
				class="max-w-full object-contain {previewLoading ? 'hidden' : ''} {previewError
 ? 'hidden'
 : ''}"
				style="max-height: {previewMaxHeight(selectedAspect)}"
				onload={handlePreviewLoad}
				onerror={handlePreviewError}
			/>
		</div>

		<div class="flex flex-wrap gap-2">
			<button class="btn btn-primary gap-2" onclick={downloadImage}>
				<Download class="w-4 h-4" />
				{$t('social_share.download_image')}
			</button>
			<button class="btn btn-neutral gap-2" onclick={copyImage}>
				<ContentCopy class="w-4 h-4" />
				{$t('social_share.copy_image')}
			</button>
			{#if isPublic}
				<button class="btn btn-neutral gap-2" onclick={copyLink}>
					{#if copiedLink}
						<Check class="w-4 h-4 text-success" />
						{$t('adventures.link_copied')}
					{:else}
						<LinkIcon class="w-4 h-4" />
						{$t('adventures.copy_link')}
					{/if}
				</button>
			{/if}
			{#if canNativeShare}
				<button class="btn btn-outline gap-2" onclick={nativeShare}>
					<Share class="w-4 h-4" />
					{$t('social_share.share_native')}
				</button>
			{/if}
		</div>
	</div>
</dialog>
