<script lang="ts">
	import { t } from 'svelte-i18n';

	interface Props {
		/** Total seconds, or `null` when empty. */
		value: number | null;
		id?: string;
		readonly?: boolean;
	}

	let { value = $bindable(null), id, readonly = false }: Props = $props();

	const parts = $derived({
		hours: value == null ? '' : Math.floor(value / 3600),
		minutes: value == null ? '' : Math.floor((value % 3600) / 60),
		seconds: value == null ? '' : Math.floor(value % 60)
	});

	function update(part: 'hours' | 'minutes' | 'seconds', raw: string) {
		const next = {
			hours: Number(parts.hours || 0),
			minutes: Number(parts.minutes || 0),
			seconds: Number(parts.seconds || 0)
		};
		next[part] = Math.max(0, Math.floor(Number(raw) || 0));
		const total = next.hours * 3600 + next.minutes * 60 + next.seconds;
		value = raw === '' && total === 0 ? null : total;
	}
</script>

<div class="flex gap-2">
	{#each [{ key: 'hours', unit: 'h', max: undefined, label: $t('activities.hours') }, { key: 'minutes', unit: 'm', max: 59, label: $t('activities.minutes') }, { key: 'seconds', unit: 's', max: 59, label: $t('activities.seconds') }] as part, index (part.key)}
		<label class="input min-w-0 flex-1">
			<input
				id={index === 0 ? id : undefined}
				type="number"
				inputmode="numeric"
				min="0"
				max={part.max}
				class="w-full min-w-0 grow"
				aria-label={part.label}
				value={parts[part.key as keyof typeof parts]}
				{readonly}
				oninput={(event) =>
					update(part.key as 'hours' | 'minutes' | 'seconds', event.currentTarget.value)}
			/>
			<span class="label">{part.unit}</span>
		</label>
	{/each}
</div>
