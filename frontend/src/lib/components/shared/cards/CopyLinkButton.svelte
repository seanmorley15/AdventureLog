<script lang="ts">
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import LinkIcon from '~icons/mdi/link';
	import Check from '~icons/mdi/check';

	export let url: string;
	export let feedbackDuration: number = 2000;

	let copied: boolean = false;

	async function copyLink() {
		try {
			await navigator.clipboard.writeText(url);
			copied = true;
			setTimeout(() => (copied = false), feedbackDuration);
		} catch (e) {
			addToast('error', $t('adventures.copy_failed') || 'Copy failed');
		}
	}
</script>

<button on:click={copyLink} class="w-full text-left">
	{#if copied}
		<Check class="w-4 h-4 text-success" />
		<span>{$t('adventures.link_copied')}</span>
	{:else}
		<LinkIcon class="w-4 h-4" />
		{$t('adventures.copy_link')}
	{/if}
</button>
