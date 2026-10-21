<script lang="ts">
	import { apiErrorMessage } from '$lib/api';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { t } from 'svelte-i18n';
	import type { CollectionComment, CommentThread, CommentThreadResponse } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import PersonAvatar from './PersonAvatar.svelte';
	import PersonName from './PersonName.svelte';
	import CommentOutline from '~icons/mdi/comment-outline';
	import Send from '~icons/mdi/send';
	import Reply from '~icons/mdi/reply';
	import Pencil from '~icons/mdi/pencil-outline';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';

	type DayOption = { id: string; index: number; name?: string | null };
	type Member = { username: string; name: string };

	interface Props {
		collectionId: string;
		thread: CommentThread;
		/** Plan thread: the days a comment can be about, and the day being viewed. */
		days?: DayOption[];
		dayFilter?: string | null;
		/** Plan thread: members offered for @mentions. */
		members?: Member[];
		/** Story thread: where a reader signs in to comment. */
		signInHref?: string | null;
		onChange?: () => void;
	}

	let {
		collectionId,
		thread,
		days = [],
		dayFilter = null,
		members = [],
		signInHref = null,
		onChange
	}: Props = $props();

	let data = $state<CommentThreadResponse | null>(null);
	let failed = $state(false);
	let posting = $state(false);
	let body = $state('');
	let replyTo = $state<CollectionComment | null>(null);
	let replyBody = $state('');
	let editingId = $state<string | null>(null);
	let editBody = $state('');
	let confirmDelete = $state<string | null>(null);
	let mentionQuery = $state<string | null>(null);
	let composer: HTMLTextAreaElement | undefined = $state();

	let comments = $derived(
		(data?.comments ?? []).filter((comment) => !dayFilter || comment.day === dayFilter)
	);
	let mentionMatches = $derived(
		mentionQuery === null
			? []
			: members
					.filter(
						(m) =>
							m.username.toLowerCase().startsWith(mentionQuery!.toLowerCase()) ||
							m.name.toLowerCase().includes(mentionQuery!.toLowerCase())
					)
					.slice(0, 6)
	);

	// A new comment is about the day being viewed, or the whole trip when viewing all days.
	let postingTo = $derived.by(() => {
		const day = days.find((d) => d.id === dayFilter);
		return day ? $t('story.day_n', { values: { n: day.index } }) : $t('comments.whole_trip');
	});

	// An unlisted story is readable only with its link secret. Readers carry it in
	// ?s= on the page; every comment request needs it too, or the API answers 404.
	let storySecret = $derived(thread === 'story' ? $page.url.searchParams.get('s') : null);

	function withSecret(url: string) {
		if (!storySecret) return url;
		return `${url}${url.includes('?') ? '&' : '?'}s=${encodeURIComponent(storySecret)}`;
	}

	async function load() {
		failed = false;
		const params = new URLSearchParams({ thread });
		if (storySecret) params.set('s', storySecret);
		try {
			const res = await fetch(`/api/collections/${collectionId}/comments/?${params}`);
			if (!res.ok) throw new Error(String(res.status));
			data = await res.json();
		} catch {
			failed = true;
		}
	}

	async function send(method: string, url: string, payload?: unknown) {
		posting = true;
		try {
			const res = await fetch(withSecret(url), {
				method,
				headers: { 'Content-Type': 'application/json' },
				body: payload === undefined ? undefined : JSON.stringify(payload)
			});
			if (!res.ok) {
				const error = await res.json().catch(() => null);
				addToast('error', apiErrorMessage(error, $t('comments.failed')));
				return false;
			}
			await load();
			onChange?.();
			return true;
		} finally {
			posting = false;
		}
	}

	async function post(event?: Event) {
		event?.preventDefault();
		if (!body.trim()) return;
		const ok = await send('POST', `/api/collections/${collectionId}/comments/`, {
			thread,
			body,
			...(thread === 'plan' && dayFilter ? { day: dayFilter } : {})
		});
		if (ok) body = '';
	}

	async function postReply(event: Event) {
		event.preventDefault();
		if (!replyTo || !replyBody.trim()) return;
		const ok = await send('POST', `/api/collections/${collectionId}/comments/`, {
			thread,
			body: replyBody,
			parent: replyTo.id
		});
		if (ok) {
			replyTo = null;
			replyBody = '';
		}
	}

	async function saveEdit(event: Event) {
		event.preventDefault();
		if (!editingId || !editBody.trim()) return;
		const ok = await send('PATCH', `/api/comments/${editingId}/`, { body: editBody });
		if (ok) editingId = null;
	}

	async function remove(comment: CollectionComment) {
		if (confirmDelete !== comment.id) {
			confirmDelete = comment.id;
			return;
		}
		confirmDelete = null;
		await send('DELETE', `/api/comments/${comment.id}/`);
	}

	function submitOnShortcut(event: KeyboardEvent, submit: (event: Event) => void) {
		if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) submit(event);
	}

	function trackMention(event: Event) {
		const el = event.currentTarget as HTMLTextAreaElement;
		const before = el.value.slice(0, el.selectionStart ?? el.value.length);
		const match = /(?:^|\s)@([\w.+-]*)$/.exec(before);
		mentionQuery = match && members.length ? match[1] : null;
	}

	function insertMention(member: Member) {
		if (!composer) return;
		const caret = composer.selectionStart ?? body.length;
		const before = body.slice(0, caret).replace(/@([\w.+-]*)$/, `@${member.username} `);
		body = before + body.slice(caret);
		mentionQuery = null;
		requestAnimationFrame(() => {
			composer?.focus();
			composer?.setSelectionRange(before.length, before.length);
		});
	}

	/** Body text with @mentions of members picked out. Rendered as text, never HTML. */
	function parts(text: string, mentions: string[] = []) {
		const known = new Set(mentions.map((m) => m.toLowerCase()));
		return text.split(/(@[\w.+-]+)/g).map((part) => ({
			text: part,
			mention: part.startsWith('@') && known.has(part.slice(1).toLowerCase())
		}));
	}

	function when(value: string) {
		const seconds = (new Date(value).getTime() - Date.now()) / 1000;
		const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
		const steps: [Intl.RelativeTimeFormatUnit, number][] = [
			['year', 31536000],
			['month', 2592000],
			['week', 604800],
			['day', 86400],
			['hour', 3600],
			['minute', 60]
		];
		for (const [unit, size] of steps) {
			if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit);
		}
		return $t('comments.just_now');
	}

	function dayLabel(index: number | null) {
		return index ? $t('story.day_n', { values: { n: index } }) : null;
	}

	onMount(load);
</script>

{#snippet comment(item: CollectionComment, isReply: boolean)}
	<div class="flex gap-3">
		<PersonAvatar person={item.author} size={isReply ? 'sm' : 'md'} />
		<div class="min-w-0 flex-1">
			<div class="rounded-2xl bg-base-200 px-3 py-2">
				<div class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
					<PersonName person={item.author} fallback={$t('comments.someone')} />
					{#if item.author.is_guest}
						<span class="badge badge-ghost badge-xs">{$t('comments.guest')}</span>
					{/if}
					{#if !isReply && dayLabel(item.day_index)}
						<span class="badge badge-outline badge-xs">{dayLabel(item.day_index)}</span>
					{/if}
					<span
						class="text-xs text-base-content/50"
						title={new Date(item.created_at).toLocaleString()}
					>
						{when(item.created_at)}{item.edited_at ? ` · ${$t('comments.edited')}` : ''}
					</span>
				</div>
				{#if editingId === item.id}
					<form class="mt-2 space-y-2" onsubmit={saveEdit}>
						<textarea
							class="textarea w-full"
							rows="3"
							maxlength="4000"
							bind:value={editBody}
							onkeydown={(e) => submitOnShortcut(e, saveEdit)}
						></textarea>
						<div class="flex justify-end gap-2">
							<button type="button" class="btn btn-ghost btn-xs" onclick={() => (editingId = null)}>
								{$t('adventures.cancel')}
							</button>
							<button type="submit" class="btn btn-primary btn-xs" disabled={posting}>
								{$t('comments.save')}
							</button>
						</div>
					</form>
				{:else}
					<p class="mt-0.5 whitespace-pre-wrap break-words text-sm">
						{#each parts(item.body, item.mentions) as part, i (i)}
							{#if part.mention}
								<span class="font-semibold text-primary">{part.text}</span>
							{:else}
								{part.text}
							{/if}
						{/each}
					</p>
				{/if}
			</div>
			<div class="mt-0.5 flex gap-1 pl-2">
				{#if !isReply && data?.can_post}
					<button
						type="button"
						class="btn btn-ghost btn-xs gap-1"
						onclick={() => {
							replyTo = item;
							replyBody = '';
						}}
					>
						<Reply class="h-3.5 w-3.5" />
						{$t('comments.reply')}
					</button>
				{/if}
				{#if item.can_edit && editingId !== item.id}
					<button
						type="button"
						class="btn btn-ghost btn-xs gap-1"
						onclick={() => {
							editingId = item.id;
							editBody = item.body;
						}}
					>
						<Pencil class="h-3.5 w-3.5" />
						{$t('comments.edit')}
					</button>
				{/if}
				{#if item.can_delete}
					<button
						type="button"
						class="btn btn-ghost btn-xs gap-1 {confirmDelete === item.id ? 'text-error' : ''}"
						disabled={posting}
						onclick={() => remove(item)}
						onblur={() => (confirmDelete = null)}
					>
						<TrashCanOutline class="h-3.5 w-3.5" />
						{confirmDelete === item.id ? $t('comments.confirm_delete') : $t('comments.delete')}
					</button>
				{/if}
			</div>
		</div>
	</div>
{/snippet}

<div class="space-y-4">
	{#if data?.can_post}
		<form class="relative space-y-2" onsubmit={post}>
			<textarea
				bind:this={composer}
				class="textarea w-full"
				rows="3"
				maxlength="4000"
				placeholder={thread === 'plan'
					? $t('comments.plan_placeholder')
					: $t('comments.story_placeholder')}
				bind:value={body}
				oninput={trackMention}
				onkeydown={(e) => submitOnShortcut(e, post)}
			></textarea>
			{#if mentionMatches.length}
				<ul
					class="menu absolute left-0 top-full z-20 -mt-1 w-64 rounded-box border border-base-300 bg-base-100 p-1 shadow-lg"
					role="listbox"
				>
					{#each mentionMatches as member (member.username)}
						<li>
							<button type="button" onclick={() => insertMention(member)}>
								<span class="font-medium">{member.name}</span>
								<span class="text-xs text-base-content/60">@{member.username}</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}
			<div class="flex flex-wrap items-center gap-2">
				{#if thread === 'plan' && days.length}
					<!-- The day comes from the selector above the list. -->
					<span class="badge badge-outline gap-1">{postingTo}</span>
				{/if}
				<span class="hidden text-xs text-base-content/50 sm:inline">
					{thread === 'plan' ? $t('comments.mention_hint') : $t('comments.story_public_hint')}
				</span>
				<button
					type="submit"
					class="btn btn-primary btn-sm ml-auto gap-1"
					disabled={posting || !body.trim()}
				>
					<Send class="h-4 w-4" />
					{$t('comments.post')}
				</button>
			</div>
		</form>
	{:else if data && thread === 'story'}
		<div class="alert rounded-xl text-sm">
			<CommentOutline class="h-5 w-5 shrink-0" />
			{#if signInHref}
				<span>{$t('comments.sign_in_to_comment')}</span>
				<a class="btn btn-primary btn-sm" href={signInHref}>{$t('auth.login')}</a>
			{:else}
				<span>{$t('comments.story_read_only')}</span>
			{/if}
		</div>
	{/if}

	{#if failed}
		<p class="text-sm text-base-content/60">{$t('comments.load_failed')}</p>
	{:else if !data}
		<div class="flex justify-center py-6">
			<span class="loading loading-spinner loading-sm"></span>
		</div>
	{:else if comments.length === 0}
		<div class="flex flex-col items-center gap-2 py-8 text-center text-base-content/60">
			<CommentOutline class="h-8 w-8 opacity-50" />
			<p class="text-sm">
				{dayFilter ? $t('comments.none_for_day') : $t('comments.none_yet')}
			</p>
		</div>
	{:else}
		<ul class="space-y-5">
			{#each comments as item (item.id)}
				<li class="space-y-3">
					{@render comment(item, false)}
					{#if item.replies?.length || replyTo?.id === item.id}
						<div class="ml-12 space-y-3 border-l-2 border-base-300 pl-3">
							{#each item.replies ?? [] as reply (reply.id)}
								{@render comment(reply, true)}
							{/each}
							{#if replyTo?.id === item.id}
								<form class="space-y-2" onsubmit={postReply}>
									<textarea
										class="textarea w-full"
										rows="2"
										maxlength="4000"
										placeholder={$t('comments.reply_placeholder', {
											values: { name: item.author.name || $t('comments.someone') }
										})}
										bind:value={replyBody}
										onkeydown={(e) => submitOnShortcut(e, postReply)}
									></textarea>
									<div class="flex justify-end gap-2">
										<button
											type="button"
											class="btn btn-ghost btn-xs"
											onclick={() => (replyTo = null)}
										>
											{$t('adventures.cancel')}
										</button>
										<button
											type="submit"
											class="btn btn-primary btn-xs gap-1"
											disabled={posting || !replyBody.trim()}
										>
											<Send class="h-3.5 w-3.5" />
											{$t('comments.reply')}
										</button>
									</div>
								</form>
							{/if}
						</div>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>
