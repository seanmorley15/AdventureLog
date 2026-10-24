<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { CalendarDisplayEvent } from '$lib/calendar/types';
	import { groupEventsByDay } from '$lib/calendar/events';
	import CalendarBlank from '~icons/mdi/calendar-blank';

	interface Props {
		events?: CalendarDisplayEvent[];
		emptyMessage?: string;
	}

	let { events = [], emptyMessage = '' }: Props = $props();

	const dispatch = createEventDispatcher<{ select: CalendarDisplayEvent }>();

	let grouped = $derived(groupEventsByDay(events));
</script>

{#if grouped.length === 0}
	<div class="flex flex-col items-center justify-center py-16 text-center text-base-content/60">
		<CalendarBlank class="w-12 h-12 mb-3 opacity-40" />
		<p>{emptyMessage || $t('calendar.no_events_in_range')}</p>
	</div>
{:else}
	<div class="space-y-6">
		{#each grouped as group (group.date)}
			<section>
				<h3
					class="sticky top-0 z-10 bg-base-100/95 backdrop-blur-sm py-2 text-sm font-semibold text-primary border-b border-base-300"
				>
					{group.label}
				</h3>
				<div class="divide-y divide-base-300/60">
					{#each group.events as event (event.id)}
						<button
							type="button"
							class="w-full text-left py-3 px-1 hover:bg-base-200/60 rounded-lg transition-colors"
							onclick={() => dispatch('select', event)}
						>
							<div class="flex items-start gap-3">
								<div
									class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-lg"
									style={`background-color: ${event.backgroundColor}20; color: ${event.backgroundColor}`}
								>
									{event.extendedProps.icon}
								</div>
								<div class="min-w-0 flex-1">
									<div class="flex flex-wrap items-center gap-2">
										<span class="font-semibold truncate">{event.extendedProps.adventureName}</span>
										<span class="badge badge-sm badge-ghost capitalize"
											>{event.extendedProps.type}</span
										>
									</div>
									<p class="text-sm text-base-content/70 mt-0.5">
										{#if event.extendedProps.isAllDay}
											{$t('calendar.all_day_event')}
										{:else}
											{event.extendedProps.formattedStart}
										{/if}
									</p>
									{#if event.extendedProps.location}
										<p class="text-xs text-base-content/60 mt-1 truncate">
											{event.extendedProps.location}
										</p>
									{/if}
									{#if event.extendedProps.collectionName}
										<p class="text-xs text-base-content/50 mt-1">
											{$t('calendar.in_collection')}: {event.extendedProps.collectionName}
										</p>
									{/if}
								</div>
							</div>
						</button>
					{/each}
				</div>
			</section>
		{/each}
	</div>
{/if}
