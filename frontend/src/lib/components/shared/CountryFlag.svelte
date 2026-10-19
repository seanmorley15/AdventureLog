<script lang="ts">
	interface Props {
		/** Image URL from the API, when there is one. */
		src?: string | null;
		/** ISO 3166-1 alpha-2 code, used for the emoji fallback. */
		code?: string | null;
		name?: string;
		class?: string;
	}

	let { src = null, code = null, name = '', class: className = 'h-4 w-6' }: Props = $props();

	let failed = $state(false);

	// Regional-indicator letters spell a flag emoji, so a missing image still shows a flag.
	let emoji = $derived.by(() => {
		const letters = (code ?? '').toUpperCase();
		if (!/^[A-Z]{2}$/.test(letters)) return null;
		return String.fromCodePoint(...[...letters].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65));
	});
</script>

{#if src && !failed}
	<img
		{src}
		alt={name}
		loading="lazy"
		class="shrink-0 rounded-[3px] object-cover shadow-xs ring-1 ring-base-content/10 {className}"
		onerror={() => (failed = true)}
	/>
{:else if emoji}
	<span class="shrink-0 leading-none" role="img" aria-label={name}>{emoji}</span>
{/if}
