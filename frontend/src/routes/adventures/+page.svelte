<script lang="ts">
	import { enhance } from '$app/forms';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import EditAdventure from '$lib/components/EditAdventure.svelte';
	import NewAdventure from '$lib/components/NewAdventure.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure } from '$lib/types';

	import Plus from '~icons/mdi/plus';

	export let data: any;
	console.log(data);

	let adventures: Adventure[] = data.adventures || [];

	let currentSort = { attribute: 'name', order: 'asc' };

	let isShowingCreateModal: boolean = false;
	let newType: string = '';

	function handleSubmit() {
		return async ({ result, update }: any) => {
			// First, call the update function with reset: false
			update({ reset: false });

			// Then, handle the result
			if (result.type === 'success') {
				if (result.data) {
					// console.log(result.data);
					adventures = result.data as Adventure[];
					sort(currentSort);
				}
			}
		};
	}

	function sort({ attribute, order }: { attribute: string; order: string }) {
		currentSort.attribute = attribute;
		currentSort.order = order;
		if (attribute === 'name') {
			if (order === 'asc') {
				adventures = adventures.sort((a, b) => a.name.localeCompare(b.name));
			} else {
				adventures = adventures.sort((a, b) => b.name.localeCompare(a.name));
			}
		}
	}

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

	let sidebarOpen = false;

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}
</script>

{#if isShowingCreateModal}
	<NewAdventure
		type={newType}
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
				<button
					class="btn btn-primary"
					on:click={() => {
						isShowingCreateModal = true;
						newType = 'visited';
					}}
				>
					Visited Adventure</button
				>
				<!-- <button
			class="btn btn-primary"
			on:click={() => (isShowingNewTrip = true)}>Trip Planner</button
		  > -->
			</ul>
		</div>
	</div>
</div>

<div class="drawer lg:drawer-open">
	<input id="my-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />
	<div class="drawer-content">
		<!-- Page content -->
		<h1 class="text-center font-bold text-4xl mb-6">My Adventures</h1>
		{#if adventures.length === 0}
			<NotFound />
		{/if}
		<div class="p-4">
			<button
				class="btn btn-primary drawer-button lg:hidden mb-4 fixed bottom-0 left-0 ml-2 z-[999]"
				on:click={toggleSidebar}
			>
				{sidebarOpen ? 'Close Filters' : 'Open Filters'}
			</button>
			<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
				{#each adventures as adventure}
					<AdventureCard
						type={adventure.type}
						{adventure}
						on:delete={deleteAdventure}
						on:edit={editAdventure}
					/>
				{/each}
			</div>
		</div>
	</div>
	<div class="drawer-side">
		<label for="my-drawer" class="drawer-overlay"></label>
		<ul class="menu p-4 w-80 h-full bg-base-200 text-base-content rounded-lg">
			<!-- Sidebar content here -->
			<h3 class="text-center font-semibold text-lg mb-4">Adventure Types</h3>
			<div class="form-control">
				<form action="?/get" method="post" use:enhance={handleSubmit}>
					<label class="label cursor-pointer">
						<span class="label-text">Completed</span>
						<input
							type="checkbox"
							name="visited"
							id="visited"
							class="checkbox checkbox-primary"
							checked
						/>
					</label>
					<label class="label cursor-pointer">
						<span class="label-text">Planned</span>
						<input
							type="checkbox"
							id="planned"
							name="planned"
							class="checkbox checkbox-primary"
							checked
						/>
					</label>
					<label class="label cursor-pointer">
						<span class="label-text">Featured</span>
						<input
							type="checkbox"
							id="featured"
							name="featured"
							class="checkbox checkbox-primary"
						/>
					</label>

					<button type="submit" class="btn btn-primary mt-4">Filter</button>
					<div class="divider"></div>
					<h3 class="text-center font-semibold text-lg mb-4">Sort</h3>
					<label for="name-asc">Name ASC</label>
					<input
						type="radio"
						name="name"
						id="name-asc"
						class="radio radio-primary"
						checked
						on:click={() => sort({ attribute: 'name', order: 'asc' })}
					/>
					<label for="name-desc">Name DESC</label>
					<input
						type="radio"
						name="name"
						id="name-desc"
						class="radio radio-primary"
						on:click={() => sort({ attribute: 'name', order: 'desc' })}
					/>
				</form>
			</div>
		</ul>
	</div>
</div>
