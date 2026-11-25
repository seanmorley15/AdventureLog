<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { NotificationItem } from '#lib/types.js';
	import { addToast } from '#lib/toasts.js';
	import PersonAvatar from './collections/discussion/PersonAvatar.svelte';

	interface Props {
		item: NotificationItem;
		/** Called when the row's link is followed, so the inbox can close. */
		onnavigate?: () => void;
		/** Called once you are off the visit, so the inbox can drop this row. */
		onremoved?: (item: NotificationItem) => void;
	}

	let { item, onnavigate, onremoved }: Props = $props();

	let busy = $state(false);
	let removed = $state(false);

	let name = $derived(item.actor.name || $t('notifications.someone'));
	let summary = $derived(item.count > 1);
	let href = $derived(
		summary
			? item.collection_id
				? `/collections/${item.collection_id}`
				: item.location_id
					? `/locations/${item.location_id}`
					: null
			: item.location_id
				? `/locations/${item.location_id}`
				: item.collection_id
					? `/collections/${item.collection_id}`
					: null
	);
	// Leaving needs the one visit, which only the single form names.
	let canRemove = $derived(!summary && Boolean(item.visit_id) && !removed);

	let text = $derived.by(() => {
		if (summary) {
			return item.collection_name
				? $t('notifications.added_you_to_visits_on', {
						values: { name, count: item.count, trip: item.collection_name }
					})
				: $t('notifications.added_you_to_visits', { values: { name, count: item.count } });
		}
		return item.location_name
			? $t('notifications.added_you_to_visit_at', { values: { name, place: item.location_name } })
			: $t('notifications.added_you_to_visit', { values: { name } });
	});

	function day(value: string) {
		const [y, m, d] = value.split('-').map(Number);
		return new Date(y, m - 1, d).toLocaleDateString(undefined, {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		});
	}

	let dates = $derived.by(() => {
		if (!item.start_date) return '';
		if (!item.end_date || item.end_date === item.start_date) return day(item.start_date);
		return `${day(item.start_date)} – ${day(item.end_date)}`;
	});

	const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
		['year', 31_536_000],
		['month', 2_592_000],
		['day', 86_400],
		['hour', 3_600],
		['minute', 60]
	];

	function ago(value: string) {
		const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
		const format = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
		for (const [unit, size] of UNITS) {
			if (Math.abs(seconds) >= size) return format.format(Math.round(seconds / size), unit);
		}
		return format.format(0, 'second');
	}

	async function removeMe() {
		busy = true;
		try {
			const response = await fetch(`/api/visits/${item.visit_id}/leave/`, { method: 'POST' });
			// 204: you were the last traveler, so the visit is gone. 200: the visit lost you.
			if (response.status === 204 || response.ok) {
				removed = true;
				onremoved?.(item);
				addToast('success', $t('notifications.removed'));
			} else {
				addToast('error', $t('notifications.remove_failed'));
			}
		} catch {
			addToast('error', $t('notifications.remove_failed'));
		} finally {
			busy = false;
		}
	}
</script>

{#snippet body()}
	{#if item.read === false}
		<span
			class="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary"
			role="img"
			aria-label={$t('notifications.unread')}
		></span>
	{/if}
	{#if item.actor.username}
		<PersonAvatar person={item.actor} size="xs" linked={false} />
	{/if}
	<span class="min-w-0 flex-1">
		<span class="block text-sm">{text}</span>
		{#if dates}
			<span class="block text-xs text-base-content/60">{dates}</span>
		{/if}
	</span>
	<span class="shrink-0 text-xs text-base-content/50">{ago(item.created_at)}</span>
{/snippet}

<div class="flex flex-col gap-1 rounded-lg px-3 py-2 hover:bg-base-200">
	{#if href}
		<a {href} class="flex items-start gap-2" onclick={onnavigate}>{@render body()}</a>
	{:else}
		<div class="flex items-start gap-2">{@render body()}</div>
	{/if}
	{#if canRemove}
		<div class="flex justify-end">
			<button type="button" class="btn btn-ghost btn-xs" disabled={busy} onclick={removeMe}>
				{$t('notifications.remove_me')}
			</button>
		</div>
	{/if}
</div>
