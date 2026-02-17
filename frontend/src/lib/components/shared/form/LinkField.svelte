<script lang="ts">
	import { t } from 'svelte-i18n';

	export let value: string = '';
	export let placeholder: string = 'https://example.com';
	export let id: string = 'link';
</script>

<div class="form-control">
	<label class="label" for={id}>
		<span class="label-text font-medium">{$t('adventures.link')}</span>
	</label>
	<input
		type="url"
		{id}
		bind:value
		class="input input-bordered bg-base-100/80 focus:bg-base-100"
		{placeholder}
	/>
</div>
