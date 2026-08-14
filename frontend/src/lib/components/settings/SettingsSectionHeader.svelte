<script lang="ts">
	interface Props {
		icon: string;
		title: string;
		description?: string;
		iconBgClass?: string;
	}

	let {
		icon,
		title,
		description = '',
		iconBgClass = 'bg-primary/10'
	}: Props = $props();
</script>

<div class="flex items-center gap-4 mb-6">
	<div class="p-3 {iconBgClass} rounded-xl shrink-0">
		<span class="text-2xl">{icon}</span>
	</div>
	<div>
		<h2 class="text-2xl font-bold">{title}</h2>
		{#if description}
			<p class="text-base-content/70">{description}</p>
		{/if}
	</div>
</div>
