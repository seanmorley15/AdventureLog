<script lang="ts">
	import type { Snippet } from 'svelte';
	import type InformationOutline from '~icons/mdi/information-outline';

	interface Props {
		label: string;
		/** An mdi icon component. */
		icon?: typeof InformationOutline;
		/** Or an emoji, for things like a type icon that come from data. */
		emoji?: string | null;
		/** Monospace value, for codes and numbers. */
		mono?: boolean;
		children: Snippet;
	}

	let { label, icon: Icon, emoji = null, mono = false, children }: Props = $props();
</script>

<div class="flex items-start gap-3">
	<div
		class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-base-200"
		aria-hidden="true"
	>
		{#if Icon}
			<Icon class="h-4 w-4 text-primary" />
		{:else if emoji}
			<span class="text-base">{emoji}</span>
		{/if}
	</div>
	<div class="min-w-0 flex-1">
		<p class="text-xs font-medium uppercase tracking-wide text-base-content/60">{label}</p>
		<div class="break-words text-base {mono ? 'font-mono' : ''}">
			{@render children()}
		</div>
	</div>
</div>
