<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	interface Props {
		tags: string[] | undefined | null;
	}

	let { tags = $bindable() }: Props = $props();

	let allTags: string[] = $state([]);
	let inputVal: string = $state('');

	if (tags == null || tags == undefined) {
		tags = [];
	}

	onMount(async () => {
		let res = await fetch('/activities', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		let data = await res.json();
		if (data && data.activities) {
			allTags = data.activities;
		}
	});

	function addActivity() {
		if (inputVal && tags) {
			const trimmedInput = inputVal.trim().toLocaleLowerCase();
			if (trimmedInput && !tags.includes(trimmedInput)) {
				tags = [...tags, trimmedInput];
				inputVal = '';
			}
		}
	}

	function removeActivity(item: string) {
		if (tags) {
			tags = tags.filter((activity) => activity !== item);
		}
	}

	let filteredItems = $derived(allTags.filter(function (activity) {
		return (
			activity.toLowerCase().includes(inputVal.toLowerCase()) && (!tags || !tags.includes(activity))
		);
	}));
</script>

<div class="relative">
	<div class="flex gap-2">
		<input
			type="text"
			class="input input-bordered w-full"
			placeholder={$t('adventures.add_a_tag')}
			bind:value={inputVal}
			onkeydown={(e) => {
				if (e.key === 'Enter') {
					e.preventDefault();
					addActivity();
				}
			}}
		/>
		<button type="button" class="btn btn-neutral" onclick={addActivity}
			>{$t('adventures.add')}</button
		>
	</div>
	{#if inputVal && filteredItems.length > 0}
		<ul class="absolute z-10 w-full bg-base-100 shadow-lg max-h-60 overflow-auto">
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			{#each filteredItems as item}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
				<li
					class="p-2 hover:bg-base-200 cursor-pointer"
					onclick={() => {
						inputVal = item;
						addActivity();
					}}
				>
					{item}
				</li>
			{/each}
		</ul>
	{/if}
</div>

<div class="mt-2">
	<ul class="space-y-2">
		{#if tags}
			{#each tags as activity}
				<li class="flex items-center justify-between bg-base-200 p-2 rounded">
					{activity}
					<button
						type="button"
						class="btn btn-sm btn-error"
						onclick={() => removeActivity(activity)}
					>
						{$t('adventures.remove')}
					</button>
				</li>
			{/each}
		{/if}
	</ul>
</div>
