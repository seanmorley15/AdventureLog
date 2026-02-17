<script lang="ts">
	import { t } from 'svelte-i18n';

	export let value: string = '';
	export let placeholder: string = '';
	export let id: string = 'name';
</script>

<div class="form-control">
	<label class="label" for={id}>
		<span class="label-text font-medium">
			{$t('adventures.name')} <span class="text-error">*</span>
		</span>
	</label>
	<input
		type="text"
		{id}
		bind:value
		class="input input-bordered bg-base-100/80 focus:bg-base-100"
		{placeholder}
		required
	/>
</div>
