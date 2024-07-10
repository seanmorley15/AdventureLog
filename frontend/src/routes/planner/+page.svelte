<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import NewAdventure from '$lib/components/NewAdventure.svelte';
	import type { Adventure } from '$lib/types';
	import Plus from '~icons/mdi/plus';
	import type { PageData } from './$types';
	import EditAdventure from '$lib/components/EditAdventure.svelte';

	export let data: PageData;
	console.log(data);

	let adventures: Adventure[] = data.props.planned;
	let isShowingCreateModal: boolean = false;

	let adventureToEdit: Adventure;
	let isEditModalOpen: boolean = false;

	function deleteAdventure(event: CustomEvent<number>) {
		adventures = adventures.filter((adventure) => adventure.id !== event.detail);
	}

	function createAdventure(event: CustomEvent<Adventure>) {
		adventures = [event.detail, ...adventures];
		isShowingCreateModal = false;
	}

	function editAdventure(event: CustomEvent<Adventure>) {
		adventureToEdit = event.detail;
		isEditModalOpen = true;
	}

	function saveEdit(event: CustomEvent<Adventure>) {
		adventures = adventures.map((adventure) => {
			if (adventure.id === event.detail.id) {
				return event.detail;
			}
			return adventure;
		});
		isEditModalOpen = false;
	}
</script>

{#if isShowingCreateModal}
	<NewAdventure
		type="planned"
		on:create={createAdventure}
		on:close={() => (isShowingCreateModal = false)}
	/>
{/if}

{#if isEditModalOpen}
	<EditAdventure
		{adventureToEdit}
		on:close={() => (isEditModalOpen = false)}
		on:saveEdit={saveEdit}
	/>
{/if}

<div class="fixed bottom-4 right-4 z-[999]">
	<div class="flex flex-row items-center justify-center gap-4">
		<div class="dropdown dropdown-top dropdown-end">
			<div tabindex="0" role="button" class="btn m-1 size-16 btn-primary">
				<Plus class="w-8 h-8" />
			</div>
			<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
			<ul
				tabindex="0"
				class="dropdown-content z-[1] menu p-4 shadow bg-base-300 text-base-content rounded-box w-52 gap-4"
			>
				<p class="text-center font-bold text-lg">Create new...</p>
				<button class="btn btn-primary" on:click={() => (isShowingCreateModal = true)}
					>Planned Adventure</button
				>
				<!-- <button
			class="btn btn-primary"
			on:click={() => (isShowingNewTrip = true)}>Trip Planner</button
		  > -->
			</ul>
		</div>
	</div>
</div>

<h1 class="text-center font-bold text-4xl mb-4">Planned Adventures</h1>
<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
	{#each adventures as adventure}
		<AdventureCard type="planned" {adventure} on:delete={deleteAdventure} on:edit={editAdventure} />
	{/each}
</div>

{#if adventures.length === 0}
	<div class="flex justify-center items-center h-96">
		<p class="text-2xl text-primary-content">No planned adventures yet!</p>
	</div>
{/if}
