<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Collection } from '$lib/types';
	import type { DateFormatPreference } from '$lib/dateFormat';
	import { hiddenStoryGroups } from '$lib/collections/story';
	import { copyToClipboard } from '$lib/index';
	import { addToast } from '$lib/toasts';
	import CollectionStory from './CollectionStory.svelte';
	import LockOutline from '~icons/mdi/lock-outline';
	import Earth from '~icons/mdi/earth';
	import LinkVariant from '~icons/mdi/link-variant';
	import ContentCopy from '~icons/mdi/content-copy';
	import OpenInNew from '~icons/mdi/open-in-new';
	import Tune from '~icons/mdi/tune-variant';

	interface Props {
		/** The member payload; the tab loads the story payload readers get. */
		collection: Collection;
		dateFormat: DateFormatPreference;
		isOwner: boolean;
		onOpenShare?: () => void;
	}

	let { collection, dateFormat, isOwner, onOpenShare }: Props = $props();

	let story = $state<Collection | null>(null);
	let failed = $state(false);

	let visibility = $derived(collection.visibility ?? (collection.is_public ? 'public' : 'private'));
	let shareUrl = $derived.by(() => {
		if (typeof window === 'undefined' || visibility === 'private') return null;
		const base = `${window.location.origin}/collections/${collection.id}`;
		if (visibility === 'public') return base;
		return collection.share_secret
			? `${base}?s=${encodeURIComponent(collection.share_secret)}`
			: null;
	});
	let hidden = $derived(
		hiddenStoryGroups(story ?? collection).map((group) => $t(`share.group_${group}`))
	);

	// Reload whenever what readers would see changes.
	let reloadKey = $derived(
		`${collection.id}|${visibility}|${JSON.stringify(collection.story_groups ?? {})}|${collection.updated_at ?? ''}`
	);

	$effect(() => {
		void reloadKey;
		const controller = new AbortController();
		failed = false;
		fetch(`/api/collections/${collection.id}/?as=story`, { signal: controller.signal })
			.then(async (res) => {
				if (!res.ok) throw new Error(String(res.status));
				story = (await res.json()) as Collection;
			})
			.catch((error) => {
				if (error?.name !== 'AbortError') failed = true;
			});
		return () => controller.abort();
	});

	async function copyLink() {
		if (!shareUrl) return;
		try {
			await copyToClipboard(shareUrl);
			addToast('success', $t('adventures.link_copied'));
		} catch {
			addToast('error', $t('adventures.copy_failed'));
		}
	}
</script>

<div class="flex h-full min-h-0 flex-col gap-3">
	<div
		class="flex shrink-0 flex-wrap items-center gap-3 rounded-xl border px-3 py-2 {visibility ===
		'private'
			? 'border-base-300 bg-base-200'
			: 'border-success/40 bg-success/10'}"
		role="status"
	>
		{#if visibility === 'private'}
			<LockOutline class="h-5 w-5 shrink-0" />
			<div class="min-w-0 flex-1">
				<p class="font-semibold">{$t('story.tab_private_title')}</p>
				<p class="text-sm text-base-content/70">
					{isOwner ? $t('story.tab_private_owner') : $t('story.tab_private_member')}
				</p>
			</div>
			{#if isOwner}
				<button type="button" class="btn btn-primary btn-sm gap-1" onclick={() => onOpenShare?.()}>
					<Earth class="h-4 w-4" />
					{$t('story.publish')}
				</button>
			{/if}
		{:else}
			{#if visibility === 'public'}
				<Earth class="h-5 w-5 shrink-0 text-success" />
			{:else}
				<LinkVariant class="h-5 w-5 shrink-0 text-success" />
			{/if}
			<div class="min-w-0 flex-1">
				<p class="font-semibold">{$t(`share.story_is_live_${visibility}`)}</p>
				{#if hidden.length}
					<p class="truncate text-sm text-base-content/70">
						{$t('share.story_hidden_groups', { values: { groups: hidden.join(', ') } })}
					</p>
				{/if}
			</div>
			{#if shareUrl}
				<button type="button" class="btn btn-sm gap-1" onclick={copyLink}>
					<ContentCopy class="h-4 w-4" />
					{$t('share.copy_link')}
				</button>
				<a class="btn btn-sm gap-1" href={shareUrl} target="_blank" rel="noopener">
					<OpenInNew class="h-4 w-4" />
					{$t('share.open')}
				</a>
			{/if}
			{#if isOwner}
				<button type="button" class="btn btn-ghost btn-sm gap-1" onclick={() => onOpenShare?.()}>
					<Tune class="h-4 w-4" />
					{$t('story.settings')}
				</button>
			{/if}
		{/if}
	</div>

	<div
		class="min-h-0 flex-1 overflow-hidden rounded-2xl border border-base-300/70 bg-base-100 shadow-sm"
	>
		{#if story}
			<CollectionStory collection={story} {dateFormat} {shareUrl} embedded />
		{:else if failed}
			<p class="p-10 text-center text-base-content/60">{$t('story.load_failed')}</p>
		{:else}
			<div class="flex justify-center p-16">
				<span class="loading loading-spinner loading-lg"></span>
			</div>
		{/if}
	</div>
</div>
