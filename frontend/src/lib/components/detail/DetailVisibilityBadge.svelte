<script lang="ts">
	import { t } from 'svelte-i18n';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';

	interface Props {
		isPublic: boolean;
	}

	let { isPublic }: Props = $props();
</script>

<span class="badge gap-1 {isPublic ? 'badge-accent' : 'badge-ghost'}">
	{#if isPublic}
		<Eye class="h-3.5 w-3.5" />
		{$t('adventures.public')}
	{:else}
		<EyeOff class="h-3.5 w-3.5" />
		{$t('adventures.private')}
	{/if}
</span>
