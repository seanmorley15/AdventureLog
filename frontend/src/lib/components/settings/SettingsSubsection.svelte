<script lang="ts">
	export let title: string;
	export let description: string = '';
	export let showDivider: boolean = true;
</script>

{#if showDivider}
	<div class="divider my-8">{title}</div>
{:else}
	<div class="mb-6">
		<h3 class="text-lg font-semibold">{title}</h3>
		{#if description}
			<p class="text-sm text-base-content/70 mt-1">{description}</p>
		{/if}
	</div>
{/if}

<slot />
