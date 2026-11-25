<script lang="ts">
	import { t } from 'svelte-i18n';
	import PersonAvatar from '#lib/components/collections/discussion/PersonAvatar.svelte';
	import { travelerName, travelerPerson } from '#lib/travelers.js';
	import type { TravelerSummary } from '#lib/types.js';

	interface Props {
		/** The people a visit here can name. */
		candidates: TravelerSummary[];
		/** The uuids of the people who were there. */
		selected?: string[];
		/** A person who is always checked, e.g. the current user. */
		lockedUuid?: string;
	}

	let { candidates, selected = $bindable([]), lockedUuid }: Props = $props();

	// The locked person is always on the visit.
	$effect(() => {
		if (lockedUuid && !selected.includes(lockedUuid)) selected = [...selected, lockedUuid];
	});

	// A visit always has someone on it, so the last checked person cannot be unchecked.
	function isFixed(uuid: string): boolean {
		return uuid === lockedUuid || (selected.length <= 1 && selected.includes(uuid));
	}

	function toggle(uuid: string, checked: boolean) {
		if (checked) {
			if (!selected.includes(uuid)) selected = [...selected, uuid];
		} else if (!isFixed(uuid)) {
			selected = selected.filter((id) => id !== uuid);
		}
	}
</script>

<fieldset class="space-y-2">
	<legend class="field-label">{$t('visits.who_was_there')}</legend>
	<div class="flex flex-wrap gap-2">
		{#each candidates as person (person.uuid)}
			{@const checked = person.uuid === lockedUuid || selected.includes(person.uuid)}
			{@const fixed = isFixed(person.uuid)}
			<label
				class="flex items-center gap-2 rounded-full border px-2 py-1 text-sm {checked
					? 'border-primary/40 bg-primary/10'
					: 'border-base-300 bg-base-100'} {fixed ? 'cursor-not-allowed' : 'cursor-pointer'}"
				title={fixed && checked ? $t('visits.keep_one_traveler') : undefined}
			>
				<input
					type="checkbox"
					class="checkbox checkbox-primary checkbox-xs"
					{checked}
					disabled={fixed && checked}
					onchange={(event) => toggle(person.uuid, event.currentTarget.checked)}
				/>
				<PersonAvatar person={travelerPerson(person)} size="xs" linked={false} />
				<span>{travelerName(person)}</span>
			</label>
		{/each}
	</div>
</fieldset>
