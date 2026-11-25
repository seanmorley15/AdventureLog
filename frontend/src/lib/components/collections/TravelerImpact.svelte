<script lang="ts">
	import { t } from 'svelte-i18n';
	import { travelerName } from '#lib/travelers.js';
	import type { TravelerSummary } from '#lib/types.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';

	/**
	 * What happens to people who travelled to a place when they lose their way to it. One wording
	 * for every dialog: they keep a copy with their visits, everyone else keeps the place as it
	 * is, and only visits nobody else was on are deleted, with what other people added to them.
	 */
	interface Props {
		/** Who gets their own copy (from a preview's `people_released`). */
		people?: TravelerSummary[];
		/** You are one of them. */
		includesYou?: boolean;
		/** Your uuid, so you are named by "you" and left out of the list. */
		meUuid?: string | null;
		/** Visits only the people getting copies were on, which go with the original. */
		visitsDeleted?: number;
		/** Photos, files and activities other people added to those visits. */
		othersUploads?: number;
		/** Places that would be copied, when more than one place is involved. */
		places?: number;
		/** Say that everyone else keeps the place. Off when the place itself is going (account deletion). */
		othersKeep?: boolean;
	}

	let {
		people = [],
		includesYou = false,
		meUuid = null,
		visitsDeleted = 0,
		othersUploads = 0,
		places = 0,
		othersKeep = true
	}: Props = $props();

	// You are named by "you", so leave you out of the list of other people.
	let others = $derived(includesYou ? people.filter((p) => p.uuid !== meUuid) : people);
	let anyone = $derived(people.length > 0 || includesYou);
</script>

{#if anyone}
	<div class="space-y-2 text-sm" data-testid="traveler-impact">
		{#if includesYou}
			<p>{$t('traveler_impact.you_copy')}</p>
		{/if}
		{#if others.length > 0}
			<p>{$t('traveler_impact.people_copy', { values: { count: others.length } })}</p>
			<ul class="flex flex-wrap gap-2">
				{#each others as person (person.uuid)}
					<li class="flex items-center gap-1.5 rounded-full bg-base-200 py-0.5 pr-2.5 pl-0.5">
						<UserAvatar user={person} className="h-6 w-6 rounded-full" textClass="text-[10px]" />
						<span>{travelerName(person)}</span>
					</li>
				{/each}
			</ul>
		{/if}
		{#if places > 1}
			<p class="text-base-content/70">
				{$t('traveler_impact.places', { values: { count: places } })}
			</p>
		{/if}
		{#if visitsDeleted > 0}
			<p>{$t('traveler_impact.visits_deleted', { values: { count: visitsDeleted } })}</p>
		{/if}
		{#if othersUploads > 0}
			<div role="alert" class="alert alert-warning alert-soft text-sm">
				{$t('traveler_impact.others_uploads', { values: { count: othersUploads } })}
			</div>
		{/if}
		{#if othersKeep}
			<p class="text-base-content/70">{$t('traveler_impact.others_keep')}</p>
		{/if}
	</div>
{/if}
