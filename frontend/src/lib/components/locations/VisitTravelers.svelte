<script lang="ts">
	import { t } from 'svelte-i18n';
	import PersonAvatar from '#lib/components/collections/discussion/PersonAvatar.svelte';
	import { travelerName, travelerPerson } from '#lib/travelers.js';
	import { addToast } from '#lib/toasts.js';
	import type { Visit } from '#lib/types.js';

	interface Props {
		visit: Visit;
		/** The signed-in user; without one there are no join or leave buttons. */
		currentUserUuid?: string | null;
		/** Called with the visit as it is now, or null when leaving deleted it. */
		onchange?: (visit: Visit | null) => void;
	}

	let { visit, currentUserUuid = null, onchange }: Props = $props();

	let busy = $state(false);
	let isTraveler = $derived(
		Boolean(currentUserUuid && visit.travelers?.some((person) => person.uuid === currentUserUuid))
	);

	// Leaving a visit you are alone on would only delete it, which the delete button is for.
	let hasOthers = $derived(
		Boolean(visit.travelers?.some((person) => person.uuid !== currentUserUuid))
	);
	let canAct = $derived(Boolean(currentUserUuid) && (!isTraveler || hasOthers));

	async function send(action: 'join' | 'leave') {
		busy = true;
		try {
			const response = await fetch(`/api/visits/${visit.id}/${action}/`, { method: 'POST' });
			if (response.status === 204) {
				onchange?.(null);
			} else if (response.ok) {
				onchange?.((await response.json()) as Visit);
			} else {
				addToast('error', $t(action === 'join' ? 'visits.join_failed' : 'visits.leave_failed'));
			}
		} catch {
			addToast('error', $t(action === 'join' ? 'visits.join_failed' : 'visits.leave_failed'));
		} finally {
			busy = false;
		}
	}
</script>

<!-- Travelers are left out of the visit when the viewer may not see them. -->
{#if visit.travelers}
	<div class="mt-3 flex flex-wrap items-center gap-2">
		<div class="flex -space-x-1" aria-label={$t('visits.who_was_there')}>
			{#each visit.travelers as person (person.uuid)}
				<PersonAvatar person={travelerPerson(person)} size="sm" linked={false} />
			{/each}
		</div>
		<span class="text-xs text-base-content/70">
			{visit.travelers
				.map((person) =>
					person.uuid === currentUserUuid ? $t('visits.you') : travelerName(person)
				)
				.join(', ')}
		</span>
		{#if canAct}
			<button
				type="button"
				class="btn btn-ghost btn-xs"
				disabled={busy}
				onclick={() => send(isTraveler ? 'leave' : 'join')}
			>
				{isTraveler ? $t('visits.i_wasnt_there') : $t('visits.i_was_there_too')}
			</button>
		{/if}
	</div>
{/if}
