<script lang="ts">
	import { t } from 'svelte-i18n';

	export let checked: boolean = false;
	export let label: string;
	export let description: string;
	export let id: string = 'is_public';
</script>

<div class="form-control">
	<label class="label cursor-pointer justify-start gap-4" for={id}>
		<input
			type="checkbox"
			class="toggle toggle-primary"
			{id}
			bind:checked
		/>
		<div>
			<span class="label-text font-medium">{label}</span>
			<p class="text-sm text-base-content/60">{description}</p>
		</div>
	</label>
</div>
