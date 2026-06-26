<script lang="ts">
	import { appTitle, appVersion, appCodename } from '$lib/config';

	export let size: 'sm' | 'md' = 'md';
</script>

<p
	class="inline-flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5 leading-snug m-0
		{size === 'sm' ? 'text-sm' : 'text-lg'}"
>
	<span class="font-bold text-primary">{appTitle}</span>
	<span class="font-semibold italic text-secondary">&ldquo;{appCodename}&rdquo;</span>
	<span class="text-base-content/35 font-light select-none" aria-hidden="true">·</span>
	<span
		class="font-mono text-base-content/60 tabular-nums tracking-tight
			{size === 'sm' ? 'text-xs' : 'text-sm'}">{appVersion}</span
	>
</p>
