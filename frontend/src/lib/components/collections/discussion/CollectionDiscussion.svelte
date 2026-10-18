<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Collection } from '$lib/types';
	import { indexedDays } from '$lib/collections/plan';
	import CommentThread from './CommentThread.svelte';
	import ActivityFeed from './ActivityFeed.svelte';
	import CommentMultiple from '~icons/mdi/comment-multiple-outline';
	import History from '~icons/mdi/history';

	interface Props {
		collection: Collection;
		/** Owner and editors also see the activity feed. Viewers read comments only. */
		canEdit: boolean;
	}

	let { collection, canEdit }: Props = $props();

	let dayFilter = $state<string | null>(null);
	let refreshKey = $state(0);

	let days = $derived(
		indexedDays(collection).map((day) => ({ id: day.id, index: day.index ?? 0, name: day.name }))
	);
	let members = $derived(
		(collection.collaborators ?? []).map((person) => ({
			username: person.username,
			name: [person.first_name, person.last_name].filter(Boolean).join(' ') || person.username
		}))
	);
</script>

<!-- Phones: one scrolling column. Wide screens: comments and activity side by side,
     each scrolling on its own. Bodies are block, not flex, so content never shrinks. -->
<div
	class="h-full min-h-0 space-y-4 overflow-y-auto pb-4 lg:grid lg:gap-4 lg:space-y-0 lg:overflow-hidden lg:pb-0 {canEdit
		? 'lg:grid-cols-[minmax(0,1fr)_22rem]'
		: ''}"
>
	<section class="card min-w-0 border border-base-300 bg-base-100 lg:min-h-0">
		<div class="card-body block min-w-0 space-y-4 p-4 md:p-6 lg:min-h-0 lg:overflow-y-auto">
			<div class="flex items-start gap-3">
				<div class="shrink-0 rounded-lg bg-primary/10 p-2">
					<CommentMultiple class="h-5 w-5 text-primary" />
				</div>
				<div class="min-w-0">
					<h2 class="text-lg font-bold">{$t('comments.plan_title')}</h2>
					<p class="field-hint">
						{canEdit ? $t('comments.plan_hint') : $t('comments.plan_hint_viewer')}
					</p>
				</div>
			</div>

			{#if days.length}
				<div class="tabs tabs-box w-full max-w-full flex-nowrap overflow-x-auto bg-base-200">
					<button
						type="button"
						class="tab tab-sm shrink-0 {dayFilter === null ? 'tab-active' : ''}"
						onclick={() => (dayFilter = null)}
					>
						{$t('comments.all')}
					</button>
					{#each days as day (day.id)}
						<button
							type="button"
							class="tab tab-sm shrink-0 {dayFilter === day.id ? 'tab-active' : ''}"
							onclick={() => (dayFilter = day.id)}
						>
							{$t('story.day_n', { values: { n: day.index } })}
						</button>
					{/each}
				</div>
			{/if}

			<CommentThread
				collectionId={collection.id}
				thread="plan"
				{days}
				{dayFilter}
				{members}
				onChange={() => (refreshKey += 1)}
			/>
		</div>
	</section>

	{#if canEdit}
		<aside class="card min-w-0 border border-base-300 bg-base-100 lg:min-h-0">
			<div class="card-body block min-w-0 space-y-4 p-4 md:p-6 lg:min-h-0 lg:overflow-y-auto">
				<div class="flex items-start gap-3">
					<div class="shrink-0 rounded-lg bg-primary/10 p-2">
						<History class="h-5 w-5 text-primary" />
					</div>
					<div class="min-w-0">
						<h2 class="text-lg font-bold">{$t('activity.title')}</h2>
						<p class="field-hint">{$t('activity.hint')}</p>
					</div>
				</div>
				<ActivityFeed collectionId={collection.id} {refreshKey} />
			</div>
		</aside>
	{/if}
</div>
