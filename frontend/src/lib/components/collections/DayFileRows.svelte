<script lang="ts">
	import { t } from 'svelte-i18n';
	import type {
		Activity,
		Collection,
		CollectionItineraryDay,
		CollectionItineraryItem,
		Trail,
		Visit
	} from '#lib/types.js';
	import { addToast } from '#lib/toasts.js';
	import { errorMessage } from '#lib/collections/plan.js';
	import Hiking from '~icons/mdi/hiking';
	import MapMarkerPath from '~icons/mdi/map-marker-path';
	import CheckCircle from '~icons/mdi/check-circle';
	import Close from '~icons/mdi/close';

	interface Props {
		collection: Collection;
		/** Null lists the Ideas copies. */
		day?: CollectionItineraryDay | null;
		canModify?: boolean;
		readMode?: boolean;
		anchored?: boolean;
		onLogged?: (result: { item?: CollectionItineraryItem; visit?: Visit }) => void;
	}

	let {
		collection = $bindable(),
		day = null,
		canModify = false,
		readMode = false,
		anchored = false,
		onLogged
	}: Props = $props();

	const planning = $derived(canModify && !readMode);

	const trails = $derived.by(() => {
		const all = collection.day_trails ?? [];
		if (!day) return all.filter((trail) => !trail.day);
		return all.filter((trail) => coversDay(trail, day));
	});
	const activities = $derived(
		(collection.day_activities ?? []).filter((activity) =>
			day ? activity.day === day.id : !activity.day
		)
	);
	const photos = $derived.by(() => {
		const images = collection.day_images ?? [];
		if (!day) {
			return images.filter((image) => image.content_type === 'collection');
		}
		const activityIds = new Set(activities.map((activity) => activity.id));
		const trailIds = new Set(
			trails.filter((trail) => trail.day === day.id).map((trail) => trail.id)
		);
		return images.filter((image) => {
			if (image.content_type === 'collectionitineraryday' && image.object_id === day.id)
				return true;
			if (image.content_type === 'activity' && activityIds.has(image.object_id)) return true;
			if (image.content_type === 'trail' && trailIds.has(image.object_id)) return true;
			return false;
		});
	});

	let stopChoices = $state<{ id: string; name: string }[]>([]);
	let stopFor = $state<string | null>(null);
	let chosenStop = $state('');
	let dateFor = $state<string | null>(null);
	let visitDate = $state(new Date().toISOString().slice(0, 10));
	let logging = $state<string | null>(null);

	function coversDay(trail: Trail, current: CollectionItineraryDay): boolean {
		if (trail.day === current.id) return true;
		if (!trail.day_index || !trail.span_end_index || !current.index) return false;
		return trail.day_index < current.index && current.index <= trail.span_end_index;
	}

	function replaceActivity(activity: Activity) {
		collection.day_activities = (collection.day_activities ?? []).map((existing) =>
			existing.id === activity.id ? activity : existing
		);
	}

	async function remove(url: string, apply: () => void) {
		const res = await fetch(url, { method: 'DELETE' });
		if (res.ok) apply();
		else addToast('error', $t('itinerary.save_failed'));
	}

	function removeTrail(trail: Trail) {
		void remove(`/api/trails/${trail.id}/`, () => {
			collection.day_trails = (collection.day_trails ?? []).filter(
				(existing) => existing.id !== trail.id
			);
		});
	}

	function removeActivity(activity: Activity) {
		void remove(`/api/activities/${activity.id}/`, () => {
			collection.day_activities = (collection.day_activities ?? []).filter(
				(existing) => existing.id !== activity.id
			);
		});
	}

	function removePhoto(id: string) {
		void remove(`/api/images/${id}/`, () => {
			collection.day_images = (collection.day_images ?? []).filter((image) => image.id !== id);
		});
	}

	async function logActivity(activity: Activity, placement?: string, date?: string) {
		logging = activity.id;
		try {
			const res = await fetch(`/api/activities/${activity.id}/log-visit/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					...(placement ? { placement } : {}),
					...(date ? { date } : {})
				})
			});
			const data = await res.json().catch(() => null);
			if (res.ok) {
				replaceActivity(data.activity);
				stopFor = null;
				dateFor = null;
				onLogged?.({ item: data.item, visit: data.visit });
				if (data.created) addToast('success', $t('itinerary.activity_copied'));
				return;
			}
			if (data?.code === 'stop_required') {
				const stops = (data.stops ?? []) as { id: string; name: string }[];
				if (!stops.length) {
					addToast('error', $t('itinerary.no_stop_for_activity'));
					return;
				}
				stopChoices = stops;
				chosenStop = stops[0].id;
				stopFor = activity.id;
				return;
			}
			if (data?.code === 'date_required') {
				dateFor = activity.id;
				return;
			}
			addToast('error', errorMessage(data, $t('itinerary.save_failed')));
		} finally {
			logging = null;
		}
	}

	function startLog(activity: Activity) {
		if (anchored) void logActivity(activity);
		else dateFor = activity.id;
	}
</script>

{#if trails.length || activities.length || photos.length}
	<div class="flex flex-col gap-2">
		{#each trails as trail (trail.id)}
			{@const continuation = Boolean(day && trail.day !== day.id)}
			<div
				class={[
					'flex items-center gap-2 rounded-xl border px-3 py-2.5',
					continuation
						? 'border-dashed border-base-300 bg-base-100/70'
						: 'border-base-300/80 bg-base-100 shadow-sm'
				]}
			>
				<div
					class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary/15 text-secondary"
				>
					<MapMarkerPath class="h-4 w-4" />
				</div>
				<div class="min-w-0 flex-1">
					<div class="flex flex-wrap items-baseline gap-x-2">
						{#if trail.link || trail.wanderer_link}
							<a
								href={trail.link || trail.wanderer_link || undefined}
								target="_blank"
								rel="noopener noreferrer"
								class="truncate font-medium link link-hover"
							>
								{trail.name}
							</a>
						{:else}
							<span class="truncate font-medium">{trail.name}</span>
						{/if}
						{#if continuation}
							<span class="text-xs text-base-content/60">
								{$t('itinerary.continues_trail', { values: { n: trail.day_index } })}
							</span>
						{:else if trail.span_end_index && trail.day_index && trail.span_end_index > trail.day_index}
							<span class="text-xs text-base-content/60">
								{$t('itinerary.listed_through', { values: { n: trail.span_end_index } })}
							</span>
						{/if}
					</div>
				</div>
				{#if planning && !continuation}
					<button
						type="button"
						class="btn btn-sm btn-square btn-ghost text-error"
						aria-label={$t('itinerary.remove')}
						onclick={() => removeTrail(trail)}
					>
						<Close class="h-4 w-4" />
					</button>
				{/if}
			</div>
		{/each}

		{#each activities as activity (activity.id)}
			<div
				class="flex flex-col gap-2 rounded-xl border border-base-300/80 bg-base-100 px-3 py-2.5 shadow-sm"
			>
				<div class="flex items-center gap-2">
					<div
						class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary"
					>
						<Hiking class="h-4 w-4" />
					</div>
					<div class="min-w-0 flex-1">
						<p class="truncate font-medium">{activity.name}</p>
						<p class="text-xs text-base-content/60">{activity.sport_type}</p>
					</div>
					{#if activity.promoted_visit && activity.promoted_location}
						<a
							href={`/locations/${activity.promoted_location}#visit-${activity.promoted_visit}`}
							class="btn btn-sm btn-ghost gap-1 text-success"
						>
							<CheckCircle class="h-4 w-4" />
							{$t('itinerary.visited')}
						</a>
					{:else if canModify && day}
						<button
							type="button"
							class="btn btn-sm btn-ghost"
							disabled={logging === activity.id}
							onclick={() => startLog(activity)}
						>
							{#if logging === activity.id}
								<span class="loading loading-spinner loading-xs"></span>
							{/if}
							{$t('itinerary.log_visit')}
						</button>
					{/if}
					{#if planning}
						<button
							type="button"
							class="btn btn-sm btn-square btn-ghost text-error"
							aria-label={$t('itinerary.remove')}
							onclick={() => removeActivity(activity)}
						>
							<Close class="h-4 w-4" />
						</button>
					{/if}
				</div>
				{#if stopFor === activity.id}
					<form
						class="flex flex-wrap items-center gap-2"
						onsubmit={(event) => {
							event.preventDefault();
							void logActivity(
								activity,
								chosenStop,
								dateFor === activity.id ? visitDate : undefined
							);
						}}
					>
						<label class="text-sm" for={`stop-${activity.id}`}>{$t('itinerary.choose_stop')}</label>
						<select id={`stop-${activity.id}`} class="select select-sm" bind:value={chosenStop}>
							{#each stopChoices as stop (stop.id)}
								<option value={stop.id}>{stop.name}</option>
							{/each}
						</select>
						<button type="submit" class="btn btn-sm btn-primary">{$t('itinerary.log')}</button>
					</form>
				{/if}
				{#if dateFor === activity.id && stopFor !== activity.id}
					<form
						class="flex flex-wrap items-center gap-2"
						onsubmit={(event) => {
							event.preventDefault();
							void logActivity(activity, undefined, visitDate);
						}}
					>
						<label class="text-sm" for={`date-${activity.id}`}>{$t('itinerary.visit_date')}</label>
						<input
							id={`date-${activity.id}`}
							type="date"
							class="input input-sm"
							bind:value={visitDate}
							required
						/>
						<button type="submit" class="btn btn-sm btn-primary">{$t('itinerary.log')}</button>
					</form>
				{/if}
			</div>
		{/each}

		{#if photos.length}
			<div class="flex flex-wrap gap-2">
				{#each photos as photo (photo.id)}
					<div class="relative">
						<img src={photo.image} alt="" class="h-16 w-16 rounded-lg object-cover" />
						{#if planning}
							<button
								type="button"
								class="btn btn-xs btn-circle btn-ghost absolute -right-1 -top-1 bg-base-100"
								aria-label={$t('itinerary.remove')}
								onclick={() => removePhoto(photo.id)}
							>
								<Close class="h-3 w-3" />
							</button>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
