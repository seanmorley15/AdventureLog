<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { CommentInboxItem } from '$lib/types';
	import CommentTextMultiple from '~icons/mdi/comment-text-multiple-outline';
	import CheckAll from '~icons/mdi/check-all';

	interface Props {
		/** Unread count from the session lookup, so the badge needs no request of its own. */
		initialUnread?: number;
	}

	let { initialUnread = 0 }: Props = $props();

	// Window focus refreshes the badge, at most once a minute.
	const FOCUS_REFRESH_MS = 60_000;
	let lastLoad = Date.now();

	let open = $state(false);
	let unread = $state(untrack(() => initialUnread));
	let items = $state<CommentInboxItem[] | null>(null);
	let root: HTMLDivElement | undefined = $state();

	async function load() {
		lastLoad = Date.now();
		try {
			const res = await fetch('/api/collection-comments/inbox/?limit=20');
			if (!res.ok) return;
			const data = await res.json();
			unread = data.unread_count ?? 0;
			items = data.comments ?? [];
		} catch {
			// The inbox is a convenience; a failed load leaves the last state.
		}
	}

	async function markRead() {
		const res = await fetch('/api/collection-comments/inbox/seen/', { method: 'POST' });
		if (res.ok) {
			unread = 0;
			items = (items ?? []).map((item) => ({ ...item, unread: false }));
		}
	}

	function toggle() {
		open = !open;
		if (open) void load();
	}

	function href(item: CommentInboxItem) {
		const view = item.thread === 'story' ? 'story' : 'discussion';
		return `/collections/${item.collection.id}?view=${view}`;
	}

	function when(value: string) {
		return new Date(value).toLocaleString(undefined, {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});
	}

	onMount(() => {
		const onFocus = () => {
			if (Date.now() - lastLoad >= FOCUS_REFRESH_MS) void load();
		};
		const onClick = (event: MouseEvent) => {
			if (open && root && !root.contains(event.target as Node)) open = false;
		};
		window.addEventListener('focus', onFocus);
		document.addEventListener('click', onClick);
		return () => {
			window.removeEventListener('focus', onFocus);
			document.removeEventListener('click', onClick);
		};
	});
</script>

<div bind:this={root} class="dropdown dropdown-end z-[999]" class:dropdown-open={open}>
	<button
		type="button"
		class="btn btn-ghost btn-sm btn-square indicator"
		aria-label={$t('comments.inbox_title')}
		title={$t('comments.inbox_title')}
		aria-haspopup="menu"
		aria-expanded={open}
		onclick={toggle}
	>
		{#if unread > 0}
			<span class="indicator-item badge badge-primary badge-xs">{unread > 99 ? '99+' : unread}</span
			>
		{/if}
		<CommentTextMultiple class="h-5 w-5" />
	</button>
	{#if open}
		<div
			class="dropdown-content z-[999] mt-3 w-80 rounded-2xl border border-base-300 bg-base-100 p-3 shadow-2xl"
			role="menu"
		>
			<div class="mb-2 flex items-center justify-between gap-2 px-1">
				<h2 class="font-semibold">{$t('comments.inbox_title')}</h2>
				{#if unread > 0}
					<button type="button" class="btn btn-ghost btn-xs gap-1" onclick={markRead}>
						<CheckAll class="h-4 w-4" />
						{$t('comments.mark_read')}
					</button>
				{/if}
			</div>
			{#if items === null}
				<div class="flex justify-center py-6">
					<span class="loading loading-spinner loading-sm"></span>
				</div>
			{:else if items.length === 0}
				<p class="px-1 py-6 text-center text-sm text-base-content/60">
					{$t('comments.inbox_empty')}
				</p>
			{:else}
				<ul class="menu max-h-[60vh] w-full flex-nowrap overflow-y-auto p-0">
					{#each items as item (item.id)}
						<li>
							<a
								href={href(item)}
								class="flex flex-col items-start gap-0.5"
								onclick={() => (open = false)}
							>
								<span class="flex w-full items-center gap-2">
									{#if item.unread}
										<span
											class="h-2 w-2 shrink-0 rounded-full bg-primary"
											aria-label={$t('comments.unread')}
										></span>
									{/if}
									<span class="truncate text-sm font-semibold">{item.author_name}</span>
									{#if item.mentions_me}
										<span class="badge badge-primary badge-xs">@</span>
									{/if}
									<span class="ml-auto shrink-0 text-xs text-base-content/50"
										>{when(item.created_at)}</span
									>
								</span>
								<span class="line-clamp-2 text-xs text-base-content/70">{item.excerpt}</span>
								<span class="text-xs text-base-content/50">
									{item.collection.name} ·
									{item.thread === 'story' ? $t('comments.on_story') : $t('comments.on_plan')}
									{#if item.day_index}
										· {$t('story.day_n', { values: { n: item.day_index } })}
									{/if}
								</span>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	{/if}
</div>
