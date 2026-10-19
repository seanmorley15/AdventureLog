<script lang="ts">
	import type { Snippet } from 'svelte';
	import type InformationOutline from '~icons/mdi/information-outline';

	interface Props {
		title: string;
		/** A one-line explanation under the title. */
		hint?: string;
		/** An mdi icon component, shown in a tinted tile. */
		icon?: typeof InformationOutline;
		/** Buttons or a count on the right of the heading. */
		actions?: Snippet;
		class?: string;
		children: Snippet;
	}

	let { title, hint = '', icon: Icon, actions, class: className = '', children }: Props = $props();
</script>

<section class="card border border-base-300 bg-base-100 {className}">
	<div class="card-body gap-4 p-4 md:p-6">
		<div class="flex items-start gap-3">
			{#if Icon}
				<div class="shrink-0 rounded-lg bg-primary/10 p-2">
					<Icon class="h-5 w-5 text-primary" />
				</div>
			{/if}
			<div class="min-w-0 flex-1">
				<h2 class="text-lg font-bold text-base-content">{title}</h2>
				{#if hint}
					<p class="field-hint">{hint}</p>
				{/if}
			</div>
			{#if actions}
				<div class="flex shrink-0 items-center gap-2">
					{@render actions()}
				</div>
			{/if}
		</div>
		{@render children()}
	</div>
</section>
