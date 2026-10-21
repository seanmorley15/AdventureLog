<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { CollectionActivityEvent } from '$lib/types';
	import PersonAvatar from './PersonAvatar.svelte';
	import CalendarArrowRight from '~icons/mdi/calendar-arrow-right';
	import SwapVertical from '~icons/mdi/swap-vertical';
	import CursorMove from '~icons/mdi/cursor-move';
	import CommentOutline from '~icons/mdi/comment-outline';
	import AccountPlus from '~icons/mdi/account-plus-outline';
	import AccountMinus from '~icons/mdi/account-minus-outline';
	import History from '~icons/mdi/history';

	interface Props {
		collectionId: string;
		/** Change it to reload, e.g. after a comment is posted. */
		refreshKey?: number;
	}

	let { collectionId, refreshKey = 0 }: Props = $props();

	let events = $state<CollectionActivityEvent[] | null>(null);
	let failed = $state(false);

	const ICONS = {
		day_moved: SwapVertical,
		item_moved: CursorMove,
		anchor_changed: CalendarArrowRight,
		comment_added: CommentOutline,
		member_added: AccountPlus,
		member_removed: AccountMinus
	};

	$effect(() => {
		void refreshKey;
		const controller = new AbortController();
		fetch(`/api/collections/${collectionId}/activity/?limit=100`, { signal: controller.signal })
			.then(async (res) => {
				if (!res.ok) throw new Error(String(res.status));
				events = await res.json();
				failed = false;
			})
			.catch((error) => {
				if (error?.name !== 'AbortError') failed = true;
			});
		return () => controller.abort();
	});

	function describe(event: CollectionActivityEvent) {
		const d = event.data ?? {};
		const who = event.actor_name || $t('comments.someone');
		switch (event.verb) {
			case 'day_moved':
				return $t('activity.day_moved', { values: { who, from: d.from_index, to: d.to_index } });
			case 'item_moved':
				if (d.count) return $t('activity.items_reordered', { values: { who, count: d.count } });
				if (d.day_index)
					return $t('activity.item_moved_to_day', {
						values: { who, name: d.name ?? $t('activity.an_item'), day: d.day_index }
					});
				return $t(d.is_global ? 'activity.item_moved_trip_wide' : 'activity.item_moved_to_ideas', {
					values: { who, name: d.name ?? $t('activity.an_item') }
				});
			case 'anchor_changed':
				return d.to_date
					? $t('activity.anchor_changed', { values: { who, date: d.to_date } })
					: $t('activity.anchor_cleared', { values: { who } });
			case 'comment_added':
				return $t(d.thread === 'story' ? 'activity.story_comment' : 'activity.plan_comment', {
					values: { who }
				});
			case 'member_added':
				return $t('activity.member_added', {
					values: { who: d.username ?? who, role: d.role ?? '' }
				});
			case 'member_removed':
				return d.left
					? $t('activity.member_left', { values: { who: d.username ?? who } })
					: $t('activity.member_removed', { values: { who, name: d.username ?? '' } });
		}
		return event.verb;
	}

	function when(value: string) {
		return new Date(value).toLocaleString(undefined, {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});
	}
</script>

{#if failed}
	<p class="text-sm text-base-content/60">{$t('activity.load_failed')}</p>
{:else if !events}
	<div class="flex justify-center py-6">
		<span class="loading loading-spinner loading-sm"></span>
	</div>
{:else if events.length === 0}
	<div class="flex flex-col items-center gap-2 py-8 text-center text-base-content/60">
		<History class="h-8 w-8 opacity-50" />
		<p class="text-sm">{$t('activity.empty')}</p>
	</div>
{:else}
	<ol class="space-y-3">
		{#each events as event (event.id)}
			{@const Icon = ICONS[event.verb] ?? History}
			<li class="flex items-start gap-3">
				{#if event.actor?.username}
					<div class="mt-0.5 shrink-0">
						<PersonAvatar
							person={{
								name: event.actor_name,
								username: event.actor.username,
								profile_pic: event.actor.profile_pic,
								can_view_profile: event.actor.can_view_profile
							}}
							size="sm"
						/>
					</div>
				{:else}
					<div class="mt-0.5 shrink-0 self-start rounded-lg bg-primary/10 p-1.5">
						<Icon class="h-4 w-4 text-primary" />
					</div>
				{/if}
				<div class="min-w-0">
					<p class="text-sm">{describe(event)}</p>
					{#if event.verb === 'comment_added' && event.data?.excerpt}
						<p class="truncate text-xs text-base-content/60">“{event.data.excerpt}”</p>
					{/if}
					<p class="text-xs text-base-content/50">{when(event.created_at)}</p>
				</div>
			</li>
		{/each}
	</ol>
{/if}
