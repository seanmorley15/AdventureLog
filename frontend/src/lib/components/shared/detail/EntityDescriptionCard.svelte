<script lang="ts">
	import { t } from 'svelte-i18n';
	import { renderMarkdown } from './detailUtils';

	export let description: string;
	export let title: string = $t('adventures.description') || 'Description';
	export let icon: string = '📝';
</script>

{#if description}
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body">
			<h2 class="card-title text-2xl mb-4">{icon} {title}</h2>
			<article class="prose max-w-none">
				{@html renderMarkdown(description)}
			</article>
		</div>
	</div>
{/if}
