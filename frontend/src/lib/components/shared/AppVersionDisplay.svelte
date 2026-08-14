<script lang="ts">
	import { appTitle, appVersion, appCodename } from '$lib/config';

	interface Props {
		size?: 'sm' | 'md';
		variant?: 'default' | 'inverse';
	}

	let { size = 'md', variant = 'default' }: Props = $props();

	let titleClass = $derived(variant === 'inverse' ? 'text-primary-content' : 'text-primary');
	let versionClass = $derived(variant === 'inverse' ? 'text-primary-content/80' : 'text-base-content/70');
	let codenameClass = $derived(variant === 'inverse' ? 'text-primary-content/90' : 'text-secondary');
</script>

<p
	class="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5 leading-snug m-0 w-full
 {size === 'sm' ? 'text-sm' : 'text-lg'}"
>
	<span class="font-bold {titleClass}">{appTitle}</span>
	<span
		class="font-mono tabular-nums tracking-tight {versionClass}
 {size === 'sm' ? 'text-xs' : 'text-sm'}">{appVersion}</span
	>
	<span class="font-semibold italic {codenameClass}">{appCodename}</span>
</p>
