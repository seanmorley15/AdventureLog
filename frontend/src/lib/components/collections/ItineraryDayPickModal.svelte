<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import CalendarBlank from '~icons/mdi/calendar-blank';
	import { t } from 'svelte-i18n';

	interface Props {
		isOpen?: boolean;
		days?: Array<{ date: string; displayDate: string; items: any[] }>;
		itemName?: string;
		scheduledDates?: string[];
		sourceVisitDate?: string | null;
	}

	let {
		isOpen = $bindable(false),
		days = [],
		itemName = 'Item',
		scheduledDates = [],
		sourceVisitDate = null
	}: Props = $props();
	// Optional: source visit info when moving a dated location

	const dispatch = createEventDispatcher();

	let deleteSourceVisit: boolean = false;

	function handleDaySelect(dayDate: string, updateDate: boolean) {
		dispatch('daySelected', { date: dayDate, updateDate, deleteSourceVisit });
		isOpen = false;
	}

	function handleClose() {
		dispatch('close');
		isOpen = false;
	}
</script>

{#if isOpen}
	<dialog class="modal modal-open backdrop-blur-sm">
		<div
			class="modal-box w-11/12 max-w-4xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		>
			<div
				class="sticky top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
			>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<div class="p-1 bg-primary/10 rounded-xl">
							<CalendarBlank class="w-6 h-6 text-primary" />
						</div>
						<div>
							<h1 class="text-xl font-bold text-primary">
								Add "{itemName}" to itinerary
							</h1>
							<p class="text-xs text-base-content/60">
								{days.length}
								{days.length === 1 ? 'day available' : 'days available'}
							</p>
						</div>
					</div>
					<button class="btn btn-ghost btn-square" onclick={handleClose}>
						<span class="text-lg">✕</span>
					</button>
				</div>
			</div>

			<div class="px-2 max-h-[28rem] overflow-y-auto space-y-3 pt-4 pb-4">
				{#if days.length === 0}
					<div class="card bg-base-200 border border-base-300">
						<div class="card-body text-center py-10">
							<CalendarBlank class="w-10 h-10 mx-auto mb-3 opacity-40" />
							<p class="font-semibold opacity-80">No days available</p>
							<p class="text-sm opacity-60">Create itinerary dates to add this item.</p>
						</div>
					</div>
				{/if}

				{#each days as day, index}
					{@const dayNumber = index + 1}
					{@const totalDays = days.length}
					{@const weekday = DateTime.fromISO(day.date).toFormat('ccc')}
					{@const dayOfMonth = DateTime.fromISO(day.date).toFormat('d')}
					{@const monthAbbrev = DateTime.fromISO(day.date).toFormat('LLL')}
					{@const isScheduled = scheduledDates?.includes(day.date)}

					<div
						class="card bg-base-100 border border-base-300 shadow-sm hover:border-primary/60 hover:shadow-md transition-all"
					>
						<div class="card-body p-4">
							<div class="flex flex-row items-center gap-4 mb-3">
								<div class="flex-none">
									<div class="text-center bg-base-300 rounded-xl px-3 py-2 w-16">
										<div class="text-xs opacity-70">{weekday}</div>
										<div class="text-2xl font-bold -mt-1">{dayOfMonth}</div>
										<div class="text-xs opacity-70">{monthAbbrev}</div>
									</div>
								</div>

								<div class="flex-1">
									<div class="flex items-center gap-2">
										<span class="badge badge-primary badge-sm">Day {dayNumber}</span>
										<span class="text-xs opacity-60">of {totalDays}</span>
										{#if isScheduled}
											<span class="badge badge-neutral badge-outline badge-sm"
												>Already scheduled</span
											>
										{/if}
									</div>
									<div class="font-semibold text-base mt-1">{day.displayDate}</div>
									<div class="text-sm opacity-70 flex items-center gap-2 mt-1">
										<span class="badge badge-outline badge-sm"
											>{day.items.length} {day.items.length === 1 ? 'item' : 'items'}</span
										>
									</div>
								</div>
							</div>

							<div class="flex gap-2">
								<button
									type="button"
									class="btn btn-primary btn-sm flex-1"
									disabled={isScheduled}
									onclick={() => handleDaySelect(day.date, true)}
								>
									{isScheduled ? 'Already scheduled' : 'Move to this day'}
								</button>
							</div>
						</div>
					</div>
				{/each}
			</div>

			<div
				class="sticky bottom-0 bg-base-100/90 backdrop-blur-lg border-t border-base-300 -mx-6 -mb-6 px-4 py-3 mt-6 flex items-center justify-between"
			>
				<div class="text-xs text-base-content/60">
					{days.length}
					{days.length === 1 ? 'day available' : 'days available'}
				</div>
				<button type="button" class="btn" onclick={handleClose}>Cancel</button>
			</div>
		</div>
		<form method="dialog" class="modal-backdrop">
			<button type="button" onclick={handleClose}>close</button>
		</form>
	</dialog>
{/if}
