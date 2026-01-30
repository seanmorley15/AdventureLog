<script lang="ts">
	export let spanish: string;
	export let english: string;
	export let spanishSize: string = 'text-3xl';
	export let englishSize: string = 'text-sm';
</script>

<div class="space-y-1">
	<h2 class="font-display font-bold {spanishSize} leading-tight text-amber-950">
		{spanish}
	</h2>
	<p class="font-body font-normal {englishSize} text-stone-600">
		{english}
	</p>
</div>

<style>
	:global(.font-display) {
		font-family: 'Playfair Display', Georgia, serif;
	}
	:global(.font-body) {
		font-family:
			'Inter',
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			sans-serif;
	}
</style>
