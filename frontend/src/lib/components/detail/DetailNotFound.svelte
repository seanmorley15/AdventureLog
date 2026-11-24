<script lang="ts">
	import { t } from 'svelte-i18n';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import CompassOff from '~icons/mdi/compass-off-outline';
	import HomeOutline from '~icons/mdi/home-outline';
	import ArrowLeft from '~icons/mdi/arrow-left';

	interface Props {
		title: string;
		description?: string;
	}

	let { title, description = '' }: Props = $props();
	const canGoBack = $derived(typeof history !== 'undefined' && history.length > 1);
</script>

<ErrorState
	status={404}
	icon={CompassOff}
	{title}
	description={description || $t('errors.not_found_description')}
>
	{#snippet actions()}
		{#if canGoBack}
			<button class="btn btn-ghost gap-2" onclick={() => history.back()}>
				<ArrowLeft class="h-5 w-5" />
				{$t('errors.go_back')}
			</button>
		{/if}
		<a href="/" class="btn btn-primary gap-2">
			<HomeOutline class="h-5 w-5" />
			{$t('adventures.homepage')}
		</a>
	{/snippet}
</ErrorState>
