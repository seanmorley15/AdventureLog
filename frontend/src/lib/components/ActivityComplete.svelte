<script lang="ts">
	import { onMount } from 'svelte';

	export let activities: string[] | undefined | null;

	let allActivities: string[] = [];
	let inputVal: string = '';

	if (activities == null || activities == undefined) {
		activities = [];
	}

	onMount(async () => {
		let res = await fetch('/activities', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		let data = await res.json();
		console.log('ACTIVITIES' + data.activities);
		if (data && data.activities) {
			allActivities = data.activities;
		}
	});

	function addActivity() {
		if (inputVal && activities) {
			const trimmedInput = inputVal.trim().toLocaleLowerCase();
			if (trimmedInput && !activities.includes(trimmedInput)) {
				activities = [...activities, trimmedInput];
				inputVal = '';
			}
		}
	}

	function removeActivity(item: string) {
		if (activities) {
			activities = activities.filter((activity) => activity !== item);
		}
	}

	$: filteredItems = allActivities.filter(function (activity) {
		return (
			activity.toLowerCase().includes(inputVal.toLowerCase()) &&
			(!activities || !activities.includes(activity))
		);
	});
</script>

<div class="relative">
	<div class="flex gap-2">
		<input
			type="text"
			class="input input-bordered w-full"
			placeholder="Add an activity"
			bind:value={inputVal}
			on:keydown={(e) => {
				if (e.key === 'Enter') {
					e.preventDefault();
					addActivity();
				}
			}}
		/>
		<button type="button" class="btn btn-neutral" on:click={addActivity}>Add</button>
	</div>
	{#if inputVal && filteredItems.length > 0}
		<ul class="absolute z-10 w-full bg-base-100 shadow-lg max-h-60 overflow-auto">
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			{#each filteredItems as item}
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
				<li
					class="p-2 hover:bg-base-200 cursor-pointer"
					on:click={() => {
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
		{#if activities}
			{#each activities as activity}
				<li class="flex items-center justify-between bg-base-200 p-2 rounded">
					{activity}
					<button
						type="button"
						class="btn btn-sm btn-error"
						on:click={() => removeActivity(activity)}
					>
						Remove
					</button>
				</li>
			{/each}
		{/if}
	</ul>
</div>
