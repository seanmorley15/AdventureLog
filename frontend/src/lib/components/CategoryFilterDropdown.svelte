<script lang="ts">
	import { ADVENTURE_TYPES } from '$lib';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	let types_arr: string[] = [];
	export let types: string;

	onMount(() => {
		console.log(types);
		types_arr = types.split(',');
	});

	function clearTypes() {
		types = '';
		types_arr = [];
	}

	function toggleSelect(type: string) {
		if (types_arr.includes(type)) {
			types_arr = types_arr.filter((t) => t !== type);
		} else {
			types_arr.push(type);
		}
		types = types_arr.join(',');
		console.log(types);
		console.log(types_arr);
	}
</script>

<div class="collapse collapse-plus mb-4">
	<input type="checkbox" />
	<div class="collapse-title text-xl bg-base-300 font-medium">
		{$t('adventures.category_filter')}
	</div>
	<div class="collapse-content bg-base-300">
		<button class="btn btn-wide btn-neutral-300" on:click={clearTypes}
			>{$t(`adventures.clear`)}</button
		>
		{#each ADVENTURE_TYPES as type}
			<li>
				<label class="cursor-pointer">
					<input
						type="checkbox"
						value={type.label}
						on:change={() => toggleSelect(type.type)}
						checked={types.indexOf(type.type) > -1}
					/>
					<span>{$t(`adventures.activities.${type.type}`)}</span>
				</label>
			</li>
		{/each}
	</div>
</div>
