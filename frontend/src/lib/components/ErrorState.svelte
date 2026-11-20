<script lang="ts">
	import type { Component, Snippet } from 'svelte';
	import type { ErrorTone } from '#lib/errors.js';

	interface Props {
		/** The HTTP status, shown as a small label. */
		status?: number | null;
		icon: Component<{ class?: string }>;
		tone?: ErrorTone;
		title: string;
		description?: string;
		/** Buttons under the text. */
		actions?: Snippet;
		/** Anything else: hints, a reference id. */
		children?: Snippet;
		/** Fill the screen under the navbar (an error page), or just take the space it needs. */
		fullPage?: boolean;
		/** Smaller, for a frame or a panel. */
		compact?: boolean;
	}

	let {
		status = null,
		icon: Icon,
		tone = 'info',
		title,
		description = '',
		actions,
		children,
		fullPage = true,
		compact = false
	}: Props = $props();

	// Whole class names, so Tailwind generates them.
	const tones: Record<ErrorTone, { halo: string; chip: string; glow: string }> = {
		info: {
			halo: 'bg-primary/10 text-primary ring-primary/20',
			chip: 'badge-primary',
			glow: 'from-primary/10'
		},
		warning: {
			halo: 'bg-warning/10 text-warning ring-warning/25',
			chip: 'badge-warning',
			glow: 'from-warning/10'
		},
		error: {
			halo: 'bg-error/10 text-error ring-error/25',
			chip: 'badge-error',
			glow: 'from-error/10'
		}
	};
	const look = $derived(tones[tone]);
</script>

<div
	class="relative flex w-full items-center justify-center overflow-hidden px-4 {fullPage
		? 'min-h-[calc(100dvh-5rem)] py-16'
		: compact
			? 'h-full py-6'
			: 'min-h-[50vh] py-12'}"
	role="alert"
>
	<div
		class="pointer-events-none absolute inset-x-0 top-0 h-2/3 bg-gradient-to-b {look.glow} to-transparent"
		aria-hidden="true"
	></div>

	<div class="relative mx-auto flex max-w-lg flex-col items-center text-center">
		<div
			class="grid place-items-center rounded-full ring-8 {look.halo} {compact
				? 'h-14 w-14'
				: 'h-24 w-24'}"
		>
			<Icon class={compact ? 'h-7 w-7' : 'h-12 w-12'} />
		</div>

		{#if status}
			<span class="badge badge-soft badge-sm mt-6 font-mono tracking-wider {look.chip}"
				>{status}</span
			>
		{/if}

		<h1 class="font-bold tracking-tight {compact ? 'mt-3 text-xl' : 'mt-3 text-3xl sm:text-4xl'}">
			{title}
		</h1>
		{#if description}
			<p class="mt-3 text-base-content/70 {compact ? 'text-sm' : ''}">{description}</p>
		{/if}

		{#if actions}
			<div class="mt-8 flex flex-wrap items-center justify-center gap-3">
				{@render actions()}
			</div>
		{/if}

		{#if children}
			<div class="mt-8 w-full">
				{@render children()}
			</div>
		{/if}
	</div>
</div>
