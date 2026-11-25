<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { CommentInboxItem, NotificationItem } from '#lib/types.js';
	import type { Schemas } from '#lib/api/index.js';
	import NotificationRow from './NotificationRow.svelte';
	import CommentTextMultiple from '~icons/mdi/comment-text-multiple-outline';
	import PersonAvatar from './collections/discussion/PersonAvatar.svelte';
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
	// The badge counts comments and notifications together.
	let unread = $state(untrack(() => initialUnread));
	let commentUnread = $state(untrack(() => initialUnread));
	let items = $state<CommentInboxItem[] | null>(null);
	let notifications = $state<NotificationItem[]>([]);
	// The last unread notification count the server gave, kept when a later request for them fails.
	let notificationUnread = 0;
	let root: HTMLDivElement | undefined = $state();

	async function load() {
		lastLoad = Date.now();
		try {
			const [commentsRes, notificationsRes] = await Promise.all([
				fetch('/api/comments/inbox/?limit=20'),
				fetch('/api/notifications/?page_size=20')
			]);
			if (notificationsRes.ok) {
				const data = (await notificationsRes.json()) as Schemas['PaginatedNotificationList'];
				notifications = data.results ?? [];
				notificationUnread = data.unread_count ?? 0;
			}
			if (commentsRes.ok) {
				const data = await commentsRes.json();
				commentUnread = data.unread_count ?? 0;
				items = data.comments ?? [];
			}
			unread = commentUnread + notificationUnread;
			// Only a list that loaded may be marked as seen.
			return notificationsRes.ok ? notificationUnread : 0;
		} catch {
			// The inbox is a convenience; a failed load leaves the last state.
		}
	}

	/**
	 * Opening the inbox is seeing the notifications it shows: those are marked read by id, so one
	 * that arrives meanwhile, or sits beyond the first page, stays unread. They stay marked in the
	 * list until the next open.
	 */
	async function markNotificationsRead() {
		const ids = notifications.filter((item) => !item.read).map((item) => item.id);
		if (!ids.length) return;
		try {
			const res = await fetch('/api/notifications/mark-read/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ ids } satisfies Schemas['MarkNotificationsReadRequest'])
			});
			if (res.ok) {
				const data = (await res.json()) as Schemas['UnreadCount'];
				notificationUnread = data.unread_count;
				unread = commentUnread + notificationUnread;
			}
		} catch {
			// Still unread; the next open tries again.
		}
	}

	/** The person left the visit, so its notification is gone: drop the row and its share of the badge. */
	function dropNotification(item: NotificationItem) {
		notifications = notifications.filter((n) => n.id !== item.id);
		// Only a row that was unread and is still counted lowers the badge; opening the inbox may already have cleared it.
		if (!item.read && notificationUnread > 0) {
			notificationUnread -= 1;
			unread = Math.max(0, unread - 1);
		}
	}

	/** "Mark all read": every comment and every notification, also those beyond the first page. */
	async function markRead() {
		const [comments, notes] = await Promise.all([
			fetch('/api/comments/inbox/mark-seen/', { method: 'POST' }),
			// Leaving `ids` out marks all of them: what this button promises.
			fetch('/api/notifications/mark-read/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({} satisfies Schemas['MarkNotificationsReadRequest'])
			})
		]);
		if (comments.ok) {
			commentUnread = 0;
			items = (items ?? []).map((item) => ({ ...item, unread: false }));
		}
		if (notes.ok) {
			notificationUnread = 0;
			notifications = notifications.map((item) => ({ ...item, read: true }));
		}
		unread = commentUnread + notificationUnread;
	}

	async function toggle() {
		open = !open;
		if (!open) return;
		const notificationUnread = await load();
		if (notificationUnread) void markNotificationsRead();
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
			{:else if items.length === 0 && notifications.length === 0}
				<p class="px-1 py-6 text-center text-sm text-base-content/60">
					{$t('comments.inbox_empty')}
				</p>
			{:else}
				<div class="max-h-[60vh] overflow-y-auto">
					{#if notifications.length > 0}
						<h3 class="px-1 pt-1 text-xs font-semibold uppercase text-base-content/50">
							{$t('notifications.section_title')}
						</h3>
						<ul class="flex flex-col">
							{#each notifications as item (item.id)}
								<li>
									<NotificationRow
										{item}
										onnavigate={() => (open = false)}
										onremoved={dropNotification}
									/>
								</li>
							{/each}
						</ul>
					{/if}
					{#if items.length > 0}
						{#if notifications.length > 0}
							<h3 class="px-1 pt-2 text-xs font-semibold uppercase text-base-content/50">
								{$t('notifications.comments_title')}
							</h3>
						{/if}
						<ul class="menu w-full flex-nowrap p-0">
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
											{#if item.author?.username}
												<!-- The whole entry is a link, so the avatar is not one. -->
												<PersonAvatar person={item.author} size="xs" linked={false} />
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
	{/if}
</div>
