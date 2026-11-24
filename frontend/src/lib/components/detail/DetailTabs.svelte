<script lang="ts" module>
	import type InformationOutline from '~icons/mdi/information-outline';

	export type DetailTab = {
		id: string;
		label: string;
		icon?: typeof InformationOutline;
		/** A small count next to the label. Omit or 0 to hide. */
		count?: number;
	};
</script>

<script lang="ts">
	interface Props {
		tabs: DetailTab[];
		value: string;
		onChange: (id: string) => void;
		label?: string;
	}

	let { tabs, value, onChange, label = '' }: Props = $props();
</script>

<!-- Scrolls sideways on narrow screens instead of wrapping. -->
<div
	role="tablist"
	aria-label={label}
	class="tabs tabs-box w-full max-w-full flex-nowrap overflow-x-auto bg-base-200"
>
	{#each tabs as tab (tab.id)}
		{@const Icon = tab.icon}
		<button
			type="button"
			role="tab"
			aria-selected={value === tab.id}
			class="tab shrink-0 gap-2 {value === tab.id ? 'tab-active' : ''}"
			onclick={() => onChange(tab.id)}
		>
			{#if Icon}<Icon class="h-4 w-4" />{/if}
			{tab.label}
			{#if tab.count}<span class="badge badge-sm">{tab.count}</span>{/if}
		</button>
	{/each}
</div>
