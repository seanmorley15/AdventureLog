<script lang="ts">
	import { t } from 'svelte-i18n';
	import MarkdownEditor from '../../MarkdownEditor.svelte';
	import GenerateIcon from '~icons/mdi/lightning-bolt';
	import InfoIcon from '~icons/mdi/information';

	export let text: string = '';
	export let entityName: string = '';
	export let disabled: boolean = false;
	export let editorHeight: string = 'h-32';

	let isGenerating = false;
	let error = '';

	async function generateDesc() {
		if (!entityName) return;

		isGenerating = true;
		error = '';

		try {
			const response = await fetch(`/api/generate/desc/?name=${encodeURIComponent(entityName)}`);
			if (response.ok) {
				const data = await response.json();
				text = data.extract || '';
			} else {
				error = $t('adventures.wikipedia_error') || 'Error fetching description from Wikipedia';
			}
		} catch (e) {
			error = $t('adventures.wikipedia_error') || '';
		} finally {
			isGenerating = false;
		}
	}
</script>

<div class="form-control">
	<label class="label" for="description">
		<span class="label-text font-medium">{$t('adventures.description')}</span>
	</label>
	<MarkdownEditor bind:text editor_height={editorHeight} />

	<div class="flex items-center gap-4 mt-3">
		<button
			type="button"
			class="btn btn-neutral btn-sm gap-2"
			on:click={generateDesc}
			disabled={disabled || !entityName || isGenerating}
		>
			{#if isGenerating}
				<span class="loading loading-spinner loading-xs"></span>
			{:else}
				<GenerateIcon class="w-4 h-4" />
			{/if}
			{$t('adventures.generate_desc')}
		</button>
		{#if error}
			<div class="alert alert-error alert-sm">
				<InfoIcon class="w-4 h-4" />
				<span class="text-sm">{error}</span>
			</div>
		{/if}
	</div>
</div>
