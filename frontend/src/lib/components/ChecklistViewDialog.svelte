<script lang="ts">
	import { t } from 'svelte-i18n';
	import { addToast } from '#lib/toasts.js';
	import type { Checklist, User } from '#lib/types.js';
	import { dateFormatFromUser, formatDisplayDate } from '#lib/dateFormat.js';
	import ClipboardListOutline from '~icons/mdi/clipboard-list-outline';
	import Calendar from '~icons/mdi/calendar';
	import CheckCircle from '~icons/mdi/check-circle';
	import CheckboxBlankCircleOutline from '~icons/mdi/checkbox-blank-circle-outline';
	import Close from '~icons/mdi/close';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';

	interface Props {
		checklist: Checklist;
		user?: User | null;
		/** Items can be ticked off from here when true. */
		canToggle?: boolean;
		/** Shows the Edit button when set. */
		onEdit?: (() => void) | null;
		onUpdate?: (checklist: Checklist) => void;
		onClose: () => void;
	}

	let {
		checklist,
		user = null,
		canToggle = false,
		onEdit = null,
		onUpdate,
		onClose
	}: Props = $props();

	// Local copy so ticking an item reflects immediately and survives the parent not re-passing it.
	let current = $state<Checklist>(untrackedCopy());
	let updatingItemId: string | null = $state(null);

	function untrackedCopy(): Checklist {
		return { ...checklist, items: (checklist.items ?? []).map((item) => ({ ...item })) };
	}

	const dateFormat = $derived(dateFormatFromUser(user));
	const total = $derived(current.items.length);
	const done = $derived(current.items.filter((item) => item.is_checked).length);
	const hasDate = $derived(Boolean(current.date && current.date !== ''));

	function normalizeDate(date: string | Date | null | undefined): string | null {
		if (!date) return null;
		if (date instanceof Date && !isNaN(date.getTime())) return date.toISOString().slice(0, 10);
		if (typeof date === 'string') return date.match(/^\d{4}-\d{2}-\d{2}/)?.[0] ?? null;
		return null;
	}

	async function toggle(itemId: string) {
		if (!canToggle || !itemId || updatingItemId) return;
		const previous = current.items.map((item) => ({ ...item }));
		const items = current.items.map((item) =>
			item.id === itemId ? { ...item, is_checked: !item.is_checked } : item
		);
		updatingItemId = itemId;
		current = { ...current, items };
		try {
			const res = await fetch(`/api/checklists/${current.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: current.name,
					date: normalizeDate(current.date),
					items,
					collection: current.collection,
					is_public: current.is_public
				})
			});
			if (res.ok) {
				const data = await res.json();
				if (data) {
					current = data;
					onUpdate?.(data);
				}
			} else {
				current = { ...current, items: previous };
				addToast('error', 'Unable to update checklist item');
			}
		} catch (error) {
			current = { ...current, items: previous };
			addToast('error', 'Unable to update checklist item');
			console.error(error);
		} finally {
			updatingItemId = null;
		}
	}
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onClose()} />

<dialog class="modal modal-open" open aria-label={current.name}>
	<div class="modal-box flex max-h-[85vh] w-full max-w-xl flex-col gap-0 p-0">
		<header class="flex items-start gap-3 border-b border-base-300/70 px-5 py-4 sm:px-6">
			<div
				class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10"
				aria-hidden="true"
			>
				<ClipboardListOutline class="h-5 w-5 text-primary" />
			</div>
			<div class="min-w-0 flex-1">
				<h3 class="text-xl font-semibold leading-snug wrap-break-word">{current.name}</h3>
				<div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
					<span class="badge badge-primary badge-soft badge-sm">{$t('adventures.checklist')}</span>
					{#if hasDate}
						<span class="inline-flex items-center gap-1.5 text-base-content/70">
							<Calendar class="h-4 w-4 text-primary" />
							{formatDisplayDate(current.date as string, dateFormat, { timeZone: 'UTC' })}
						</span>
					{/if}
				</div>
			</div>
			<button
				type="button"
				class="btn btn-circle btn-ghost btn-sm"
				onclick={onClose}
				aria-label={$t('about.close')}
			>
				<Close class="h-4 w-4" />
			</button>
		</header>

		<div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4 sm:px-6">
			{#if total > 0}
				<div class="space-y-1.5">
					<div class="flex items-center justify-between text-sm text-base-content/70">
						<span>{done}/{total} {$t('checklist.completed')}</span>
					</div>
					<progress class="progress progress-success w-full" value={done} max={total}></progress>
				</div>

				<ul class="space-y-1.5">
					{#each current.items as item (item.id)}
						<li>
							{#if canToggle}
								<button
									type="button"
									onclick={() => toggle(item.id)}
									disabled={updatingItemId === item.id}
									class="flex w-full items-center gap-3 rounded-lg bg-base-200/60 p-2.5 text-left transition-colors hover:bg-base-200 disabled:opacity-70"
								>
									{@render itemBody(item.name, item.is_checked, updatingItemId === item.id)}
								</button>
							{:else}
								<div class="flex items-center gap-3 rounded-lg bg-base-200/60 p-2.5">
									{@render itemBody(item.name, item.is_checked, false)}
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{:else}
				<p class="py-6 text-center text-sm text-base-content/60">{$t('checklist.no_items_yet')}</p>
			{/if}
		</div>

		<footer class="flex justify-end gap-2 border-t border-base-300/70 px-5 py-3 sm:px-6">
			{#if onEdit}
				<button type="button" class="btn btn-ghost btn-sm gap-1" onclick={onEdit}>
					<FileDocumentEdit class="h-4 w-4" />
					{$t('lodging.edit')}
				</button>
			{/if}
			<button type="button" class="btn btn-sm" onclick={onClose}>{$t('about.close')}</button>
		</footer>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button aria-label={$t('about.close')} onclick={onClose}>{$t('about.close')}</button>
	</form>
</dialog>

{#snippet itemBody(name: string, checked: boolean, busy: boolean)}
	{#if busy}
		<span class="loading loading-spinner loading-xs shrink-0 text-primary"></span>
	{:else if checked}
		<CheckCircle class="h-5 w-5 shrink-0 text-success" />
	{:else}
		<CheckboxBlankCircleOutline class="h-5 w-5 shrink-0" />
	{/if}
	<span class={['flex-1 text-sm', checked && 'line-through opacity-60']}>{name}</span>
{/snippet}
