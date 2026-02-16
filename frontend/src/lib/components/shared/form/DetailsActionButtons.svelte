<script lang="ts">
	/**
	 * DetailsActionButtons - Shared action buttons for entity details forms
	 */
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import SaveIcon from '~icons/mdi/content-save';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';

	export let disabled: boolean = false;
	export let isProcessing: boolean = false;
	export let showBack: boolean = false;

	const dispatch = createEventDispatcher();

	function handleSave() {
		dispatch('save');
	}

	function handleBack() {
		dispatch('back');
	}
</script>

<div class="flex gap-3 justify-end pt-4">
	{#if showBack}
		<button class="btn btn-neutral-200 gap-2" on:click={handleBack}>
			<ArrowLeftIcon class="w-5 h-5" />
			{$t('adventures.back')}
		</button>
	{/if}
	<button
		class="btn btn-primary gap-2"
		{disabled}
		on:click={handleSave}
	>
		{#if isProcessing}
			<span class="loading loading-spinner loading-sm"></span>
			{$t('adventures.processing')}...
		{:else}
			<SaveIcon class="w-5 h-5" />
			{$t('adventures.continue')}
		{/if}
	</button>
</div>
