<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';

	/**
	 * Standard action buttons for modal forms.
	 * Provides back/continue/save button patterns.
	 */

	export let showBack: boolean = true;
	export let showContinue: boolean = true;
	export let showSave: boolean = false;
	export let showClose: boolean = false;

	export let backLabel: string | null = null;
	export let continueLabel: string | null = null;
	export let saveLabel: string | null = null;
	export let closeLabel: string | null = null;

	export let continueDisabled: boolean = false;
	export let saveDisabled: boolean = false;
	export let isLoading: boolean = false;

	const dispatch = createEventDispatcher<{
		back: void;
		continue: void;
		save: void;
		close: void;
	}>();
</script>

<div class="flex justify-between mt-6">
	<div>
		{#if showBack}
			<button type="button" class="btn btn-outline" on:click={() => dispatch('back')}>
				<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M15 19l-7-7 7-7"
					/>
				</svg>
				{backLabel || $t('adventures.back')}
			</button>
		{/if}
	</div>

	<div class="flex gap-2">
		{#if showClose}
			<button type="button" class="btn btn-ghost" on:click={() => dispatch('close')}>
				{closeLabel || $t('adventures.close')}
			</button>
		{/if}

		{#if showSave}
			<button
				type="button"
				class="btn btn-primary"
				disabled={saveDisabled || isLoading}
				on:click={() => dispatch('save')}
			>
				{#if isLoading}
					<span class="loading loading-spinner loading-sm"></span>
				{/if}
				{saveLabel || $t('adventures.save_changes')}
			</button>
		{/if}

		{#if showContinue}
			<button
				type="button"
				class="btn btn-primary"
				disabled={continueDisabled || isLoading}
				on:click={() => dispatch('continue')}
			>
				{#if isLoading}
					<span class="loading loading-spinner loading-sm"></span>
				{/if}
				{continueLabel || $t('adventures.continue')}
				<svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 5l7 7-7 7"
					/>
				</svg>
			</button>
		{/if}
	</div>
</div>
