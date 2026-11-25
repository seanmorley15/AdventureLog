<script lang="ts">
	import { t } from 'svelte-i18n';
	import PersonAvatar from '#lib/components/collections/discussion/PersonAvatar.svelte';
	import { travelerName, travelerPerson } from '#lib/travelers.js';
	import type { TravelerSummary } from '#lib/types.js';

	interface Props {
		/** The people a visit here can name. */
		candidates: TravelerSummary[];
		/** The uuids of the people who were there. A visit needs at least one. */
		selected?: string[];
		/** Hide the legend visually (still read by screen readers) when a title already sits above. */
		hideLegend?: boolean;
	}

	let { candidates, selected = $bindable([]), hideLegend = false }: Props = $props();

	const uid = $props.id();
	const messageId = `traveler-picker-${uid}`;
	// Nobody checked is invalid, not locked: whoever uses the picker disables saving while it is.
	const invalid = $derived(selected.length === 0);

	function toggle(uuid: string, checked: boolean) {
		if (checked) {
			if (!selected.includes(uuid)) selected = [...selected, uuid];
		} else {
			selected = selected.filter((id) => id !== uuid);
		}
	}
</script>

<fieldset class="space-y-2">
	<legend class={hideLegend ? 'sr-only' : 'field-label'}>{$t('visits.who_was_there')}</legend>
	<div
		class="flex flex-wrap gap-2 rounded-box {invalid ? 'border border-error p-1' : ''}"
		data-invalid={invalid ? 'true' : undefined}
	>
		{#each candidates as person (person.uuid)}
			{@const checked = selected.includes(person.uuid)}
			<label
				class="flex cursor-pointer items-center gap-2 rounded-full border px-2 py-1 text-sm {checked
					? 'border-primary/40 bg-primary/10'
					: 'border-base-300 bg-base-100'}"
			>
				<input
					type="checkbox"
					class="checkbox checkbox-primary checkbox-xs {invalid ? 'border-error' : ''}"
					{checked}
					aria-invalid={invalid ? 'true' : undefined}
					aria-describedby={invalid ? messageId : undefined}
					onchange={(event) => toggle(person.uuid, event.currentTarget.checked)}
				/>
				<PersonAvatar person={travelerPerson(person)} size="xs" linked={false} />
				<span>{travelerName(person)}</span>
			</label>
		{/each}
	</div>
	{#if invalid}
		<p id={messageId} role="alert" class="text-xs text-error">{$t('visits.pick_one_traveler')}</p>
	{:else if candidates.length > 1}
		<p class="text-xs text-base-content/60">{$t('traveler_impact.picker_hint')}</p>
	{/if}
</fieldset>
