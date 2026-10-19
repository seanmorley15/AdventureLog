<script lang="ts">
	import type InformationOutline from '~icons/mdi/information-outline';

	interface Props {
		label: string;
		value: string | number;
		/** Appended to the value in a smaller size, e.g. km. */
		unit?: string;
		icon?: typeof InformationOutline;
	}

	let { label, value, unit = '', icon: Icon }: Props = $props();
</script>

<div class="rounded-xl bg-base-200 p-3">
	<p
		class="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-base-content/60"
	>
		{#if Icon}<Icon class="h-3.5 w-3.5 text-primary" />{/if}
		{label}
	</p>
	<p class="mt-0.5 text-2xl font-bold leading-tight">
		{value}{#if unit}<span class="ml-1 text-sm font-medium text-base-content/60">{unit}</span>{/if}
	</p>
</div>
