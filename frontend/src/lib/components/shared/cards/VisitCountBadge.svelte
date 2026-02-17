<script lang="ts">
	import { t } from 'svelte-i18n';
	import Eye from '~icons/mdi/eye';

	export let visitCount: number;
</script>

{#if visitCount > 0}
	<div class="flex items-center gap-1 text-base-content/70">
		<Eye class="w-4 h-4" />
		<span>
			{visitCount}
			{visitCount === 1 ? $t('adventures.visit') : $t('adventures.visits')}
		</span>
	</div>
{/if}
