<script lang="ts">
	import { enhance, deserialize } from '$app/forms';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import EditAdventure from '$lib/components/EditAdventure.svelte';
	import NewAdventure from '$lib/components/NewAdventure.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure } from '$lib/types';

	import Plus from '~icons/mdi/plus';

	export let data: any;
	console.log(data);

	let adventures: Adventure[] = data.props.adventures || [];

	let currentSort = { attribute: 'name', order: 'asc' };

	let isShowingCreateModal: boolean = false;
	let newType: string = '';

	let resultsPerPage: number = 10;

	let currentView: string = 'cards';

	let next: string | null = data.props.next || null;
	let previous: string | null = data.props.previous || null;
	let count = data.props.count || 0;
	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = 1;

	function handleChangePage() {
		return async ({ result }: any) => {
			if (result.type === 'success') {
				console.log(result.data);
				adventures = result.data.body.adventures as Adventure[];
				next = result.data.body.next;
				previous = result.data.body.previous;
				count = result.data.body.count;
				currentPage = result.data.body.page;
				totalPages = Math.ceil(count / resultsPerPage);
			}
		};
	}

	function handleSubmit() {
		return async ({ result, update }: any) => {
			// First, call the update function with reset: false
			update({ reset: false });

			// Then, handle the result
			if (result.type === 'success') {
				if (result.data) {
					// console.log(result.data);
					adventures = result.data.adventures as Adventure[];
					next = result.data.next;
					previous = result.data.previous;
					count = result.data.count;
					totalPages = Math.ceil(count / resultsPerPage);
					currentPage = 1;

					console.log(next);
				}
			}
		};
	}

	function sort({ attribute, order }: { attribute: string; order: string }) {
		currentSort.attribute = attribute;
		currentSort.order = order;
		if (attribute === 'name') {
			if (order === 'asc') {
				adventures = adventures.sort((a, b) => b.name.localeCompare(a.name));
			} else {
				adventures = adventures.sort((a, b) => a.name.localeCompare(b.name));
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
				<button
					class="btn btn-primary"
					on:click={() => {
						isShowingCreateModal = true;
						newType = 'planned';
					}}
				>
					Planned Adventure</button
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
		<p class="text-center">This search returned {count} results.</p>
		{#if adventures.length === 0}
			<NotFound error={undefined} />
		{/if}
		<div class="p-4">
			<button
				class="btn btn-primary drawer-button lg:hidden mb-4 fixed bottom-0 left-0 ml-2 z-[999]"
				on:click={toggleSidebar}
			>
				{sidebarOpen ? 'Close Filters' : 'Open Filters'}
			</button>
			{#if currentView == 'cards'}
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
			{/if}
			{#if currentView == 'table'}
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th>Name</th>
							<th>Date</th>
							<th>Rating</th>
							<th>Type</th>
							<th>Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each adventures as adventure}
							<tr>
								<td>{adventure.name}</td>
								<td>{adventure.date}</td>
								<td>{adventure.rating}</td>
								<td>{adventure.type}</td>
								<td>
									<button
										class="btn btn-sm btn-primary"
										on:click={() => editAdventure(new CustomEvent('edit', { detail: adventure }))}
									>
										Edit
									</button>
									<button
										class="btn btn-sm btn-error"
										on:click={() =>
											deleteAdventure(new CustomEvent('delete', { detail: adventure.id }))}
									>
										Delete
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
			<div class="join flex items-center justify-center mt-4">
				{#if next || previous}
					<div class="join">
						{#each Array.from({ length: totalPages }, (_, i) => i + 1) as page}
							<form action="?/changePage" method="POST" use:enhance={handleChangePage}>
								<input type="hidden" name="page" value={page} />
								<input type="hidden" name="next" value={next} />
								<input type="hidden" name="previous" value={previous} />
								{#if currentPage != page}
									<button class="join-item btn btn-lg">{page}</button>
								{:else}
									<button class="join-item btn btn-lg btn-active">{page}</button>
								{/if}
							</form>
						{/each}
					</div>
				{/if}
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
					<!-- <div class="divider"></div> -->
					<h3 class="text-center font-semibold text-lg mb-4">Sort</h3>
					<p class="text-md font-semibold mb-2">Order Direction</p>
					<label for="asc">Ascending</label>
					<input
						type="radio"
						name="order_direction"
						id="asc"
						class="radio radio-primary"
						checked
						value="asc"
					/>
					<label for="desc">Descending</label>
					<input
						type="radio"
						name="order_direction"
						id="desc"
						value="desc"
						class="radio radio-primary"
					/>
					<br />
					<p class="text-md font-semibold mt-2 mb-2">Order By</p>
					<label for="name">Created At</label>
					<input
						type="radio"
						name="order_by"
						id="created_at"
						class="radio radio-primary"
						checked
						value="created_at"
					/>
					<label for="name">Name</label>
					<input
						type="radio"
						name="order_by"
						id="name"
						class="radio radio-primary"
						checked
						value="name"
					/>
					<label for="date">Date</label>
					<input type="radio" value="date" name="order_by" id="date" class="radio radio-primary" />
					<label for="rating">Rating</label>
					<input
						type="radio"
						value="rating"
						name="order_by"
						id="rating"
						class="radio radio-primary"
					/>
					<br />
					<label class="label cursor-pointer">
						<span class="label-text">Include Collection Adventures</span>
						<input
							type="checkbox"
							name="include_collections"
							id="include_collections"
							class="checkbox checkbox-primary"
						/>
					</label>
					<button type="submit" class="btn btn-primary mt-4">Filter</button>
				</form>
				<div class="divider"></div>
				<h3 class="text-center font-semibold text-lg mb-4">View</h3>
				<div class="join">
					<input
						class="join-item btn-neutral btn"
						type="radio"
						name="options"
						aria-label="Cards"
						on:click={() => (currentView = 'cards')}
						checked
					/>
					<input
						class="join-item btn btn-neutral"
						type="radio"
						name="options"
						aria-label="Table"
						on:click={() => (currentView = 'table')}
					/>
				</div>
			</div>
		</ul>
	</div>
</div>
