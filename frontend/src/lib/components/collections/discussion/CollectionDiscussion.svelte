<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Collection } from '#lib/types.js';
	import { indexedDays } from '#lib/collections/plan.js';
	import CommentThread from './CommentThread.svelte';
	import ActivityFeed from './ActivityFeed.svelte';
	import CommentMultiple from '~icons/mdi/comment-multiple-outline';
	import History from '~icons/mdi/history';
	import ChevronLeft from '~icons/mdi/chevron-left';
	import ChevronRight from '~icons/mdi/chevron-right';

	interface Props {
		collection: Collection;
		/** Owner and editors also see the activity feed. Viewers read comments only. */
		canEdit: boolean;
	}

	let { collection, canEdit }: Props = $props();

	// '' means every day; otherwise the id of the day being read and commented on.
	let selectedDay = $state('');
	let dayFilter = $derived(selectedDay || null);
	let refreshKey = $state(0);

	let days = $derived(
		indexedDays(collection).map((day) => ({ id: day.id, index: day.index ?? 0, name: day.name }))
	);
	let dayPosition = $derived(days.findIndex((day) => day.id === selectedDay));

	// Previous from "all days" goes to the first day, next from it to the first day too.
	function step(direction: -1 | 1) {
		const next = dayPosition < 0 ? (direction === 1 ? 0 : -1) : dayPosition + direction;
		if (next >= 0 && next < days.length) selectedDay = days[next].id;
	}

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

			<!-- One day control for both reading and writing: it filters the list and is the
			     day a new comment is about. A dropdown with step buttons stays tidy at any
			     number of days. -->
			{#if days.length}
				<div class="join w-full">
					<button
						type="button"
						class="btn btn-square join-item"
						aria-label={$t('comments.previous_day')}
						disabled={dayPosition <= 0}
						onclick={() => step(-1)}
					>
						<ChevronLeft class="h-5 w-5" />
					</button>
					<select
						class="select join-item min-w-0 flex-1"
						aria-label={$t('comments.about')}
						bind:value={selectedDay}
					>
						<option value="">{$t('comments.all_days')}</option>
						{#each days as day (day.id)}
							<option value={day.id}>
								{$t('story.day_n', { values: { n: day.index } })}{day.name ? ` · ${day.name}` : ''}
							</option>
						{/each}
					</select>
					<button
						type="button"
						class="btn btn-square join-item"
						aria-label={$t('comments.next_day')}
						disabled={dayPosition >= days.length - 1}
						onclick={() => step(1)}
					>
						<ChevronRight class="h-5 w-5" />
					</button>
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
